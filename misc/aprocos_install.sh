#!/bin/sh

if [ $EUID -ne 0 ]; then
   echo "$0 must be run as root... Exit."
   exit 1
fi

which pip3 > /dev/null
if [ $? -ne 0 ]; then
    echo "$0 needs python 3 and pip3... Exit."
    exit 1
fi

`which curl`
if [ $? -ne 0 ]; then
    echo "$0 needs curl... Exit."
    exit 1
fi

pip3 uninstall ariane_procos -y > /dev/null
pip3 install --pre ariane_procos > /dev/null
if [ $? -ne 0 ]; then
    pip3 install --pre ariane_procos
    echo "Problems while installing Ariane ProcOS python module... Exit."
    exit 1
fi

if [ ! -d /etc/ariane ]; then
    mkdir /etc/ariane
fi

if [ ! -d /var/log/ariane ]; then
    mkdir /var/log/ariane
fi

curl -L 