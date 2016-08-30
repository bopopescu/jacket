#!/bin/bash

source /root/keystonerc_admin

HOST_IP=`ip addr |grep inet|grep -v 127.0.0.1|grep -v inet6|grep ens|awk '{print $2}'|tr -d "addr:" | awk -F '/' '{print $1}'`

mysqldbadm="root"
mysqldbpassword="P@ssw0rd"
mysqldbport="3306"
dbbackendhost="${HOST_IP}"

jacketdbname="jacketdb"
jacketapidbname="jacketapidb"
jacketdbuser="jacketdbuser"
jacketdbpass="P@ssw0rd"
jacketsvce="jacket"

jacket_host="${HOST_IP}"

keystonehost="${HOST_IP}"
keystonedomain="default"
keystoneservicestenant="services"
keystoneadminuser="admin"
endpointsregion="RegionOne"

jacketuser="jacket"
jacketpass="P@ssw0rd"

messagebrokerhost="${HOST_IP}"
brokerflavor="rabbitmq"
brokeruser="openstack"
brokerpass="P@ssw0rd"
brokervhost="/openstack"

#keystone中设置jacket
openstack user show $jacketuser | openstack user create --domain $keystonedomain --password $jacketpass --email "root@email" $jacketuser
openstack role add --project $keystoneservicestenant --user $jacketuser $keystoneadminuser

openstack service show $jacketsvce | openstack service create --name $jacketsvce --description "OpenStack jacket service" jacket

openstack endpoint create --region $endpointsregion \
        jacket public http://$jacket_host:9774/v1/%\(tenant_id\)s

openstack endpoint create --region $endpointsregion \
        jacket internal http://$jacket_host:9774/v1/%\(tenant_id\)s

openstack endpoint create --region $endpointsregion \
        jacket admin http://$jacket_host:9774/v1/%\(tenant_id\)s



#  数据库部署
mysqlcommand="mysql --port=$mysqldbport --password=$mysqldbpassword --user=$mysqldbadm --host=$dbbackendhost"

echo "CREATE DATABASE IF NOT EXISTS $jacketdbname default character set utf8;"|$mysqlcommand
echo "GRANT ALL ON $jacketdbname.* TO '$jacketdbuser'@'%' IDENTIFIED BY '$jacketdbpass';"|$mysqlcommand
echo "GRANT ALL ON $jacketdbname.* TO '$jacketdbuser'@'localhost' IDENTIFIED BY '$jacketdbpass';"|$mysqlcommand
echo "GRANT ALL ON $jacketdbname.* TO '$jacketdbuser'@'$jackethost' IDENTIFIED BY '$jacketdbpass';"|$mysqlcommand


echo "CREATE DATABASE IF NOT EXISTS $jacketapidbname default character set utf8;"|$mysqlcommand
echo "GRANT ALL ON $jacketapidbname.* TO '$jacketdbuser'@'%' IDENTIFIED BY '$jacketdbpass';"|$mysqlcommand
echo "GRANT ALL ON $jacketapidbname.* TO '$jacketdbuser'@'localhost' IDENTIFIED BY '$jacketdbpass';"|$mysqlcommand
echo "GRANT ALL ON $jacketapidbname.* TO '$jacketdbuser'@'$jackethost' IDENTIFIED BY '$jacketdbpass';"|$mysqlcommand


#jacket-manage db sync

mkdir -p /var/log/jacket

#配置文件的设置
crudini --set /etc/jacket/jacket.conf database connection "mysql+pymysql://${jacketdbuser}:${jacketdbpass}@${dbbackendhost}:${mysqldbport}/${jacketdbname}"
crudini --set /etc/jacket/jacket.conf database retry_interval 10
crudini --set /etc/jacket/jacket.conf database idle_timeout 3600
crudini --set /etc/jacket/jacket.conf database min_pool_size 1
crudini --set /etc/jacket/jacket.conf database max_pool_size 10
crudini --set /etc/jacket/jacket.conf database max_retries 100
crudini --set /etc/jacket/jacket.conf database pool_timeout 10

# api database
crudini --set /etc/jacket/jacket.conf api_database connection "mysql+pymysql://${jacketdbuser}:${jacketdbpass}@${dbbackendhost}:${mysqldbport}/${jacketapidbname}"
crudini --set /etc/jacket/jacket.conf api_database retry_interval 10
crudini --set /etc/jacket/jacket.conf api_database idle_timeout 3600
crudini --set /etc/jacket/jacket.conf api_database min_pool_size 1
crudini --set /etc/jacket/jacket.conf api_database max_pool_size 10
crudini --set /etc/jacket/jacket.conf api_database max_retries 100
crudini --set /etc/jacket/jacket.conf api_database pool_timeout 10


crudini --set /etc/jacket/jacket.conf keystone_authtoken auth_uri http://$keystonehost:5000
crudini --set /etc/jacket/jacket.conf keystone_authtoken auth_url http://$keystonehost:35357
crudini --set /etc/jacket/jacket.conf keystone_authtoken auth_type password
crudini --set /etc/jacket/jacket.conf keystone_authtoken project_domain_name $keystonedomain
crudini --set /etc/jacket/jacket.conf keystone_authtoken user_domain_name $keystonedomain
crudini --set /etc/jacket/jacket.conf keystone_authtoken project_name $keystoneservicestenant
crudini --set /etc/jacket/jacket.conf keystone_authtoken username $jacketuser
crudini --set /etc/jacket/jacket.conf keystone_authtoken password $jacketpass
crudini --set /etc/jacket/jacket.conf keystone_authtoken memcached_servers $keystonehost:11211

crudini --set /etc/jacket/jacket.conf DEFAULT osapi_jacket_listen "${jacket_host}"
crudini --set /etc/jacket/jacket.conf DEFAULT osapi_compute_listen "${jacket_host}"
crudini --set /etc/jacket/jacket.conf DEFAULT metadata_listen "${jacket_host}"
crudini --set /etc/jacket/jacket.conf DEFAULT osapi_volume_listen "${jacket_host}"
crudini --set /etc/jacket/jacket.conf DEFAULT debug "true"
crudini --set /etc/jacket/jacket.conf DEFAULT log_dir "/var/log/jacket"
crudini --set /etc/jacket/jacket.conf wsgi api_paste_config "/etc/jacket/jacket-api-paste.ini"
crudini --set /etc/jacket/jacket.conf DEFAULT image_service jacket.compute.image.glance.GlanceImageService


crudini --set /etc/jacket/jacket.conf DEFAULT rpc_backend rabbit
crudini --set /etc/jacket/jacket.conf oslo_messaging_rabbit rabbit_host $messagebrokerhost
crudini --set /etc/jacket/jacket.conf oslo_messaging_rabbit rabbit_password $brokerpass
crudini --set /etc/jacket/jacket.conf oslo_messaging_rabbit rabbit_userid $brokeruser
crudini --set /etc/jacket/jacket.conf oslo_messaging_rabbit rabbit_port 5672
crudini --set /etc/jacket/jacket.conf oslo_messaging_rabbit rabbit_use_ssl false
crudini --set /etc/jacket/jacket.conf oslo_messaging_rabbit rabbit_virtual_host $brokervhost
crudini --set /etc/jacket/jacket.conf oslo_messaging_rabbit rabbit_max_retries 0
crudini --set /etc/jacket/jacket.conf oslo_messaging_rabbit rabbit_retry_interval 1
crudini --set /etc/jacket/jacket.conf oslo_messaging_rabbit rabbit_ha_queues false

#compute
crudini --set /etc/jacket/jacket.conf DEFAULT compute_driver libvirt.LibvirtDriver
crudini --set /etc/jacket/jacket.conf DEFAULT firewall_driver jacket.compute.virt.firewall.NoopFirewallDriver
crudini --set /etc/jacket/jacket.conf DEFAULT rootwrap_config /etc/jacket/rootwrap.conf
crudini --set /etc/jacket/jacket.conf DEFAULT compute_topic "jacket-worker"
crudini --set /etc/jacket/jacket.conf DEFAULT volume_topic "jacket-worker"

crudini --set /etc/jacket/jacket.conf DEFAULT use_local true


# storage
backend="lvm"
crudini --set /etc/jacket/jacket.conf DEFAULT enabled_backends ${backend}
crudini --set /etc/jacket/jacket.conf ${backend} iscsi_helper tgtadm
crudini --set /etc/jacket/jacket.conf ${backend} iscsi_ip_address ${HOST_IP}
crudini --set /etc/jacket/jacket.conf ${backend} volume_driver jacket.storage.volume.drivers.lvm.LVMVolumeDriver
crudini --set /etc/jacket/jacket.conf ${backend} volumes_dir /var/lib/cinder/volumes
crudini --set /etc/jacket/jacket.conf ${backend} volume_backend_name lvm
crudini --set /etc/jacket/jacket.conf ${backend} volume_group cinder-volumes


