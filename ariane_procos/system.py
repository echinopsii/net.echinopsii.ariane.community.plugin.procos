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
from ipaddress import ip_network, IPv4Address
import json
import logging
import re
import socket
import netifaces
import psutil

__author__ = 'mffrench'

LOGGER = logging.getLogger(__name__)


class MapSocket(object):
    def __init__(self, source_ip=None, source_port=None, source_endpoint_id=None,
                 destination_ip=None, destination_port=None, destination_osi_id=None,
                 destination_subnet_id=None, destination_routing_area_id=None, destination_location_id=None,
                 destination_endpoint_id=None, destination_node_id=None, destination_container_id=None,
                 family=None, rtype=None, status=None, link_id=None, transport_id=None, file_descriptors=None):
        self.source_ip = source_ip
        self.source_port = source_port
        self.source_endpoint_id = source_endpoint_id

        self.destination_ip = destination_ip
        self.destination_port = destination_port
        self.destination_osi_id = destination_osi_id
        self.destination_subnet_id = destination_subnet_id
        self.destination_routing_area_id = destination_routing_area_id
        self.destination_location_id = destination_location_id
        self.destination_endpoint_id = destination_endpoint_id
        self.destination_node_id = destination_node_id
        self.destination_container_id = destination_container_id

        self.file_descriptors = file_descriptors if file_descriptors is not None else []
        self.status = status
        self.family = family
        self.type = rtype
        self.link_id = link_id
        self.transport_id = transport_id

    def __str__(self):
        return json.dumps(self.to_json())

    __repr__ = __str__

    def __eq__(self, other):
        if self.family != other.family or self.type != other.type or self.source_ip != other.source_ip\
                or self.source_port != other.source_port or self.destination_ip != other.destination_ip\
                or self.destination_port != other.destination_port:
            return False
        else:
            return True

    @staticmethod
    def ipv6_2_ipv4(ipv6):
        ipv4 = ipv6
        if ipv6.startswith("::127"):
            ipv4 = ipv6.split("::")[1]
        elif ipv6.lower().startswith("::ffff:"):
            ipv4 = ipv6.lower().split("::ffff:")[1]
        elif ipv6 == "::1":
            ipv4 = "127.0.0.1"
        elif ipv6 == "::":
            ipv4 = "0.0.0.0"
        elif re.match(r"::*\.*\.*\.*", ipv6.lower()):
            ipv4 = ipv6.split("::")[1]
        return ipv4

    def transform_system_ipv6_to_ipv4(self):
        source_ip = self.source_ip
        destination_ip = self.destination_ip
        if self.family == "AF_INET6":
            if self.destination_ip is not None:
                destination_ip = MapSocket.ipv6_2_ipv4(self.destination_ip)
            if self.source_ip is not None:
                source_ip = MapSocket.ipv6_2_ipv4(self.source_ip)
        return source_ip, destination_ip

    def to_json(self):
        json_obj = {
            'status': self.status,
            'family': self.family,
            'type': self.type,
            'file_descriptors': self.file_descriptors,
            'link_id': self.link_id,
            'transport_id': self.transport_id,
            'source_ip': self.source_ip,
            'source_port': self.source_port,
            'source_endpoint_id': self.source_endpoint_id,
            'destination_ip': self.destination_ip,
            'destination_port': self.destination_port,
            'destination_osi_id': self.destination_osi_id,
            'destination_subnet_id': self.destination_subnet_id,
            'destination_routing_area_id': self.destination_routing_area_id,
            'destination_location_id': self.destination_location_id,
            'destination_endpoint_id': self.destination_endpoint_id,
            'destination_node_id': self.destination_node_id,
            'destination_container_id': self.destination_container_id
        }
        return json_obj

    @staticmethod
    def from_json(json_obj):
        return MapSocket(
            status=json_obj['status'],
            family=json_obj['family'],
            rtype=json_obj['type'],
            file_descriptors=json_obj['file_descriptors'],
            link_id=json_obj['link_id'],
            transport_id=json_obj['transport_id'],
            source_ip=json_obj['source_ip'],
            source_port=json_obj['source_port'],
            source_endpoint_id=json_obj['source_endpoint_id'],
            destination_ip=json_obj['destination_ip'],
            destination_port=json_obj['destination_port'],
            destination_osi_id=json_obj['destination_osi_id'],
            destination_subnet_id=json_obj['destination_subnet_id'],
            destination_routing_area_id=json_obj['destination_routing_area_id'],
            destination_location_id=json_obj['destination_location_id'],
            destination_endpoint_id=json_obj['destination_endpoint_id'],
            destination_node_id=json_obj['destination_node_id'],
            destination_container_id=json_obj['destination_container_id']
        )

    @staticmethod
    def type_2_string(mstype):
        if mstype == socket.SOCK_STREAM:
            return 'SOCK_STREAM'
        elif mstype == socket.SOCK_DGRAM:
            return 'SOCK_DGRAM'
        else:
            return mstype

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
    def __init__(self, mapping_id=None, is_node=True, name=None, pid=None, create_time=None, exe=None, cwd=None,
                 cmdline=None, username=None, cpu_affinity=None, terminal=None, map_sockets=None,
                 last_map_sockets=None, new_map_sockets=None, dead_map_sockets=None,
                 uids=None, gids=None):
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
        self.last_map_sockets = last_map_sockets
        self.map_sockets = map_sockets
        self.new_map_sockets = new_map_sockets
        self.dead_map_sockets = dead_map_sockets
        self.uids = uids
        self.gids = gids

    def __eq__(self, other):
        if self.pid != other.pid or self.name != other.name or self.create_time != other.create_time:
            return False
        else:
            return True

    def __str__(self):
        return json.dumps(self.proc_2_json())

    __repr__ = __str__

    def proc_2_json(self):
        map_sockets_json = []
        if self.map_sockets is not None:
            for map_socket in self.map_sockets:
                map_sockets_json.append(map_socket.to_json())
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
            'sockets': map_sockets_json,
            'uids': self.uids,
            'gids': self.gids,
            'mapping_id': self.mapping_id,
            'is_node': self.is_node
        }
        return json_obj

    @staticmethod
    def json_2_proc(json_obj):
        map_sockets = []
        map_sockets_json = json_obj['sockets']
        for connection_json in map_sockets_json:
            map_sockets.append(MapSocket.from_json(connection_json))
        return Process(pid=json_obj['pid'], name=json_obj['name'], create_time=json_obj['create_time'],
                       exe=json_obj['exe'], cwd=json_obj['cwd'], cmdline=json_obj['cmdline'],
                       username=json_obj['username'], cpu_affinity=json_obj['cpu_affinity'],
                       terminal=json_obj['terminal'], map_sockets=map_sockets, uids=json_obj['uids'],
                       gids=json_obj['gids'], mapping_id=json_obj['mapping_id'], is_node=json_obj['is_node'])


class NicDuplex(object):
    NIC_DUPLEX_FULL = 2
    NIC_DUPLEX_HALF = 1
    NIC_DUPLEX_UNKNOWN = 0


class NetworkInterfaceCard(object):
    def __init__(self, nic_id=None, name=None, mac_address=None, duplex=None, speed=None, mtu=None,
                 ipv4_id=None, ipv4_address=None, ipv4_subnet_addr=None, ipv4_subnet_mask=None, ipv4_broadcast=None,
                 ipv4_fqdn=None, ipv6_address=None, ipv6_mask=None, is_default=False, in_local_routingarea=False):
        self.nic_id = nic_id
        self.name = name
        self.mac_address = mac_address
        self.duplex = duplex
        self.speed = speed
        self.mtu = mtu
        self.ipv4_id = ipv4_id
        self.ipv4_address = ipv4_address
        self.ipv4_subnet_addr = ipv4_subnet_addr
        self.ipv4_subnet_mask = ipv4_subnet_mask
        self.ipv4_broadcast = ipv4_broadcast
        self.ipv4_fqdn = ipv4_fqdn
        self.ipv6_address = ipv6_address
        self.ipv6_mask = ipv6_mask
        self.is_default = is_default
        self.in_local_routingarea = in_local_routingarea

    def __eq__(self, other):
        if self.nic_id != other.nic_id or self.name != other.name or self.mac_address != other.mac_address\
                or self.duplex != other.duplex or self.speed != other.speed or self.mtu != other.mtu\
                or self.ipv4_id != other.ipv4_id or self.ipv4_address != other.ipv4_address\
                or self.ipv4_subnet_mask != other.ipv4_subnet_mask \
                or self.ipv4_fqdn != other.ipv4_fqdn or self.ipv4_broadcast != other.ipv4_broadcast:
            return False
        else:
            return True

    def __str__(self):
        return json.dumps(self.to_json())

    __repr__ = __str__

    def to_json(self):
        json_obj = {
            'nic_id': self.nic_id,
            'ipv4_id': self.ipv4_id,
            'name': self.name,
            'mac_address': self.mac_address,
            'duplex': self.duplex,
            'speed': self.speed,
            'mtu': self.mtu,
            'ipv4_address': self.ipv4_address,
            'ipv4_subnet_addr': self.ipv4_subnet_addr,
            'ipv4_subnet_mask': self.ipv4_subnet_mask,
            'ipv4_broadcast': self.ipv4_broadcast,
            'ipv4_fqdn': self.ipv4_fqdn,
            'ipv6_address': self.ipv6_address,
            'ipv6_mask': self.ipv6_mask,
            'is_default': self.is_default,
            'in_local_routingarea': self.in_local_routingarea
        }
        return json_obj

    @staticmethod
    def ip_is_in_subnet(ip_address, subnet_ip, subnet_mask):
        ret = False
        if ip_address and subnet_ip and subnet_mask:
            ret = IPv4Address(ip_address) in ip_network(subnet_ip+'/' + subnet_mask)
        return ret

    @staticmethod
    def from_json(json_obj):
        return NetworkInterfaceCard(nic_id=json_obj['nic_id'], name=json_obj['name'],
                                    mac_address=json_obj['mac_address'], duplex=json_obj['duplex'],
                                    speed=json_obj['speed'], mtu=json_obj['mtu'],
                                    ipv4_address=json_obj['ipv4_address'],
                                    ipv4_subnet_addr=json_obj['ipv4_subnet_addr'],
                                    ipv4_subnet_mask=json_obj['ipv4_subnet_mask'],
                                    ipv4_broadcast=json_obj['ipv4_broadcast'], ipv4_fqdn=json_obj['ipv4_fqdn'],
                                    ipv4_id=json_obj['ipv4_id'], ipv6_address=json_obj['ipv6_address'],
                                    ipv6_mask=json_obj['ipv6_mask'],
                                    in_local_routingarea=json_obj['in_local_routingarea'])

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
    def __init__(self, container_id=None, osi_id=None, ost_id=None, environment_id=None, team_id=None,
                 location_id=None, routing_area_ids=None, subnet_ids=None,
                 hostname=None, last_nics=None, nics=None, last_processs=None, processs=None,
                 duplex_links_endpoint=None, wip_delete_duplex_links_endpoints=None, config=None):
        LOGGER.debug("OperatingSystem.__init__")

        self.container_id = container_id

        self.osi_id = osi_id
        self.ost_id = ost_id
        self.location_id = location_id
        self.routing_area_ids = routing_area_ids if routing_area_ids is not None else []
        self.subnet_ids = subnet_ids if subnet_ids is not None else []
        self.environment_id = environment_id
        self.team_id = team_id

        self.config = config
        self.hostname = hostname if hostname is not None else socket.gethostname()
        self.last_nics = last_nics if last_nics is not None else []
        self.nics = nics if nics is not None else []
        self.last_processs = last_processs if last_processs is not None else []
        self.processs = processs if processs is not None else []
        self.new_processs = []
        self.dead_processs = []

        self.duplex_links_endpoints = duplex_links_endpoint if duplex_links_endpoint is not None else []
        self.wip_delete_duplex_links_endpoints = wip_delete_duplex_links_endpoints if wip_delete_duplex_links_endpoints is not None else []

    def __eq__(self, other):
        if self.osi_id != other.osi_id or self.hostname != other.hostname:
            return False
        else:
            return True

    def __str__(self):
        return json.dumps(self.operating_system_2_json())

    __repr__ = __str__

    def is_local(self, ip, family):
        is_local = False

        if ip is not None and family == "AF_INET":
            for nic in self.nics:
                if nic.in_local_routingarea and NetworkInterfaceCard.ip_is_in_subnet(
                        ip, nic.ipv4_subnet_addr, nic.ipv4_subnet_mask
                ):
                    is_local = True
                    break

        elif ip is not None and family == "AF_INET6":
            destination_ipv4 = MapSocket.ipv6_2_ipv4(ip)
            if destination_ipv4 != ip:
                for nic in self.nics:
                    if nic.in_local_routingarea and NetworkInterfaceCard.ip_is_in_subnet(
                            destination_ipv4, nic.ipv4_subnet_addr, nic.ipv4_subnet_mask
                    ):
                        is_local = True
                        break
            else:
                # TODO: check is ipv6 in subnet ?
                for nic in self.nics:
                    if nic.in_local_routingarea and nic.ipv6_address is not None and \
                                    ip == nic.ipv6_address:
                        is_local = True
                        break

        elif family == "AF_UNIX":
            is_local = True

        LOGGER.debug(str(ip) + " is local: " + str(is_local))

        return is_local

    def is_local_destination(self, mapping_socket):
        LOGGER.debug("OperatingSystem.is_local_destination")
        return self.is_local(mapping_socket.destination_ip, mapping_socket.family)

    def is_local_service(self, mapping_socket):
        LOGGER.debug("OperatingSystem.is_local_service")
        return self.is_local(mapping_socket.source_ip, mapping_socket.family)

    def need_directories_refresh(self):
        LOGGER.debug("OperatingSystem.need_directories_refresh")
        if self.last_nics != self.nics:
            return True
        else:
            return False

    def operating_system_2_json(self):
        LOGGER.debug("OperatingSystem.operating_system_2_json")
        last_nics_json = []
        for nic in self.last_nics:
            last_nics_json.append(nic.to_json())
        nics_json = []
        for nic in self.nics:
            nics_json.append(nic.to_json())
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
            'ost_id': self.ost_id,
            'location_id': self.location_id,
            'routing_area_ids': self.routing_area_ids,
            'subnet_ids': self.subnet_ids,
            'environment_id': self.environment_id,
            'team_id': self.team_id,
            'duplex_links_endpoints': self.duplex_links_endpoints,
            'wip_delete_duplex_links_endpoints': self.wip_delete_duplex_links_endpoints
        }
        return json_obj

    @staticmethod
    def json_2_operating_system(json_obj):
        LOGGER.debug("OperatingSystem.json_2_operating_system")
        last_nics_json = json_obj['last_nics']
        last_nics = []
        for last_nic_json in last_nics_json:
            last_nics.append(NetworkInterfaceCard.from_json(last_nic_json))

        nics_json = json_obj['nics']
        nics = []
        for nic_json in nics_json:
            nics.append(NetworkInterfaceCard.from_json(nic_json))

        last_processs_json = json_obj['last_processs']
        last_processs = []
        for last_process in last_processs_json:
            last_processs.append(Process.json_2_proc(last_process))

        processs_json = json_obj['processs']
        processs = []
        for process in processs_json:
            processs.append(Process.json_2_proc(process))

        return OperatingSystem(
            container_id=json_obj['container_id'], osi_id=json_obj['osi_id'],
            ost_id=json_obj['ost_id'], location_id=json_obj['location_id'],
            environment_id=json_obj['environment_id'], team_id=json_obj['team_id'],
            routing_area_ids=json_obj['routing_area_ids'], subnet_ids=json_obj['subnet_ids'],
            hostname=json_obj['hostname'], last_nics=last_nics, nics=nics, last_processs=last_processs,
            processs=processs, duplex_links_endpoint=json_obj['duplex_links_endpoints'],
            wip_delete_duplex_links_endpoints=json_obj['wip_delete_duplex_links_endpoints']
        )

    def update(self):
        LOGGER.debug("OperatingSystem.update")
        self.last_nics = copy.deepcopy(self.nics)
        self.last_processs = copy.deepcopy(self.processs)
        self.sniff()

    def sniff(self):
        LOGGER.debug("OperatingSystem.sniff")
        self.nics = []
        self.processs = []
        self.new_processs = []
        self.dead_processs = []

        default_nic = netifaces.gateways()['default'][netifaces.AF_INET][1]

        for nic_name_stat, snicstats in psutil.net_if_stats().items():
            is_default = (nic_name_stat == default_nic)
            nic = NetworkInterfaceCard(name=nic_name_stat,
                                       duplex=NetworkInterfaceCard.duplex_2_string(snicstats.duplex),
                                       speed=snicstats.speed, mtu=snicstats.mtu, is_default=is_default)
            for nic_name_snic, snic_table in psutil.net_if_addrs().items():
                if nic_name_snic == nic_name_stat:
                    for snic in snic_table:
                        if snic.family == psutil.AF_LINK:
                            nic.mac_address = snic.address
                        elif snic.family == socket.AddressFamily.AF_INET:
                            nic.ipv4_address = snic.address
                            if snic.address is not None and snic.netmask is not None:
                                ntw_addr = ip_network(str(snic.address) + '/' +
                                                      str(snic.netmask), strict=False).network_address
                            else:
                                ntw_addr = None
                            if ntw_addr is not None:
                                nic.ipv4_subnet_addr = str(ntw_addr)
                            else:
                                nic.ipv4_subnet_addr = None
                            nic.ipv4_subnet_mask = snic.netmask
                            nic.ipv4_broadcast = snic.broadcast
                            if self.config is not None and self.config.local_routing_area is not None and \
                                    self.config.local_routing_area.subnets.__len__() != 0:
                                for subnet in self.config.local_routing_area.subnets:
                                    if nic.ipv4_subnet_addr == subnet.subnet_ip:
                                        LOGGER.debug('OperatingSystem.sniff - NIC ' + str(nic.ipv4_address) +
                                                     ' playing in local area only.')
                                        nic.in_local_routingarea = True
                                        break
                            try:
                                nic.ipv4_fqdn = socket.gethostbyaddr(snic.address)[0]
                                if nic.ipv4_fqdn == 'localhost' or nic.ipv4_fqdn == socket.gethostname():
                                    nic.ipv4_fqdn = nic_name_stat + '.' + socket.gethostname()
                            except socket.herror:
                                nic.ipv4_fqdn = nic_name_stat + '.' + socket.gethostname()
                        elif snic.family == socket.AddressFamily.AF_INET6:
                            nic.ipv6_address = snic.address
                            nic.ipv6_mask = snic.netmask
                            # ARIANE SERVER DO NOT MANAGE IPv6 CURRENTLY
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

                try:
                    proc_connections = psutil_proc.connections()
                except ProcessLookupError:
                    proc_connections = []

                proc.map_sockets = []

                for psutil_connection in proc_connections:
                    if psutil_connection.status == psutil.CONN_LISTEN or psutil_connection.status == psutil.CONN_NONE \
                            or psutil_connection.status == psutil.CONN_CLOSE:
                        map_socket = MapSocket(family=MapSocket.family_2_string(psutil_connection.family),
                                               rtype=MapSocket.type_2_string(psutil_connection.type),
                                               source_ip=psutil_connection.laddr[0],
                                               source_port=psutil_connection.laddr[1],
                                               status=psutil_connection.status)
                    else:
                        map_socket = MapSocket(family=MapSocket.family_2_string(psutil_connection.family),
                                               rtype=MapSocket.type_2_string(psutil_connection.type),
                                               source_ip=psutil_connection.laddr[0],
                                               source_port=psutil_connection.laddr[1],
                                               destination_ip=psutil_connection.raddr[0],
                                               destination_port=psutil_connection.raddr[1],
                                               status=psutil_connection.status)
                    if map_socket not in proc.map_sockets:
                        proc.map_sockets.append(map_socket)
                    map_socket.file_descriptors.append(psutil_connection.fd)
                    LOGGER.debug("OperatingSystem.sniff - " + str(psutil_connection))

                if proc in self.last_processs:
                    for last_proc in self.last_processs:
                        if last_proc == proc:
                            if last_proc.mapping_id is not None:
                                proc.mapping_id = last_proc.mapping_id
                                proc.is_node = last_proc.is_node
                            else:
                                name = '[' + str(proc.pid) + '] ' + str(proc.name)
                                LOGGER.debug('OperatingSystem.sniff - process not saved on DB on previous round: ' +
                                             name)
                                self.new_processs.append(proc)

                            proc.last_map_sockets = copy.deepcopy(last_proc.map_sockets)
                            for map_socket in proc.map_sockets:
                                if map_socket in proc.last_map_sockets:
                                    for last_map_socket in proc.last_map_sockets:
                                        if map_socket == last_map_socket:
                                            if map_socket.status == psutil.CONN_LISTEN \
                                                    or map_socket.status == psutil.CONN_NONE \
                                                    or map_socket.status == psutil.CONN_CLOSE:
                                                if last_map_socket.source_endpoint_id is not None:
                                                    map_socket.source_endpoint_id = \
                                                        last_map_socket.source_endpoint_id
                                                else:
                                                    if proc.new_map_sockets is None:
                                                        proc.new_map_sockets = []
                                                    proc.new_map_sockets.append(map_socket)
                                            else:
                                                if last_map_socket.source_endpoint_id is not None \
                                                        and last_map_socket.destination_endpoint_id is not None \
                                                        and last_map_socket.link_id is not None \
                                                        and last_map_socket.transport_id is not None:
                                                    map_socket.source_endpoint_id = last_map_socket.source_endpoint_id
                                                    map_socket.osi_id = last_map_socket.destination_osi_id
                                                    map_socket.subnet_id = last_map_socket.destination_subnet_id
                                                    map_socket.routing_area_id = \
                                                        last_map_socket.destination_routing_area_id
                                                    map_socket.location_id = last_map_socket.destination_location_id
                                                    map_socket.destination_endpoint_id = \
                                                        last_map_socket.destination_endpoint_id
                                                    map_socket.destination_node_id = \
                                                        last_map_socket.destination_node_id
                                                    map_socket.destination_container_id = \
                                                        last_map_socket.destination_container_id
                                                    map_socket.link_id = last_map_socket.link_id
                                                    map_socket.transport_id = last_map_socket.transport_id
                                                else:
                                                    if proc.new_map_sockets is None:
                                                        proc.new_map_sockets = []
                                                    proc.new_map_sockets.append(map_socket)

                            for map_socket in proc.last_map_sockets:
                                if map_socket not in proc.map_sockets:
                                    if map_socket.source_endpoint_id is not None or \
                                            map_socket.destination_endpoint_id is not None:
                                        if proc.dead_map_sockets is None:
                                            proc.dead_map_sockets = []
                                        proc.dead_map_sockets.append(map_socket)
                            break
                else:
                    self.new_processs.append(proc)

                self.processs.append(proc)
            except psutil.NoSuchProcess:
                LOGGER.debug("OperatingSystem.sniff - process " + str(pid) + " doesnt exist anymore")
            except psutil.AccessDenied:
                LOGGER.debug("OperatingSystem.sniff - access denied for process " + str(pid))

        for process in self.last_processs:
            if process not in self.processs:
                self.dead_processs.append(process)
