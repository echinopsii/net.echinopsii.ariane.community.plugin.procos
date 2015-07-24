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
from ariane_clip3.injector import InjectorGearSkeleton
from components import SystemComponent

__author__ = 'mffrench'


class DirectoryGear(InjectorGearSkeleton):
    def __init__(self):
        self.hostname = socket.gethostname()
        super(DirectoryGear, self).__init__(
            gear_id='ariane.community.plugin.procos.gears.cache.directory_gear@'+self.hostname,
            gear_name='procos_directory_gear@'+self.hostname,
            gear_description='Ariane ProcOS directory gear for '+self.hostname,
            gear_admin_queue='ariane.community.plugin.procos.gears.cache.directory_gear@'+self.hostname,
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

    def synchronize_with_ariane_directories(self, data):
        self.update_count += 1


class SystemGear(InjectorGearSkeleton):
    def __init__(self, config, directory_gear_proxy, mapping_gear_proxy):
        self.hostname = socket.gethostname()
        super(SystemGear, self).__init__(
            gear_id='ariane.community.plugin.procos.gears.cache.system_gear@'+self.hostname,
            gear_name='procos_system_gear@'+self.hostname,
            gear_description='Ariane ProcOS system gear for '+self.hostname,
            gear_admin_queue='ariane.community.plugin.procos.gears.cache.system_gear@'+self.hostname,
            running=False
        )
        self.sleeping_period = config.sleeping_period
        self.service = None
        self.service_name = 'system_procos@'+self.hostname+' gear'
        self.component = SystemComponent.start(config, attached_gear_id=self.gear_id()).proxy()
        self.directory_gear = directory_gear_proxy
        self.mapping_gear = mapping_gear_proxy

    def run(self):
        if self.sleeping_period is not None and self.sleeping_period > 0:
            while self.running:
                time.sleep(self.sleeping_period)
                self.component.sniff()
                data_blob = self.component.data_blob()
                self.directory_gear.synchronize_with_ariane_directories(data_blob)
                self.mapping_gear.synchronize_with_ariane_mapping(data_blob)

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

    def synchronize_with_ariane_mapping(self, data):
        self.update_count += 1