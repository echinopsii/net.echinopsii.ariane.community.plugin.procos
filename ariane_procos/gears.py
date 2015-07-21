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
import threading
import time
from ariane_clip3.injector import InjectorGearSkeleton
from components import SystemComponent

__author__ = 'mffrench'


class DirectoryGear(InjectorGearSkeleton):
    def __init__(self):
        super(DirectoryGear, self).__init__(
            gear_id='ariane.community.plugin.procos.gears.cache.directory_gear@localhost',
            gear_name='docker@localhost',
            gear_description='Ariane remote injector for localhost',
            gear_admin_queue='ariane.community.plugin.procos.gears.cache.directory_gear@localhost',
            running=False
        )

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


class SystemGear(InjectorGearSkeleton):
    def __init__(self, sleeping_period):
        super(SystemGear, self).__init__(
            gear_id='ariane.community.plugin.procos.gears.cache.system_gear@localhost',
            gear_name='docker@localhost',
            gear_description='Ariane remote injector for localhost',
            gear_admin_queue='ariane.community.plugin.procos.gears.cache.system_gear@localhost',
            running=False
        )
        self.sleeping_period = sleeping_period
        self.service = None
        self.service_name = 'docker@localhost gear'
        self.component = SystemComponent.start(attached_gear_id=self.gear_id()).proxy()

    def run(self):
        if self.sleeping_period is not None and self.sleeping_period > 0:
            while self.running:
                time.sleep(self.sleeping_period)
                self.component.sniff()

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
        super(MappingGear, self).__init__(
            gear_id='ariane.community.plugin.procos.gears.cache.mapping_gear@localhost',
            gear_name='docker@localhost',
            gear_description='Ariane remote injector for localhost',
            gear_admin_queue='ariane.community.plugin.procos.gears.cache.mapping_gear@localhost',
            running=False
        )

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