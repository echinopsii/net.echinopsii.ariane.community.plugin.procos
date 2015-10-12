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
import logging
import os
import socket
import threading
import time
import timeit
import traceback
from ariane_clip3.mapping import ContainerService, Container, NodeService, Node, Endpoint, EndpointService, Transport, \
    Link
from ariane_clip3.directory import LocationService, Location, RoutingAreaService, RoutingArea, OSInstanceService,\
    OSInstance, SubnetService, Subnet, IPAddressService, IPAddress, EnvironmentService, Environment, TeamService, Team,\
    OSTypeService, OSType, Company, CompanyService
from ariane_clip3.injector import InjectorGearSkeleton
from ariane_procos.components import SystemComponent
from ariane_procos.config import RoutingAreaConfig, SubnetConfig
from ariane_procos.system import NetworkInterfaceCard, MapSocket

__author__ = 'mffrench'

LOGGER = logging.getLogger(__name__)


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

    def gear_start(self):
        LOGGER.warn('procos_directory_gear@'+SystemGear.hostname+' has been started.')
        self.on_start()

    def gear_stop(self):
        if self.running:
            LOGGER.warn('procos_directory_gear@'+SystemGear.hostname+' has been stopped.')
            self.running = False
            self.cache(running=self.running)

    def compute_current_possible_network(self, operating_system):
        # Find current Location, routing area and subnets according to runtime IP on NICs and possible locations:
        current_possible_location_config = []
        current_possible_routing_area_config = []
        current_possible_subnet_config = []

        current_possible_remote_vpn_location_config = []
        current_possible_remote_vpn_routing_area_config = []
        current_possible_remote_vpn_subnet_config = []

        for nic in operating_system.nics:
            nic_is_located = False
            try:
                if nic.ipv4_address is not None:
                    if not nic.ipv4_address.startswith('127'):
                        for location_config in SystemGear.config.potential_locations:
                            for routing_area_config in location_config.routing_areas:
                                for subnet_config in routing_area_config.subnets:

                                    if NetworkInterfaceCard.ip_is_in_subnet(nic.ipv4_address,
                                                                            subnet_config.subnet_ip,
                                                                            subnet_config.subnet_mask):
                                        if routing_area_config.type == RoutingArea.RA_TYPE_VPN:
                                                current_possible_remote_vpn_location_config.append(location_config)
                                                current_possible_remote_vpn_routing_area_config.append(
                                                    routing_area_config)
                                                current_possible_remote_vpn_subnet_config.append(subnet_config)
                                                nic_is_located = True
                                                break
                                        else:
                                            if location_config not in current_possible_location_config:
                                                current_possible_location_config.append(location_config)
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
                                LOGGER.warn('nic ' + nic.mac_address + '/' + nic.ipv4_address +
                                            ' has not been located on the possibles networks')
                            else:
                                LOGGER.warn('nic ' + nic.ipv4_address +
                                            ' has not been located on the possibles networks')

            except Exception as e:
                print(e.__str__())

        if current_possible_location_config.__len__() > 1:
            LOGGER.warn('multiple current possible location found - will ignore directories sync')
        elif current_possible_location_config.__len__() == 0:
            LOGGER.warn('no current possible location found - will ignore directories sync')

        if current_possible_location_config.__len__() != 1:
            self.is_network_sync_possible = False
        if current_possible_routing_area_config.__len__() == 0:
            self.is_network_sync_possible = False
        if current_possible_subnet_config.__len__() == 0:
            self.is_network_sync_possible = False

        self.current_possible_network = [
            current_possible_location_config,
            current_possible_routing_area_config,
            current_possible_subnet_config,
            current_possible_remote_vpn_location_config,
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
            LOGGER.error('operating system instance is not synced')
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
            LOGGER.error('operating system instance is not synced')
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
                        description=SystemGear.config.organisation_context.environment.description,
                        color_code=SystemGear.config.organisation_context.environment.color_code
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
            LOGGER.error('operating system instance is not synced')
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
            LOGGER.error('operating system instance is not synced')
            return

        # Sync network stuffs
        current_possible_location_config = self.current_possible_network[0]
        current_possible_routing_area_config = self.current_possible_network[1]
        current_possible_subnet_config = self.current_possible_network[2]
        current_possible_remote_vpn_location_config = self.current_possible_network[3]
        current_possible_remote_vpn_routing_area_config = self.current_possible_network[4]
        current_possible_remote_vpn_subnet_config = self.current_possible_network[5]

        current_location = current_possible_location_config[0]

        # Sync location
        if operating_system.location_id is not None:
            SystemGear.location = LocationService.find_location(operating_system.location_id)
            if SystemGear.location is not None and SystemGear.location.name != current_location.name:
                # This OS has moved
                LOGGER.debug("operating system has a new location !")
                SystemGear.location = None
                operating_system.location_id = None

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

        if SystemGear.location is None:
            SystemGear.location = LocationService.find_location(loc_name=current_location.name)
            if SystemGear.location is None:
                SystemGear.location = Location(name=current_location.name,
                                               description=current_location.description,
                                               type=current_location.type,
                                               address=current_location.address,
                                               zip_code=current_location.zipcode,
                                               town=current_location.town,
                                               country=current_location.country,
                                               gps_latitude=current_location.gps_lat,
                                               gps_longitude=current_location.gps_lng)
                SystemGear.location.save()
            operating_system.location_id = SystemGear.location.id

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

        for remote_vpn_loc_config in current_possible_remote_vpn_location_config:
            vpn_loc = LocationService.find_location(loc_name=remote_vpn_loc_config.name)
            if vpn_loc is None:
                vpn_loc = Location(
                    name=remote_vpn_loc_config.name,
                    description=remote_vpn_loc_config.description,
                    address=remote_vpn_loc_config.address,
                    zip_code=remote_vpn_loc_config.zipcode,
                    town=remote_vpn_loc_config.town,
                    country=remote_vpn_loc_config.country,
                    gps_latitude=remote_vpn_loc_config.gps_lat,
                    gps_longitude=remote_vpn_loc_config.gps_lng
                )
                vpn_loc.save()

            for remote_routing_area_config in remote_vpn_loc_config.routing_areas:
                if remote_routing_area_config in current_possible_remote_vpn_routing_area_config:
                    vpn_ra = RoutingAreaService.find_routing_area(ra_name=remote_routing_area_config.name)
                    if vpn_ra is None:
                        vpn_ra = RoutingArea(name=remote_routing_area_config.name,
                                             multicast=remote_routing_area_config.multicast,
                                             ra_type=remote_routing_area_config.type,
                                             description=remote_routing_area_config.description)
                        vpn_ra.save()
                    vpn_ra.add_location(SystemGear.location)
                    vpn_ra.add_location(vpn_loc)
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
                            vpn_subnet.add_location(SystemGear.location)
                            vpn_subnet.add_location(vpn_loc)
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
                routing_area.add_location(SystemGear.location)
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
                        subnet.add_location(SystemGear.location)
                    operating_system.subnet_ids.append(subnet.id)
                    SystemGear.subnets.append(subnet)
                    if subnet.id not in SystemGear.osi.subnet_ids:
                        SystemGear.osi.add_subnet(subnet)

        SystemGear.osi.sync()
        for ipv4_id in SystemGear.osi.ip_address_ids:
            ipv4 = IPAddressService.find_ip_address(ipa_id=ipv4_id)
            to_be_removed = True
            if ipv4 is not None:
                for nic in operating_system.nics:
                    if nic is not None and nic.ipv4_address == ipv4.ip_address:
                        to_be_removed = False
                if to_be_removed:
                    ipv4.remove()
            else:
                LOGGER.error("sync error on IP ("+str(ipv4_id)+")")
                SystemGear.osi.ip_address_ids.remove(ipv4_id)

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
                            subnet.is_default = nic.is_default
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
                    operating_system.routing_area_ids.append(local_routing_area.id)
                    SystemGear.routing_areas.append(local_routing_area)

                    loopback_subnet = SubnetService.find_subnet(sb_name=SystemGear.hostname+".loopback")
                    if loopback_subnet is not None:
                        loopback_subnet.remove()

                    loopback_subnet = Subnet(name=SystemGear.hostname+".loopback",
                                             description=SystemGear.hostname + " loopback subnet",
                                             routing_area_id=local_routing_area.id,
                                             ip='127.0.0.0', mask='255.0.0.0')
                    loopback_subnet.save()
                    loopback_subnet.add_location(SystemGear.location)
                    local_routing_area.sync()

                    SystemGear.osi.add_subnet(loopback_subnet)
                    operating_system.subnet_ids.append(loopback_subnet.id)
                    SystemGear.subnets.append(loopback_subnet)

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
            LOGGER.error(e.__str__())

    def update_ariane_directories(self, operating_system):
        # check last / new sniff diff on nics
        if self.is_network_sync_possible:
            try:
                if operating_system.last_nics != operating_system.nics:
                    if self.is_network_sync_possible:
                        self.sync_network(operating_system)
                else:
                    LOGGER.debug('NO CHANGES WITH LAST SNIFF')
            except Exception as e:
                LOGGER.error(e.__str__())
                LOGGER.error(traceback.format_exc())
        else:
            LOGGER.warn('DIRECTORIES SYNC ARE IGNORED')

    def synchronize_with_ariane_directories(self, component):
        if self.running:
            operating_system = component.operating_system.get()
            self.update_ariane_directories(operating_system)
            self.update_count += 1
        else:
            LOGGER.warn("Synchronization requested but procos_directory_gear@"+SystemGear.hostname+" is not running.")


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

    def gear_start(self):
        LOGGER.warn('procos_mapping_gear@'+SystemGear.hostname+' has been started.')
        self.on_start()

    def gear_stop(self):
        if self.running:
            LOGGER.warn('procos_mapping_gear@'+SystemGear.hostname+' has been stopped.')
            self.running = False
            self.cache(running=self.running)

    @staticmethod
    def sync_container_network(container, location, routing_areas, subnets):
        if location is not None:
            location_properties = {
                Container.PL_NAME_MAPPING_FIELD: location.name,
                Container.PL_ADDR_MAPPING_FIELD: location.address,
                Container.PL_TOWN_MAPPING_FIELD: location.town,
                Container.PL_CNTY_MAPPING_FIELD: location.country,
                Container.PL_GPSA_MAPPING_FIELD: location.gpsLatitude,
                Container.PL_GPSN_MAPPING_FIELD: location.gpsLongitude
            }
            container.add_property((Container.PL_MAPPING_PROPERTIES, location_properties))

        if routing_areas is not None:
            network_properties = []
            for routing_area in routing_areas:
                routing_area_subnets = []
                for subnet in subnets:
                    if subnet.id in routing_area.subnet_ids:
                        routing_area_subnets.append(
                            {
                                Container.SUBNET_NAME_MAPPING_FIELD: subnet.name,
                                Container.SUBNET_IPAD_MAPPING_FIELD: subnet.ip,
                                Container.SUBNET_MASK_MAPPING_FIELD: subnet.mask,
                                Container.SUBNET_ISDEFAULT_MAPPING_FIELD: subnet.is_default
                            }
                        )
                network_properties.append(
                    {
                        Container.RAREA_NAME_MAPPING_FIELD: routing_area.name,
                        Container.RAREA_MLTC_MAPPING_FIELD: routing_area.multicast,
                        Container.RAREA_TYPE_MAPPING_FIELD: routing_area.type,
                        Container.RAREA_SUBNETS: routing_area_subnets
                    }
                )
            if network_properties.__len__() > 0:
                container.add_property((Container.NETWORK_MAPPING_PROPERTIES, network_properties))

    def sync_container_properties(self):
        self.sync_container_network(self.osi_container, SystemGear.location, SystemGear.routing_areas,
                                    SystemGear.subnets)
        if SystemGear.team is not None:
            team_properties = {
                Container.TEAM_NAME_MAPPING_FIELD: SystemGear.team.name,
                Container.TEAM_COLR_MAPPING_FIELD: SystemGear.team.color_code
            }
            self.osi_container.add_property((Container.TEAM_SUPPORT_MAPPING_PROPERTIES, team_properties))

    def sync_container(self, operating_system):
        if self.osi_container is None and operating_system.container_id is not None:
            self.osi_container = ContainerService.find_container(cid=operating_system.container_id)
            if self.osi_container is None:
                LOGGER.error('consistency error between ProcOS cache and mapping DB (' +
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
            LOGGER.debug('operating_system.container_id : (' + SystemGear.hostname + ',' +
                         str(operating_system.container_id) + ')')
        self.sync_container_properties()

    @staticmethod
    def sync_remote_container_network(target_os_instance, target_container):
        target_possible_locations = []
        target_routing_areas = []
        target_subnets = []

        for subnet_id in target_os_instance.subnet_ids:
            target_subnet = SubnetService.find_subnet(
                sb_id=subnet_id
            )
            if target_subnet is not None and target_subnet not in target_subnets:
                target_subnets.append(target_subnet)
                target_routing_area = RoutingAreaService.find_routing_area(
                    ra_id=target_subnet.routing_area_id
                )
                if target_routing_area is not None and target_routing_area not in target_routing_areas:
                    target_routing_areas.append(target_routing_area)
                    for location_id in target_routing_area.loc_ids:
                        target_possible_location = LocationService.find_location(
                            loc_id=location_id
                        )
                        if target_possible_location is not None and \
                                target_possible_location not in target_possible_locations:
                            target_possible_locations.append(target_possible_location)

        if target_possible_locations.__len__() == 1:
            target_location = target_possible_locations[0]
            MappingGear.sync_container_network(target_container, target_location, target_routing_areas, target_subnets)
        else:
            LOGGER.warn("REMOTE CONTAINER LOCALISATION HAS NOT BEEN FOUND")

    @staticmethod
    def sync_remote_container_team(target_os_instance, target_container):
        teams_props = []
        for team_id in target_os_instance.team_ids:
            team = TeamService.find_team(team_id)
            team_properties = {
                Container.TEAM_NAME_MAPPING_FIELD: team.name,
                Container.TEAM_COLR_MAPPING_FIELD: team.color_code
            }
            teams_props.append(team_properties)
        target_container.add_property((Container.TEAM_SUPPORT_MAPPING_PROPERTIES, teams_props))

    def sync_map_socket(self, operating_system):
        if self.osi_container is None:
            LOGGER.error('operating system container is not synced')
            return

        t = timeit.default_timer()
        for proc in operating_system.processs:
            if proc.mapping_id is not None and proc.new_map_sockets is not None:
                exe_tab = proc.exe.split(os.path.sep)
                name = '[' + str(proc.pid) + '] ' + exe_tab[exe_tab.__len__() - 1]
                LOGGER.debug(str(proc.new_map_sockets.__len__()) + ' new socket found for process ' + name)
                for map_socket in proc.new_map_sockets:
                    if map_socket.source_ip is not None and map_socket.source_port is not None:

                        if map_socket.source_port == SystemGear.config.system_context.admin_gate_port and \
                                map_socket.status == "LISTEN":
                            LOGGER.debug("gate process found (" + name + ")")
                            continue

                        proto = None
                        if map_socket.type == "SOCK_STREAM":
                            proto = "tcp://"
                        elif map_socket.type == "SOCK_DGRAM":
                            proto = "udp://"
                        else:
                            LOGGER.warn("socket type " + map_socket.type + " currently not supported !")

                        if proto is not None:
                            if proc.is_node:
                                source_parent_node_id = proc.mapping_id
                            else:
                                source_parent_node_id = 0
                                LOGGER.warn("process as container not yet implemented !")

                            if source_parent_node_id != 0:
                                source_url = proto + map_socket.source_ip + ":" + str(map_socket.source_port) + \
                                    str(map_socket.file_descriptors) if map_socket.status != "LISTEN" else ""

                                source_endpoint = Endpoint(url=source_url, parent_node_id=proc.mapping_id)
                                source_endpoint.add_property(('type', map_socket.type))
                                source_endpoint.add_property(('family', map_socket.family))
                                source_endpoint.add_property(('status', map_socket.status))
                                source_endpoint.add_property(('file descriptors', map_socket.file_descriptors))
                                source_endpoint.save()
                                map_socket.source_endpoint_id = source_endpoint.id
                                LOGGER.debug('source socket endpoint on mapping db : (' + source_url + ',' +
                                             str(map_socket.source_endpoint_id) + ')')

                                if map_socket.destination_ip is not None and map_socket.destination_port is not None:
                                    target_url = proto + map_socket.destination_ip + ":" + \
                                        str(map_socket.destination_port)

                                    target_fqdn = None
                                    try:
                                        if map_socket.family == "AF_INET":
                                            target_fqdn = socket.gethostbyaddr(map_socket.destination_ip)[0]
                                        elif map_socket.family == "AF_INET6":
                                            target_fqdn = socket.gethostbyaddr(MapSocket.ipv6_2_ipv4(
                                                map_socket.destination_ip))[0]

                                    except socket.herror as e:
                                        LOGGER.debug(str(map_socket))
                                        LOGGER.debug(e.__str__())
                                        LOGGER.debug(traceback.format_exc())
                                    except OSError as e:
                                        LOGGER.debug(str(map_socket))
                                        LOGGER.debug(e.__str__())
                                        LOGGER.debug(traceback.format_exc())

                                    destination_is_local = map_socket.is_local_destination(operating_system)
                                    target_container = None if not destination_is_local else self.osi_container
                                    target_node = None
                                    target_endpoint = None

                                    if target_fqdn is not None:
                                        target_ipa = IPAddressService.find_ip_address(ipa_fqdn=target_fqdn)
                                        if target_ipa is not None:
                                            target_os_instance = OSInstanceService.find_os_instance(
                                                osi_id=target_ipa.ipa_os_instance_id
                                            )
                                            if target_os_instance is not None:
                                                if target_container is None:
                                                    target_container = ContainerService.find_container(
                                                        primary_admin_gate_url=target_os_instance.admin_gate_uri
                                                    )
                                                if target_container is None:
                                                    target_os_instance_type = OSTypeService.find_ostype(
                                                        ost_id=target_os_instance.ost_id
                                                    )
                                                    product = target_os_instance_type.name + " - " + \
                                                        target_os_instance_type.architecture \
                                                        if target_os_instance_type is not None else\
                                                        "Unknown OS Type",

                                                    target_os_instance_type_cmp = CompanyService.find_company(
                                                        cmp_id=target_os_instance_type.company_id
                                                    ) if target_os_instance_type is not None else None
                                                    company = target_os_instance_type_cmp.name\
                                                        if target_os_instance_type_cmp is not None else\
                                                        "Unknown OS Type Company"

                                                    name = target_fqdn if target_fqdn is not None else\
                                                        map_socket.destination_ip

                                                    target_container = Container(
                                                        name=name,
                                                        gate_uri=target_os_instance.admin_gate_uri,
                                                        primary_admin_gate_name=target_fqdn + " Primary Admin Gate",
                                                        company=company,
                                                        product=product,
                                                        c_type="Operating System"
                                                    )
                                                    target_container.save()
                                            MappingGear.sync_remote_container_network(target_os_instance,
                                                                                      target_container)
                                            MappingGear.sync_remote_container_team(target_os_instance,
                                                                                   target_container)
                                    if target_container is None:
                                        target_container = Container(
                                            name=target_fqdn if target_fqdn is not None else map_socket.destination_ip,
                                            gate_uri="not_my_concern://"+map_socket.destination_ip,
                                            primary_admin_gate_name="External OS Primary Admin Gate"
                                        )
                                        target_container.save()

                                    if not destination_is_local:
                                        target_node = NodeService.find_node(
                                            endpoint_url=target_url
                                        )
                                        if target_node is None:
                                            addr = target_fqdn if target_fqdn is not None else map_socket.destination_ip
                                            target_node = Node(
                                                name=addr + ':' + str(map_socket.destination_port),
                                                container_id=target_container.id
                                            )
                                            target_node.save()
                                        target_endpoint = EndpointService.find_endpoint(
                                            url=target_url
                                        )
                                        if target_endpoint is None:
                                            target_endpoint = Endpoint(
                                                url=target_url, parent_node_id=target_node.id
                                            )
                                        target_endpoint.save()
                                    else:
                                        for proc_srv in operating_system.processs:
                                            for srv_socket in proc_srv.map_sockets:
                                                map_ipv4_ap = map_socket.transform_system_ipv6_to_ipv4()
                                                srv_ipv4_ap = srv_socket.transform_system_ipv6_to_ipv4()

                                                srv_source_ip = srv_ipv4_ap[0]
                                                srv_destination_ip = srv_ipv4_ap[1]
                                                map_source_ip = map_ipv4_ap[0]
                                                map_destination_ip = map_ipv4_ap[1]

                                                if srv_source_ip == map_destination_ip and\
                                                        srv_socket.source_port == map_socket.destination_port and\
                                                        srv_destination_ip == map_source_ip and\
                                                        srv_socket.destination_port == map_socket.source_port:
                                                    if proc_srv.is_node:
                                                        target_node = NodeService.find_node(nid=proc_srv.mapping_id)
                                                    else:
                                                        LOGGER.warn("process as container not yet implemented !")
                                                    target_url += str(srv_socket.file_descriptors)
                                                    if target_node is not None:
                                                        target_endpoint = EndpointService.find_endpoint(
                                                            url=target_url
                                                        )
                                                        if target_endpoint is None:
                                                            target_endpoint = Endpoint(
                                                                url=target_url, parent_node_id=target_node.id
                                                            )
                                                            target_endpoint.add_property(('type', srv_socket.type))
                                                            target_endpoint.add_property(('family', srv_socket.family))
                                                            target_endpoint.add_property(('status', srv_socket.status))
                                                            target_endpoint.add_property(('file descriptors',
                                                                                          srv_socket.file_descriptors))
                                                            target_endpoint.save()
                                                    break

                                    if target_endpoint is not None:
                                        map_socket.destination_endpoint_id = target_endpoint.id
                                    if target_node is not None:
                                        map_socket.destination_node_id = target_node.id
                                    map_socket.destination_container_id = target_container.id

                                    if map_socket.destination_endpoint_id is not None and \
                                            map_socket.source_endpoint_id is not None:
                                        transport = Transport(name=proto)
                                        transport.save()
                                        if transport is not None:
                                            link = Link(source_endpoint_id=map_socket.source_endpoint_id,
                                                        target_endpoint_id=map_socket.destination_endpoint_id,
                                                        transport_id=transport.id)
                                            link.save()
                                            map_socket.transport_id = transport.id
                                            map_socket.link_id = link.id
                                    else:
                                        LOGGER.debug('missing destination endpoint id for ' + str(map_socket))

                    else:
                        LOGGER.debug('no source ip / port - ' + str(map_socket))

            if proc.mapping_id is not None and proc.dead_map_sockets is not None:
                exe_tab = proc.exe.split(os.path.sep)
                name = '[' + str(proc.pid) + '] ' + exe_tab[exe_tab.__len__() - 1]
                LOGGER.debug(str(proc.dead_map_sockets.__len__()) + ' dead socket found for process ['
                             + str(proc.mapping_id) + ']' + name)
                for map_socket in proc.dead_map_sockets:
                    if map_socket.source_endpoint_id is not None:
                        source_endpoint = EndpointService.find_endpoint(eid=map_socket.source_endpoint_id)
                        if source_endpoint is not None:
                            source_endpoint.remove()
                    if map_socket.destination_endpoint_id is not None:
                        target_endpoint = EndpointService.find_endpoint(eid=map_socket.destination_endpoint_id)
                        if target_endpoint is not None:
                            target_endpoint.remove()

        sync_proc_time = round(timeit.default_timer()-t)
        LOGGER.debug('time : {0}'.format(sync_proc_time))

    def sync_processs(self, operating_system):
        if self.osi_container is None:
            LOGGER.error('operating system container is not synced')
            return

        t = timeit.default_timer()
        LOGGER.debug(str(operating_system.new_processs.__len__()) + ' new processes found')
        for process in operating_system.new_processs:
            exe_tab = process.exe.split(os.path.sep)
            name = '[' + str(process.pid) + '] ' + exe_tab[exe_tab.__len__() - 1]

            process_map_obj = Node(
                name=name,
                container=self.osi_container
            )
            process_map_obj.add_property(('pid', process.pid), sync=False)
            process_map_obj.add_property(('exe', process.exe), sync=False)
            process_map_obj.add_property(('cwd', process.cwd), sync=False)
            process_map_obj.add_property(('creation time', process.create_time), sync=False)
            process_map_obj.add_property(('username', process.username), sync=False)
            process_map_obj.add_property(('uids', process.uids), sync=False)
            process_map_obj.add_property(('gids', process.gids), sync=False)
            if process.terminal is not None:
                process_map_obj.add_property(('terminal', process.terminal), sync=False)
            if process.cpu_affinity is not None:
                process_map_obj.add_property(('cpu_affinity', process.cpu_affinity), sync=False)
            process_map_obj.save()
            process_map_obj.add_property(('cmdline', process.cmdline))
            process.mapping_id = process_map_obj.id
            LOGGER.debug('new process on mapping db : (' + name + ',' + str(process.mapping_id) + ')')

        LOGGER.debug(str(operating_system.dead_processs.__len__()) + ' old processes found')
        for process in operating_system.dead_processs:
            process_map_obj = None
            exe_tab = process.exe.split(os.path.sep)
            name = '[' + str(process.pid) + '] ' + exe_tab[exe_tab.__len__() - 1]
            if process.mapping_id is None:
                LOGGER.error('dead process (' + name + ') has not been saved on mapping db !')
            else:
                if process.is_node:
                    process_map_obj = NodeService.find_node(nid=process.mapping_id)
                else:
                    process_map_obj = ContainerService.find_container(cid=process.mapping_id)
                if process_map_obj is None:
                    LOGGER.error('consistency error between ProcOS cache and mapping DB (' + name + ',' +
                                 str(process.mapping_id) + ')')
                else:
                    process_map_obj.remove()

        sync_proc_time = round(timeit.default_timer()-t)
        LOGGER.debug('time : {0}'.format(sync_proc_time))

    def synchronize_with_ariane_mapping(self, component):
        if self.running:
            operating_system = component.operating_system.get()
            try:
                self.sync_container(operating_system)
                self.sync_processs(operating_system)
                self.sync_map_socket(operating_system)
            except Exception as e:
                LOGGER.error(e.__str__())
                LOGGER.error(traceback.format_exc())
            self.update_count += 1
        else:
            LOGGER.warn('Synchronization requested but procos_mapping_gear@'+SystemGear.hostname+' is not running.')


class SystemGear(InjectorGearSkeleton):
    #static reference on commons var
    config = None
    hostname = None

    #static reference to up to date ariane directories objects linked to this System
    location = None
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
            gear_id='ariane.community.plugin.procos.gears.cache.system_gear@'+str(SystemGear.hostname),
            gear_name='procos_system_gear@'+str(SystemGear.hostname),
            gear_description='Ariane ProcOS system gear for '+str(SystemGear.hostname),
            gear_admin_queue='ariane.community.plugin.procos.gears.cache.system_gear@'+str(SystemGear.hostname),
            running=False
        )
        self.sleeping_period = config.sleeping_period
        self.service = None
        self.service_name = 'system_procos@'+str(SystemGear.hostname)+' gear'
        component_type = SystemGear.config.system_context.os_type.name + " - " + \
            SystemGear.config.system_context.os_type.architecture
        self.component = SystemComponent.start(
            attached_gear_id=self.gear_id(),
            hostname=SystemGear.hostname,
            component_type=component_type,
            system_gear_actor_ref=self.actor_ref
        ).proxy()
        self.directory_gear = DirectoryGear.start().proxy()
        self.mapping_gear = MappingGear.start().proxy()

    def synchronize_with_ariane_dbs(self):
        LOGGER.info("Synchonize with Ariane DBs...")
        self.directory_gear.synchronize_with_ariane_directories(self.component)
        self.mapping_gear.synchronize_with_ariane_mapping(self.component)

    def run(self):
        if self.sleeping_period is not None and self.sleeping_period > 0:
            while self.running:
                time.sleep(self.sleeping_period)
                if self.running:
                    self.component.sniff().get()

    def on_start(self):
        self.cache(running=self.running)
        LOGGER.warn("Initializing...")
        self.directory_gear.init_ariane_directories(self.component).get()
        self.component.sniff(synchronize_with_ariane_dbs=False).get()
        LOGGER.info("Synchonize with Ariane DBs...")
        self.directory_gear.synchronize_with_ariane_directories(self.component).get()
        self.mapping_gear.synchronize_with_ariane_mapping(self.component).get()
        LOGGER.warn("Initialization done.")
        self.running = True
        self.cache(running=self.running)
        self.service = threading.Thread(target=self.run, name=self.service_name)
        self.service.start()

    def on_stop(self):
        try:
            if self.running:
                self.running = False
                self.cache(running=self.running)
            self.service = None
            self.component.stop().get()
            self.directory_gear.stop().get()
            self.mapping_gear.stop().get()
            self.cached_gear_actor.remove().get()
        except Exception as e:
            LOGGER.error(e.__str__())
            LOGGER.error(traceback.format_exc())

    def gear_start(self):
        if self.service is not None:
            LOGGER.warn('procos_system_gear@'+str(SystemGear.hostname)+' has been started')
            self.running = True
            self.service = threading.Thread(target=self.run, name=self.service_name)
            self.service.start()
            self.cache(running=self.running)
        else:
            LOGGER.warn('procos_system_gear@'+str(SystemGear.hostname)+' has been restarted')
            self.on_start()

    def gear_stop(self):
        if self.running:
            LOGGER.warn('procos_system_gear@'+str(SystemGear.hostname)+' has been stopped')
            self.running = False
            self.cache(running=self.running)
