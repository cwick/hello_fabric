#!/bin/bash
cd
apt-get install git puppet
rm -rf hello_fabric
git clone git://github.com/cwick/hello_fabric.git
rm -rf /etc/puppet/modules/*
rm -rf /etc/puppet/manifests/*
cd hello_fabric/config
cp -R puppet/modules/* /etc/puppet/modules
puppet apply --verbose puppet/manifests/provision.pp

