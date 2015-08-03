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
import socket
import threading
import time
from ariane_clip3.directory import DatacenterService, Datacenter, RoutingAreaService, RoutingArea, OSInstanceService, \
    OSInstance, SubnetService, Subnet, IPAddressService, IPAddress, EnvironmentService, Environment, TeamService, Team
from ariane_clip3.injector import InjectorGearSkeleton
from components import SystemComponent

__author__ = 'mffrench'


class DirectoryGear(InjectorGearSkeleton):
    def __init__(self, config):
        self.config = config
        self.hostname = socket.gethostname()
        super(DirectoryGear, self).__init__(
            gear_id='ariane.community.plugin.procos.gears.cache.directory_gear@'+self.hostname,
            gear_name='procos_directory_gear@'+self.hostname,
            gear_description='Ariane ProcOS directory gear for '+self.hostname,
            gear_admin_queue='ariane.community.plugin.procos.gears.cache.directory_gear@'+self.hostname,
            running=False
        )
        self.update_count = 0
        self.ignore_directories_sync = True

        self.datacenter = None
        self.routing_areas = []
        self.subnets = []
        self.osi = None
        self.team = None
        self.environment = None

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

    def init_ariane_directories(self, component):
        operating_system = component.operating_system.get()
        # Find current Datacenter, routing area and subnets according to runtime IP on NICs and possible datacenters:
        current_possible_datacenter_config = []
        current_possible_routing_area_config = []
        current_possible_subnet_config = []

        for nic in operating_system.nics:
            nic_is_located = False
            try:
                if nic.ipv4_address is not None:
                    subnet_ip = nic.ipv4_address.split('.')[0] + '.' + nic.ipv4_address.split('.')[1] + '.' + \
                                nic.ipv4_address.split('.')[2] + '.0'
                    subnet_mask = nic.ipv4_mask

                    if subnet_ip != '127.0.0.0':
                        for datacenter_config in self.config.potential_datacenters:
                            for routing_area_config in datacenter_config.routing_areas:
                                for subnet_config in routing_area_config.subnets:
                                    if subnet_config.subnet_ip == subnet_ip and \
                                                    subnet_config.subnet_mask == subnet_mask:
                                        if datacenter_config not in current_possible_datacenter_config:
                                            current_possible_datacenter_config.append(datacenter_config)
                                        current_possible_routing_area_config.append(routing_area_config)
                                        current_possible_subnet_config.append(subnet_config)
                                        nic_is_located = True

                    if not nic_is_located:
                        print('WARN: nic ' +
                              nic.mac_address + '/' if nic.mac_address is not None else ''
                                                                                        + nic.ipv4_address +
                              ' has not been located on the possibles networks')

            except Exception as e:
                print(e.__str__())

        if current_possible_datacenter_config.__len__() > 1:
            print('WARN: multiple current possible datacenter found - will ignore directories sync')
        elif current_possible_datacenter_config.__len__() == 0:
            print('WARN: no current possible datacenter found - will ignore directories sync')

        # Sync Operating System
        if operating_system.osi_id is not None:
            self.osi = OSInstanceService.find_os_instance(osi_id=operating_system.osi_id)
            if self.osi.name != self.hostname:
                self.osi = None
                operating_system.osi_id = None

        if self.osi is None:
            self.osi = OSInstanceService.find_os_instance(osi_name=self.hostname)
            if self.osi is None:
                self.osi = OSInstance(name=self.hostname, description=self.config.system_context.description,
                                      admin_gate_uri=self.config.system_context.admin_gate_protocol+self.hostname)
                self.osi.save()
            operating_system.osi_id = self.osi.id

        # Sync environment
        if self.config.organisation_context is not None and self.config.organisation_context.environment is not None:
            if operating_system.environment_id is not None:
                self.environment = EnvironmentService.find_environment(operating_system.environment_id)
                if self.environment is not None and \
                                self.environment.name != self.config.organisation_context.environment.name:
                    self.environment.del_os_instance(self.osi)
                    self.environment = None
                    operating_system.environment_id = None

            if self.environment is None:
                self.environment = Environment(name=self.config.organisation_context.environment.name,
                                               description=self.config.organisation_context.environment.description)
                self.environment.save()
                operating_system.environment_id = self.environment.id
                self.osi.add_environment(self.environment)
        else:
            if operating_system.environment_id is not None:
                environment = EnvironmentService.find_environment(operating_system.environment_id)
                environment.del_os_instance(self.osi)
                operating_system.environment_id = None

        # Sync team
        if self.config.organisation_context is not None and self.config.organisation_context.team is not None:
            if operating_system.team_id is not None:
                self.team = TeamService.find_team(team_id=operating_system.team_id)
                if self.team is not None and self.team.name != self.config.organisation_context.team.name:
                    self.team.del_os_instance(self.osi)
                    self.team = None
                    operating_system.team_id = None

            if self.team is None:
                self.team = TeamService.find_team(team_name=self.config.organisation_context.team.name)
                if self.team is None:
                    self.team = Team(name=self.config.organisation_context.team.name,
                                     color_code=self.config.organisation_context.team.color_code,
                                     description=self.config.organisation_context.team.description)
                    self.team.save()
                operating_system.team_id = self.team.id
                self.osi.add_team(self.team)
        else:
            if operating_system.team_id is not None:
                team = TeamService.find_team(team_id=operating_system.team_id)
                team.del_os_instance(self.osi)
                operating_system.team_id = None

        # Sync network stuffs
        if current_possible_datacenter_config.__len__() == 1:
            self.ignore_directories_sync = False
            current_datacenter = current_possible_datacenter_config[0]

            # Sync datacenter
            if operating_system.datacenter_id is not None:
                self.datacenter = DatacenterService.find_datacenter(operating_system.datacenter_id)
                if self.datacenter is not None and self.datacenter.name != current_datacenter.name:
                    self.datacenter = None
                    operating_system.datacenter_id = None

            if self.datacenter is None:
                self.datacenter = DatacenterService.find_datacenter(dc_name=current_datacenter.name)
                if self.datacenter is None:
                    self.datacenter = Datacenter(name=current_datacenter.name,
                                                 description=current_datacenter.description,
                                                 address=current_datacenter.address,
                                                 zip_code=current_datacenter.zipcode,
                                                 town=current_datacenter.town,
                                                 country=current_datacenter.country,
                                                 gps_latitude=current_datacenter.gps_lat,
                                                 gps_longitude=current_datacenter.gps_lng)
                    self.datacenter.save()
                operating_system.datacenter_id = self.datacenter.id

            # Sync routing areas and subnets
            if not operating_system.routing_area_ids.empty():
                for cached_routing_area_id in operating_system.routing_area_ids:
                    cached_routing_area = RoutingAreaService.find_routing_area(ra_id=cached_routing_area_id)
                    if cached_routing_area is not None:
                        if cached_routing_area in current_possible_routing_area_config:
                            for subnet_id in cached_routing_area.subnet_ids:
                                subnet = SubnetService.find_subnet(sb_id=subnet_id)
                                if subnet is not None:
                                    if subnet in current_possible_subnet_config:
                                        if subnet.id not in operating_system.subnet_ids:
                                            operating_system.subnet_ids.append(subnet.id)
                                        if subnet.id not in self.osi.subnet_ids:
                                            self.osi.add_subnet(subnet)
                                        if subnet not in self.subnets:
                                            self.subnets.append(subnet)
                                        current_possible_subnet_config.remove(subnet)
                                    else:
                                        if subnet.id in operating_system.subnet_ids:
                                            operating_system.subnet_ids.remove(subnet.id)
                                        if subnet.id in self.osi.subnet_ids:
                                            self.osi.del_subnet(subnet)
                                        if subnet in self.subnets:
                                            self.subnets.remove(subnet)

                            if cached_routing_area not in self.routing_areas:
                                self.routing_areas.append(cached_routing_area)
                            current_possible_routing_area_config.remove(cached_routing_area)

                        else:
                            for subnet_id in cached_routing_area.subnet_ids:
                                subnet = SubnetService.find_subnet(sb_id=subnet_id)
                                if subnet is not None:
                                    if subnet in current_possible_subnet_config:
                                        current_possible_subnet_config.remove(subnet)
                                    if subnet.id in operating_system.subnet_ids:
                                        operating_system.subnet_ids.remove(subnet.id)
                                    if subnet.id in self.osi.subnet_ids:
                                        self.osi.del_subnet(subnet)
                                    if subnet in self.subnets:
                                        self.subnets.remove(subnet)
                            if cached_routing_area in self.routing_areas:
                                self.routing_areas.remove(cached_routing_area)
                    else:
                        operating_system.routing_area_ids.remove(cached_routing_area_id)

            for routing_area_config in current_possible_routing_area_config:
                routing_area = RoutingAreaService.find_routing_area(ra_name=routing_area_config.name)

                if routing_area is None:
                    routing_area = RoutingArea(name=routing_area_config.name,
                                               multicast=routing_area_config.multicast,
                                               ra_type=routing_area_config.type,
                                               description=routing_area_config.description)
                    routing_area.save()
                    routing_area.add_datacenter(self.datacenter)
                    operating_system.routing_area_ids.append(routing_area.id)
                    self.routing_areas.append(routing_area_config)

                for subnet_config in routing_area_config.subnets:
                    if subnet_config in current_possible_subnet_config:
                        subnet = SubnetService.find_subnet(sb_name=subnet_config.name)
                        if subnet is None:
                            subnet = Subnet(name=subnet_config.name,
                                            description=subnet_config.description,
                                            routing_area_id=routing_area.id,
                                            ip=subnet_config.subnet_ip, mask=subnet_config.subnet_mask)
                            subnet.save()
                        operating_system.subnet_ids.append(subnet.id)
                        self.subnets.append(subnet)
                        if subnet.id not in self.osi.subnet_ids:
                            self.osi.add_subnet(subnet)

            for nic in operating_system.nics:
                try:
                    if nic.ipv4_address is not None:
                        subnet_ip = nic.ipv4_address.split('.')[0] + '.' + nic.ipv4_address.split('.')[1] + '.' + \
                                    nic.ipv4_address.split('.')[2] + '.0'
                        subnet_mask = nic.ipv4_mask

                        if subnet_ip != '127.0.0.0':
                            for subnet in self.subnets:
                                if subnet_ip == subnet.ip and subnet_mask == subnet.mask:
                                    ip_address = IPAddressService.find_ip_address(nic.ipv4_address, subnet.id)
                                    if ip_address is None:
                                        ip_address = IPAddress(ip_address=nic.ipv4_address, fqdn=nic.ipv4_fqdn,
                                                               ipa_subnet_id=subnet.id, ipa_osi_id=self.osi.id)
                                        ip_address.save()
                                        subnet.sync()
                                    else:
                                        if ip_address.ipa_os_instance_id != self.osi.id:
                                            ip_address.ipa_os_instance_id = self.osi.id
                                            ip_address.save()
                                    self.osi.sync()
                        else:
                            local_routing_area = RoutingAreaService.find_routing_area(self.hostname+".local")
                            if local_routing_area is None:
                                local_routing_area = RoutingArea(name=self.hostname+".local",
                                                                 multicast=RoutingArea.RA_MULTICAST_NOLIMIT,
                                                                 ra_type=RoutingArea.RA_TYPE_VIRT,
                                                                 description=self.hostname+".local routing area")
                                local_routing_area.save()

                            loopback_subnet = SubnetService.find_subnet(sb_name=self.hostname+".loopback")
                            if loopback_subnet is None:
                                loopback_subnet = Subnet(name=self.hostname+".loopback",
                                                         description=self.hostname + " loopback subnet",
                                                         routing_area_id=local_routing_area.id,
                                                         ip=subnet_ip, mask=subnet_mask)
                                loopback_subnet.save()
                            self.osi.add_subnet(loopback_subnet)

                            ip_address = IPAddressService.find_ip_address(nic.ipv4_fqdn)
                            if ip_address is None:
                                ip_address = IPAddress(ip_address=nic.ipv4_address, fqdn=nic.ipv4_fqdn,
                                                       ipa_subnet_id=loopback_subnet, ipa_osi_id=self.osi.id)
                                ip_address.save()
                                loopback_subnet.sync()

                except Exception as e:
                    print(e.__str__())

    def update_ariane_directories(self, operating_system):
        pass

    def synchronize_with_ariane_directories(self, component):
        operating_system = component.operating_system.get()
        self.update_ariane_directories(operating_system)
        self.update_count += 1


class MappingGear(InjectorGearSkeleton):
    def __init__(self):
        self.hostname = socket.gethostname()
        super(MappingGear, self).__init__(
            gear_id='ariane.community.plugin.procos.gears.cache.mapping_gear@'+self.hostname,
            gear_name='procos_mapping_gear@'+self.hostname,
            gear_description='Ariane ProcOS injector gear for '+self.hostname,
            gear_admin_queue='ariane.community.plugin.procos.gears.cache.mapping_gear@'+self.hostname,
            running=False
        )
        self.update_count = 0

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

    def synchronize_with_ariane_mapping(self, component):
        self.update_count += 1


class SystemGear(InjectorGearSkeleton):
    def __init__(self, config):
        self.hostname = socket.gethostname()
        super(SystemGear, self).__init__(
            gear_id='ariane.community.plugin.procos.gears.cache.system_gear@'+self.hostname,
            gear_name='procos_system_gear@'+self.hostname,
            gear_description='Ariane ProcOS system gear for '+self.hostname,
            gear_admin_queue='ariane.community.plugin.procos.gears.cache.system_gear@'+self.hostname,
            running=False
        )
        self.component = SystemComponent.start(attached_gear_id=self.gear_id()).proxy()
        self.sleeping_period = config.sleeping_period
        self.service = None
        self.service_name = 'system_procos@'+self.hostname+' gear'
        self.directory_gear = DirectoryGear.start(config).proxy()
        self.mapping_gear = MappingGear.start().proxy()

    def run(self):
        if self.sleeping_period is not None and self.sleeping_period > 0:
            self.component.sniff()
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