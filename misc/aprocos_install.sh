#!/bin/bash

if [ "$UID" = "" ]; then
    UID = `id -u`
fi

if [ ${UID} -ne 0 ]; then
   echo "$0 must be run as root... Exit."
   exit 1
fi

which pip3 > /dev/null
if [ $? -ne 0 ]; then
    echo "$0 needs python 3 and pip3... Exit."
    exit 1
fi

which curl > /dev/null
if [ $? -ne 0 ]; then
    echo "$0 needs curl... Exit."
    exit 1
fi

pip3 uninstall ariane_procos -y > /dev/null
pip3 install ariane_procos > /dev/null
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

curl -L https://raw.githubusercontent.com/echinopsii/net.echinopsii.ariane.community.plugin.procos/master/misc/aprocos_configuration.json > /etc/ariane/aprocos_configuration.json
curl -L https://raw.githubusercontent.com/echinopsii/net.echinopsii.ariane.community.plugin.procos/master/misc/aprocos_logging.json > /etc/ariane/aprocos_logging.json
curl -L https://raw.githubusercontent.com/echinopsii/net.echinopsii.ariane.community.plugin.procos/master/misc/aprocos.sh > /usr/local/bin/aprocos
chmod 755 /usr/local/bin/aprocos

echo ""
echo "Ariane ProcOS successfully installed on this operating system..."
echo "Take time to define Ariane server connections and describe this operating system context by editing /etc/ariane/aprocos_configuration.json..."
echo "Then you can start mapping your Operating System components by starting Ariane ProcOS this way : /usr/local/bin/aprocos start"