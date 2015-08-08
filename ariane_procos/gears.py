# Ariane ProcOS plugin
# Gears
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
import json
import os
import socket
import threading
import time
import timeit
import traceback
from ariane_clip3.mapping import ContainerService, Container, NodeService, Node
from ariane_clip3.directory import DatacenterService, Datacenter, RoutingAreaService, RoutingArea, OSInstanceService, \
    OSInstance, SubnetService, Subnet, IPAddressService, IPAddress, EnvironmentService, Environment, TeamService, Team, \
    OSTypeService, OSType, Company
from ariane_clip3.injector import InjectorGearSkeleton
from components import SystemComponent
from config import RoutingAreaConfig, SubnetConfig
from system import NetworkInterfaceCard

__author__ = 'mffrench'


class DirectoryGear(InjectorGearSkeleton):
    def __init__(self):
        super(DirectoryGear, self).__init__(
            gear_id='ariane.community.plugin.procos.gears.cache.directory_gear@'+SystemGear.hostname,
            gear_name='procos_directory_gear@'+SystemGear.hostname,
            gear_description='Ariane ProcOS directory gear for '+SystemGear.hostname,
            gear_admin_queue='ariane.community.plugin.procos.gears.cache.directory_gear@'+SystemGear.hostname,
            running=False
        )
        self.update_count = 0
        self.is_network_sync_possible = True
        self.current_possible_network = []

    def on_start(self):
        self.running = True
        self.cache(running=self.running)

    def on_stop(self):
        if self.running:
            self.running = False
            self.cache(running=self.running)
        self.cached_gear_actor.remove().get()
        self.cached_gear_actor.stop()

    def gear_start(self):
        self.on_start()

    def gear_stop(self):
        if self.running:
            self.running = False
            self.cache(running=self.running)

    def compute_current_possible_network(self, operating_system):
        # Find current Datacenter, routing area and subnets according to runtime IP on NICs and possible datacenters:
        current_possible_datacenter_config = []
        current_possible_routing_area_config = []
        current_possible_subnet_config = []

        current_possible_remote_vpn_datacenter_config = []
        current_possible_remote_vpn_routing_area_config = []
        current_possible_remote_vpn_subnet_config = []

        for nic in operating_system.nics:
            nic_is_located = False
            try:
                if nic.ipv4_address is not None:
                    if not nic.ipv4_address.startswith('127'):
                        for datacenter_config in SystemGear.config.potential_datacenters:
                            for routing_area_config in datacenter_config.routing_areas:
                                for subnet_config in routing_area_config.subnets:

                                    if NetworkInterfaceCard.ip_is_in_subnet(nic.ipv4_address,
                                                                            subnet_config.subnet_ip,
                                                                            subnet_config.subnet_mask):
                                        if routing_area_config.type == RoutingArea.RA_TYPE_VPN:
                                                current_possible_remote_vpn_datacenter_config.append(datacenter_config)
                                                current_possible_remote_vpn_routing_area_config.append(
                                                    routing_area_config)
                                                current_possible_remote_vpn_subnet_config.append(subnet_config)
                                                nic_is_located = True
                                                break
                                        else:
                                            if datacenter_config not in current_possible_datacenter_config:
                                                current_possible_datacenter_config.append(datacenter_config)
                                            current_possible_routing_area_config.append(routing_area_config)
                                            current_possible_subnet_config.append(subnet_config)
                                            nic_is_located = True
                                            break
                                if nic_is_located:
                                    break
                            if nic_is_located:
                                break

                        if not nic_is_located:
                            if nic.mac_address is not None:
                                print('WARN: nic ' + nic.mac_address + '/' + nic.ipv4_address +
                                      ' has not been located on the possibles networks')
                            else:
                                print('WARN: nic ' + nic.ipv4_address +
                                      ' has not been located on the possibles networks')

            except Exception as e:
                print(e.__str__())

        if current_possible_datacenter_config.__len__() > 1:
            print('WARN: multiple current possible datacenter found - will ignore directories sync')
        elif current_possible_datacenter_config.__len__() == 0:
            print('WARN: no current possible datacenter found - will ignore directories sync')

        if current_possible_datacenter_config.__len__() != 1:
            self.is_network_sync_possible = False
        if current_possible_routing_area_config.__len__() == 0:
            self.is_network_sync_possible = False
        if current_possible_subnet_config.__len__() == 0:
            self.is_network_sync_possible = False

        self.current_possible_network = [
            current_possible_datacenter_config,
            current_possible_routing_area_config,
            current_possible_subnet_config,
            current_possible_remote_vpn_datacenter_config,
            current_possible_remote_vpn_routing_area_config,
            current_possible_remote_vpn_subnet_config
        ]

    @staticmethod
    def sync_operating_system(operating_system):
        # Sync Operating System
        if operating_system.osi_id is not None:
            SystemGear.osi = OSInstanceService.find_os_instance(osi_id=operating_system.osi_id)
            if SystemGear.osi.name != SystemGear.hostname:
                SystemGear.osi = None
                operating_system.osi_id = None

        if SystemGear.osi is None:
            SystemGear.osi = OSInstanceService.find_os_instance(osi_name=SystemGear.hostname)
            if SystemGear.osi is None:
                SystemGear.osi = OSInstance(
                    name=SystemGear.hostname,
                    description=SystemGear.config.system_context.description,
                    admin_gate_uri=SystemGear.config.system_context.admin_gate_protocol+SystemGear.hostname)
                SystemGear.osi.save()
            operating_system.osi_id = SystemGear.osi.id

    @staticmethod
    def sync_operating_system_type(operating_system):
        if SystemGear.osi is None:
            print('ERROR: operating system instance is not synced')
            return

        # Sync OS Type
        if operating_system.ost_id is not None:
            SystemGear.ost = OSTypeService.find_ostype(ost_id=operating_system.ost_id)
            if SystemGear.ost is not None and SystemGear.osi.ost_id != SystemGear.ost.id:
                SystemGear.ost = None
                SystemGear.ost_company = None
                SystemGear.osi.ost_id = 0
                SystemGear.osi.save()

        if SystemGear.ost is None:
            SystemGear.ost_company = Company(
                name=SystemGear.config.system_context.os_type.company.name,
                description=SystemGear.config.system_context.os_type.company.description
            )
            SystemGear.ost_company.save()
            SystemGear.ost = OSType(
                name=SystemGear.config.system_context.os_type.name,
                architecture=SystemGear.config.system_context.os_type.architecture,
                os_type_company_id=SystemGear.ost_company.id
            )
            SystemGear.ost.save()
            SystemGear.osi.ost_id = SystemGear.ost.id
            SystemGear.osi.save()
            operating_system.ost_id = SystemGear.ost.id

    @staticmethod
    def sync_environment(operating_system):
        if SystemGear.osi is None:
            print('ERROR: operating system instance is not synced')
            return

        # Sync environment
        if SystemGear.config.organisation_context is not None and \
                        SystemGear.config.organisation_context.environment is not None:
            if operating_system.environment_id is not None:
                SystemGear.environment = EnvironmentService.find_environment(operating_system.environment_id)
                if SystemGear.environment is not None and \
                                SystemGear.environment.name != SystemGear.config.organisation_context.environment.name:
                    SystemGear.environment.del_os_instance(SystemGear.osi)
                    SystemGear.environment = None
                    operating_system.environment_id = None

            if SystemGear.environment is None:
                SystemGear.environment = EnvironmentService.find_environment(
                    env_name=SystemGear.config.organisation_context.environment.name
                )
                if SystemGear.environment is None:
                    SystemGear.environment = Environment(
                        name=SystemGear.config.organisation_context.environment.name,
                        description=SystemGear.config.organisation_context.environment.description
                    )
                    SystemGear.environment.save()
                operating_system.environment_id = SystemGear.environment.id
                SystemGear.osi.add_environment(SystemGear.environment)
        else:
            if operating_system.environment_id is not None:
                environment = EnvironmentService.find_environment(operating_system.environment_id)
                environment.del_os_instance(SystemGear.osi)
                operating_system.environment_id = None

    @staticmethod
    def sync_team(operating_system):
        if SystemGear.osi is None:
            print('ERROR: operating system instance is not synced')
            return

        # Sync team
        if SystemGear.config.organisation_context is not None and \
                        SystemGear.config.organisation_context.team is not None:
            if operating_system.team_id is not None:
                SystemGear.team = TeamService.find_team(team_id=operating_system.team_id)
                if SystemGear.team is not None and \
                                SystemGear.team.name != SystemGear.config.organisation_context.team.name:
                    SystemGear.team.del_os_instance(SystemGear.osi)
                    SystemGear.team = None
                    operating_system.team_id = None

            if SystemGear.team is None:
                SystemGear.team = TeamService.find_team(team_name=SystemGear.config.organisation_context.team.name)
                if SystemGear.team is None:
                    SystemGear.team = Team(name=SystemGear.config.organisation_context.team.name,
                                           color_code=SystemGear.config.organisation_context.team.color_code,
                                           description=SystemGear.config.organisation_context.team.description)
                    SystemGear.team.save()
                operating_system.team_id = SystemGear.team.id
                SystemGear.osi.add_team(SystemGear.team)
        else:
            if operating_system.team_id is not None:
                team = TeamService.find_team(team_id=operating_system.team_id)
                team.del_os_instance(SystemGear.osi)
                operating_system.team_id = None

    def sync_network(self, operating_system):
        if SystemGear.osi is None:
            print('ERROR: operating system instance is not synced')
            return

        # Sync network stuffs
        current_possible_datacenter_config = self.current_possible_network[0]
        current_possible_routing_area_config = self.current_possible_network[1]
        current_possible_subnet_config = self.current_possible_network[2]
        current_possible_remote_vpn_datacenter_config = self.current_possible_network[3]
        current_possible_remote_vpn_routing_area_config = self.current_possible_network[4]
        current_possible_remote_vpn_subnet_config = self.current_possible_network[5]

        current_datacenter = current_possible_datacenter_config[0]

        # Sync datacenter
        if operating_system.datacenter_id is not None:
            SystemGear.datacenter = DatacenterService.find_datacenter(operating_system.datacenter_id)
            if SystemGear.datacenter is not None and SystemGear.datacenter.name != current_datacenter.name:
                # This OS has moved
                print("INFO - The operating system has a new location !")
                SystemGear.datacenter = None
                operating_system.datacenter_id = None

                for subnet_id in SystemGear.osi.subnet_ids:
                    subnet_to_unbind = SubnetService.find_subnet(sb_id=subnet_id)
                    if subnet_to_unbind is not None:
                        SystemGear.osi.del_subnet(subnet_to_unbind)
                        operating_system.routing_area_ids.remove(subnet_to_unbind.routing_area_id)
                    operating_system.subnet_ids.remove(subnet_id)

                embedding_osi = OSInstanceService.find_os_instance(osi_id=SystemGear.osi.embedding_osi_id)
                embedding_osi.del_embedded_osi(SystemGear.osi)

                for ip_id in SystemGear.osi.ip_address_ids:
                    ip_to_unbind = IPAddressService.find_ip_address(ipa_id=ip_id)
                    if ip_to_unbind is not None:
                        ip_to_unbind.remove()
                SystemGear.osi.sync()

        if SystemGear.datacenter is None:
            SystemGear.datacenter = DatacenterService.find_datacenter(dc_name=current_datacenter.name)
            if SystemGear.datacenter is None:
                SystemGear.datacenter = Datacenter(name=current_datacenter.name,
                                                   description=current_datacenter.description,
                                                   address=current_datacenter.address,
                                                   zip_code=current_datacenter.zipcode,
                                                   town=current_datacenter.town,
                                                   country=current_datacenter.country,
                                                   gps_latitude=current_datacenter.gps_lat,
                                                   gps_longitude=current_datacenter.gps_lng)
                SystemGear.datacenter.save()
            operating_system.datacenter_id = SystemGear.datacenter.id

        # Sync routing areas and subnets
        for cached_routing_area_id in operating_system.routing_area_ids:
            cached_routing_area = RoutingAreaService.find_routing_area(ra_id=cached_routing_area_id)
            if cached_routing_area is not None:
                mimic_cached_routing_area_config = RoutingAreaConfig(name=cached_routing_area.name)
                if mimic_cached_routing_area_config in current_possible_routing_area_config or \
                                mimic_cached_routing_area_config in current_possible_remote_vpn_routing_area_config:
                    for subnet_id in cached_routing_area.subnet_ids:
                        subnet = SubnetService.find_subnet(sb_id=subnet_id)
                        if subnet is not None:
                            mimic_cached_subnet_config = SubnetConfig(name=subnet.name)
                            if mimic_cached_subnet_config in current_possible_subnet_config or \
                                            mimic_cached_subnet_config in current_possible_remote_vpn_subnet_config:
                                if subnet.id not in operating_system.subnet_ids:
                                    operating_system.subnet_ids.append(subnet.id)
                                if subnet.id not in SystemGear.osi.subnet_ids:
                                    SystemGear.osi.add_subnet(subnet)
                                if subnet not in SystemGear.subnets:
                                    SystemGear.subnets.append(subnet)
                                if mimic_cached_subnet_config in current_possible_subnet_config:
                                    current_possible_subnet_config.remove(mimic_cached_subnet_config)
                                if mimic_cached_subnet_config in current_possible_remote_vpn_subnet_config:
                                    current_possible_remote_vpn_subnet_config.remove(mimic_cached_subnet_config)
                            else:
                                if subnet.id in operating_system.subnet_ids:
                                    operating_system.subnet_ids.remove(subnet.id)
                                if subnet.id in SystemGear.osi.subnet_ids:
                                    SystemGear.osi.del_subnet(subnet)
                                if subnet in SystemGear.subnets:
                                    SystemGear.subnets.remove(subnet)

                    if cached_routing_area not in SystemGear.routing_areas:
                        SystemGear.routing_areas.append(cached_routing_area)
                    if mimic_cached_routing_area_config in current_possible_routing_area_config:
                        current_possible_routing_area_config.remove(mimic_cached_routing_area_config)
                    if mimic_cached_routing_area_config in current_possible_remote_vpn_routing_area_config:
                        current_possible_remote_vpn_routing_area_config.remove(mimic_cached_routing_area_config)

                else:
                    for subnet_id in cached_routing_area.subnet_ids:
                        subnet = SubnetService.find_subnet(sb_id=subnet_id)
                        if subnet is not None:
                            mimic_cached_subnet_config = SubnetConfig(name=subnet.name)
                            if mimic_cached_subnet_config in current_possible_subnet_config:
                                current_possible_subnet_config.remove(mimic_cached_subnet_config)
                            if subnet.id in operating_system.subnet_ids:
                                operating_system.subnet_ids.remove(subnet.id)
                            if subnet.id in SystemGear.osi.subnet_ids:
                                SystemGear.osi.del_subnet(subnet)
                            if subnet in SystemGear.subnets:
                                SystemGear.subnets.remove(subnet)
                    if cached_routing_area in SystemGear.routing_areas:
                        SystemGear.routing_areas.remove(cached_routing_area)
            else:
                operating_system.routing_area_ids.remove(cached_routing_area_id)

        for remote_vpn_dc_config in current_possible_remote_vpn_datacenter_config:
            vpn_dc = DatacenterService.find_datacenter(dc_name=remote_vpn_dc_config.name)
            if vpn_dc is None:
                vpn_dc = Datacenter(
                    name=remote_vpn_dc_config.name,
                    description=remote_vpn_dc_config.description,
                    address=remote_vpn_dc_config.address,
                    zip_code=remote_vpn_dc_config.zipcode,
                    town=remote_vpn_dc_config.town,
                    country=remote_vpn_dc_config.country,
                    gps_latitude=remote_vpn_dc_config.gps_lat,
                    gps_longitude=remote_vpn_dc_config.gps_lng
                )
                vpn_dc.save()

            for remote_routing_area_config in remote_vpn_dc_config.routing_areas:
                if remote_routing_area_config in current_possible_remote_vpn_routing_area_config:
                    vpn_ra = RoutingAreaService.find_routing_area(ra_name=remote_routing_area_config.name)
                    if vpn_ra is None:
                        vpn_ra = RoutingArea(name=remote_routing_area_config.name,
                                             multicast=remote_routing_area_config.multicast,
                                             ra_type=remote_routing_area_config.type,
                                             description=remote_routing_area_config.description)
                        vpn_ra.save()
                    vpn_ra.add_datacenter(SystemGear.datacenter)
                    vpn_ra.add_datacenter(vpn_dc)
                    SystemGear.routing_areas.append(vpn_ra)
                    operating_system.routing_area_ids.append(vpn_ra.id)

                    for remote_subnet_config in remote_routing_area_config.subnets:
                        if remote_subnet_config in current_possible_remote_vpn_subnet_config:
                            vpn_subnet = SubnetService.find_subnet(sb_name=remote_subnet_config.name)
                            if vpn_subnet is None:
                                vpn_subnet = Subnet(name=remote_subnet_config.name,
                                                    description=remote_subnet_config.description,
                                                    routing_area_id=vpn_ra.id,
                                                    ip=remote_subnet_config.subnet_ip,
                                                    mask=remote_subnet_config.subnet_mask)
                                vpn_subnet.save()
                            vpn_subnet.add_datacenter(SystemGear.datacenter)
                            vpn_subnet.add_datacenter(vpn_dc)
                            operating_system.subnet_ids.append(vpn_subnet.id)
                            SystemGear.subnets.append(vpn_subnet)
                            if vpn_subnet.id not in SystemGear.osi.subnet_ids:
                                SystemGear.osi.add_subnet(vpn_subnet)

        for routing_area_config in current_possible_routing_area_config:
            routing_area = RoutingAreaService.find_routing_area(ra_name=routing_area_config.name)

            if routing_area is None:
                routing_area = RoutingArea(name=routing_area_config.name,
                                           multicast=routing_area_config.multicast,
                                           ra_type=routing_area_config.type,
                                           description=routing_area_config.description)
                routing_area.save()
                routing_area.add_datacenter(SystemGear.datacenter)
                operating_system.routing_area_ids.append(routing_area.id)
                SystemGear.routing_areas.append(routing_area)

            for subnet_config in routing_area_config.subnets:
                if subnet_config in current_possible_subnet_config:
                    subnet = SubnetService.find_subnet(sb_name=subnet_config.name)
                    if subnet is None:
                        subnet = Subnet(name=subnet_config.name,
                                        description=subnet_config.description,
                                        routing_area_id=routing_area.id,
                                        ip=subnet_config.subnet_ip, mask=subnet_config.subnet_mask)
                        subnet.save()
                        subnet.add_datacenter(SystemGear.datacenter)
                    operating_system.subnet_ids.append(subnet.id)
                    SystemGear.subnets.append(subnet)
                    if subnet.id not in SystemGear.osi.subnet_ids:
                        SystemGear.osi.add_subnet(subnet)

        for ipv4_id in SystemGear.osi.ip_address_ids:
            ipv4 = IPAddressService.find_ip_address(ipa_id=ipv4_id)
            to_be_removed = True
            for nic in operating_system.nics:
                if nic.ipv4_address is not None and nic.ipv4_address == ipv4.ip_address:
                    to_be_removed = False
            if to_be_removed:
                ipv4.remove()

        for nic in operating_system.nics:
            if nic.ipv4_address is not None:
                if not nic.ipv4_address.startswith('127'):
                    for subnet in SystemGear.subnets:
                        if NetworkInterfaceCard.ip_is_in_subnet(nic.ipv4_address, subnet.ip, subnet.mask):
                            ip_address = IPAddressService.find_ip_address(ipa_ip_address=nic.ipv4_address,
                                                                          ipa_subnet_id=subnet.id)
                            if ip_address is None:
                                ip_address = IPAddress(ip_address=nic.ipv4_address, fqdn=nic.ipv4_fqdn,
                                                       ipa_subnet_id=subnet.id, ipa_osi_id=SystemGear.osi.id)
                                ip_address.save()
                                subnet.sync()
                            else:
                                if ip_address.ipa_os_instance_id != SystemGear.osi.id:
                                    ip_address.ipa_os_instance_id = SystemGear.osi.id
                                    ip_address.save()
                            SystemGear.osi.sync()
                            break
                else:
                    local_routing_area = RoutingAreaService.find_routing_area(ra_name=SystemGear.hostname+".local")
                    if local_routing_area is None:
                        local_routing_area = RoutingArea(name=SystemGear.hostname+".local",
                                                         multicast=RoutingArea.RA_MULTICAST_NOLIMIT,
                                                         ra_type=RoutingArea.RA_TYPE_VIRT,
                                                         description=SystemGear.hostname+".local routing area")
                        local_routing_area.save()

                    loopback_subnet = SubnetService.find_subnet(sb_name=SystemGear.hostname+".loopback")
                    if loopback_subnet is not None:
                        loopback_subnet.remove()

                    loopback_subnet = Subnet(name=SystemGear.hostname+".loopback",
                                             description=SystemGear.hostname + " loopback subnet",
                                             routing_area_id=local_routing_area.id,
                                             ip='127.0.0.0', mask='255.0.0.0')
                    loopback_subnet.save()
                    loopback_subnet.add_datacenter(SystemGear.datacenter)

                    SystemGear.osi.add_subnet(loopback_subnet)

                    ip_address = IPAddressService.find_ip_address(ipa_fqdn=nic.ipv4_fqdn)
                    if ip_address is None:
                        ip_address = IPAddress(ip_address=nic.ipv4_address, fqdn=nic.ipv4_fqdn,
                                               ipa_subnet_id=loopback_subnet.id, ipa_osi_id=SystemGear.osi.id)
                        ip_address.save()
                        loopback_subnet.sync()

    def init_ariane_directories(self, component):
        operating_system = component.operating_system.get()
        try:
            self.sync_operating_system(operating_system)
            self.sync_operating_system_type(operating_system)
            self.sync_environment(operating_system)
            self.sync_team(operating_system)

            self.compute_current_possible_network(operating_system)
            if self.is_network_sync_possible:
                self.sync_network(operating_system)
        except Exception as e:
            print(e.__str__())

    def update_ariane_directories(self, operating_system):
        # check last / new sniff diff on nics
        if self.is_network_sync_possible:
            try:
                if operating_system.last_nics != operating_system.nics:
                    if self.is_network_sync_possible:
                        self.sync_network(operating_system)
                else:
                    print('DEBUG - NO CHANGES WITH LAST SNIFF')
            except Exception as e:
                print(e.__str__())
                print(traceback.format_exc())
        else:
            print('WARN - DIRECTORIES SYNC ARE IGNORED')

    def synchronize_with_ariane_directories(self, component):
        operating_system = component.operating_system.get()
        self.update_ariane_directories(operating_system)
        self.update_count += 1


class MappingGear(InjectorGearSkeleton):
    def __init__(self):
        super(MappingGear, self).__init__(
            gear_id='ariane.community.plugin.procos.gears.cache.mapping_gear@'+SystemGear.hostname,
            gear_name='procos_mapping_gear@'+SystemGear.hostname,
            gear_description='Ariane ProcOS injector gear for '+SystemGear.hostname,
            gear_admin_queue='ariane.community.plugin.procos.gears.cache.mapping_gear@'+SystemGear.hostname,
            running=False
        )
        self.update_count = 0
        self.osi_container = None

    def on_start(self):
        self.running = True
        self.cache(running=self.running)

    def on_stop(self):
        if self.running:
            self.running = False
            self.cache(running=self.running)
        self.cached_gear_actor.remove().get()
        self.cached_gear_actor.stop()

    def gear_start(self):
        self.on_start()

    def gear_stop(self):
        if self.running:
            self.running = False
            self.cache(running=self.running)

    def sync_container(self, operating_system):
        if self.osi_container is None and operating_system.container_id is not None:
            self.osi_container = ContainerService.find_container(cid=operating_system.container_id)
            if self.osi_container is None:
                print('ERROR: consistency error between ProcOS cache and mapping DB (' +
                      str(operating_system.container_id) + ')')
                operating_system.container_id = None

        if self.osi_container is None:
            self.osi_container = Container(
                name=SystemGear.hostname,
                gate_uri=SystemGear.config.system_context.admin_gate_protocol+SystemGear.hostname,
                primary_admin_gate_name=SystemGear.config.system_context.admin_gate_protocol + ' daemon',
                company=SystemGear.config.system_context.os_type.company.name,
                product=SystemGear.config.system_context.os_type.name + '-' +
                        SystemGear.config.system_context.os_type.architecture,
                c_type='Operating System'
            )
            self.osi_container.save()
            operating_system.container_id = self.osi_container.id
            print('DEBUG: operating_system.container_id : (' + SystemGear.hostname + ',' +
                  str(operating_system.container_id) + ')')
            datacenter_properties = {
                Container.DC_NAME_MAPPING_FIELD: SystemGear.datacenter.name,
                Container.DC_ADDR_MAPPING_FIELD: SystemGear.datacenter.address,
                Container.DC_TOWN_MAPPING_FIELD: SystemGear.datacenter.town,
                Container.DC_CNTY_MAPPING_FIELD: SystemGear.datacenter.country,
                Container.DC_GPSA_MAPPING_FIELD: SystemGear.datacenter.gpsLatitude,
                Container.DC_GPSN_MAPPING_FIELD: SystemGear.datacenter.gpsLongitude
            }
            datacenter_properties_dumped = json.dumps(datacenter_properties)
            print('DEBUG: DC properties - ' + datacenter_properties_dumped)
            self.osi_container.add_property(Container.DC_MAPPING_PROPERTIES, json.dumps(datacenter_properties))

    def sync_processs(self, operating_system):
        if self.osi_container is None:
            print('ERROR: operating system container is not synced')
            return

        t = timeit.default_timer()
        print('DEBUG: ' + str(operating_system.new_processs.__len__()) + ' new processes found')
        for process in operating_system.new_processs:
            process_map_obj = None
            exe_tab = process.exe.split(os.path.sep)
            name = '[' + str(process.pid) + '] ' + exe_tab[exe_tab.__len__() - 1]

            if process_map_obj is None:
                process_map_obj = Node(
                    name=name,
                    container=self.osi_container
                )
                process_map_obj.save()
                process_map_obj.add_property(('pid', process.pid))
                process_map_obj.add_property(('exe', process.exe))
                #process_map_obj.add_property(('cmdline', process.cmdline))
                process_map_obj.add_property(('cwd', process.cwd))
                process_map_obj.add_property(('creation time', process.create_time))
                process_map_obj.add_property(('username', process.username))
                process_map_obj.add_property(('uids', process.uids))
                process_map_obj.add_property(('gids', process.gids))
                if process.terminal is not None:
                    process_map_obj.add_property(('terminal', process.terminal))
                if process.cpu_affinity is not None:
                    process_map_obj.add_property(('cpu_affinity', process.cpu_affinity))
                process.mapping_id = process_map_obj.id
                print('DEBUG: new process on mapping db : (' + name + ',' + str(process.mapping_id) + ')')

        print('DEBUG: ' + str(operating_system.dead_processs.__len__()) + ' old processes found')
        for process in operating_system.dead_processs:
            process_map_obj = None
            exe_tab = process.exe.split(os.path.sep)
            name = '[' + str(process.pid) + '] ' + exe_tab[exe_tab.__len__() - 1]
            if process.mapping_id is None:
                print('ERROR: dead process (' + name + ') has not been save on mapping db !')
            else:
                if process.is_node:
                    process_map_obj = NodeService.find_node(nid=process.mapping_id)
                else:
                    process_map_obj = ContainerService.find_container(cid=process.mapping_id)
                if process_map_obj is None:
                    print('ERROR: consistency error between ProcOS cache and mapping DB (' + name + ',' +
                          str(process.mapping_id) + ')')
                else:
                    process_map_obj.remove()

        sync_proc_time = round(timeit.default_timer()-t)
        print('time : {0}'.format(sync_proc_time))

    def synchronize_with_ariane_mapping(self, component):
        operating_system = component.operating_system.get()
        try:
            self.sync_container(operating_system)
            self.sync_processs(operating_system)
        except Exception as e:
            print(e.__str__())
            print(traceback.format_exc())
        self.update_count += 1


class SystemGear(InjectorGearSkeleton):
    #static reference on commons var
    config = None
    hostname = None

    #static reference to up to date ariane directories objects linked to this System
    datacenter = None
    routing_areas = []
    subnets = []
    osi = None
    ost = None
    ost_company = None
    team = None
    environment = None

    def __init__(self, config):
        SystemGear.hostname = socket.gethostname()
        SystemGear.config = config
        super(SystemGear, self).__init__(
            gear_id='ariane.community.plugin.procos.gears.cache.system_gear@'+SystemGear.hostname,
            gear_name='procos_system_gear@'+SystemGear.hostname,
            gear_description='Ariane ProcOS system gear for '+SystemGear.hostname,
            gear_admin_queue='ariane.community.plugin.procos.gears.cache.system_gear@'+SystemGear.hostname,
            running=False
        )
        self.component = SystemComponent.start(attached_gear_id=self.gear_id(), hostname=SystemGear.hostname).proxy()
        self.sleeping_period = config.sleeping_period
        self.service = None
        self.service_name = 'system_procos@'+SystemGear.hostname+' gear'
        self.directory_gear = DirectoryGear.start().proxy()
        self.mapping_gear = MappingGear.start().proxy()

    def run(self):
        if self.sleeping_period is not None and self.sleeping_period > 0:
            self.directory_gear.init_ariane_directories(self.component)
            while self.running:
                time.sleep(self.sleeping_period)
                self.component.sniff()
                self.directory_gear.synchronize_with_ariane_directories(self.component)
                self.mapping_gear.synchronize_with_ariane_mapping(self.component)

    def on_start(self):
        self.running = True
        self.cache(running=self.running)
        self.service = threading.Thread(target=self.run, name=self.service_name)
        self.service.start()

    def on_stop(self):
        if self.running:
            self.running = False
            self.cache(running=self.running)
        self.service = None
        self.component.service.get().stop()
        self.directory_gear.stop()
        self.mapping_gear.stop()
        self.cached_gear_actor.remove().get()
        self.cached_gear_actor.stop()

    def gear_start(self):
        if self.service is not None:
            self.running = True
            self.service.start()
            self.cache(running=self.running)
        else:
            self.on_start()

    def gear_stop(self):
        if self.running:
            self.running = False
            self.cache(running=self.running)