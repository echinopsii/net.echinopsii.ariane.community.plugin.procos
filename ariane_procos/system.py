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
import copy
import json
import socket
import psutil

__author__ = 'mffrench'


class Connection(object):
    def __init__(self, family=None, rtype=None, source_ip=None, source_port=None,
                 destination_ip=None, destination_port=None, destination_osi_id=None, destination_subnet_id=None,
                 destination_routing_area_id=None, destination_datacenter_id=None, status=None):
        self.family = family
        self.type = rtype
        self.source_ip = source_ip
        self.source_port = source_port
        self.destination_ip = destination_ip
        self.destination_port = destination_port
        self.destination_osi_id = destination_osi_id
        self.destination_subnet_id = destination_subnet_id
        self.destination_routing_area_id = destination_routing_area_id
        self.destination_datacenter_id = destination_datacenter_id
        self.status = status

    def __str__(self):
        return json.dumps(self.connection_2_json())

    def __eq__(self, other):
        if self.family != other.family or self.type != other.type or self.source_ip != other.source_ip\
                or self.source_port != other.source_port or self.destination_ip != other.destination_ip\
                or self.destination_port != other.destination_port \
                or self.destination_osi_id != other.destination_osi_id\
                or self.destination_subnet_id != other.destination_subnet_id\
                or self.destination_routing_area_id != other.destination_routing_area_id\
                or self.destination_datacenter_id != other.destination_datacenter_id:
            return False
        else:
            return True

    def connection_2_json(self):
        json_obj = {
            'status': self.status,
            'family': self.family,
            'type': self.type,
            'source_ip': self.source_ip,
            'source_port': self.source_port,
            'destination_ip': self.destination_ip,
            'destination_port': self.destination_port,
            'destination_osi_id': self.destination_osi_id,
            'destination_subnet_id': self.destination_subnet_id,
            'destination_routing_area_id': self.destination_routing_area_id,
            'destination_datacenter_id': self.destination_datacenter_id
        }
        return json_obj

    @staticmethod
    def json_2_connection(json_obj):
        return Connection(
            status=json_obj['status'],
            family=json_obj['family'],
            rtype=json_obj['type'],
            source_ip=json_obj['source_ip'],
            source_port=json_obj['source_port'],
            destination_ip=json_obj['destination_ip'],
            destination_port=json_obj['destination_port'],
            destination_osi_id=json_obj['destination_osi_id'],
            destination_subnet_id=json_obj['destination_subnet_id'],
            destination_routing_area_id=json_obj['destination_routing_area_id'],
            destination_datacenter_id=json_obj['destination_datacenter_id']
        )

    @staticmethod
    def type_2_string(type):
        if type == socket.SocketType.SOCK_STREAM:
            return 'SOCK_STREAM'
        elif type == socket.SocketType.SOCK_DGRAM:
            return 'SOCK_DGRAM'
        else:
            return type

    @staticmethod
    def family_2_string(family):
        if family == socket.AddressFamily.AF_INET:
            return 'AF_INET'
        elif family == socket.AddressFamily.AF_INET6:
            return 'AF_INET6'
        elif family == socket.AddressFamily.AF_UNIX:
            return 'AF_UNIX'
        else:
            return family


class Process(object):
    def __init__(self, mapping_id=None, is_node=None, name=None, pid=None, create_time=None, exe=None, cwd=None,
                 cmdline=None, username=None, cpu_affinity=None, terminal=None, connections=None, uids=None, gids=None):
        self.mapping_id = mapping_id
        self.is_node = is_node
        self.pid = pid
        self.name = name
        self.create_time = create_time
        self.exe = exe
        self.cwd = cwd
        self.cmdline = cmdline
        self.username = username
        self.cpu_affinity = cpu_affinity
        self.terminal = terminal
        self.connections = connections
        self.uids = uids
        self.gids = gids

    def __eq__(self, other):
        if self.mapping_id != other.mapping_id or self.is_node != other.is_node or self.pid != other.pid\
                or self.name != other.name or self.create_time != other.create_time or self.exe != other.exe\
                or self.cwd != other.cwd or self.cmdline != other.cmdline or self.username != other.username\
                or self.cpu_affinity != other.cpu_affinity or self.terminal != other.terminal\
                or self.connections != other.connections or self.uids != other.uids or self.gids != other.gids:
            return False
        else:
            return True

    def __str__(self):
        return json.dumps(self.proc_2_json())

    def proc_2_json(self):
        connections_json = []
        if self.connections is not None:
            for connection in self.connections:
                connections_json.append(connection.connection_2_json())
        json_obj = {
            'pid': self.pid,
            'name': self.name,
            'create_time': self.create_time,
            'exe': self.exe,
            'cwd': self.cwd,
            'cmdline': self.cmdline,
            'username': self.username,
            'cpu_affinity': self.cpu_affinity,
            'terminal': self.terminal,
            'connections': connections_json,
            'uids': self.uids,
            'gids': self.gids,
            'mapping_id': self.mapping_id,
            'is_node': self.is_node
        }
        return json_obj

    @staticmethod
    def json_2_proc(json_obj):
        connections = []
        connections_json = json_obj['connections']
        for connection_json in connections_json:
            connections.append(Connection.json_2_connection(connection_json))
        return Process(pid=json_obj['pid'], name=json_obj['name'], create_time=json_obj['create_time'],
                       exe=json_obj['exe'], cwd=json_obj['cwd'], cmdline=json_obj['cmdline'],
                       username=json_obj['username'], cpu_affinity=json_obj['cpu_affinity'],
                       terminal=json_obj['terminal'], connections=connections, uids=json_obj['uids'],
                       gids=json_obj['gids'], mapping_id=json_obj['mapping_id'], is_node=json_obj['is_node'])


class NicDuplex(object):
    NIC_DUPLEX_FULL = 2
    NIC_DUPLEX_HALF = 1
    NIC_DUPLEX_UNKNOWN = 0


class NetworkInterfaceCard(object):
    def __init__(self, nic_id=None, name=None, mac_address=None, duplex=None, speed=None, mtu=None,
                 ipv4_id=None, ipv4_address=None, ipv4_mask=None, ipv4_broadcast=None, ipv4_fqdn=None):
        self.nic_id = nic_id
        self.name = name
        self.mac_address = mac_address
        self.duplex = duplex
        self.speed = speed
        self.mtu = mtu
        self.ipv4_id = ipv4_id
        self.ipv4_address = ipv4_address
        self.ipv4_mask = ipv4_mask
        self.ipv4_broadcast = ipv4_broadcast
        self.ipv4_fqdn = ipv4_fqdn

    def __eq__(self, other):
        if self.nic_id != other.nic_id or self.name != other.name or self.mac_address != other.mac_address\
                or self.duplex != other.duplex or self.speed != other.speed or self.mtu != other.mtu\
                or self.ipv4_id != other.ipv4_id or self.ipv4_address != other.ipv4_address\
                or self.ipv4_mask != other.ipv4_mac or self.ipv4_fqdn != other.ipv4_fqdn\
                or self.ipv4_broadcast != other.ipv4_broadcast:
            return False
        else:
            return True

    def __str__(self):
        return json.dumps(self.nic_2_json())

    def nic_2_json(self):
        json_obj = {
            'nic_id': self.nic_id,
            'ipv4_id': self.ipv4_id,
            'name': self.name,
            'mac_address': self.mac_address,
            'duplex': self.duplex,
            'speed': self.speed,
            'mtu': self.mtu,
            'ipv4_address': self.ipv4_address,
            'ipv4_mask': self.ipv4_mask,
            'ipv4_broadcast': self.ipv4_broadcast,
            'ipv4_fqdn': self.ipv4_fqdn
        }
        return json_obj

    @staticmethod
    def json_2_nic(json_obj):
        return NetworkInterfaceCard(nic_id=json_obj['nic_id'], name=json_obj['name'],
                                    mac_address=json_obj['mac_address'], duplex=json_obj['duplex'],
                                    speed=json_obj['speed'], mtu=json_obj['mtu'],
                                    ipv4_address=json_obj['ipv4_address'], ipv4_mask=json_obj['ipv4_mask'],
                                    ipv4_broadcast=json_obj['ipv4_broadcast'], ipv4_fqdn=json_obj['ipv4_fqdn'],
                                    ipv4_id=json_obj['ipv4_id'])

    @staticmethod
    def duplex_2_string(duplex):
        if duplex == NicDuplex.NIC_DUPLEX_UNKNOWN:
            return 'UNKNOWN'
        elif duplex == NicDuplex.NIC_DUPLEX_FULL:
            return 'FULL'
        elif duplex == NicDuplex.NIC_DUPLEX_HALF:
            return 'HALF'
        else:
            return 'UNKNOWN'


class OperatingSystem(object):
    def __init__(self, container_id=None, osi_id=None, datacenter_id=None, routing_area_ids=None,
                 subnet_ids=None, environment_id=None, team_id=None,
                 hostname=None, last_nics=None, nics=None, last_processs=None, processs=None):
        self.container_id = container_id

        self.osi_id = osi_id
        self.datacenter_id = datacenter_id
        self.routing_area_ids = routing_area_ids
        self.subnet_ids = subnet_ids
        self.environment_id = environment_id
        self.team_id = team_id

        self.hostname = hostname if hostname is not None else socket.gethostname()
        self.last_nics = last_nics if last_nics is not None else []
        self.nics = nics if nics is not None else []
        self.last_processs = last_processs if last_processs is not None else []
        self.processs = processs if processs is not None else []

    def __eq__(self, other):
        if self.osi_id != other.osi_id or self.hostname != other.hostname:
            return False
        else:
            return True

    def __str__(self):
        return json.dumps(self.operating_system_2_json())

    def need_directories_refresh(self):
        if self.last_nics != self.nics:
            return True
        else:
            return False

    def operating_system_2_json(self):
        last_nics_json = []
        for nic in self.last_nics:
            last_nics_json.append(nic.nic_2_json())
        nics_json = []
        for nic in self.nics:
            nics_json.append(nic.nic_2_json())
        last_processs_json = []
        for process in self.last_processs:
            last_processs_json.append(process.proc_2_json())
        processs_json = []
        for process in self.processs:
            processs_json.append(process.proc_2_json())
        json_obj = {
            'hostname': self.hostname,
            'last_nics': last_nics_json,
            'nics': nics_json,
            'last_processs': last_processs_json,
            'processs': processs_json,
            'container_id': self.container_id,
            'osi_id': self.osi_id,
            'datacenter_id': self.datacenter_id,
            'routing_area_ids': self.routing_area_ids,
            'subnet_ids': self.subnet_ids
        }
        return json_obj

    @staticmethod
    def json_2_operating_system(json_obj):
        last_nics_json = json_obj['last_nics']
        last_nics = []
        for last_nic_json in last_nics_json:
            last_nics.append(NetworkInterfaceCard.json_2_nic(last_nic_json))

        nics_json = json_obj['nics']
        nics = []
        for nic_json in nics_json:
            nics.append(NetworkInterfaceCard.json_2_nic(nic_json))

        last_processs_json = json_obj['last_processs']
        last_processs = []
        for last_process in last_processs_json:
            last_processs.append(Process.json_2_proc(last_process))

        processs_json = json_obj['processs']
        processs = []
        for process in processs_json:
            processs.append(Process.json_2_proc(process))

        return OperatingSystem(
            container_id=json_obj['container_id'], osi_id=json_obj['osi_id'], datacenter_id=json_obj['datacenter_id'],
            routing_area_ids=json_obj['routing_area_ids'], subnet_ids=json_obj['subnet_ids'],
            hostname=json_obj['hostname'], last_nics=last_nics, nics=nics, last_processs=last_processs,
            processs=processs
        )

    def update(self):
        self.last_nics = copy.deepcopy(self.nics)
        self.last_processs = copy.deepcopy(self.processs)
        self.sniff()

    def sniff(self):
        self.nics = []
        self.processs = []

        for nic_name_stat, snicstats in psutil.net_if_stats().items():
            nic = NetworkInterfaceCard(name=nic_name_stat,
                                       duplex=NetworkInterfaceCard.duplex_2_string(snicstats.duplex),
                                       speed=snicstats.speed, mtu=snicstats.mtu)
            for nic_name_snic, snic_table in psutil.net_if_addrs().items():
                if nic_name_snic == nic_name_stat:
                    for snic in snic_table:
                        if snic.family == psutil.AF_LINK:
                            nic.mac_address = snic.address
                        elif snic.family == socket.AddressFamily.AF_INET:
                            nic.ipv4_address = snic.address
                            nic.ipv4_mask = snic.netmask
                            nic.ipv4_broadcast = snic.broadcast
                            try:
                                nic.ipv4_fqdn = socket.gethostbyaddr(snic.address)[0]
                                if nic.ipv4_fqdn == 'localhost' or nic.ipv4_fqdn == socket.gethostname():
                                    nic.ipv4_fqdn = nic_name_stat + '.' + socket.gethostname()
                            except socket.herror:
                                nic.ipv4_fqdn = nic_name_stat + '.' + socket.gethostname()
                        elif snic.family == socket.AddressFamily.AF_INET6:
                            #ARIANE SERVER DO NOT MANAGE IPv6 CURRENTLY
                            pass
                        else:
                            pass
            self.nics.append(nic)

        for pid in psutil.pids():
            try:
                psutil_proc = psutil.Process(pid)
                proc = Process(pid=pid, name=psutil_proc.name(), create_time=psutil_proc.create_time(),
                               exe=psutil_proc.exe(), cwd=psutil_proc.cwd(), cmdline=psutil_proc.cmdline(),
                               username=psutil_proc.username(),
                               cpu_affinity=
                               psutil_proc.cpu_affinity() if hasattr(psutil_proc, 'cpu_affinity') else None,
                               terminal=psutil_proc.terminal(), uids=psutil_proc.uids().effective,
                               gids=psutil_proc.gids().effective)
                proc.connections = []
                for connection in psutil_proc.connections():
                    if connection.status == psutil.CONN_LISTEN or connection.status == psutil.CONN_NONE \
                            or connection.status == psutil.CONN_CLOSE:
                        conn = Connection(family=Connection.family_2_string(connection.family),
                                          rtype=Connection.type_2_string(connection.type),
                                          source_ip=connection.laddr[0], source_port=connection.laddr[1],
                                          status=connection.status)
                    else:
                        conn = Connection(family=Connection.family_2_string(connection.family),
                                          rtype=Connection.type_2_string(connection.type),
                                          source_ip=connection.laddr[0], source_port=connection.laddr[1],
                                          destination_ip=connection.raddr[0], destination_port=connection.raddr[1],
                                          status=connection.status)
                    proc.connections.append(conn)
                self.processs.append(proc)
            except psutil.AccessDenied:
                pass