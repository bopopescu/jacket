# Copyright 2015 OpenStack Foundation
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

# This package got introduced during the Mitaka cycle in 2015 to
# have a central place where the config options of Nova can be maintained.
# For more background see the blueprint "centralize-config-options"

from oslo_config import cfg

# from compute.conf import api
# from compute.conf import api_database
from jacket.compute.conf import availability_zone
# from compute.conf import aws
# from compute.conf import barbican
# from compute.conf import base
from jacket.compute.conf import cells
from jacket.compute.conf import cert
# from compute.conf import cinder
# from compute.conf import cloudpipe
from jacket.compute.conf import compute
from jacket.compute.conf import conductor
# from compute.conf import configdrive
# from compute.conf import console
# from compute.conf import cors
# from compute.conf import cors.subdomain
# from compute.conf import crypto
# from compute.conf import database
# from compute.conf import disk
from jacket.compute.conf import ephemeral_storage
# from compute.conf import floating_ip
# from compute.conf import glance
# from compute.conf import guestfs
# from compute.conf import host
# from compute.conf import hyperv
# from compute.conf import image
# from compute.conf import imagecache
# from compute.conf import image_file_url
from jacket.compute.conf import ironic
# from compute.conf import keymgr
# from compute.conf import keystone_authtoken
# from compute.conf import libvirt
# from compute.conf import matchmaker_redis
# from compute.conf import metadata
# from compute.conf import metrics
# from compute.conf import network
# from compute.conf import neutron
# from compute.conf import notification
# from compute.conf import osapi_v21
from jacket.compute.conf import pci
# from compute.conf import rdp
from jacket.compute.conf import scheduler
# from compute.conf import security
from jacket.compute.conf import serial_console
# from compute.conf import spice
# from compute.conf import ssl
# from compute.conf import trusted_computing
# from compute.conf import upgrade_levels
from jacket.compute.conf import virt
# from compute.conf import vmware
from jacket.compute.conf import vnc
# from compute.conf import volume
# from compute.conf import workarounds
from jacket.compute.conf import wsgi
# from compute.conf import xenserver
# from compute.conf import xvp
# from compute.conf import zookeeper

CONF = cfg.CONF

# api.register_opts(CONF)
# api_database.register_opts(CONF)
availability_zone.register_opts(CONF)
# aws.register_opts(CONF)
# barbican.register_opts(CONF)
# base.register_opts(CONF)
cells.register_opts(CONF)
cert.register_opts(CONF)
# cinder.register_opts(CONF)
# cloudpipe.register_opts(CONF)
compute.register_opts(CONF)
conductor.register_opts(CONF)
# configdrive.register_opts(CONF)
# console.register_opts(CONF)
# cors.register_opts(CONF)
# cors.subdomain.register_opts(CONF)
# crypto.register_opts(CONF)
# database.register_opts(CONF)
# disk.register_opts(CONF)
ephemeral_storage.register_opts(CONF)
# floating_ip.register_opts(CONF)
# glance.register_opts(CONF)
# guestfs.register_opts(CONF)
# host.register_opts(CONF)
# hyperv.register_opts(CONF)
# image.register_opts(CONF)
# imagecache.register_opts(CONF)
# image_file_url.register_opts(CONF)
ironic.register_opts(CONF)
# keymgr.register_opts(CONF)
# keystone_authtoken.register_opts(CONF)
# libvirt.register_opts(CONF)
# matchmaker_redis.register_opts(CONF)
# metadata.register_opts(CONF)
# metrics.register_opts(CONF)
# network.register_opts(CONF)
# neutron.register_opts(CONF)
# notification.register_opts(CONF)
# osapi_v21.register_opts(CONF)
pci.register_opts(CONF)
# rdp.register_opts(CONF)
scheduler.register_opts(CONF)
# security.register_opts(CONF)
serial_console.register_opts(CONF)
# spice.register_opts(CONF)
# ssl.register_opts(CONF)
# trusted_computing.register_opts(CONF)
# upgrade_levels.register_opts(CONF)
virt.register_opts(CONF)
# vmware.register_opts(CONF)
vnc.register_opts(CONF)
# volume.register_opts(CONF)
# workarounds.register_opts(CONF)
wsgi.register_opts(CONF)
# xenserver.register_opts(CONF)
# xvp.register_opts(CONF)
# zookeeper.register_opts(CONF)
