# Ariane ProcOS plugin
# Systems tooling from psutil to Ariane server
#
# Copyright (C) 2015 echinopsii
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
import socket
import psutil

__author__ = 'mffrench'


class Connection(object):
    def __init__(self, transport_protocol=None, source_ip=None, source_port=None,
                 destination_ip=None, destination_port=None, destination_osi_id=None,
                 destination_routing_area_id=None, destination_datacenter_id=None, status=None):
        self.transport_protocol = transport_protocol
        self.source_ip = source_ip
        self.source_port = source_port
        self.destination_ip = destination_ip
        self.destination_port = destination_port
        self.destination_osi_id = destination_osi_id
        self.destination_routing_area_id = destination_routing_area_id
        self.destination_datacenter_id = destination_datacenter_id
        self.status = status


class Process(object):
    def __init__(self, mapping_id=None, is_node=None, name=None, pid=None, create_time=None, exe=None, cwd=None,
                 cmdLine=None, username=None, cpu_affinity=None, terminal=None, connections=None, uids=None, gids=None):
        self.mapping_id = mapping_id
        self.is_node = is_node
        self.pid = pid
        self.name = name
        self.create_time = create_time
        self.exe = exe
        self.cwd = cwd
        self.cmdline = cmdLine
        self.username = username
        self.cpu_affinity = cpu_affinity
        self.terminal = terminal
        self.connections = connections
        self.uids = uids
        self.gids = gids


class NetworkInterfaceCard(object):
    def __init__(self, nic_id=None, name=None, mac_address=None, duplex=None, speed=None, mtu=None,
                 ipv4_id=None, ipv4_address=None, ipv4_mask=None, ipv4_fqdn=None):
        self.nic_id = nic_id
        self.name = name
        self.mac_address = mac_address
        self.duplex = duplex
        self.speed = speed
        self.mtu = mtu
        self.ipv4_id = ipv4_id
        self.ipv4_address = ipv4_address
        self.ipv4_mask = ipv4_mask
        self.ipv4_fqdn = ipv4_fqdn


class OperatingSystem(object):
    def __init__(self, config):
        self.init_config = config
        self.container_id = None
        self.osi_id = None
        self.datacenter_id = None
        self.routing_area_id = None
        self.subnet_id = None
        self.hostname = socket.gethostname()
        self.nics = []
        self.processs = []

    def system_sniff(self):
        self.nics = []
        for nic_name_stat, snicstats in psutil.net_if_stats().__dict__.iteritems():
            nic = NetworkInterfaceCard(name=nic_name_stat, duplex=snicstats.duplex,
                                       speed=snicstats.speed, mtu=snicstats.mtu)
            for nic_name_snic, snic_table in psutil.net_if_addrs().__dict__.iteritems():
                if nic_name_snic == nic_name_stat:
                    for snic in snic_table:
                        if snic.family == socket.AddressFamily.AF_LINK:
                            nic.mac_address = snic.address
                        elif snic.family == socket.AddressFamily.AF_INET:
                            nic.ipv4_address = snic.address
                            nic.ipv4_mask = snic.netmask
                            #TO BE SOLVED : REVERSE DNS
                            #socket.gethostbyaddr(snic.address)
                        elif snic.family == socket.AddressFamily.AF_INET6:
                            #ARIANE SERVER DO NOT MANAGE IPv6 CURRENTLY
                            pass
                        else:
                            pass
            self.nics.append(nic)

        self.processs = []
        for pid in psutil.pids():
            psutil_proc = psutil.Process(pid)
            proc = Process(pid=pid, name=psutil_proc.name(), create_time=psutil_proc.create_time(),
                           exe=psutil_proc.exe(), cwd=psutil_proc.cwd(), cmdLine=psutil_proc.cmdline(),
                           username=psutil_proc.username(), cpu_affinity=psutil_proc.cpu_affinity(),
                           terminal=psutil_proc.terminal(), uids=psutil_proc.uids().effective,
                           gids=psutil_proc.gids().effective)
            proc.connections = []
            for connection in psutil_proc.connections():
                conn = Connection(transport_protocol=connection.type, source_ip=connection.laddr[0],
                                  source_port=connection.laddr[1], destination_ip=connection.raddr[0],
                                  destination_port=connection.raddr[1], status=connection.status)
                proc.connections.append(conn)
            self.processs.append(proc)




