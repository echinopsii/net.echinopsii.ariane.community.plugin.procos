# Ariane ProcOS plugin
# Connectors to Ariane server
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
from ariane_clip3.injector import InjectorService, InjectorUITreeEntity, InjectorUITreeService, \
    InjectorCachedComponentService, InjectorCachedGearService
from ariane_clip3.mapping import MappingService
from ariane_clip3.directory import DirectoryService

__author__ = 'mffrench'


class ArianeConnector(object):

    def __init__(self, procos_config):
        rest_args = {
            'type': 'REST',
            'base_url': procos_config.rest_base_url,
            'user': procos_config.rest_user,
            'password': procos_config.rest_password
        }
        client_properties = {
            'product': 'Ariane Plugin ProcOS',
            'information': 'Ariane Plugin ProcOS - Map your Operating System Process interaction and more ...',
            'ariane.pgurl': 'ssh://' + socket.gethostname(),
            'ariane.osi': socket.gethostname(),
            'ariane.otm': 'ArianeOPS',
            'ariane.app': 'Ariane',
            'ariane.cmp': 'echinopsii'
        }
        rbmq_args = {
            'type': 'RBMQ',
            'user': procos_config.rbmq_user,
            'password': procos_config.rbmq_password,
            'host': procos_config.rbmq_host,
            'port': procos_config.rbmq_port,
            'vhost': procos_config.rbmq_vhost,
            'client_properties': client_properties
        }
        self.gears_registry_cache_id = 'ariane.community.plugin.procos.gears.cache'
        procos_gears_registry_conf = {
            'registry.name': 'Ariane ProcOS plugin gears registry',
            'registry.cache.id': self.gears_registry_cache_id,
            'registry.cache.name': 'Ariane ProcOS plugin gears cache',
            'cache.mgr.name': 'ARIANE_PLUGIN_PROCOS_GEARS_CACHE_MGR'
        }
        self.components_registry_cache_id = 'ariane.community.plugin.procos.components.cache'
        procos_components_registry_conf = {
            'registry.name': 'Ariane ProcOS plugin components registry',
            'registry.cache.id': self.components_registry_cache_id,
            'registry.cache.name': 'Ariane ProcOS plugin components cache',
            'cache.mgr.name': 'ARIANE_PLUGIN_PROCOS_COMPONENTS_CACHE_MGR'
        }

        DirectoryService(rest_args)
        MappingService(rest_args)
        self.injector_service = InjectorService(
            driver_args=rbmq_args, gears_registry_args=procos_gears_registry_conf,
            components_registry_args=procos_components_registry_conf
        )

        # Register UI entity if needed
        self.injector_ui_mapping_entity = InjectorUITreeService.find_ui_tree_entity('mappingDir')
        self.injector_ui_system_entity = InjectorUITreeEntity(uitid="systemDir", value="System",
                                                              uitype=InjectorUITreeEntity.entity_dir_type,
                                                              context_address="", description="",
                                                              parent_id=self.injector_ui_mapping_entity.id,
                                                              display_roles=["sysadmin"],
                                                              display_permissions=["injMapSysOS:display"])
        self.injector_ui_system_entity.save()
        self.injector_ui_procos_entity = InjectorUITreeEntity(uitid="procos", value="ProcOS",
                                                              uitype=InjectorUITreeEntity.entity_leaf_type,
                                                              context_address=
                                                              "/ariane/views/injectors/external.jsf?id=procos",
                                                              description="ProcOS injector", icon="icon-cog",
                                                              parent_id=self.injector_ui_system_entity.id,
                                                              display_roles=["sysadmin", "sysreviewer"],
                                                              display_permissions=["injMapSysOS:display"],
                                                              remote_injector_tree_entity_gears_cache_id=
                                                              self.gears_registry_cache_id,
                                                              remote_injector_tree_entity_components_cache_id=
                                                              self.components_registry_cache_id)
        self.injector_ui_procos_entity.save()
        self.ready = True

    def stop(self):
        if InjectorCachedGearService.get_gears_cache_size() == 0 and \
                InjectorCachedComponentService.get_components_cache_size() == 0:
            self.injector_ui_procos_entity.remove()
        self.injector_service.stop()
        self.ready = False