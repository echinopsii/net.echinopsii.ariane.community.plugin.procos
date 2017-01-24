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
import timeit
import traceback
from ariane_clip3.injector import InjectorComponentSkeleton, InjectorCachedComponent
from ariane_procos.system import OperatingSystem

__author__ = 'mffrench'

LOGGER = logging.getLogger(__name__)


class SystemComponent(InjectorComponentSkeleton):
    def __init__(self, attached_gear_id=None, hostname=socket.gethostname(),
                 component_type=None, system_gear_actor_ref=None, domino_activator=None,
                 domino_topic=None, config=None):
        LOGGER.debug("SystemComponent.__init__")
        self.hostname = hostname
        self.domino = domino_activator
        self.topic = domino_topic
        self.system_gear_actor_ref = system_gear_actor_ref
        self.config = config
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
            self.operating_system.config = config
        else:
            self.operating_system = OperatingSystem(config=config)
            self.operating_system.sniff()
        self.version = 0

    def data_blob(self):
        LOGGER.debug("SystemComponent.data_blob")
        return json.dumps(self.operating_system.operating_system_2_json())

    def sniff(self, synchronize_with_ariane_dbs=True):
        try:
            LOGGER.debug("SystemComponent.sniff - activate " + self.topic)
            self.domino.activate(self.topic)
            start_time = timeit.default_timer()
            self.cache(refreshing=True, next_action=InjectorCachedComponent.action_update, data_blob=self.data_blob())
            self.operating_system.update()
            self.cache(
                refreshing=False, next_action=InjectorCachedComponent.action_update,
                data_blob=self.data_blob(), rollback_point=True
            )
            self.version += 1
            sniff_time = timeit.default_timer()-start_time
            LOGGER.info("SystemComponent.sniff - time : " + str(sniff_time))
            if synchronize_with_ariane_dbs and self.system_gear_actor_ref is not None:
                self.system_gear_actor_ref.proxy().synchronize_with_ariane_dbs()
        except Exception as e:
            LOGGER.error("SystemComponent.sniff - exception raised : " + e.__str__())
            LOGGER.debug("SystemComponent.sniff - exception raised : " + traceback.format_exc())
