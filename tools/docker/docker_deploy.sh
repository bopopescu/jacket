#!/bin/bash

apt-get update
sudo apt-get install apt-transport-https ca-certificates
sudo apt-key adv --keyserver hkp://p80.pool.sks-keyservers.net:80 --recv-keys 58118E89F3A912897C070ADBF76221572C52609D
echo "deb https://apt.dockerproject.org/repo ubuntu-trusty main" >>/etc/apt/sources.list.d/docker.list
sudo apt-get update
sudo apt-get purge lxc-docker
apt-cache policy docker-engine

sudo apt-get update
sudo apt-get install linux-image-extra-$(uname -r) linux-image-extra-virtual

sudo apt-get update
sudo apt-get -y install docker-engine

#默认让docker启动
chkconfig docker on

sed -i 's|other_args="|other_args="--registry-mirror=http://768e1313.m.daocloud.io |g' /etc/sysconfig/docker
sed -i "s|OPTIONS='|OPTIONS='--registry-mirror=http://768e1313.m.daocloud.io |g" /etc/sysconfig/docker
sed -i 'N;s|\[Service\]\n|\[Service\]\nEnvironmentFile=-/etc/sysconfig/docker\n|g' /usr/lib/systemd/system/docker.service
sed -i 's|fd://|fd:// $other_args |g' /usr/lib/systemd/system/docker.service

sudo systemctl daemon-reload
sudo service docker restart

docker pull centos:7