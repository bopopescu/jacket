"""Handles all processes to clouds.

The :py:class:`WorkerManager` class is a :py:class:`jacket.manager.Manager` that
handles RPC calls relating to creating instances.  It is responsible for
building a disk image, launching it via the underlying virtualization driver,
responding to calls to check its state, attaching persistent storage, and
terminating it.

"""


import functools
import eventlet.event

from oslo_utils import timeutils

from jacket.compute.cloud import task_states
from jacket.compute.cloud import vm_states

from jacket.i18n import _
from jacket.i18n import _LE
from jacket.i18n import _LI
from jacket.i18n import _LW
from jacket.objects import compute as objects
from jacket.compute import utils
from jacket.compute.cloud import power_state
from jacket.compute.cloud.manager import ComputeVirtAPI
from jacket.compute.virt import driver

from oslo_config import cfg
from oslo_log import log as logging
import oslo_messaging as messaging
from oslo_service import periodic_task

from jacket.compute import exception
from jacket.compute import network
from jacket.compute.cloud import resource_tracker
from jacket import rpc
from jacket import manager

CONF = cfg.CONF
CONF.import_opt('heal_instance_info_cache_interval', 'jacket.compute.cloud.manager')
CONF.import_opt('instance_build_timeout', 'jacket.compute.cloud.manager')
CONF.import_opt('reboot_timeout', 'jacket.compute.cloud.manager')
CONF.import_opt('rescue_timeout', 'jacket.compute.cloud.manager')
CONF.import_opt('resize_confirm_window', 'jacket.compute.cloud.manager')
CONF.import_opt('shelved_offload_time', 'jacket.compute.cloud.manager')
CONF.import_opt('sync_power_state_interval', 'jacket.compute.cloud.manager')
CONF.import_opt('reclaim_instance_interval', 'jacket.compute.cloud.manager')
CONF.import_opt('running_deleted_instance_poll_interval', 'jacket.compute.cloud.manager')
CONF.import_opt('running_deleted_instance_action', 'jacket.compute.cloud.manager')
CONF.import_opt('instance_delete_interval', 'jacket.compute.cloud.manager')
CONF.import_opt('host', 'jacket.compute.cloud.manager')
CONF.import_opt('host', 'jacket.compute.netconf')


LOG = logging.getLogger(__name__)

get_notifier = functools.partial(rpc.get_notifier, service='controller')
wrap_exception = functools.partial(exception.wrap_exception,
                                   get_notifier=get_notifier)


class ControllerManager(manager.Manager):
    """Manages the running instances from creation to destruction."""
    RPC_API_VERSION = '1.0'

    target = messaging.Target(version="1.0")

    def __init__(self, compute_driver=None, *args, **kwargs):
        """Load configuration options and connect to the cloud."""
        self.network_api = network.API()
        self.virtapi = ComputeVirtAPI(self)
        self.driver = driver.load_compute_driver(self.virtapi, compute_driver)
        self._resource_tracker_dict = {}
        self._sync_power_pool = eventlet.GreenPool()
        self._syncs_in_progress = {}

        super(ControllerManager, self).__init__(service_name="controller", *args, **kwargs)

    def init_host(self):
        super(ControllerManager, self).init_host()

    def cleanup_host(self):
        super(ControllerManager, self).cleanup_host()

    def pre_start_hook(self):
        super(ControllerManager, self).pre_start_hook()

    def post_start_hook(self):
        super(ControllerManager, self).post_start_hook()

    def reset(self):
        super(ControllerManager, self).reset()

    @periodic_task.periodic_task
    def _check_instance_build_time(self, context):
        """Ensure that instances are not stuck in build."""
        timeout = CONF.instance_build_timeout
        if timeout == 0:
            return

        filters = {'vm_state': vm_states.BUILDING,
                   'host': self.host}

        building_insts = objects.InstanceList.get_by_filters(context,
                                                             filters, expected_attrs=[], use_subordinate=True)

        for instance in building_insts:
            if timeutils.is_older_than(instance.created_at, timeout):
                self._set_instance_obj_error_state(context, instance)
                LOG.warning(_LW("Instance build timed out. Set to error "
                                "state."), instance=instance)

    @periodic_task.periodic_task(
        spacing=CONF.heal_instance_info_cache_interval)
    def _heal_instance_info_cache(self, context):
        """Called periodically.  On every call, try to update the
        info_cache's network information for another instance by
        calling to the network manager.

        This is implemented by keeping a cache of uuids of instances
        that live on this host.  On each call, we pop one off of a
        list, pull the DB record, and try the call to the network API.
        If anything errors don't fail, as it's possible the instance
        has been deleted, etc.
        """
        heal_interval = CONF.heal_instance_info_cache_interval
        if not heal_interval:
            return

        instance_uuids = getattr(self, '_instance_uuids_to_heal', [])
        instance = None

        LOG.debug('Starting heal instance info cache')

        if not instance_uuids:
            # The list of instances to heal is empty so rebuild it
            LOG.debug('Rebuilding the list of instances to heal')
            db_instances = objects.InstanceList.get_by_host(
                context, self.host, expected_attrs=[], use_subordinate=True)
            for inst in db_instances:
                # We don't want to refresh the cache for instances
                # which are building or deleting so don't put them
                # in the list. If they are building they will get
                # added to the list next time we build it.
                if (inst.vm_state == vm_states.BUILDING):
                    LOG.debug('Skipping network cache update for instance '
                              'because it is Building.', instance=inst)
                    continue
                if (inst.task_state == task_states.DELETING):
                    LOG.debug('Skipping network cache update for instance '
                              'because it is being deleted.', instance=inst)
                    continue

                if not instance:
                    # Save the first one we find so we don't
                    # have to get it again
                    instance = inst
                else:
                    instance_uuids.append(inst['uuid'])

            self._instance_uuids_to_heal = instance_uuids
        else:
            # Find the next valid instance on the list
            while instance_uuids:
                try:
                    inst = objects.Instance.get_by_uuid(
                        context, instance_uuids.pop(0),
                        expected_attrs=['system_metadata', 'info_cache',
                                        'flavor'],
                        use_subordinate=True)
                except exception.InstanceNotFound:
                    # Instance is gone.  Try to grab another.
                    continue

                # Check the instance hasn't been migrated
                if inst.host != self.host:
                    LOG.debug('Skipping network cache update for instance '
                              'because it has been migrated to another '
                              'host.', instance=inst)
                # Check the instance isn't being deleting
                elif inst.task_state == task_states.DELETING:
                    LOG.debug('Skipping network cache update for instance '
                              'because it is being deleted.', instance=inst)
                else:
                    instance = inst
                    break

        if instance:
            # We have an instance now to refresh
            try:
                # Call to network API to get instance info.. this will
                # force an update to the instance's info_cache
                self.network_api.get_instance_nw_info(context, instance)
                LOG.debug('Updated the network info_cache for instance',
                          instance=instance)
            except exception.InstanceNotFound:
                # Instance is gone.
                LOG.debug('Instance no longer exists. Unable to refresh',
                          instance=instance)
                return
            except exception.InstanceInfoCacheNotFound:
                # InstanceInfoCache is gone.
                LOG.debug('InstanceInfoCache no longer exists. '
                          'Unable to refresh', instance=instance)
            except Exception:
                LOG.error(_LE('An error occurred while refreshing the network '
                              'cache.'), instance=instance, exc_info=True)
        else:
            LOG.debug("Didn't find any instances for network info cache "
                      "update.")

    @periodic_task.periodic_task
    def _poll_rebooting_instances(self, context):
        if CONF.reboot_timeout > 0:
            filters = {'task_state':
                           [task_states.REBOOTING,
                            task_states.REBOOT_STARTED,
                            task_states.REBOOT_PENDING],
                       'host': self.host}
            rebooting = objects.InstanceList.get_by_filters(
                context, filters, expected_attrs=[], use_subordinate=True)

            to_poll = []
            for instance in rebooting:
                if timeutils.is_older_than(instance.updated_at,
                                           CONF.reboot_timeout):
                    to_poll.append(instance)

            self.driver.poll_rebooting_instances(CONF.reboot_timeout, to_poll)

    @periodic_task.periodic_task
    def _poll_rescued_instances(self, context):
        if CONF.rescue_timeout > 0:
            filters = {'vm_state': vm_states.RESCUED,
                       'host': self.host}
            rescued_instances = objects.InstanceList.get_by_filters(
                context, filters, expected_attrs=["system_metadata"],
                use_subordinate=True)

            to_unrescue = []
            for instance in rescued_instances:
                if timeutils.is_older_than(instance.launched_at,
                                           CONF.rescue_timeout):
                    to_unrescue.append(instance)

            for instance in to_unrescue:
                self.compute_api.unrescue(context, instance)

    @periodic_task.periodic_task
    def _poll_unconfirmed_resizes(self, context):
        if CONF.resize_confirm_window == 0:
            return

        migrations = objects.MigrationList.get_unconfirmed_by_dest_compute(
            context, CONF.resize_confirm_window, self.host,
            use_subordinate=True)

        migrations_info = dict(migration_count=len(migrations),
                               confirm_window=CONF.resize_confirm_window)

        if migrations_info["migration_count"] > 0:
            LOG.info(_LI("Found %(migration_count)d unconfirmed migrations "
                         "older than %(confirm_window)d seconds"),
                     migrations_info)

        def _set_migration_to_error(migration, reason, **kwargs):
            LOG.warning(_LW("Setting migration %(migration_id)s to error: "
                            "%(reason)s"),
                        {'migration_id': migration['id'], 'reason': reason},
                        **kwargs)
            migration.status = 'error'
            with migration.obj_as_admin():
                migration.save()

        for migration in migrations:
            instance_uuid = migration.instance_uuid
            LOG.info(_LI("Automatically confirming migration "
                         "%(migration_id)s for instance %(instance_uuid)s"),
                     {'migration_id': migration.id,
                      'instance_uuid': instance_uuid})
            expected_attrs = ['metadata', 'system_metadata']
            try:
                instance = objects.Instance.get_by_uuid(context,
                                                        instance_uuid, expected_attrs=expected_attrs,
                                                        use_subordinate=True)
            except exception.InstanceNotFound:
                reason = (_("Instance %s not found") %
                          instance_uuid)
                _set_migration_to_error(migration, reason)
                continue
            if instance.vm_state == vm_states.ERROR:
                reason = _("In ERROR state")
                _set_migration_to_error(migration, reason,
                                        instance=instance)
                continue
            # race condition: The instance in DELETING state should not be
            # set the migration state to error, otherwise the instance in
            # to be deleted which is in RESIZED state
            # will not be able to confirm resize
            if instance.task_state in [task_states.DELETING,
                                       task_states.SOFT_DELETING]:
                msg = ("Instance being deleted or soft deleted during resize "
                       "confirmation. Skipping.")
                LOG.debug(msg, instance=instance)
                continue

            # race condition: This condition is hit when this method is
            # called between the save of the migration record with a status of
            # finished and the save of the instance object with a state of
            # RESIZED. The migration record should not be set to error.
            if instance.task_state == task_states.RESIZE_FINISH:
                msg = ("Instance still resizing during resize "
                       "confirmation. Skipping.")
                LOG.debug(msg, instance=instance)
                continue

            vm_state = instance.vm_state
            task_state = instance.task_state
            if vm_state != vm_states.RESIZED or task_state is not None:
                reason = (_("In states %(vm_state)s/%(task_state)s, not "
                            "RESIZED/None") %
                          {'vm_state': vm_state,
                           'task_state': task_state})
                _set_migration_to_error(migration, reason,
                                        instance=instance)
                continue
            try:
                self.compute_api.confirm_resize(context, instance,
                                                migration=migration)
            except Exception as e:
                LOG.info(_LI("Error auto-confirming resize: %s. "
                             "Will retry later."),
                         e, instance=instance)

    @periodic_task.periodic_task(spacing=CONF.shelved_poll_interval)
    def _poll_shelved_instances(self, context):

        if CONF.shelved_offload_time <= 0:
            return

        filters = {'vm_state': vm_states.SHELVED,
                   'task_state': None,
                   'host': self.host}
        shelved_instances = objects.InstanceList.get_by_filters(
            context, filters=filters, expected_attrs=['system_metadata'],
            use_subordinate=True)

        to_gc = []
        for instance in shelved_instances:
            sys_meta = instance.system_metadata
            shelved_at = timeutils.parse_strtime(sys_meta['shelved_at'])
            if timeutils.is_older_than(shelved_at, CONF.shelved_offload_time):
                to_gc.append(instance)

        for instance in to_gc:
            try:
                instance.task_state = task_states.SHELVING_OFFLOADING
                instance.save(expected_task_state=(None,))
                self.shelve_offload_instance(context, instance,
                                             clean_shutdown=False)
            except Exception:
                LOG.exception(_LE('Periodic task failed to offload instance.'),
                              instance=instance)

    @periodic_task.periodic_task(spacing=CONF.sync_power_state_interval,
                                 run_immediately=True)
    def _sync_power_states(self, context):
        """Align power states between the database and the hypervisor.

        To sync power state data we make a DB call to get the number of
        virtual machines known by the hypervisor and if the number matches the
        number of virtual machines known by the database, we proceed in a lazy
        loop, one database record at a time, checking if the hypervisor has the
        same power state as is in the database.
        """
        db_instances = objects.InstanceList.get_by_host(context, self.host,
                                                        expected_attrs=[],
                                                        use_subordinate=True)

        #num_vm_instances = self.driver.get_num_instances()
        vm_instances_stats = self.driver.list_instances_stats()
        num_vm_instances = len(vm_instances_stats)
        num_db_instances = len(db_instances)

        if num_vm_instances != num_db_instances:
            LOG.warning(_LW("While synchronizing instance power states, found "
                            "%(num_db_instances)s instances in the database "
                            "and %(num_vm_instances)s instances on the "
                            "hypervisor."),
                        {'num_db_instances': num_db_instances,
                         'num_vm_instances': num_vm_instances})

        def _sync(db_instance, state):
            # NOTE(melwitt): This must be synchronized as we query state from
            #                two separate sources, the driver and the database.
            #                They are set (in stop_instance) and read, in sync.
            @utils.synchronized(db_instance.uuid)
            def query_driver_power_state_and_sync():
                self._query_driver_power_state_and_sync(context, db_instance, state)

            try:
                query_driver_power_state_and_sync()
            except Exception:
                LOG.exception(_LE("Periodic sync_power_state task had an "
                                  "error while processing an instance."),
                              instance=db_instance)

            self._syncs_in_progress.pop(db_instance.uuid)

        for db_instance in db_instances:
            # process syncs asynchronously - don't want instance locking to
            # block entire periodic task thread
            uuid = db_instance.uuid
            if uuid in self._syncs_in_progress:
                LOG.debug('Sync already in progress for %s' % uuid)
            else:
                LOG.debug('Triggering sync for uuid %s' % uuid)
                provider_instance_id = self._get_provider_instance_id(uuid)
                provider_instance_state = vm_instances_stats.get(provider_instance_id,
                                                                 power_state.NOSTATE)

                self._syncs_in_progress[uuid] = True
                self._sync_power_pool.spawn_n(_sync, db_instance, provider_instance_state)

    def _query_driver_power_state_and_sync(self, context, db_instance, vm_power_state):
        if db_instance.task_state is not None:
            LOG.info(_LI("During sync_power_state the instance has a "
                         "pending task (%(task)s). Skip."),
                     {'task': db_instance.task_state}, instance=db_instance)
            return
        # No pending tasks. Now try to figure out the real vm_power_state.
        # try:
        #     vm_instance = self.driver.get_info(db_instance)
        #     vm_power_state = vm_instance.state
        # except exception.InstanceNotFound:
        #     vm_power_state = power_state.NOSTATE
        # Note(maoy): the above get_info call might take a long time,
        # for example, because of a broken libvirt driver.
        try:
            self._sync_instance_power_state(context,
                                            db_instance,
                                            vm_power_state,
                                            use_subordinate=True)
        except exception.InstanceNotFound:
            # NOTE(hanlind): If the instance gets deleted during sync,
            # silently ignore.
            pass

    def _sync_instance_power_state(self, context, db_instance, vm_power_state,
                                   use_subordinate=False):
        """Align instance power state between the database and hypervisor.

        If the instance is not found on the hypervisor, but is in the database,
        then a stop() API will be called on the instance.
        """

        # We re-query the DB to get the latest instance info to minimize
        # (not eliminate) race condition.
        db_instance.refresh(use_subordinate=use_subordinate)
        db_power_state = db_instance.power_state
        vm_state = db_instance.vm_state

        if self.host != db_instance.host:
            # on the sending end of cloud-cloud _sync_power_state
            # may have yielded to the greenthread performing a live
            # migration; this in turn has changed the resident-host
            # for the VM; However, the instance is still active, it
            # is just in the process of migrating to another host.
            # This implies that the cloud source must relinquish
            # control to the cloud destination.
            LOG.info(_LI("During the sync_power process the "
                         "instance has moved from "
                         "host %(src)s to host %(dst)s"),
                     {'src': db_instance.host,
                      'dst': self.host},
                     instance=db_instance)
            return
        elif db_instance.task_state is not None:
            # on the receiving end of cloud-cloud, it could happen
            # that the DB instance already report the new resident
            # but the actual VM has not showed up on the hypervisor
            # yet. In this case, let's allow the loop to continue
            # and run the state sync in a later round
            LOG.info(_LI("During sync_power_state the instance has a "
                         "pending task (%(task)s). Skip."),
                     {'task': db_instance.task_state},
                     instance=db_instance)
            return

        orig_db_power_state = db_power_state
        if vm_power_state != db_power_state:
            LOG.info(_LI('During _sync_instance_power_state the DB '
                         'power_state (%(db_power_state)s) does not match '
                         'the vm_power_state from the hypervisor '
                         '(%(vm_power_state)s). Updating power_state in the '
                         'DB to match the hypervisor.'),
                     {'db_power_state': db_power_state,
                      'vm_power_state': vm_power_state},
                     instance=db_instance)
            # power_state is always updated from hypervisor to db
            db_instance.power_state = vm_power_state
            db_instance.save()
            db_power_state = vm_power_state

        # Note(maoy): Now resolve the discrepancy between vm_state and
        # vm_power_state. We go through all possible vm_states.
        if vm_state in (vm_states.BUILDING,
                        vm_states.RESCUED,
                        vm_states.RESIZED,
                        vm_states.SUSPENDED,
                        vm_states.ERROR):
            # TODO(maoy): we ignore these vm_state for now.
            pass
        elif vm_state == vm_states.ACTIVE:
            # The only rational power state should be RUNNING
            if vm_power_state in (power_state.SHUTDOWN,
                                  power_state.CRASHED):
                LOG.warning(_LW("Instance shutdown by itself. Calling the "
                                "stop API. Current vm_state: %(vm_state)s, "
                                "current task_state: %(task_state)s, "
                                "original DB power_state: %(db_power_state)s, "
                                "current VM power_state: %(vm_power_state)s"),
                            {'vm_state': vm_state,
                             'task_state': db_instance.task_state,
                             'db_power_state': orig_db_power_state,
                             'vm_power_state': vm_power_state},
                            instance=db_instance)
                try:
                    # Note(maoy): here we call the API instead of
                    # brutally updating the vm_state in the database
                    # to allow all the hooks and checks to be performed.
                    if db_instance.shutdown_terminate:
                        self.compute_api.delete(context, db_instance)
                    else:
                        self.compute_api.stop(context, db_instance)
                except Exception:
                    # Note(maoy): there is no need to propagate the error
                    # because the same power_state will be retrieved next
                    # time and retried.
                    # For example, there might be another task scheduled.
                    LOG.exception(_LE("error during stop() in "
                                      "sync_power_state."),
                                  instance=db_instance)
            elif vm_power_state == power_state.SUSPENDED:
                LOG.warning(_LW("Instance is suspended unexpectedly. Calling "
                                "the stop API."), instance=db_instance)
                try:
                    self.compute_api.stop(context, db_instance)
                except Exception:
                    LOG.exception(_LE("error during stop() in "
                                      "sync_power_state."),
                                  instance=db_instance)
            elif vm_power_state == power_state.PAUSED:
                # Note(maoy): a VM may get into the paused state not only
                # because the user request via API calls, but also
                # due to (temporary) external instrumentations.
                # Before the virt layer can reliably report the reason,
                # we simply ignore the state discrepancy. In many cases,
                # the VM state will go back to running after the external
                # instrumentation is done. See bug 1097806 for details.
                LOG.warning(_LW("Instance is paused unexpectedly. Ignore."),
                            instance=db_instance)
            elif vm_power_state == power_state.NOSTATE:
                # Occasionally, depending on the status of the hypervisor,
                # which could be restarting for example, an instance may
                # not be found.  Therefore just log the condition.
                LOG.warning(_LW("Instance is unexpectedly not found. Ignore."),
                            instance=db_instance)
        elif vm_state == vm_states.STOPPED:
            if vm_power_state not in (power_state.NOSTATE,
                                      power_state.SHUTDOWN,
                                      power_state.CRASHED):
                LOG.warning(_LW("Instance is not stopped. Calling "
                                "the stop API. Current vm_state: %(vm_state)s,"
                                " current task_state: %(task_state)s, "
                                "original DB power_state: %(db_power_state)s, "
                                "current VM power_state: %(vm_power_state)s"),
                            {'vm_state': vm_state,
                             'task_state': db_instance.task_state,
                             'db_power_state': orig_db_power_state,
                             'vm_power_state': vm_power_state},
                            instance=db_instance)
                try:
                    # NOTE(russellb) Force the stop, because normally the
                    # cloud API would not allow an attempt to stop a stopped
                    # instance.
                    self.compute_api.force_stop(context, db_instance)
                except Exception:
                    LOG.exception(_LE("error during stop() in "
                                      "sync_power_state."),
                                  instance=db_instance)
        elif vm_state == vm_states.PAUSED:
            if vm_power_state in (power_state.SHUTDOWN,
                                  power_state.CRASHED):
                LOG.warning(_LW("Paused instance shutdown by itself. Calling "
                                "the stop API."), instance=db_instance)
                try:
                    self.compute_api.force_stop(context, db_instance)
                except Exception:
                    LOG.exception(_LE("error during stop() in "
                                      "sync_power_state."),
                                  instance=db_instance)
        elif vm_state in (vm_states.SOFT_DELETED,
                          vm_states.DELETED):
            if vm_power_state not in (power_state.NOSTATE,
                                      power_state.SHUTDOWN):
                # Note(maoy): this should be taken care of periodically in
                # _cleanup_running_deleted_instances().
                LOG.warning(_LW("Instance is not (soft-)deleted."),
                            instance=db_instance)

    @periodic_task.periodic_task
    def _reclaim_queued_deletes(self, context):
        """Reclaim instances that are queued for deletion."""
        interval = CONF.reclaim_instance_interval
        if interval <= 0:
            LOG.debug("CONF.reclaim_instance_interval <= 0, skipping...")
            return

        # TODO(comstud, jichenjc): Dummy quota object for now See bug 1296414.
        # The only case that the quota might be inconsistent is
        # the cloud node died between set instance state to SOFT_DELETED
        # and quota commit to DB. When cloud node starts again
        # it will have no idea the reservation is committed or not or even
        # expired, since it's a rare case, so marked as todo.
        quotas = objects.Quotas.from_reservations(context, None)

        filters = {'vm_state': vm_states.SOFT_DELETED,
                   'task_state': None,
                   'host': self.host}
        instances = objects.InstanceList.get_by_filters(
            context, filters,
            expected_attrs=objects.instance.INSTANCE_DEFAULT_FIELDS,
            use_subordinate=True)
        for instance in instances:
            if self._deleted_old_enough(instance, interval):
                bdms = objects.BlockDeviceMappingList.get_by_instance_uuid(
                    context, instance.uuid)
                LOG.info(_LI('Reclaiming deleted instance'), instance=instance)
                try:
                    self._delete_instance(context, instance, bdms, quotas)
                except Exception as e:
                    LOG.warning(_LW("Periodic reclaim failed to delete "
                                    "instance: %s"),
                                e, instance=instance)

    @periodic_task.periodic_task(
        spacing=CONF.running_deleted_instance_poll_interval)
    def _cleanup_running_deleted_instances(self, context):
        """Cleanup any instances which are erroneously still running after
        having been deleted.

        Valid actions to take are:

            1. noop - do nothing
            2. log - log which instances are erroneously running
            3. reap - shutdown and cleanup any erroneously running instances
            4. shutdown - power off *and disable* any erroneously running
                          instances

        The use-case for this cleanup task is: for various reasons, it may be
        possible for the database to show an instance as deleted but for that
        instance to still be running on a host machine (see bug
        https://bugs.launchpad.net/cloud/+bug/911366).

        This cleanup task is a cross-hypervisor utility for finding these
        zombied instances and either logging the discrepancy (likely what you
        should do in production), or automatically reaping the instances (more
        appropriate for dev environments).
        """
        action = CONF.running_deleted_instance_action

        if action == "noop":
            return

        # NOTE(sirp): admin contexts don't ordinarily return deleted records
        with utils.temporary_mutation(context, read_deleted="yes"):
            for instance in self._running_deleted_instances(context):
                if action == "log":
                    LOG.warning(_LW("Detected instance with name label "
                                    "'%s' which is marked as "
                                    "DELETED but still present on host."),
                                instance.name, instance=instance)

                elif action == 'shutdown':
                    LOG.info(_LI("Powering off instance with name label "
                                 "'%s' which is marked as "
                                 "DELETED but still present on host."),
                             instance.name, instance=instance)
                    try:
                        try:
                            # disable starting the instance
                            self.driver.set_bootable(instance, False)
                        except NotImplementedError:
                            LOG.debug("set_bootable is not implemented "
                                      "for the current driver")
                        # and power it off
                        self.driver.power_off(instance)
                    except Exception:
                        msg = _LW("Failed to power off instance")
                        LOG.warn(msg, instance=instance, exc_info=True)

                elif action == 'reap':
                    LOG.info(_LI("Destroying instance with name label "
                                 "'%s' which is marked as "
                                 "DELETED but still present on host."),
                             instance.name, instance=instance)
                    bdms = objects.BlockDeviceMappingList.get_by_instance_uuid(
                        context, instance.uuid, use_subordinate=True)
                    self.instance_events.clear_events_for_instance(instance)
                    try:
                        self._shutdown_instance(context, instance, bdms,
                                                notify=False)
                        self._cleanup_volumes(context, instance.uuid, bdms)
                    except Exception as e:
                        LOG.warning(_LW("Periodic cleanup failed to delete "
                                        "instance: %s"),
                                    e, instance=instance)
                else:
                    raise Exception(_("Unrecognized value '%s'"
                                      " for CONF.running_deleted_"
                                      "instance_action") % action)

    @periodic_task.periodic_task(spacing=CONF.instance_delete_interval)
    def _cleanup_incomplete_migrations(self, context):
        """Delete instance files on failed resize/revert-resize operation

        During resize/revert-resize operation, if that instance gets deleted
        in-between then instance files might remain either on source or
        destination cloud node because of race condition.
        """
        LOG.debug('Cleaning up deleted instances with incomplete migration ')
        migration_filters = {'host': CONF.host,
                             'status': 'error'}
        migrations = objects.MigrationList.get_by_filters(context,
                                                          migration_filters)

        if not migrations:
            return

        inst_uuid_from_migrations = set([migration.instance_uuid for migration
                                         in migrations])

        inst_filters = {'deleted': True, 'soft_deleted': False,
                        'uuid': inst_uuid_from_migrations}
        attrs = ['info_cache', 'security_groups', 'system_metadata']
        with utils.temporary_mutation(context, read_deleted='yes'):
            instances = objects.InstanceList.get_by_filters(
                context, inst_filters, expected_attrs=attrs, use_subordinate=True)

        for instance in instances:
            if instance.host != CONF.host:
                for migration in migrations:
                    if instance.uuid == migration.instance_uuid:
                        # Delete instance files if not cleanup properly either
                        # from the source or destination cloud nodes when
                        # the instance is deleted during resizing.
                        self.driver.delete_instance_files(instance)
                        try:
                            migration.status = 'failed'
                            with migration.obj_as_admin():
                                migration.save()
                        except exception.MigrationNotFound:
                            LOG.warning(_LW("Migration %s is not found."),
                                        migration.id, context=context,
                                        instance=instance)
                        break

    @periodic_task.periodic_task(spacing=CONF.update_resources_interval)
    def update_available_resource(self, context):
        """See driver.get_available_resource()

        Periodic process that keeps that the compute host's understanding of
        resource availability and usage in sync with the underlying hypervisor.

        :param context: security context
        """
        new_resource_tracker_dict = {}

        compute_nodes_in_db = self._get_compute_nodes_in_db(context,
                                                            use_subordinate=True)
        nodenames = set(self.driver.get_available_nodes())
        for nodename in nodenames:
            rt = self._get_resource_tracker(nodename)
            try:
                rt.update_available_resource(context)
            except exception.ComputeHostNotFound:
                # NOTE(comstud): We can get to this case if a node was
                # marked 'deleted' in the DB and then re-added with a
                # different auto-increment id. The cached resource
                # tracker tried to update a deleted record and failed.
                # Don't add this resource tracker to the new dict, so
                # that this will resolve itself on the next run.
                LOG.info(_LI("Compute node '%s' not found in "
                             "update_available_resource."), nodename)
                continue
            except Exception:
                LOG.exception(_LE("Error updating resources for node "
                                  "%(node)s."), {'node': nodename})
            new_resource_tracker_dict[nodename] = rt

        # NOTE(comstud): Replace the RT cache before looping through
        # compute nodes to delete below, as we can end up doing greenthread
        # switches there. Best to have everyone using the newest cache
        # ASAP.
        self._resource_tracker_dict = new_resource_tracker_dict

        # Delete orphan compute node not reported by driver but still in db
        for cn in compute_nodes_in_db:
            if cn.hypervisor_hostname not in nodenames:
                LOG.info(_LI("Deleting orphan compute node %s"), cn.id)
                cn.destroy()

    def _get_compute_nodes_in_db(self, context, use_subordinate=False):
        try:
            return objects.ComputeNodeList.get_all_by_host(context, self.host,
                                                           use_subordinate=use_subordinate)
        except exception.NotFound:
            LOG.error(_LE("No compute node record for host %s"), self.host)
            return []

    def _get_resource_tracker(self, nodename):
        rt = self._resource_tracker_dict.get(nodename)
        if not rt:
            if not self.driver.node_is_available(nodename):
                raise exception.NovaException(
                    _("%s is not a valid node managed by this "
                      "compute host.") % nodename)

            rt = resource_tracker.ResourceTracker(self.host,
                                                  self.driver,
                                                  nodename)
            self._resource_tracker_dict[nodename] = rt
        return rt

    def _get_provider_instance_id(self, context, caa_instance_id):
        instance_mapper = self.caa_db_api.instance_mapper_get(context,
                                                              caa_instance_id)
        return instance_mapper.get('provider_instance_id', None)