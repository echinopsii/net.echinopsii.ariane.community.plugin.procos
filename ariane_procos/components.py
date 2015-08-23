# Ariane ProcOS plugin
# System component
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
import datetime
import json
import logging
import socket
import traceback
from ariane_clip3.injector import InjectorComponentSkeleton, InjectorCachedComponent
from ariane_procos.system import OperatingSystem

__author__ = 'mffrench'

LOGGER = logging.getLogger(__name__)


class SystemComponent(InjectorComponentSkeleton):
    def __init__(self, attached_gear_id=None, hostname=socket.gethostname(),
                 component_type=None, system_gear_actor_ref=None):
        self.hostname = hostname
        self.system_gear_actor_ref = system_gear_actor_ref
        super(SystemComponent, self).__init__(
            component_id=
            'ariane.community.plugin.procos.components.cache.system_component@' + self.hostname,
            component_name='procos_system_component@' + self.hostname,
            component_type=component_type if component_type is not None else "ProcOS injector",
            component_admin_queue=
            'ariane.community.plugin.procos.components.cache.system_component@' + self.hostname,
            refreshing=False, next_action=InjectorCachedComponent.action_create,
            json_last_refresh=datetime.datetime.now(),
            attached_gear_id=attached_gear_id
        )
        cached_blob = self.component_cache_actor.blob.get()
        if cached_blob is not None:
            self.operating_system = OperatingSystem.json_2_operating_system(cached_blob)
        else:
            self.operating_system = OperatingSystem()
            self.operating_system.sniff()
        self.version = 0

    def data_blob(self):
        return json.dumps(self.operating_system.operating_system_2_json())

    def sniff(self, synchronize_with_ariane_dbs=True):
        try:
            LOGGER.info("Sniffing...")
            self.cache(refreshing=True, next_action=InjectorCachedComponent.action_update, data_blob=self.data_blob())
            self.operating_system.update()
            self.cache(refreshing=False, next_action=InjectorCachedComponent.action_update, data_blob=self.data_blob())
            self.version += 1
            if synchronize_with_ariane_dbs and self.system_gear_actor_ref is not None:
                self.system_gear_actor_ref.proxy().synchronize_with_ariane_dbs()
        except Exception as e:
            LOGGER.error(e.__str__())
            LOGGER.error(traceback.format_exc())