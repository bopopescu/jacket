#!/bin/bash

if [ -e /root/adminrc ]; then
    source /root/adminrc
elif [ -e /root/keystonerc_admin ]; then
    source /root/keystonerc_admin
fi

HOST_IP=`ip addr |grep inet|grep -v 127.0.0.1|grep -v inet6|grep -E "ens|eth"|awk '{print $2}'|tr -d "addr:" | awk -F '/' '{print $1}'`

ATTRS="mysqldbadm mysqldbpassword mysqldbport dbbackendhost jacketdbname \
jacketapidbname jacketdbuser jacketdbpass jacket_host messagebrokerhost \
brokerflavor brokerflavor brokeruser brokerpass brokervhost \
virt_type state_path default_schedule_zone default_availability_zone \
storage_availability_zone compute_topic volume_topic \
linuxnet_ovs_integration_bridge use_neutron image_service compute_driver \
firewall_driver rootwrap_config use_local enabled_backends log_dir \
enabled_apis glance_host glance_port glance_protocol glance_api_insecure \
glance_api_servers lvm_type iscsi_helper volume_driver volume_group \
volumes_dir volume_backend_name http_timeout api_insecure endpoint_template \
auth_url auth_type project_name auth_username auth_password memcached_servers \
auth_insecure neutron_url neutron_default_tenant_id neutron_auth_type \
neutron_auth_section neutron_auth_url neutron_user_domain_name \
neutron_project_domain_name neutron_region_name neutron_project_name \
neutron_auth_username neutron_auth_password metadata_proxy_shared_secret \
service_metadata_proxy neutron_auth_insecure integration_bridge net_data \
availability_zone region pwd base_linux_image pro_auth_url net_api \
tenant user volume_type tunnel_cidr personality_path route_gw \
rabbit_host_user_password rabbit_host_user_id rabbit_host_ip \
jacketsvce endpointsregion publicurl adminurl internalurl"

CONF_FILE=

# 打印帮助信息
usage()
{
cat << HELP
	-f,--conf				jacket deploy config file
HELP
	exit 1;
}

#打印错误代码并退出
die()
{
	ecode=$1;
	shift;
	echo -e "${CRED}$*, exit $ecode${C0}" | tee -a $LOG_NAME;
	exit $ecode;
}
#[ $#  -lt 2 ] && usage

#解析参数
param_parse()
{
	# 可输入的选项参数设置
	ARGS=`getopt -a -o f: -l conf: -- "$@"`
	[ $? -ne 0 ] && usage

	eval set -- "${ARGS}"
	while true
	do
		case "$1" in
		-f|--conf)
			CONF_FILE="$2";
			shift
			;;
		--)
			shift
			break
			;;
			esac
	shift
	done
}

attrs_init()
{
    for attr in ${ATTRS}; do
        crudini --get "${CONF_FILE}" CONF $attr
        if [ $? -ne 0 ]; then
            die 1 "get attr($attr) from $CONF_FILE failed!"
        fi
        attr_value=`crudini --get "${CONF_FILE}" CONF $attr`
        eval "export $attr=$attr_value"

        echo "$attr=$attr_value"
    done
}

system_service()
{
    #生成jacket-worker jacket-api.service
    cat << EOF >/usr/lib/systemd/system/jacket-api.service
    [Unit]
    Deacription=Jacket API Server
    After=syslog.target network.target

    [Service]
    Type=notify
    NotifyAccess=all
    TimeoutStartSec=0
    Restart=always
    User=jacket
    ExecStart=/usr/bin/jacket-api --config-file /etc/jacket/jacket.conf

    [Install]
    WantedBy=multi-user.target
EOF

    cat << EOF >/usr/lib/systemd/system/jacket-worker.service
    [Unit]
    Deacription=Jacket Worker Server
    After=syslog.target network.target

    [Service]
    Type=notify
    NotifyAccess=all
    TimeoutStartSec=0
    Restart=always
    User=jacket
    ExecStart=/usr/bin/jacket-worker --config-file /etc/jacket/jacket.conf

    [Install]
    WantedBy=multi-user.target
EOF

    systemctl daemon-reload
    systemctl enable jacket-api.service
    systemctl enable jacket-worker.service

}

db_init()
{
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
}

conf_init()
{
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
    crudini --set /etc/jacket/jacket.conf DEFAULT state_path "${state_path}"
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
    if [ "${lvm_type}" != "" ] ; then
        crudini --set /etc/jacket/jacket.conf ${enabled_backends} lvm_type "${lvm_type}"
    fi
    if [ "${iscsi_helper}" != "" ] ; then
        crudini --set /etc/jacket/jacket.conf ${enabled_backends} iscsi_helper "${iscsi_helper}"
    fi

    if [ "${volume_group}" != "" ] ; then
        crudini --set /etc/jacket/jacket.conf ${enabled_backends} volume_group "${volume_group}"
    fi

    if [ "${volumes_dir}" != "" ] ; then
        crudini --set /etc/jacket/jacket.conf ${enabled_backends} volumes_dir "${volumes_dir}"
    fi

    crudini --set /etc/jacket/jacket.conf ${enabled_backends} volume_driver "${volume_driver}"
    crudini --set /etc/jacket/jacket.conf ${enabled_backends} volume_backend_name "${volume_backend_name}"

    # cinder
    crudini --set /etc/jacket/jacket.conf cinder http_timeout "${http_timeout}"
    crudini --set /etc/jacket/jacket.conf cinder api_insecure "${api_insecure}"
    crudini --set /etc/jacket/jacket.conf cinder endpoint_template "${endpoint_template}"

    #neutron
    crudini --set /etc/jacket/jacket.conf neutron url "${neutron_url}"
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

    #hybrid_cloud_agent_opts
    crudini --set /etc/jacket/jacket.conf hybrid_cloud_agent_opts tunnel_cidr "${tunnel_cidr}"
    crudini --set /etc/jacket/jacket.conf hybrid_cloud_agent_opts personality_path "${personality_path}"
    crudini --set /etc/jacket/jacket.conf hybrid_cloud_agent_opts route_gw "${route_gw}"
    crudini --set /etc/jacket/jacket.conf hybrid_cloud_agent_opts rabbit_host_user_password "${rabbit_host_user_password}"
    crudini --set /etc/jacket/jacket.conf hybrid_cloud_agent_opts rabbit_host_user_id "${rabbit_host_user_id}"
    crudini --set /etc/jacket/jacket.conf hybrid_cloud_agent_opts rabbit_host_ip "${rabbit_host_ip}"

    crudini --set /etc/jacket/jacket.conf oslo_concurrency lock_path "${state_path}"
}

jacket_user_init()
{
    #生成jacket用户
    getent group jacket >/dev/null || groupadd -r jacket --gid 1066
    if ! getent passwd jacket >/dev/null; then
      # Id reservation request: https://bugzilla.redhat.com/923891
      useradd -u 1066 -r -g jacket -G jacket,nobody -d /var/lib/jacket/ -s /sbin/nologin -c "OpenStack jacket Daemons" jacket
    fi

    #加入到sudo中
    cat <<EOF >/etc/sudoers.d/jacket
Defaults:jacket !requiretty
jacket ALL = (root) NOPASSWD: /usr/bin/jacket-rootwrap /etc/jacket/rootwrap.conf *
EOF

}

main()
{
    script_dir=`dirname $0`
    param_parse $*
    if [ "x$CONF_FILE" = "x" ]; then
        script_dir=`dirname $0`
        CONF_FILE="${script_dir}/jacket_conf.ini"
    fi

    if [ ! -e "$CONF_FILE" ]; then
        usage
    fi

    attrs_init
    mkdir -p "${state_path}"
    mkdir -p "${state_path}/instances"
    mkdir -p "${log_dir}"
    mkdir -p /etc/jacket
    conf_init
    db_init
    jacket_user_init
    chown jacket:jacket "${state_path}" -R
    chown jacket:jacket "${log_dir}"
    system_service

    #keystone中设置jacket

    keystone user-get $auth_username || keystone user-create --name $auth_username \
    --tenant $project_name --pass $auth_password --email "jacket@email"

    keystone user-role-add --user $auth_username --role admin --tenant $project_name

    keystone service-get $jacketsvce || keystone service-create --name $jacketsvce --description "OpenStack jacket service" --type jacket

    keystone endpoint-get --service $jacketsvce || keystone endpoint-create --region $endpointsregion --service $jacketsvce \
    --publicurl "${publicurl}" \
    --adminurl "${adminurl}" \
    --internalurl "${internalurl}"

    # 创建image对应关系
    #jacket --insecure --debug image-mapper-create 66ecc1c0-8367-477b-92c5-1bb09b0bfa89 fc84fa2c-dafd-498a-8246-0692702532c3

    service jacket-api restart
    service jacket-worker restart

    #provider_opts
    jacket --insecure project-mapper-create "default" "${tenant}" --property net_data="$net_data" \
    --property availability_zone="$availability_zone" --property region="$region" \
    --property pwd="$pwd" --property base_linux_image="$base_linux_image" \
    --property auth_url="$pro_auth_url" --property net_api="$net_api" \
    --property tenant="$tenant" --property net_api="$net_api" \
    --property user="$user" --property volume_type="$volume_type"
}

main $*
exit 0
