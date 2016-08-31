FROM centos:7
MAINTAINER laoyi <yibo_grace@163.com>

# install dep lib

RUN yum -y install epel-release
RUN yum clean all && yum list && yum repolist all
RUN yum install -y gcc git libxslt-devel openssl-devel libffi-devel python-devel python-pip python-virtualenv
RUN pip install junitxml

RUN git clone https://github.com/openstack/tempest.git && cd tempest && python setup.py install
RUN mkdir -p ~/.pip && echo -e "[global]\ntrusted-host=pypi.douban.com\nindex-url = http://pypi.douban.com/simple/" >>~/.pip/pip.conf
RUN cd tempest && pip install -r requirements.txt
RUN cd tempest && pip install tox && tox -egenconfig
RUN cd tempest && mkdir -p /etc/tempest && ls -l /etc/tempest && ls -l etc && cp etc/tempest.conf.sample /etc/tempest/tempest.conf
