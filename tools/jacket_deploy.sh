#!/bin/bash

source /root/adminrc

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

# rabbit
messagebrokerhost="${HOST_IP}"
brokerflavor="rabbitmq"
brokeruser="openstack"
brokerpass="P@ssw0rd"
brokervhost="/openstack"

#DEFAULT
virt_type="qemu"
#instances_path="/root/mnt/sdb/instances"
instances_path="/var/lib/jacket/instances"
default_schedule_zone="az2.dc2"
default_availability_zone="az2.dc2"
storage_availability_zone="az2.dc2"
compute_topic="jacket-worker"
volume_topic="jacket-worker"
linuxnet_ovs_integration_bridge="br-int"
use_neutron="True"
image_service="jacket.compute.image.glance.GlanceImageService"
compute_driver="fs.FsComputeDriver"
#compute_driver="libvirt.LibvirtDriver"
firewall_driver="jacket.compute.virt.firewall.NoopFirewallDriver"
rootwrap_config="/etc/jacket/rootwrap.conf"
use_local="True"
enabled_backends="lvm"
log_dir="/var/log/jacket"
enabled_apis="osapi_compute, osapi_volume"

# glance
glance_host="image.az0.dc0.huawei.com"
#glance_port=9292
glance_port=443
glance_protocol="https"
glance_api_insecure="True"
glance_api_servers="https://image.az0.dc0.huawei.com:443"

#volume driver
lvm_type="default"
iscsi_helper="tgtadm"
#volume_driver="jacket.storage.volume.drivers.lvm.LVMVolumeDriver"
volume_driver="jacket.drivers.fs.volume_driver.FsVolumeDriver"
volume_group="cinder-volumes"
volumes_dir="/var/lib/cinder/volumes"
volume_backend_name="lvm"

#cinder
http_timeout=120
api_insecure="True"
endpoint_template="http://${jacket_host}:8776/v2/%(project_id)s"

#keystone_authtoken
auth_url="https://identity.az0.dc0.huawei.com:443/identity/v2.0"
auth_type="password"
project_name="service"
auth_username="jacket"
auth_password="FusionSphere123"
memcached_servers="${jacket_host}:11211"
auth_insecure="True"

#neutron
neutron_url="https://network.az4.dc4.huawei.com:443"
neutron_default_tenant_id="default"
neutron_auth_type="password"
neutron_auth_section="keystone_authtoken"
neutron_auth_url="https://identity.az4.dc4.huawei.com:443/identity/v2.0"
neutron_user_domain_name="default"
neutron_project_domain_name="default"
neutron_region_name="az4.dc4"
neutron_project_name="service"
neutron_auth_username="neutron"
neutron_auth_password="FusionSphere123"
metadata_proxy_shared_secret="FusionSphere123"
service_metadata_proxy="True"
neutron_auth_insecure="True"
integration_bridge="br-int"

#provider_opts
net_data="5cff8ed7-98c5-40a6-95f1-168f07767888"
availability_zone="az2.dc2"
region="az2.dc2"
pwd="FusionSphere123"
base_linux_image="bbe031b2-044d-4bae-a15e-a3dd8f1c7428"
pro_auth_url="https://identity.az2.dc2.huawei.com:443/identity/v2.0"
flavor_map="e8b2f438-b08a-457d-8dce-6cebbcc2640b"
net_api="e8b2f438-b08a-457d-8dce-6cebbcc2640b"
tenant="demo_tenant"
user="demo_user"
volume_type="NAS-Storage-AZ2.DC2"

#hybrid_cloud_agent_opts
tunnel_cidr="172.16.6.0/24"
personality_path="/home/neutron_agent_conf.txt"
route_gw="172.28.48.1"
rabbit_host_user_password="FusionSphere123"
rabbit_host_user_id="rabbit"
rabbit_host_ip="172.16.6.8"

mkdir -p "${instances_path}"
mkdir -p "${log_dir}"

#keystone中设置jacket
#openstack user show $jacketuser | openstack user create --domain
# $keystonedomain --password $jacketpass --email "root@email" $jacketuser
#openstack role add --project $keystoneservicestenant --user $jacketuser
# $keystoneadminuser

#openstack service show $jacketsvce | openstack service create --name
# $jacketsvce --description "OpenStack jacket service" jacket

#openstack endpoint create --region $endpointsregion \
#        jacket public http://$jacket_host:9774/v1/%\(tenant_id\)s

#openstack endpoint create --region $endpointsregion \
#        jacket internal http://$jacket_host:9774/v1/%\(tenant_id\)s

#openstack endpoint create --region $endpointsregion \
#        jacket admin http://$jacket_host:9774/v1/%\(tenant_id\)s

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

jacket-manage db sync
jacket-manage api_db sync

#配置文件的设置
crudini --set /etc/jacket/jacket.conf DEFAULT osapi_jacket_listen "${jacket_host}"
crudini --set /etc/jacket/jacket.conf DEFAULT osapi_compute_listen "${jacket_host}"
crudini --set /etc/jacket/jacket.conf DEFAULT metadata_listen "${jacket_host}"
crudini --set /etc/jacket/jacket.conf DEFAULT osapi_volume_listen "${jacket_host}"
crudini --set /etc/jacket/jacket.conf DEFAULT debug "true"
crudini --set /etc/jacket/jacket.conf DEFAULT log_dir "$log_dir"
crudini --set /etc/jacket/jacket.conf DEFAULT image_service "${image_service}"
crudini --set /etc/jacket/jacket.conf DEFAULT enabled_apis "${enabled_apis}"
crudini --set /etc/jacket/jacket.conf DEFAULT compute_driver "${compute_driver}"
crudini --set /etc/jacket/jacket.conf DEFAULT firewall_driver "${firewall_driver}"
crudini --set /etc/jacket/jacket.conf DEFAULT rootwrap_config "${rootwrap_config}"
crudini --set /etc/jacket/jacket.conf DEFAULT compute_topic "${compute_topic}"
crudini --set /etc/jacket/jacket.conf DEFAULT volume_topic "${volume_topic}"
crudini --set /etc/jacket/jacket.conf DEFAULT use_local "${use_local}"
crudini --set /etc/jacket/jacket.conf DEFAULT instances_path "${instances_path}"
crudini --set /etc/jacket/jacket.conf DEFAULT enabled_backends "${enabled_backends}"
crudini --set /etc/jacket/jacket.conf DEFAULT rpc_backend rabbit
crudini --set /etc/jacket/jacket.conf DEFAULT use_neutron "${use_neutron}"
crudini --set /etc/jacket/jacket.conf DEFAULT linuxnet_ovs_integration_bridge "${linuxnet_ovs_integration_bridge}"
crudini --set /etc/jacket/jacket.conf DEFAULT default_schedule_zone "${default_schedule_zone}"
crudini --set /etc/jacket/jacket.conf DEFAULT default_availability_zone "${default_availability_zone}"
crudini --set /etc/jacket/jacket.conf DEFAULT storage_availability_zone "${storage_availability_zone}"
crudini --set /etc/jacket/jacket.conf DEFAULT glance_host "${glance_host}"
crudini --set /etc/jacket/jacket.conf DEFAULT glance_api_servers "${glance_api_servers}"

#database
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

# keystone
#crudini --set /etc/jacket/jacket.conf keystone_authtoken auth_uri http://$keystonehost:5000
crudini --set /etc/jacket/jacket.conf keystone_authtoken auth_url "${auth_url}"
crudini --set /etc/jacket/jacket.conf keystone_authtoken auth_type "${auth_type}"
#crudini --set /etc/jacket/jacket.conf keystone_authtoken project_domain_name $keystonedomain
#crudini --set /etc/jacket/jacket.conf keystone_authtoken user_domain_name $keystonedomain
crudini --set /etc/jacket/jacket.conf keystone_authtoken project_name "${project_name}"
crudini --set /etc/jacket/jacket.conf keystone_authtoken username "${auth_username}"
crudini --set /etc/jacket/jacket.conf keystone_authtoken password "${auth_password}"
crudini --set /etc/jacket/jacket.conf keystone_authtoken memcached_servers "${memcached_servers}"
crudini --set /etc/jacket/jacket.conf keystone_authtoken insecure "${auth_insecure}"

# rabbit
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
crudini --set /etc/jacket/jacket.conf libvirt virt_type ${virt_type}

# storage
crudini --set /etc/jacket/jacket.conf ${enabled_backends} lvm_type "${lvm_type}"
crudini --set /etc/jacket/jacket.conf ${enabled_backends} iscsi_helper "${iscsi_helper}"
crudini --set /etc/jacket/jacket.conf ${enabled_backends} volume_driver "${volume_driver}"
crudini --set /etc/jacket/jacket.conf ${enabled_backends} volume_group "${volume_group}"
crudini --set /etc/jacket/jacket.conf ${enabled_backends} volumes_dir "${volumes_dir}"
crudini --set /etc/jacket/jacket.conf ${enabled_backends} volume_backend_name "${volume_backend_name}"

# cinder
crudini --set /etc/jacket/jacket.conf cinder http_timeout "${http_timeout}"
crudini --set /etc/jacket/jacket.conf cinder api_insecure "${api_insecure}"
crudini --set /etc/jacket/jacket.conf cinder endpoint_template "${endpoint_template}"

#neutron
crudini --set /etc/jacket/jacket.conf neutron url "${neutron_auth_url}"
crudini --set /etc/jacket/jacket.conf neutron neutron_default_tenant_id "${neutron_default_tenant_id}"
crudini --set /etc/jacket/jacket.conf neutron auth_type "${neutron_auth_type}"
crudini --set /etc/jacket/jacket.conf neutron auth_section "${neutron_auth_section}"
crudini --set /etc/jacket/jacket.conf neutron auth_url "${neutron_auth_url}"
crudini --set /etc/jacket/jacket.conf neutron project_domain_name "${neutron_project_domain_name}"
crudini --set /etc/jacket/jacket.conf neutron user_domain_name "${neutron_user_domain_name}"
crudini --set /etc/jacket/jacket.conf neutron region_name "${neutron_region_name}"
crudini --set /etc/jacket/jacket.conf neutron project_name "${neutron_project_name}"
crudini --set /etc/jacket/jacket.conf neutron username "${neutron_auth_username}"
crudini --set /etc/jacket/jacket.conf neutron password "${neutron_auth_password}"
crudini --set /etc/jacket/jacket.conf neutron service_metadata_proxy "${service_metadata_proxy}"
crudini --set /etc/jacket/jacket.conf neutron metadata_proxy_shared_secret "${metadata_proxy_shared_secret}"
crudini --set /etc/jacket/jacket.conf neutron ovs_bridge "${integration_bridge}"
crudini --set /etc/jacket/jacket.conf neutron api_insecure "${neutron_auth_insecure}"

#glance
crudini --set /etc/jacket/jacket.conf glance host "${glance_host}"
crudini --set /etc/jacket/jacket.conf glance port "${glance_port}"
crudini --set /etc/jacket/jacket.conf glance protocol "${glance_protocol}"
crudini --set /etc/jacket/jacket.conf glance api_insecure "${glance_api_insecure}"

#provider_opts
crudini --set /etc/jacket/jacket.conf provider_opts net_data "${net_data}"
crudini --set /etc/jacket/jacket.conf provider_opts availability_zone "${availability_zone}"
crudini --set /etc/jacket/jacket.conf provider_opts region "${region}"
crudini --set /etc/jacket/jacket.conf provider_opts pwd "${pwd}"
crudini --set /etc/jacket/jacket.conf provider_opts base_linux_image "${base_linux_image}"
crudini --set /etc/jacket/jacket.conf provider_opts auth_url "${pro_auth_url}"
crudini --set /etc/jacket/jacket.conf provider_opts net_api "${net_api}"
crudini --set /etc/jacket/jacket.conf provider_opts flavor_map "${flavor_map}"
crudini --set /etc/jacket/jacket.conf provider_opts tenant "${tenant}"
crudini --set /etc/jacket/jacket.conf provider_opts user "${user}"
crudini --set /etc/jacket/jacket.conf provider_opts volume_type "${volume_type}"

#hybrid_cloud_agent_opts
crudini --set /etc/jacket/jacket.conf hybrid_cloud_agent_opts tunnel_cidr "${tunnel_cidr}"
crudini --set /etc/jacket/jacket.conf hybrid_cloud_agent_opts personality_path "${personality_path}"
crudini --set /etc/jacket/jacket.conf hybrid_cloud_agent_opts route_gw "${route_gw}"
crudini --set /etc/jacket/jacket.conf hybrid_cloud_agent_opts rabbit_host_user_password "${rabbit_host_user_password}"
crudini --set /etc/jacket/jacket.conf hybrid_cloud_agent_opts rabbit_host_user_id "${rabbit_host_user_id}"
crudini --set /etc/jacket/jacket.conf hybrid_cloud_agent_opts rabbit_host_ip "${rabbit_host_ip}"

