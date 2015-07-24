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
import socket
from ariane_clip3.injector import InjectorComponentSkeleton, InjectorCachedComponent

__author__ = 'mffrench'


class SystemComponent(InjectorComponentSkeleton):
    def __init__(self, config, attached_gear_id=None):
        self.hostname = socket.gethostname()
        super(SystemComponent, self).__init__(
            component_id=
            'ariane.community.plugin.procos.components.cache.system_component@' + self.hostname,
            component_name='procos_system_component@localhost',
            component_admin_queue=
            'ariane.community.plugin.procos.components.cache.system_component@' + self.hostname,
            refreshing=False, next_action=InjectorCachedComponent.action_create,
            json_last_refresh=datetime.datetime.now(),
            attached_gear_id=attached_gear_id,
            data_blob=''
        )
        self.version = 0

    def data_blob(self):
        json_obj = {
            'hostname': self.hostname
        }
        return str(json_obj).replace("'", '"')

    def sniff(self):
        self.hostname = socket.gethostname()
        self.cache(data_blob=self.data_blob())
        self.version += 1