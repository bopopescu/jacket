FROM centos:7
MAINTAINER laoyi <yibo_grace@163.com>

# install dep lib

RUN yum -y install epel-release
RUN yum clean all && yum list && yum repolist all
RUN yum install -y gcc git libxslt-devel openssl-devel libffi-devel python-devel python-pip python-virtualenv
RUN pip install junitxml
RUN yum -y install crudini
RUN yum -y install python-nose
