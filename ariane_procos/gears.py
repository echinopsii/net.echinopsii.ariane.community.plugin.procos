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
import socket
import threading
import time
import timeit
import traceback
from ariane_clip3.exceptions import ArianeMessagingTimeoutError
from ariane_clip3.mapping import ContainerService, Container, NodeService, Node, Endpoint, EndpointService, Transport, \
    Link, LinkService, SessionService, Gate, GateService
from ariane_clip3.directory import LocationService, Location, RoutingAreaService, RoutingArea, OSInstanceService,\
    OSInstance, SubnetService, Subnet, IPAddressService, IPAddress, EnvironmentService, Environment, TeamService, Team,\
    OSTypeService, OSType, Company, CompanyService, NICService, NIC
from ariane_clip3.injector import InjectorGearSkeleton
from ariane_procos.components import SystemComponent
from ariane_procos.config import RoutingAreaConfig, SubnetConfig
from ariane_procos.system import NetworkInterfaceCard, MapSocket
from ariane_clip3.domino import DominoActivator

__author__ = 'mffrench'

LOGGER = logging.getLogger(__name__)


class DirectoryGear(InjectorGearSkeleton):
    def __init__(self):
        LOGGER.debug("DirectoryGear.__init__")
        super(DirectoryGear, self).__init__(
            gear_id='ariane.community.plugin.procos.gears.cache.directory_gear@' + str(SystemGear.hostname),
            gear_name='procos_directory_gear@' + str(SystemGear.hostname),
            gear_description='Ariane ProcOS directory gear for ' + str(SystemGear.hostname),
            gear_admin_queue='ariane.community.plugin.procos.gears.cache.directory_gear@' + str(SystemGear.hostname),
            running=False
        )
        self.update_count = 0
        self.is_network_sync_possible = True
        self.current_possible_network = []

    def on_start(self):
        LOGGER.debug("DirectoryGear.on_start")
        self.running = True
        self.cache(running=self.running)

    def on_stop(self):
        LOGGER.debug("DirectoryGear.on_stop")
        if self.running:
            self.running = False
            self.cache(running=self.running)

    def on_failure(self, exception_type, exception_value, traceback_):
        LOGGER.debug("DirectoryGear.on_failure")
        LOGGER.error("DirectoryGear.on_failure - " + exception_type.__str__() + "/" + exception_value.__str__())
        LOGGER.error("DirectoryGear.on_failure - " + traceback_.format_exc())
        if self.running:
            self.running = False
            self.cache(running=self.running)

    def gear_start(self):
        LOGGER.debug("DirectoryGear.gear_start")
        self.on_start()
        LOGGER.info('procos_directory_gear@' + str(SystemGear.hostname) + ' has been started.')

    def gear_stop(self):
        LOGGER.debug("DirectoryGear.gear_stop")
        if self.running:
            self.running = False
            self.cache(running=self.running)
            LOGGER.info('procos_directory_gear@' + str(SystemGear.hostname) + ' has been stopped.')

    def compute_current_possible_network(self, operating_system):
        LOGGER.debug("DirectoryGear.compute_current_possible_network")
        # Find current Location, routing area and subnets according to runtime IP on NICs and possible locations:
        current_possible_location_config = []
        current_possible_routing_area_config = []
        current_possible_subnet_config = []

        current_possible_remote_vpn_location_config = []
        current_possible_remote_vpn_routing_area_config = []
        current_possible_remote_vpn_subnet_config = []

        local_routing_area = SystemGear.config.local_routing_area
        if local_routing_area is not None:
            local_routing_area.name = SystemGear.hostname+".local"
            local_routing_area.description = SystemGear.hostname+".local routing area"
            local_routing_area.multicast = RoutingArea.RA_MULTICAST_NOLIMIT
            local_routing_area.ra_type = RoutingArea.RA_TYPE_VIRT
        else:
            local_routing_area = RoutingAreaConfig(
                name=SystemGear.hostname+".local",
                description=SystemGear.hostname+".local routing area",
                multicast=RoutingArea.RA_MULTICAST_NOLIMIT,
                ra_type=RoutingArea.RA_TYPE_VIRT
            )
        local_virt_subnet_config = []

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
                                            current_possible_remote_vpn_routing_area_config.append(routing_area_config)
                                            current_possible_remote_vpn_subnet_config.append(subnet_config)
                                        else:
                                            if location_config not in current_possible_location_config:
                                                current_possible_location_config.append(location_config)
                                            current_possible_routing_area_config.append(routing_area_config)
                                            current_possible_subnet_config.append(subnet_config)
                                        nic_is_located = True
                                        current_fqdn = socket.gethostbyaddr(nic.ipv4_address)[0]
                                        if current_fqdn is not None:
                                            SystemGear.fqdn = current_fqdn
                                        break
                                if nic_is_located:
                                    break
                            if nic_is_located:
                                break

                        if not nic_is_located:
                            for subnet_config in local_routing_area.subnets:
                                if NetworkInterfaceCard.ip_is_in_subnet(nic.ipv4_address,
                                                                        subnet_config.subnet_ip,
                                                                        subnet_config.subnet_mask):
                                    local_virt_subnet_config.append(subnet_config)
                                    nic_is_located = True
                                    break

                        if not nic_is_located:
                            if nic.mac_address is not None:
                                LOGGER.warn('DirectoryGear.compute_current_possible_network - '
                                            'nic ' + nic.mac_address + '/' + nic.ipv4_address +
                                            ' has not been located on the possibles networks')
                            else:
                                LOGGER.warn('DirectoryGear.compute_current_possible_network - '
                                            'nic ' + nic.ipv4_address +
                                            ' has not been located on the possibles networks')

            except Exception as e:
                print(e.__str__())

        if current_possible_location_config.__len__() > 1:
            LOGGER.warn('DirectoryGear.compute_current_possible_network - '
                        'multiple current possible location found - will ignore directories sync')
        elif current_possible_location_config.__len__() == 0:
            LOGGER.warn('DirectoryGear.compute_current_possible_network - '
                        'no current possible location found - will ignore directories sync')

        if current_possible_location_config.__len__() != 1:
            self.is_network_sync_possible = False
        if current_possible_routing_area_config.__len__() == 0:
            self.is_network_sync_possible = False
        if current_possible_subnet_config.__len__() == 0:
            self.is_network_sync_possible = False

        if self.is_network_sync_possible:
            if SystemGear.hostname != SystemGear.fqdn and SystemGear.fqdn is not None:
                SystemGear.osi.admin_gate_uri = SystemGear.config.system_context.admin_gate_protocol+SystemGear.fqdn
                SystemGear.osi.save()

        if SystemGear.fqdn is None:
            SystemGear.fqdn = SystemGear.hostname

        LOGGER.debug("DirectoryGear.compute_current_possible_network - FQDN : " + str(SystemGear.fqdn))

        self.current_possible_network = [
            current_possible_location_config,
            current_possible_routing_area_config,
            current_possible_subnet_config,
            current_possible_remote_vpn_location_config,
            current_possible_remote_vpn_routing_area_config,
            current_possible_remote_vpn_subnet_config,
            local_routing_area,
            local_virt_subnet_config
        ]

    @staticmethod
    def sync_operating_system(operating_system):
        LOGGER.debug("DirectoryGear.sync_operating_system")
        # Sync Operating System
        if operating_system.osi_id is not None:
            SystemGear.osi = OSInstanceService.find_os_instance(osi_id=operating_system.osi_id)
            if SystemGear.hostname.split(".").__len__() > 1 and\
               SystemGear.osi.name != SystemGear.hostname.split(".")[0]:
                SystemGear.osi = None
                operating_system.osi_id = None
            elif SystemGear.osi.name != SystemGear.hostname:
                SystemGear.osi = None
                operating_system.osi_id = None

        if SystemGear.osi is None:
            if SystemGear.hostname.split(".").__len__() > 1:
                SystemGear.osi = OSInstanceService.find_os_instance(osi_name=SystemGear.hostname.split(".")[0])
                if SystemGear.osi is None:
                    SystemGear.osi = OSInstance(
                        name=SystemGear.hostname.split(".")[0],
                        description=SystemGear.config.system_context.description,
                        admin_gate_uri=SystemGear.config.system_context.admin_gate_protocol+SystemGear.hostname)
                    SystemGear.osi.save()
                operating_system.osi_id = SystemGear.osi.id

            if SystemGear.osi is None:
                SystemGear.osi = OSInstanceService.find_os_instance(osi_name=SystemGear.hostname)
                if SystemGear.osi is None:
                    SystemGear.osi = OSInstance(
                        name=SystemGear.hostname,
                        description=SystemGear.config.system_context.description,
                        admin_gate_uri=SystemGear.config.system_context.admin_gate_protocol+SystemGear.hostname)
                    SystemGear.osi.save()
                operating_system.osi_id = SystemGear.osi.id

        # SYNC EMBEDDING OSI
        if SystemGear.config.system_context.embedding_osi_hostname is not None and \
                SystemGear.config.system_context.embedding_osi_hostname:
            embedding_osi = OSInstanceService.find_os_instance(
                osi_name=SystemGear.config.system_context.embedding_osi_hostname
            )
            if embedding_osi is not None and SystemGear.osi.embedding_osi_id is not embedding_osi.id:
                SystemGear.osi.embedding_osi_id = embedding_osi.id

        # CLEAN NICs
        for nic_id in SystemGear.osi.nic_ids:
            nic = NICService.find_nic(nic_id=nic_id)
            nic.remove()
        SystemGear.osi.nic_ids = []

    @staticmethod
    def sync_operating_system_type(operating_system):
        LOGGER.debug("DirectoryGear.sync_operating_system_type")
        if SystemGear.osi is None:
            LOGGER.error('DirectoryGear.sync_operating_system_type - operating system instance is not synced')
            return

        # Sync OS Type
        if operating_system.ost_id is not None and operating_system.ost_id != 0:
            SystemGear.ost = OSTypeService.find_ostype(ost_id=operating_system.ost_id)
            if SystemGear.ost is not None and SystemGear.osi.ost_id != SystemGear.ost.id:
                SystemGear.ost = None
                SystemGear.ost_company = None
                SystemGear.osi.ost_id = 0
                SystemGear.osi.save()

        if SystemGear.ost is None:
            SystemGear.ost_company = CompanyService.find_company(
                cmp_name=SystemGear.config.system_context.os_type.company.name
            )
            if SystemGear.ost_company is None:
                SystemGear.ost_company = Company(
                    name=SystemGear.config.system_context.os_type.company.name,
                    description=SystemGear.config.system_context.os_type.company.description
                )
                SystemGear.ost_company.save()

            SystemGear.ost = OSTypeService.find_ostype(ost_name=SystemGear.config.system_context.os_type.name,
                                                       ost_arch=SystemGear.config.system_context.os_type.architecture)
            if SystemGear.ost is None:
                SystemGear.ost = OSType(
                    name=SystemGear.config.system_context.os_type.name,
                    architecture=SystemGear.config.system_context.os_type.architecture,
                    os_type_company_id=SystemGear.ost_company.id
                )
                SystemGear.ost.save()

            if SystemGear.osi.ost_id != SystemGear.ost.id:
                SystemGear.osi.ost_id = SystemGear.ost.id
                SystemGear.osi.save()
                operating_system.ost_id = SystemGear.ost.id

    @staticmethod
    def sync_environment(operating_system):
        LOGGER.debug("DirectoryGear.sync_environment")
        if SystemGear.osi is None:
            LOGGER.error('DirectoryGear.sync_environment - operating system instance is not synced')
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
        LOGGER.debug("DirectoryGear.sync_team")
        if SystemGear.osi is None:
            LOGGER.error('DirectoryGear.sync_team - operating system instance is not synced')
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
        LOGGER.debug("DirectoryGear.sync_network")
        if SystemGear.osi is None:
            LOGGER.error('DirectoryGear.sync_network - operating system instance is not synced')
            return

        # Sync network stuffs
        current_possible_location_config = self.current_possible_network[0]
        current_possible_routing_area_config = self.current_possible_network[1]
        current_possible_subnet_config = self.current_possible_network[2]
        current_possible_remote_vpn_location_config = self.current_possible_network[3]
        current_possible_remote_vpn_routing_area_config = self.current_possible_network[4]
        current_possible_remote_vpn_subnet_config = self.current_possible_network[5]

        local_routing_area = self.current_possible_network[6]
        local_virt_subnet_config = self.current_possible_network[7]

        current_location = current_possible_location_config[0]

        # Sync location
        if operating_system.location_id is not None:
            SystemGear.location = LocationService.find_location(operating_system.location_id)
            if SystemGear.location is not None and SystemGear.location.name != current_location.name:
                # This OS has moved
                LOGGER.debug("DirectoryGear.sync_network - operating system has a new location !")
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
                                               dc_type=current_location.type,
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
                        mimic_cached_routing_area_config in current_possible_remote_vpn_routing_area_config or \
                        mimic_cached_routing_area_config != local_routing_area:
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

                elif mimic_cached_routing_area_config != local_routing_area:
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

        # CLEAN LOCAL SUBNETS FIRST
        for local_subnet_config in local_virt_subnet_config:
            subnet = SubnetService.find_subnet(sb_name=local_subnet_config.name)
            if subnet is not None:
                if subnet.id in operating_system.subnet_ids:
                    operating_system.subnet_ids.remove(subnet.id)
                if subnet in SystemGear.subnets:
                    SystemGear.subnets.remove(subnet)
                subnet.remove()

        # THEN CLEAN LOCAL RA
        loc_ra = RoutingAreaService.find_routing_area(ra_name=local_routing_area.name)
        if loc_ra is not None:
            if loc_ra.id in operating_system.routing_area_ids:
                operating_system.routing_area_ids.remove(loc_ra.id)
            if loc_ra in SystemGear.routing_areas:
                SystemGear.routing_areas.remove(loc_ra)
            loc_ra.remove()

        # FINALLY REINIT LOCAL RA AND SUBNETS
        loc_ra = RoutingArea(name=local_routing_area.name,
                             multicast=local_routing_area.multicast,
                             ra_type=local_routing_area.type,
                             description=local_routing_area.description)
        loc_ra.save()
        loc_ra.add_location(SystemGear.location)
        operating_system.routing_area_ids.append(loc_ra.id)
        SystemGear.routing_areas.append(loc_ra)

        loopback_subnet_conf = SubnetConfig(
            name=SystemGear.hostname+".loopback",
            description=SystemGear.hostname + " loopback subnet",
            subnet_ip="127.0.0.0",
            subnet_mask="255.0.0.0"
        )
        if loopback_subnet_conf not in local_virt_subnet_config:
            local_virt_subnet_config.append(loopback_subnet_conf)

        for local_subnet_config in local_virt_subnet_config:
            subnet = Subnet(name=local_subnet_config.name,
                            description=local_subnet_config.description,
                            routing_area_id=loc_ra.id,
                            ip=local_subnet_config.subnet_ip, mask=local_subnet_config.subnet_mask)
            subnet.save()
            subnet.add_location(SystemGear.location)
            loc_ra.sync()
            SystemGear.osi.add_subnet(subnet)
            operating_system.subnet_ids.append(subnet.id)
            SystemGear.subnets.append(subnet)

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
                LOGGER.error("DirectoryGear.sync_network - sync error on IP ("+str(ipv4_id)+")")
                SystemGear.osi.ip_address_ids.remove(ipv4_id)

        for nic in operating_system.nics:
            ip_address = None
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
                    loopback_subnet = SubnetService.find_subnet(sb_name=SystemGear.hostname+".loopback")
                    ip_address = IPAddressService.find_ip_address(ipa_fqdn=nic.ipv4_fqdn)
                    if ip_address is not None:
                        ip_address.remove()
                    ip_address = IPAddress(ip_address=nic.ipv4_address, fqdn=nic.ipv4_fqdn,
                                           ipa_subnet_id=loopback_subnet.id, ipa_osi_id=SystemGear.osi.id)
                    ip_address.save()
                    loopback_subnet.sync()

            if (nic.mac_address is None or not nic.mac_address) or nic.name == "lo":
                nicmcaddr = nic.ipv4_fqdn
            else:
                nicmcaddr = nic.mac_address
            if nicmcaddr is not None and nicmcaddr:
                nic2save = NICService.find_nic(nic_mac_address=nicmcaddr)
                if nic2save is None:
                    nic2save = NIC(
                        name=SystemGear.hostname+"."+nic.name,
                        mac_address=nicmcaddr,
                        duplex=nic.duplex,
                        speed=nic.speed,
                        mtu=nic.mtu,
                        nic_osi_id=operating_system.osi_id,
                        nic_ipa_id=ip_address.id if ip_address is not None else None
                    )
                else:
                    nic2save.nic_ipa_id = ip_address.id if ip_address is not None else None
                    nic2save.nic_osi_id = operating_system.osi_id
                nic2save.save()
            else:
                LOGGER.error("DirectoryGear.sync_network - Error while saving nic : " + str(nic))

    def init_ariane_directories(self, component):
        LOGGER.debug("DirectoryGear.init_ariane_directories")
        operating_system = component.operating_system.get()
        try:
            start_time = timeit.default_timer()
            self.sync_operating_system(operating_system)
            self.sync_operating_system_type(operating_system)
            self.sync_environment(operating_system)
            self.sync_team(operating_system)

            self.compute_current_possible_network(operating_system)
            if self.is_network_sync_possible:
                self.sync_network(operating_system)
            sync_proc_time = timeit.default_timer()-start_time
            LOGGER.info('DirectoryGear.init_ariane_directories - time : ' + str(sync_proc_time))
        except Exception as e:
            LOGGER.error("DirectoryGear.init_ariane_directories - " + e.__str__())
            LOGGER.debug("DirectoryGear.init_ariane_directories - " + traceback.format_exc())

    def update_ariane_directories(self, operating_system):
        LOGGER.debug("DirectoryGear.update_ariane_directories")
        # check last / new sniff diff on nics
        if self.is_network_sync_possible:
            try:
                if operating_system.last_nics != operating_system.nics:
                    self.compute_current_possible_network(operating_system)
                    if self.is_network_sync_possible:
                        self.sync_network(operating_system)
                else:
                    LOGGER.debug('DirectoryGear.update_ariane_directories - no changes with last sniff')
            except Exception as e:
                LOGGER.error("DirectoryGear.update_ariane_directories - " + e.__str__())
                LOGGER.debug("DirectoryGear.update_ariane_directories - " + traceback.format_exc())
        else:
            LOGGER.warn('DirectoryGear.update_ariane_directories - DIRECTORIES SYNC ARE IGNORED')

    def synchronize_with_ariane_directories(self, component):
        LOGGER.debug("DirectoryGear.synchronize_with_ariane_directories")
        if self.running:
            start_time = timeit.default_timer()
            operating_system = component.operating_system.get()
            self.update_ariane_directories(operating_system)
            self.update_count += 1
            sync_proc_time = timeit.default_timer()-start_time
            LOGGER.info('DirectoryGear.synchronize_with_ariane_directories - time : ' + str(sync_proc_time))
        else:
            LOGGER.warn("DirectoryGear.synchronize_with_ariane_directories - "
                        "Synchronization requested but procos_directory_gear@" + str(SystemGear.hostname) +
                        " is not running.")


class MappingGear(InjectorGearSkeleton):
    def __init__(self):
        LOGGER.debug("MappingGear.__init__")
        super(MappingGear, self).__init__(
            gear_id='ariane.community.plugin.procos.gears.cache.mapping_gear@' + str(SystemGear.hostname),
            gear_name='procos_mapping_gear@' + str(SystemGear.hostname),
            gear_description='Ariane ProcOS injector gear for ' + str(SystemGear.hostname),
            gear_admin_queue='ariane.community.plugin.procos.gears.cache.mapping_gear@' + str(SystemGear.hostname),
            running=False
        )
        self.update_count = 0
        self.osi_container = None
        self.init_done = False

    def on_start(self):
        LOGGER.debug("MappingGear.on_start")
        self.running = True
        self.cache(running=self.running)

    def on_stop(self):
        LOGGER.debug("MappingGear.on_stop")
        if self.running:
            self.running = False
            self.cache(running=self.running)

    def on_failure(self, exception_type, exception_value, traceback_):
        LOGGER.debug("MappingGear.on_failure")
        LOGGER.error("MappingGear.on_failure - " + exception_type.__str__() + "/" + exception_value.__str__())
        LOGGER.error("MappingGear.on_failure - " + traceback_.format_exc())
        if self.running:
            self.running = False
            self.cache(running=self.running)

    def gear_start(self):
        LOGGER.debug("MappingGear.gear_start")
        self.on_start()
        LOGGER.info('procos_mapping_gear@' + str(SystemGear.hostname) + ' has been started.')

    def gear_stop(self):
        LOGGER.debug("MappingGear.gear_stop")
        if self.running:
            self.running = False
            self.cache(running=self.running)
            LOGGER.info('procos_mapping_gear@' + str(SystemGear.hostname) + ' has been stopped.')

    @staticmethod
    def diff_container_network_location(container, location):
        if Container.PL_MAPPING_PROPERTIES in container.properties:
            return (
                container.properties[Container.PL_MAPPING_PROPERTIES][Container.PL_NAME_MAPPING_FIELD] != location.name or
                container.properties[Container.PL_MAPPING_PROPERTIES][Container.PL_ADDR_MAPPING_FIELD] != location.address or
                container.properties[Container.PL_MAPPING_PROPERTIES][Container.PL_TOWN_MAPPING_FIELD] != location.town or
                container.properties[Container.PL_MAPPING_PROPERTIES][Container.PL_CNTY_MAPPING_FIELD] != location.country or
                container.properties[Container.PL_MAPPING_PROPERTIES][Container.PL_GPSA_MAPPING_FIELD] != location.gpsLatitude or
                container.properties[Container.PL_MAPPING_PROPERTIES][Container.PL_GPSN_MAPPING_FIELD] != location.gpsLongitude
            )
        else:
            return True

    @staticmethod
    def sync_container_network(container, location, routing_areas, subnets):
        LOGGER.debug("MappingGear.sync_container_network")
        if location is not None and MappingGear.diff_container_network_location(container, location):
            LOGGER.debug("MappingGear.sync_container_network - add location property")
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
                if routing_area_subnets.__len__() > 0:
                    network_properties.append(
                        {
                            Container.RAREA_NAME_MAPPING_FIELD: routing_area.name,
                            Container.RAREA_MLTC_MAPPING_FIELD: routing_area.multicast,
                            Container.RAREA_TYPE_MAPPING_FIELD: routing_area.type,
                            Container.RAREA_SUBNETS: routing_area_subnets
                        })
                else:
                    network_properties.append(
                        {
                            Container.RAREA_NAME_MAPPING_FIELD: routing_area.name,
                            Container.RAREA_MLTC_MAPPING_FIELD: routing_area.multicast,
                            Container.RAREA_TYPE_MAPPING_FIELD: routing_area.type
                        })

            if network_properties.__len__() > 0:
                LOGGER.debug("MappingGear.sync_container_network - add network property")
                container.add_property((Container.NETWORK_MAPPING_PROPERTIES, network_properties))

    @staticmethod
    def diff_container_team(container, team):
        if Container.TEAM_SUPPORT_MAPPING_PROPERTIES in container.properties:
            try:
                ret = container.properties[Container.TEAM_SUPPORT_MAPPING_PROPERTIES][Container.TEAM_NAME_MAPPING_FIELD] != team.name or \
                    container.properties[Container.TEAM_SUPPORT_MAPPING_PROPERTIES][Container.TEAM_COLR_MAPPING_FIELD] != team.color_code
                return ret
            except Exception as e:
                try:
                    ret = container.properties[Container.TEAM_SUPPORT_MAPPING_PROPERTIES][0][Container.TEAM_NAME_MAPPING_FIELD][1] != team.name or \
                        container.properties[Container.TEAM_SUPPORT_MAPPING_PROPERTIES][0][Container.TEAM_COLR_MAPPING_FIELD][1] != team.color_code
                    return ret
                except Exception as e:
                    return True
        else:
            return True

    def sync_container_properties(self, operating_system):
        LOGGER.debug("MappingGear.sync_container_properties - begin")
        if not self.init_done or operating_system.last_nics != operating_system.nics:
            self.sync_container_network(self.osi_container, SystemGear.location, SystemGear.routing_areas,
                                        SystemGear.subnets)
        if SystemGear.team is not None and MappingGear.diff_container_team(self.osi_container, SystemGear.team):
            team_properties = {
                Container.TEAM_NAME_MAPPING_FIELD: SystemGear.team.name,
                Container.TEAM_COLR_MAPPING_FIELD: SystemGear.team.color_code
            }
            LOGGER.debug("MappingGear.sync_container_network - add team property")
            self.osi_container.add_property((Container.TEAM_SUPPORT_MAPPING_PROPERTIES, team_properties))
        self.osi_container.add_property((
            Container.OWNER_MAPPING_PROPERTY,
            'procos_system_gear@'+str(SystemGear.hostname)
        ))
        LOGGER.debug("MappingGear.sync_container_properties - done")

    def sync_container(self, operating_system):
        LOGGER.debug("MappingGear.sync_container - begin")
        if self.osi_container is None and operating_system.container_id is not None:
            self.osi_container = ContainerService.find_container(cid=operating_system.container_id)
            if self.osi_container is None:
                LOGGER.error('MappingGear.sync_container - consistency error between ProcOS cache and mapping DB (' +
                             str(operating_system.container_id) + ')')
                operating_system.container_id = None

        if self.osi_container is None:
            LOGGER.debug("MappingGear.sync_container - FQDN : " + str(SystemGear.fqdn))
            if SystemGear.fqdn is None:
                SystemGear.fqdn = SystemGear.hostname
            existing_container = ContainerService.find_container(
                primary_admin_gate_url=SystemGear.config.system_context.admin_gate_protocol+SystemGear.fqdn
            )
            if existing_container is not None:
                deleted = False
                while not deleted:
                    if existing_container is not None and existing_container.remove() is not None:
                        time.sleep(5)
                        existing_container = ContainerService.find_container(
                            primary_admin_gate_url=SystemGear.config.system_context.admin_gate_protocol+SystemGear.fqdn
                        )
                    else:
                        deleted = True

            self.osi_container = Container(
                name=SystemGear.hostname,
                gate_uri=SystemGear.config.system_context.admin_gate_protocol+SystemGear.fqdn,
                primary_admin_gate_name=SystemGear.config.system_context.admin_gate_protocol + ' daemon',
                company=SystemGear.config.system_context.os_type.company.name,
                product=SystemGear.config.system_context.os_type.name + ' - ' +
                SystemGear.config.system_context.os_type.architecture,
                c_type='Operating System'
            )
            self.osi_container.save()
            operating_system.container_id = self.osi_container.id
            LOGGER.debug('operating_system.container_id : (' + str(SystemGear.hostname) + ',' +
                         str(operating_system.container_id) + ')')

        self.sync_container_properties(operating_system)
        LOGGER.debug("MappingGear.sync_container - done")

    @staticmethod
    def sync_remote_container_network(target_os_instance, target_container):
        LOGGER.debug("MappingGear.sync_remote_container_network - begin")
        target_possible_locations = []
        target_routing_areas = []
        target_subnets = []

        if Container.PL_MAPPING_PROPERTIES in target_container.properties and \
           Container.NETWORK_MAPPING_PROPERTIES in target_container.properties:
            LOGGER.debug("MappingGear.sync_remote_container_network - network already defined for remote container.")
            return

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
            LOGGER.warn("MappingGear.sync_remote_container_network - "
                        "remote container loc not found for " + target_container.name)
        LOGGER.debug("MappingGear.sync_remote_container_network - done")

    @staticmethod
    def sync_remote_container_team(target_os_instance, target_container):
        LOGGER.debug("MappingGear.sync_remote_container_team - begin")

        if Container.TEAM_SUPPORT_MAPPING_PROPERTIES in target_container.properties:
            LOGGER.debug("MappingGear.sync_remote_container_network - team already defined for remote container.")
            return

        teams_props = []
        for team_id in target_os_instance.team_ids:
            team = TeamService.find_team(team_id)
            team_properties = {
                Container.TEAM_NAME_MAPPING_FIELD: team.name,
                Container.TEAM_COLR_MAPPING_FIELD: team.color_code
            }
            teams_props.append(team_properties)
        target_container.add_property((Container.TEAM_SUPPORT_MAPPING_PROPERTIES, teams_props))
        LOGGER.debug("MappingGear.sync_remote_container_team - done")

    @staticmethod
    def find_map_socket(map_sockets, endpoint_id):
        LOGGER.debug("MappingGear.find_map_socket")
        ret = None
        for map_socket in map_sockets:
            if map_socket.source_endpoint_id == endpoint_id or map_socket.destination_endpoint_id == endpoint_id:
                ret = map_socket
                break
        return ret

    def sync_map_socket(self, operating_system):
        LOGGER.debug("MappingGear.sync_map_socket - begin")
        if self.osi_container is None:
            LOGGER.error('MappingGear.sync_map_socket - operating system container is not synced')
            return

        start_time = timeit.default_timer()
        for proc in operating_system.processs:
            if SystemGear.config.processes_filter is not None:
                is_found = False
                for process_name_filter in SystemGear.config.processes_filter:
                    if process_name_filter in proc.name:
                        is_found = True
                        break
                if not is_found:
                    continue

            if proc.mapping_id is not None and proc.new_map_sockets is not None:
                if proc.name != "exe":
                    if "java" in proc.name or "python" in proc.name:
                        if "java" in proc.name and "java" not in proc.cmdline[0]:
                            name = '[' + str(proc.pid) + '] ' + str(proc.cmdline[0])
                        elif "python" in proc.name and "python" not in proc.cmdline[0]:
                            name = '[' + str(proc.pid) + '] ' + str(proc.cmdline[0])
                        else:
                            name = '[' + str(proc.pid) + '] ' + str(proc.name)
                    else:
                        name = '[' + str(proc.pid) + '] ' + str(proc.name)
                else:
                    name = '[' + str(proc.pid) + '] ' + str(proc.name) + ' - ' + str(proc.cmdline[0])
                LOGGER.debug("MappingGear.sync_map_socket - " + str(proc.new_map_sockets.__len__()) +
                             ' new socket found for process ' + name)
                for map_socket in proc.new_map_sockets:
                    if map_socket.source_ip is not None and map_socket.source_port is not None:

                        proto = None
                        if map_socket.type == "SOCK_STREAM":
                            proto = "tcp://"
                        elif map_socket.type == "SOCK_DGRAM":
                            proto = "udp://"
                        else:
                            LOGGER.warn("MappingGear.sync_map_socket - socket type " + map_socket.type +
                                        " currently not supported !")

                        if proto is not None:
                            if proc.is_node:
                                source_parent_node_id = proc.mapping_id
                            else:
                                source_parent_node_id = 0
                                LOGGER.warn("MappingGear.sync_map_socket - process as container not yet implemented !")

                            if source_parent_node_id != 0:
                                if map_socket.status != "LISTEN":
                                    source_url = proto + map_socket.source_ip + ":" + str(map_socket.source_port) + \
                                        str(map_socket.file_descriptors) + '[' + str(proc.pid) + ']'
                                else:
                                    source_url = proto + map_socket.source_ip + ":" + str(map_socket.source_port)

                                destination_is_local = operating_system.is_local_destination(map_socket)

                                source_endpoint = EndpointService.find_endpoint(
                                    url=source_url
                                )
                                if source_endpoint is None and destination_is_local:
                                    if map_socket.source_ip == "127.0.0.1":
                                        other_source_url_possibility = proto + "::1:" + str(map_socket.source_port) + \
                                            str(map_socket.file_descriptors) + '[' + str(proc.pid) + ']'
                                        source_endpoint = EndpointService.find_endpoint(
                                            url=other_source_url_possibility
                                        )
                                        if source_endpoint is None:
                                            other_source_url_possibility = proto + "::ffff:127.0.0.1:" + str(map_socket.source_port) + \
                                                str(map_socket.file_descriptors) + '[' + str(proc.pid) + ']'
                                            source_endpoint = EndpointService.find_endpoint(
                                                url=other_source_url_possibility
                                            )
                                        if source_endpoint is None:
                                            other_source_url_possibility = proto + "::127.0.0.1:" + str(map_socket.source_port) + \
                                                str(map_socket.file_descriptors)
                                            source_endpoint = EndpointService.find_endpoint(
                                                url=other_source_url_possibility
                                            )
                                    elif map_socket.source_ip == "::ffff:127.0.0.1":
                                        other_source_url_possibility = proto + "::1:" + str(map_socket.source_port) + \
                                            str(map_socket.file_descriptors) + '[' + str(proc.pid) + ']'
                                        source_endpoint = EndpointService.find_endpoint(
                                            url=other_source_url_possibility
                                        )
                                        if source_endpoint is None:
                                            other_source_url_possibility = proto + "127.0.0.1:" + str(map_socket.source_port) + \
                                                str(map_socket.file_descriptors) + '[' + str(proc.pid) + ']'
                                            source_endpoint = EndpointService.find_endpoint(
                                                url=other_source_url_possibility
                                            )
                                        if source_endpoint is None:
                                            other_source_url_possibility = proto + "::127.0.0.1:" + str(map_socket.source_port) + \
                                                str(map_socket.file_descriptors) + '[' + str(proc.pid) + ']'
                                            source_endpoint = EndpointService.find_endpoint(
                                                url=other_source_url_possibility
                                            )
                                    elif map_socket.source_ip == "::127.0.0.1":
                                        other_source_url_possibility = proto + "::1:" + str(map_socket.source_port) + \
                                            str(map_socket.file_descriptors) + '[' + str(proc.pid) + ']'
                                        source_endpoint = EndpointService.find_endpoint(
                                            url=other_source_url_possibility
                                        )
                                        if source_endpoint is None:
                                            other_source_url_possibility = proto + "::ffff:127.0.0.1:" + str(map_socket.source_port) + \
                                                str(map_socket.file_descriptors) + '[' + str(proc.pid) + ']'
                                            source_endpoint = EndpointService.find_endpoint(
                                                url=other_source_url_possibility
                                            )
                                        if source_endpoint is None:
                                            other_source_url_possibility = proto + "127.0.0.1:" + str(map_socket.source_port) + \
                                                str(map_socket.file_descriptors) + '[' + str(proc.pid) + ']'
                                            source_endpoint = EndpointService.find_endpoint(
                                                url=other_source_url_possibility
                                            )
                                    elif map_socket.source_ip == "::1":
                                        other_source_url_possibility = proto + "127.0.0.1:" + str(map_socket.source_port) + \
                                            str(map_socket.file_descriptors) + '[' + str(proc.pid) + ']'
                                        source_endpoint = EndpointService.find_endpoint(
                                            url=other_source_url_possibility
                                        )
                                        if source_endpoint is None:
                                            other_source_url_possibility = proto + "::ffff:127.0.0.1:" + str(map_socket.source_port) + \
                                                str(map_socket.file_descriptors) + '[' + str(proc.pid) + ']'
                                            source_endpoint = EndpointService.find_endpoint(
                                                url=other_source_url_possibility
                                            )
                                        if source_endpoint is None:
                                            other_source_url_possibility = proto + "::127.0.0.1:" + str(map_socket.source_port) + \
                                                str(map_socket.file_descriptors) + '[' + str(proc.pid) + ']'
                                            source_endpoint = EndpointService.find_endpoint(
                                                url=other_source_url_possibility
                                            )

                                if source_endpoint is None:
                                    source_endpoint = Endpoint(url=source_url, parent_node_id=proc.mapping_id,
                                                               ignore_sync=True)
                                    source_endpoint.add_property(('type', map_socket.type))
                                    source_endpoint.add_property(('family', map_socket.family))
                                    source_endpoint.add_property(('status', map_socket.status))
                                    source_endpoint.add_property(('file descriptors', map_socket.file_descriptors))
                                    source_endpoint.save()
                                    if map_socket.status == "LISTEN" and \
                                            hasattr(proc, 'to_be_refined') and proc.to_be_refined:
                                        gate_to_refine = GateService.find_gate(nid=proc.mapping_id)
                                        if gate_to_refine is not None:
                                            for eid in gate_to_refine.endpoints_id:
                                                gep = EndpointService.find_endpoint(eid=eid)
                                                if gep is not None and gep.url.startswith("tbc://"):
                                                    gep.remove()
                                            gate_to_refine.sync()
                                            if map_socket.source_port == SystemGear.config.system_context.admin_gate_port:
                                                previous_prim_gate = GateService.find_gate(
                                                    self.osi_container.primary_admin_gate_id
                                                )
                                                gate_to_refine.url = SystemGear.config.system_context.admin_gate_protocol+SystemGear.fqdn
                                                gate_to_refine.is_primary_admin = True
                                                gate_to_refine.save()
                                                previous_prim_gate.remove()
                                            else:
                                                gate_to_refine.url = source_url
                                                gate_to_refine.save()
                                            proc.to_be_refined = False
                                        else:
                                            LOGGER.warn("Gate not found for LISTEN url " + source_url)
                                else:
                                    LOGGER.debug("Found source endpoint : (" +
                                                 source_url + ',' + str(source_endpoint.id) + ")")
                                if source_endpoint.id not in operating_system.duplex_links_endpoints \
                                        and destination_is_local:
                                    operating_system.duplex_links_endpoints.append(source_endpoint.id)

                                map_socket.source_endpoint_id = source_endpoint.id
                                LOGGER.debug('MappingGear.sync_map_socket - source socket endpoint on mapping db : (' +
                                             source_url + ',' + str(map_socket.source_endpoint_id) + ')')

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

                                    target_container = None if not destination_is_local else self.osi_container
                                    target_node = None
                                    target_endpoint = None

                                    if target_fqdn != "localhost" and target_fqdn is not None:
                                        target_os_instance = None
                                        if target_fqdn.split(".").__len__() > 1:
                                            target_os_instance = OSInstanceService.find_os_instance(
                                                osi_name=target_fqdn.split(".")[0]
                                            )

                                        if target_os_instance is None:
                                            target_os_instance = OSInstanceService.find_os_instance(
                                                osi_name=target_fqdn
                                            )

                                        if target_os_instance is None:
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
                                                    "Unknown OS Type"

                                                target_os_instance_type_cmp = CompanyService.find_company(
                                                    cmp_id=target_os_instance_type.company_id
                                                ) if target_os_instance_type is not None else None
                                                company = target_os_instance_type_cmp.name\
                                                    if target_os_instance_type_cmp is not None else\
                                                    "Unknown OS Type Company"

                                                name = target_fqdn.split(".")[0] if target_fqdn is not None else\
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

                                            if Container.OWNER_MAPPING_PROPERTY not in target_container.properties:
                                                MappingGear.sync_remote_container_network(target_os_instance,
                                                                                          target_container)
                                                MappingGear.sync_remote_container_team(target_os_instance,
                                                                                       target_container)
                                    if target_container is None:
                                        target_container = ContainerService.find_container(
                                            primary_admin_gate_url="not_my_concern://"+map_socket.destination_ip
                                        )
                                        if target_container is None:
                                            target_container = Container(
                                                name=target_fqdn if target_fqdn is not None else map_socket.destination_ip,
                                                gate_uri="not_my_concern://"+map_socket.destination_ip,
                                                primary_admin_gate_name="External OS Primary Admin Gate"
                                            )
                                            target_container.save()

                                    if not destination_is_local:
                                        selector = "endpointURL =~ '.*:" + str(map_socket.destination_port) + ".*'"

                                        endpoints = EndpointService.find_endpoint(
                                            selector=selector,
                                            cid=target_container.id
                                        )

                                        if endpoints is not None and endpoints.__len__() == 1:
                                            target_endpoint = endpoints[0]
                                            target_node = NodeService.find_node(nid=target_endpoint.parent_node_id)
                                        elif endpoints is not None and endpoints.__len__() > 1:
                                            LOGGER.debug("MappingGear.sync_map_socket - "
                                                         "Multiple endpoints found for selector " + selector +
                                                         " on container " + target_container.id)
                                        elif (endpoints is not None and endpoints.__len__() == 0) or endpoints is None:
                                            LOGGER.debug("MappingGear.sync_map_socket - "
                                                         "No endpoint found for selector " + selector +
                                                         " on container " + target_container.id)

                                        if target_endpoint is None and \
                                                Container.OWNER_MAPPING_PROPERTY not in target_container.properties:
                                            addr = target_fqdn if target_fqdn is not None else map_socket.destination_ip
                                            node_name = addr + ':' + str(map_socket.destination_port)
                                            LOGGER.debug("create node " + node_name + " through container " +
                                                         target_container.id)
                                            target_node = Node(
                                                name=node_name,
                                                container_id=target_container.id,
                                                ignore_sync=True
                                            )
                                            target_node.save()

                                            target_endpoint = Endpoint(
                                                url=target_url, parent_node_id=target_node.id, ignore_sync=True
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
                                                        LOGGER.warn("MappingGear.sync_map_socket - process as container"
                                                                    " not yet implemented !")
                                                    target_url += str(srv_socket.file_descriptors)
                                                    target_url += '[' + str(proc_srv.pid) + ']'
                                                    if target_node is not None:
                                                        target_endpoint = EndpointService.find_endpoint(
                                                            url=target_url
                                                        )
                                                        if target_endpoint is None:
                                                            if map_socket.destination_ip == "127.0.0.1":
                                                                other_target_url_possibility = proto + "::1:" + str(map_socket.destination_port) + \
                                                                    str(srv_socket.file_descriptors) + \
                                                                    '[' + str(proc_srv.pid) + ']'
                                                                target_endpoint = EndpointService.find_endpoint(
                                                                    url=other_target_url_possibility
                                                                )
                                                                if target_endpoint is None:
                                                                    other_target_url_possibility = proto + "::ffff:127.0.0.1:" + str(map_socket.destination_port) + \
                                                                        str(srv_socket.file_descriptors) + '[' + str(proc_srv.pid) + ']'
                                                                    target_endpoint = EndpointService.find_endpoint(
                                                                        url=other_target_url_possibility
                                                                    )
                                                                if target_endpoint is None:
                                                                    other_target_url_possibility = proto + "::127.0.0.1:" + str(map_socket.destination_port) + \
                                                                        str(srv_socket.file_descriptors) + '[' + str(proc_srv.pid) + ']'
                                                                    target_endpoint = EndpointService.find_endpoint(
                                                                        url=other_target_url_possibility
                                                                    )
                                                            elif map_socket.destination_ip == "::ffff:127.0.0.1":
                                                                other_target_url_possibility = proto + "::1:" + str(map_socket.destination_port) + \
                                                                    str(srv_socket.file_descriptors) + '[' + str(proc_srv.pid) + ']'
                                                                target_endpoint = EndpointService.find_endpoint(
                                                                    url=other_target_url_possibility
                                                                )
                                                                if target_endpoint is None:
                                                                    other_target_url_possibility = proto + "127.0.0.1:" + str(map_socket.destination_port) + \
                                                                        str(srv_socket.file_descriptors) + '[' + str(proc_srv.pid) + ']'
                                                                    target_endpoint = EndpointService.find_endpoint(
                                                                        url=other_target_url_possibility
                                                                    )
                                                                if target_endpoint is None:
                                                                    other_target_url_possibility = proto + "::127.0.0.1:" + str(map_socket.destination_port) + \
                                                                        str(srv_socket.file_descriptors) + '[' + str(proc_srv.pid) + ']'
                                                                    target_endpoint = EndpointService.find_endpoint(
                                                                        url=other_target_url_possibility
                                                                    )
                                                            elif map_socket.source_ip == "::127.0.0.1":
                                                                other_target_url_possibility = proto + "::1:" + str(map_socket.destination_port) + \
                                                                    str(srv_socket.file_descriptors) + '[' + str(proc_srv.pid) + ']'
                                                                target_endpoint = EndpointService.find_endpoint(
                                                                    url=other_target_url_possibility
                                                                )
                                                                if target_endpoint is None:
                                                                    other_target_url_possibility = proto + "::ffff:127.0.0.1:" + str(map_socket.destination_port) + \
                                                                        str(srv_socket.file_descriptors) + '[' + str(proc_srv.pid) + ']'
                                                                    target_endpoint = EndpointService.find_endpoint(
                                                                        url=other_target_url_possibility
                                                                    )
                                                                if target_endpoint is None:
                                                                    other_target_url_possibility = proto + "127.0.0.1:" + str(map_socket.destination_port) + \
                                                                        str(srv_socket.file_descriptors) + '[' + str(proc_srv.pid) + ']'
                                                                    target_endpoint = EndpointService.find_endpoint(
                                                                        url=other_target_url_possibility
                                                                    )
                                                            elif map_socket.source_ip == "::1":
                                                                other_target_url_possibility = proto + "127.0.0.1:" + str(map_socket.destination_port) + \
                                                                    str(srv_socket.file_descriptors) + '[' + str(proc_srv.pid) + ']'
                                                                target_endpoint = EndpointService.find_endpoint(
                                                                    url=other_target_url_possibility
                                                                )
                                                                if target_endpoint is None:
                                                                    other_target_url_possibility = proto + "::ffff:127.0.0.1:" + str(map_socket.destination_port) + \
                                                                        str(srv_socket.file_descriptors) + '[' + str(proc_srv.pid) + ']'
                                                                    target_endpoint = EndpointService.find_endpoint(
                                                                        url=other_target_url_possibility
                                                                    )
                                                                if target_endpoint is None:
                                                                    other_target_url_possibility = proto + "::127.0.0.1:" + str(map_socket.destination_port) + \
                                                                        str(srv_socket.file_descriptors) + '[' + str(proc_srv.pid) + ']'
                                                                    target_endpoint = EndpointService.find_endpoint(
                                                                        url=other_target_url_possibility
                                                                    )

                                                        if target_endpoint is None:
                                                            target_endpoint = Endpoint(
                                                                url=target_url, parent_node_id=target_node.id,
                                                                ignore_sync=True
                                                            )
                                                            target_endpoint.add_property(('type', srv_socket.type))
                                                            target_endpoint.add_property(('family', srv_socket.family))
                                                            target_endpoint.add_property(('status', srv_socket.status))
                                                            target_endpoint.add_property(('file descriptors',
                                                                                          srv_socket.file_descriptors))
                                                            target_endpoint.save()
                                                        if target_endpoint.id \
                                                                not in operating_system.duplex_links_endpoints and \
                                                                destination_is_local:
                                                            operating_system.duplex_links_endpoints.append(
                                                                target_endpoint.id
                                                            )
                                                    break

                                    if target_endpoint is not None:
                                        map_socket.destination_endpoint_id = target_endpoint.id
                                        LOGGER.debug('MappingGear.sync_map_socket - target socket endpoint '
                                                     'on mapping db : (' + target_url + ',' +
                                                     str(map_socket.destination_endpoint_id) + ')')
                                    if target_node is not None:
                                        map_socket.destination_node_id = target_node.id
                                        LOGGER.debug('MappingGear.sync_map_socket - target socket node '
                                                     'on mapping db : (' + target_url + ',' +
                                                     str(map_socket.destination_node_id) + ')')
                                    map_socket.destination_container_id = target_container.id
                                    LOGGER.debug('MappingGear.sync_map_socket - target socket container '
                                                 'on mapping db : (' + target_url + ',' +
                                                 str(map_socket.destination_container_id) + ')')

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
                                        LOGGER.debug('MappingGear.sync_map_socket - missing destination endpoint id '
                                                     'for ' + str(map_socket))

                    else:
                        LOGGER.debug('MappingGear.sync_map_socket - no source ip / port - ' + str(map_socket))

            if proc.mapping_id is not None and proc.dead_map_sockets is not None:
                if proc.name != "exe":
                    if "java" in proc.name or "python" in proc.name:
                        if "java" in proc.name and "java" not in proc.cmdline[0]:
                            name = '[' + str(proc.pid) + '] ' + str(proc.cmdline[0])
                        elif "python" in proc.name and "python" not in proc.cmdline[0]:
                            name = '[' + str(proc.pid) + '] ' + str(proc.cmdline[0])
                        else:
                            name = '[' + str(proc.pid) + '] ' + str(proc.name)
                    else:
                        name = '[' + str(proc.pid) + '] ' + str(proc.name)
                else:
                    name = '[' + str(proc.pid) + '] ' + str(proc.name) + ' - ' + str(proc.cmdline[0])
                LOGGER.debug("MappingGear.sync_map_socket - " + str(proc.dead_map_sockets.__len__()) +
                             ' dead socket found for process [' + str(proc.mapping_id) + ']' + name)
                for map_socket in proc.dead_map_sockets:
                    # if map_socket.link_id is not None:
                    #     link = LinkService.find_link(lid=map_socket.link_id)
                    #     if link is not None:
                    #         link.remove()
                    #     else:
                    #         LOGGER.warn("Dead socket (link : " + str(map_socket.link_id) + ") "
                    #                     "doesn't exist anymore on DB !")
                    if map_socket.source_endpoint_id is not None and \
                       (
                            map_socket.source_endpoint_id not in operating_system.wip_delete_duplex_links_endpoints or
                            map_socket.source_endpoint_id not in operating_system.duplex_links_endpoints
                       ):
                        source_endpoint = EndpointService.find_endpoint(eid=map_socket.source_endpoint_id)
                        if source_endpoint is not None:
                            LOGGER.debug('MappingGear.sync_map_socket - Remove source endpoint ' +
                                         str(map_socket.source_endpoint_id))
                            source_endpoint.remove()
                            if map_socket.source_endpoint_id in operating_system.duplex_links_endpoints:
                                operating_system.wip_delete_duplex_links_endpoints.append(map_socket.source_endpoint_id)
                        else:
                            LOGGER.warn("MappingGear.sync_map_socket - Dead socket (source endpoint : " +
                                        str(map_socket.source_endpoint_id) +
                                        ") doesn't exist anymore on DB!")
                    elif map_socket.source_endpoint_id is not None and \
                            map_socket.source_endpoint_id in operating_system.wip_delete_duplex_links_endpoints:
                        operating_system.wip_delete_duplex_links_endpoints.remove(map_socket.source_endpoint_id)
                        operating_system.duplex_links_endpoints.remove(map_socket.source_endpoint_id)

                    if map_socket.destination_endpoint_id is not None and \
                            (
                                map_socket.destination_endpoint_id not in
                                operating_system.wip_delete_duplex_links_endpoints or
                                map_socket.destination_endpoint_id not in operating_system.duplex_links_endpoints
                            ):
                        target_endpoint = EndpointService.find_endpoint(eid=map_socket.destination_endpoint_id)
                        if target_endpoint is not None:
                            array_link = LinkService.find_link(tep_id=target_endpoint.id)
                            if array_link is not None and array_link.__len__() == 0:
                                LOGGER.debug('MappingGear.sync_map_socket - Remove target endpoint ' +
                                             str(map_socket.destination_endpoint_id))
                                target_endpoint.remove()
                                if map_socket.destination_endpoint_id in operating_system.duplex_links_endpoints:
                                    operating_system.wip_delete_duplex_links_endpoints.append(
                                        map_socket.destination_endpoint_id
                                    )
                        else:
                            LOGGER.warn("MappingGear.sync_map_socket - Dead socket (target endpoint : " +
                                        str(map_socket.destination_endpoint_id) +
                                        ") doesn't exist anymore on DB!")
                    elif map_socket.destination_endpoint_id is not None and \
                            map_socket.destination_endpoint_id in operating_system.wip_delete_duplex_links_endpoints:
                        operating_system.wip_delete_duplex_links_endpoints.remove(map_socket.destination_endpoint_id)
                        operating_system.duplex_links_endpoints.remove(map_socket.destination_endpoint_id)

        sync_proc_time = timeit.default_timer()-start_time
        LOGGER.debug('MappingGear.sync_map_socket - time : ' + str(sync_proc_time))
        LOGGER.debug("MappingGear.sync_map_socket - done")

    def sync_processs(self, operating_system):
        LOGGER.debug("MappingGear.sync_processs - begin")
        if self.osi_container is None:
            LOGGER.error('MappingGear.sync_processs - operating system container is not synced')
            return

        start_time = timeit.default_timer()
        LOGGER.debug("MappingGear.sync_processs - " + str(operating_system.new_processs.__len__()) +
                     ' new processes found')
        for process in operating_system.new_processs:
            if SystemGear.config.processes_filter is not None:
                is_found = False
                for process_name_filter in SystemGear.config.processes_filter:
                    if process_name_filter in process.name:
                        is_found = True
                        break
                if not is_found:
                    continue

            if process.name != "exe":
                if "java" in process.name or "python" in process.name:
                    if "java" in process.name and "java" not in process.cmdline[0]:
                        name = '[' + str(process.pid) + '] ' + str(process.cmdline[0])
                    elif "python" in process.name and "python" not in process.cmdline[0]:
                        name = '[' + str(process.pid) + '] ' + str(process.cmdline[0])
                    else:
                        name = '[' + str(process.pid) + '] ' + str(process.name)
                else:
                    name = '[' + str(process.pid) + '] ' + str(process.name)
            else:
                name = '[' + str(process.pid) + '] ' + str(process.name) + ' - ' + str(process.cmdline[0])

            is_gate = False

            if process.new_map_sockets is not None and \
               "docker-proxy" not in process.name:   # let ariane docker plugin manage this
                for map_socket in process.new_map_sockets:
                    if map_socket.source_ip is not None and map_socket.source_port is not None:
                        if map_socket.status == "LISTEN" and not operating_system.is_local_service(map_socket):
                            LOGGER.debug("MappingGear.sync_processs - gate process found (" + name + ")")
                            is_gate = True
                            break

            if not is_gate:
                process_map_obj = Node(
                    name=name,
                    container=self.osi_container
                )
                process.to_be_refined = False
            else:
                process_map_obj = Gate(
                    name=name,
                    is_primary_admin=False,
                    url="tbc://" + str(SystemGear.fqdn) + "[" + name + "]",  # will be redefined in sync_map_socket
                    container=self.osi_container
                )
                process.to_be_refined = True
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
            if process.cmdline.__len__() > 0:
                for cmdline_part in process.cmdline:
                    if "-pass" in cmdline_part or "-pwd" in cmdline_part:
                        pass_index = process.cmdline.index(cmdline_part)
                        if pass_index + 1 < process.cmdline.__len__():
                            process.cmdline[pass_index+1] = "*****"
                process_map_obj.add_property(('cmdline', process.cmdline))
            process.mapping_id = process_map_obj.id
            LOGGER.debug('MappingGear.sync_processs - new process on mapping db : (' + name + ',' +
                         str(process.mapping_id) + ')')

        LOGGER.debug("MappingGear.sync_processs - " + str(operating_system.dead_processs.__len__()) +
                     ' old processes found')
        for process in operating_system.dead_processs:
            if SystemGear.config.processes_filter is not None:
                is_found = False
                for process_name_filter in SystemGear.config.processes_filter:
                    if process_name_filter in process.name:
                        is_found = True
                        break
                if not is_found:
                    continue

            if process.name != "exe":
                if "java" in process.name or "python" in process.name:
                    if "java" in process.name and "java" not in process.cmdline[0]:
                        name = '[' + str(process.pid) + '] ' + str(process.cmdline[0])
                    elif "python" in process.name and "python" not in process.cmdline[0]:
                        name = '[' + str(process.pid) + '] ' + str(process.cmdline[0])
                    else:
                        name = '[' + str(process.pid) + '] ' + str(process.name)
                else:
                    name = '[' + str(process.pid) + '] ' + str(process.name)
            else:
                name = '[' + str(process.pid) + '] ' + str(process.name) + ' - ' + str(process.cmdline[0])

            if process.mapping_id is None:
                LOGGER.error('MappingGear.sync_processs - dead process (' + name +
                             ') has not been saved on mapping db !')
            else:
                if process.is_node:
                    process_map_obj = NodeService.find_node(nid=process.mapping_id)
                else:
                    process_map_obj = ContainerService.find_container(cid=process.mapping_id)
                if process_map_obj is None:
                    LOGGER.error('MappingGear.sync_processs - consistency error between ProcOS cache and mapping DB (' +
                                 name + ',' + str(process.mapping_id) + ')')
                else:
                    process_map_obj.remove()

        sync_proc_time = timeit.default_timer()-start_time
        LOGGER.debug('MappingGear.sync_processs - time : ' + str(sync_proc_time))
        LOGGER.debug("MappingGear.sync_processs - done")

    def synchronize_with_ariane_mapping(self, component):
        LOGGER.debug("MappingGear.synchronize_with_ariane_mapping")
        if self.running:
            try:
                start_time = timeit.default_timer()
                operating_system = component.operating_system.get()
                # SessionService.open_session("ArianeProcOS_" + socket.gethostname())
                self.sync_container(operating_system)
                SessionService.open_session("ArianeProcOS_" + socket.gethostname())
                self.sync_processs(operating_system)
                self.sync_map_socket(operating_system)
                SessionService.commit()
                self.update_count += 1
                SessionService.close_session()
                sync_proc_time = timeit.default_timer()-start_time
                LOGGER.info('MappingGear.synchronize_with_ariane_mapping - time : ' + str(sync_proc_time))
                LOGGER.debug("MappingGear.synchronize_with_ariane_mapping - activate " +
                             SystemGear.domino_ariane_sync_topic)
                SystemGear.domino_activator.activate(SystemGear.domino_ariane_sync_topic)
                if not self.init_done:
                    self.init_done = True
            except Exception as e:
                LOGGER.error("MappingGear.synchronize_with_ariane_mapping - " + e.__str__())
                LOGGER.error("MappingGear.synchronize_with_ariane_mapping - " + traceback.format_exc())
                try:
                    LOGGER.error("MappingGear.synchronize_with_ariane_mapping - mapping rollback to previous state")
                    SessionService.rollback()
                except Exception as e:
                    LOGGER.error("MappingGear.synchronize_with_ariane_mapping - exception on mapping rollback : " +
                                 e.__str__())
                    LOGGER.debug("MappingGear.synchronize_with_ariane_mapping - exception on mapping rollback : " +
                                 traceback.format_exc())
                try:
                    LOGGER.error("MappingGear.synchronize_with_ariane_mapping - mapping session close")
                    SessionService.close_session()
                except Exception as e:
                    LOGGER.error("MappingGear.synchronize_with_ariane_mapping - exception on mapping session closing : "
                                 + e.__str__())
                    LOGGER.debug("MappingGear.synchronize_with_ariane_mapping - exception on mapping session closing : "
                                 + traceback.format_exc())
                try:
                    LOGGER.error("MappingGear.synchronize_with_ariane_mapping - injector cache rollback")
                    component.rollback().get()
                except Exception as e:
                    LOGGER.error("MappingGear.synchronize_with_ariane_mapping - exception on injector cache rollback : "
                                 + e.__str__())
                    LOGGER.debug("MappingGear.synchronize_with_ariane_mapping - exception on injector cache rollback : "
                                 + traceback.format_exc())
        else:
            LOGGER.warn('Synchronization requested but procos_mapping_gear@' + str(SystemGear.hostname) +
                        ' is not running.')


class SystemGear(InjectorGearSkeleton):
    # static reference on commons var
    config = None
    hostname = None
    fqdn = None

    # static reference to up to date ariane directories objects linked to this System
    location = None
    routing_areas = []
    subnets = []
    osi = None
    embedding_osi = None
    ost = None
    ost_company = None
    team = None
    environment = None

    domino_component_topic = "domino_component"
    domino_ariane_sync_topic = "domino_ariane_sync"
    domino_activator = None

    def __init__(self, config):
        LOGGER.debug("SystemGear.__init__")
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
        SystemGear.domino_activator = DominoActivator({'type': 'Z0MQ'})
        self.component = SystemComponent.start(
            attached_gear_id=self.gear_id(),
            hostname=SystemGear.hostname,
            component_type=component_type,
            system_gear_actor_ref=self.actor_ref,
            domino_activator=SystemGear.domino_activator,
            domino_topic=SystemGear.domino_component_topic,
            config=config
        ).proxy()
        self.directory_gear = DirectoryGear.start().proxy()
        self.mapping_gear = MappingGear.start().proxy()

    def synchronize_with_ariane_dbs(self):
        LOGGER.debug("SystemGear.synchronize_with_ariane_dbs - sync db")
        self.directory_gear.synchronize_with_ariane_directories(self.component)
        self.mapping_gear.synchronize_with_ariane_mapping(self.component)

    def init_with_ariane_dbs(self):
        LOGGER.debug("SystemGear.init_with_ariane_dbs - Initializing...")
        self.directory_gear.init_ariane_directories(self.component).get()
        self.component.sniff(synchronize_with_ariane_dbs=False).get()
        self.directory_gear.synchronize_with_ariane_directories(self.component).get()
        self.mapping_gear.synchronize_with_ariane_mapping(self.component).get()
        LOGGER.info("SystemGear.init_with_ariane_dbs - Initialization done.")

    def run(self):
        LOGGER.debug("SystemGear.run")
        if self.sleeping_period is not None and self.sleeping_period > 0:
            while self.running:
                time.sleep(self.sleeping_period)
                if self.running:
                    self.component.sniff().get()

    def on_start(self):
        LOGGER.debug("SystemGear.on_start")
        self.cache(running=self.running)
        self.init_with_ariane_dbs()
        self.running = True
        self.cache(running=self.running)
        self.service = threading.Thread(target=self.run, name=self.service_name)
        self.service.start()

    def on_stop(self):
        LOGGER.debug("SystemGear.on_stop")
        try:
            if self.running:
                self.running = False
                self.cache(running=self.running)
            self.service = None
            self.component.stop().get()
            self.directory_gear.stop().get()
            self.mapping_gear.stop().get()
            self.cached_gear_actor.remove().get()
            SystemGear.domino_activator.stop()
        except Exception as e:
            LOGGER.error(e.__str__())
            LOGGER.debug(traceback.format_exc())

    def on_failure(self, exception_type, exception_value, traceback_):
        LOGGER.debug("SystemGear.on_failure")
        LOGGER.error("SystemGear.on_failure - " + exception_type.__str__() + "/" + exception_value.__str__())
        LOGGER.error("SystemGear.on_failure - " + traceback_.format_exc())
        try:
            if self.running:
                self.running = False
                self.cache(running=self.running)
            self.service = None
            self.component.stop().get()
            self.directory_gear.stop().get()
            self.mapping_gear.stop().get()
            self.cached_gear_actor.remove().get()
            SystemGear.domino_activator.stop()
        except Exception as e:
            LOGGER.error(e.__str__())
            LOGGER.debug(traceback.format_exc())

    def gear_start(self):
        LOGGER.debug("SystemGear.gear_start")
        if self.service is not None:
            self.running = True
            self.service = threading.Thread(target=self.run, name=self.service_name)
            self.service.start()
            self.cache(running=self.running)
            LOGGER.info('procos_system_gear@'+str(SystemGear.hostname)+' has been started')
        else:
            self.on_start()
            LOGGER.info('procos_system_gear@'+str(SystemGear.hostname)+' has been restarted')

    def gear_stop(self):
        LOGGER.debug("SystemGear.gear_stop")
        if self.running:
            self.running = False
            self.cache(running=self.running)
            LOGGER.info('procos_system_gear@'+str(SystemGear.hostname)+' has been stopped')
