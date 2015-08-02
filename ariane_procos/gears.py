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
    OSInstance, SubnetService, Subnet
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
        self.datacenter = None
        self.routing_areas = []
        self.subnets = []
        self.osi = None

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

    def synchronize_with_ariane_directories(self, component):
        operating_system = component.operating_system.get()

        # Find current Datacenter and Subnets according to runtime IP on NICs and possible datacenters:
        possible_datacenter_config = []
        possible_routing_area_config = []
        possible_subnet_config = []

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
                                        if datacenter_config not in possible_datacenter_config:
                                            possible_datacenter_config.append(datacenter_config)
                                        possible_routing_area_config.append(routing_area_config)
                                        possible_subnet_config.append(subnet_config)
                                        nic_is_located = True
            except Exception as e:
                print(e.__str__())
                pass

            if not nic_is_located:
                print('WARN: nic ' + nic.mac_address + ' / ' + nic.ipv4_address + ' has not been located on the '
                                                                                  ' possibles networks')

        if possible_datacenter_config.__len__() > 1:
            print('WARN: multiple possible datacenter found - will ignore directories sync')
        elif possible_datacenter_config.__len__() == 0:
            print('WARN: no possible datacenter found - will ignore directories sync')

        # Sync Ariane Directories if not done already
        self.osi = OSInstanceService.find_os_instance(osi_name=self.hostname)
        if self.osi is None:
            self.osi = OSInstance(name=self.hostname, description=self.config.system_context.description,
                                  admin_gate_uri=self.config.system_context.admin_gate_protocol+self.hostname)
            self.osi.save()
        operating_system.osi_id = self.osi.id

        if possible_datacenter_config.__len__() == 1:
            current_datacenter = possible_datacenter_config[0]
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

            for routing_area_config in possible_routing_area_config:
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
                    if subnet_config in possible_subnet_config:
                        subnet = SubnetService.find_subnet(sb_name=subnet_config)
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

            for subnet_id in self.osi.subnet_ids:
                if subnet_id not in operating_system.subnet_ids:
                    for subnet in self.subnets:
                        if subnet.id == subnet_id:
                            self.osi.del_subnet(subnet)

            for nic in operating_system.nics:
                try:
                    if nic.ipv4_address is not None:
                        subnet_ip = nic.ipv4_address.split('.')[0] + '.' + nic.ipv4_address.split('.')[1] + '.' + \
                                    nic.ipv4_address.split('.')[2] + '.0'
                        subnet_mask = nic.ipv4_mask

                        if subnet_ip != '127.0.0.0':
                            for subnet in self.subnets:
                                if subnet_ip == subnet.ip and subnet_mask == subnet.mask:
                                    pass

                except Exception as e:
                    print(e.__str__())
                    pass

         #####
        for nic in operating_system.nics:
            try:
                if nic.ipv4_address is not None:
                    subnet_ip = nic.ipv4_address.split('.')[0] + '.' + nic.ipv4_address.split('.')[1] + '.' + \
                                     nic.ipv4_address.split('.')[2] + '.0'
                    subnet_mask = nic.ipv4_mask

                    if subnet_ip == '127.0.0.0':
                        local_routing_area = RoutingAreaService.find_routing_area(
                            self.hostname+".local")
                        if local_routing_area is None:
                            local_routing_area = RoutingArea(name=self.hostname+".local",
                                                             multicast=RoutingArea.RA_MULTICAST_NOLIMIT,
                                                             ra_type=RoutingArea.RA_TYPE_VIRT,
                                                             description=self.hostname+".local routing area")
                            local_routing_area.save()

                        os_subnet = SubnetService.find_subnet(sb_name=self.hostname+".loopback")
                        if os_subnet is None:
                            os_subnet = Subnet(name=self.hostname+".loopback",
                                               description=self.hostname + " loopback subnet",
                                               routing_area_id=local_routing_area.id,
                                               ip=subnet_ip, mask=subnet_mask)
                            os_subnet.save()
                    else:
                        os_subnet = SubnetService.find_subnet(sb_name=self.config.subnet_name)
                        if os_subnet is None:
                            os_subnet = Subnet(name=self.config.datacenter_name,
                                               description=self.config.subnet_description,
                                               routing_area_id=operating_system.routing_area_id,
                                               ip=subnet_ip, mask=subnet_mask)
                            os_subnet.save()
                        operating_system.subnet_id = os_subnet.id
                        datacenter_config.add_subnet(os_subnet)
                    osi.add_subnet(os_subnet)
            except Exception as e:
                print(e.__str__())
                pass

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