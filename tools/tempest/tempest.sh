#!/bin/bash

OPENSTACK_IP="162.3.254.249"

#compute
image_id="c40ff46b-b3c7-4266-a126-e297c9945873"
fixed_network_name="public"


#identity
uri="http://${OPENSTACK_IP}:5000/v2.0"
uri_v3="http://${OPENSTACK_IP}:5000/v3"
auth_version="v2"

#auth
admin_username="admin"
admin_project_name="admin"
admin_password="P@ssw0rd"
admin_domain_name="default"

#network
public_network_id="00e5b4e0-d968-4bd0-b31b-659be5952bed"


#auth
crudini --set /etc/tempest/tempest.conf auth admin_username ${admin_username}
crudini --set /etc/tempest/tempest.conf auth admin_project_name ${admin_project_name}
crudini --set /etc/tempest/tempest.conf auth admin_password ${admin_password}
crudini --set /etc/tempest/tempest.conf auth admin_domain_name ${admin_domain_name}

#compute
crudini --set /etc/tempest/tempest.conf compute image_ref_alt ${image_id}
crudini --set /etc/tempest/tempest.conf compute image_ref ${image_id}
crudini --set /etc/tempest/tempest.conf compute fixed_network_name ${fixed_network_name}

#identity
crudini --set /etc/tempest/tempest.conf identity uri ${uri}
crudini --set /etc/tempest/tempest.conf identity uri_v3 ${uri_v3}
crudini --set /etc/tempest/tempest.conf identity auth_version ${auth_version}


#service_available
crudini --set /etc/tempest/tempest.conf service_available cinder true
crudini --set /etc/tempest/tempest.conf service_available neutron true
crudini --set /etc/tempest/tempest.conf service_available swift false
crudini --set /etc/tempest/tempest.conf service_available nova true
crudini --set /etc/tempest/tempest.conf service_available heat false

#network
crudini --set /etc/tempest/tempest.conf network public_network_id ${public_network_id}

