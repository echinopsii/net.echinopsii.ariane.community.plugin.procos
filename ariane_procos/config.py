# Ariane ProcOS plugin
# ProcOS config
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
import configparser
import json
import os
from ariane_clip3.driver_factory import DriverFactory
from ariane_procos import exceptions

__author__ = 'mffrench'


class EnvironmentConfig(object):
    def __init__(self, name=None, color_code=None, description = None):
        self.name = name
        self.description = description
        self.color_code = color_code

    def __eq__(self, other):
        if self.name != other.name:
            return False
        else:
            return True


class TeamConfig(object):
    def __init__(self, name, color_code, description):
        self.name = name
        self.color_code = color_code
        self.description = description

    def __eq__(self, other):
        if self.name != other.name:
            return False
        else:
            return True


class OrganizationContextConfig(object):
    def __init__(self, team=None, environment=None):
        self.team = team
        self.environment = environment

    def __eq__(self, other):
        if self.team != other.team or self.environment != other.environment:
            return False
        else:
            return True


class CompanyConfig(object):
    def __init__(self, name=None, description=None):
        self.name = name
        self.description = description


class SystemTypeConfig(object):
    def __init__(self, name=None, architecture=None, company=None):
        self.name = name
        self.architecture = architecture
        self.company = company


class SystemContextConfig(object):
    def __init__(self, description=None, admin_gate_protocol=None, admin_gate_port=None, embedding_osi_hostname=None, os_type=None):
        self.description = description
        self.admin_gate_protocol = admin_gate_protocol
        self.admin_gate_port = admin_gate_port
        self.embedding_osi_hostname = embedding_osi_hostname
        self.os_type = os_type


class SubnetConfig(object):
    def __init__(self, name=None, description=None, subnet_ip=None, subnet_mask=None):
        self.name = name
        self.description = description
        self.subnet_ip = subnet_ip
        self.subnet_mask = subnet_mask

    def __eq__(self, other):
        if self.name != other.name:
            return False
        else:
            return True


class RoutingAreaConfig(object):
    def __init__(self, name=None, description=None, multicast=None, ra_type=None):
        self.name = name
        self.description = description
        self.multicast = multicast
        self.type = ra_type
        self.subnets = []

    def __eq__(self, other):
        if self.name != other.name:
            return False
        else:
            return True


class LocationConfig(object):
    def __init__(self, name=None, description=None, type=None, address=None, zipcode=None, town=None, country=None,
                 gps_lat=None, gps_lng=None):
        self.name = name
        self.description = description
        self.type = type
        self.address = address
        self.zipcode = zipcode
        self.town = town
        self.country = country
        self.gps_lat = gps_lat
        self.gps_lng = gps_lng
        self.routing_areas = []

    def __eq__(self, other):
        if self.name != other.name:
            return False
        else:
            return True

class Config(object):

    def __init__(self):
        self.rest_base_url = None
        self.rest_user = None
        self.rest_password = None

        self.nats_host = None
        self.nats_port = None
        self.nats_user = None
        self.nats_password = None

        self.rbmq_host = None
        self.rbmq_port = None
        self.rbmq_user = None
        self.rbmq_password = None
        self.rbmq_vhost = None

        self.rpc_timeout = 10   # 10 sec timeout by default
        self.rpc_retry = 2   # 2 retry by default

        self.sleeping_period = None
        self.processes_filter = None
        self.log_conf_file_path = None

        self.injector_driver_type = DriverFactory.DRIVER_NATS
        self.mapping_driver_type = DriverFactory.DRIVER_NATS

        #List of possible locations this OS instance could be located with routing area and subnets
        #(labtop of VM which can move through an hypervisor)
        self.local_routing_area = None
        self.potential_locations = []
        self.system_context = None
        self.organisation_context = None

    def parse(self, config_file):
        if not os.path.isfile(config_file):
            raise exceptions.ArianeProcOSConfigFileError(config_file)

        config_file = open(config_file, 'r')
        config = json.load(config_file)

        ariane_server_missing_fields = []
        if 'ariane_server' in config:
            self.rest_base_url = config['ariane_server']['rest_base_url']
            if self.rest_base_url is None or not self.rest_base_url:
                ariane_server_missing_fields.append('rest_base_url')

            self.rest_user = config['ariane_server']['rest_user']
            if self.rest_user is None or not self.rest_user:
                ariane_server_missing_fields.append('rest_user')

            self.rest_password = config['ariane_server']['rest_password']
            if self.rest_password is None or not self.rest_password:
                ariane_server_missing_fields.append('rest_password')

            self.nats_host = config['ariane_server']['nats_host']
            if self.nats_host is None or not self.nats_host:
                ariane_server_missing_fields.append('nats_host')

            self.nats_port = config['ariane_server']['nats_port']
            if self.nats_port is None or not self.nats_port:
                ariane_server_missing_fields.append('nats_port')

            self.nats_user = config['ariane_server']['nats_user']
            if self.nats_user is None or not self.nats_user:
                ariane_server_missing_fields.append('nats_user')

            self.nats_password = config['ariane_server']['nats_password']
            if self.nats_password is None or not self.nats_password:
                ariane_server_missing_fields.append('nats_password')

            self.rbmq_host = config['ariane_server']['rbmq_host']
            if self.rbmq_host is None or not self.rbmq_host:
                ariane_server_missing_fields.append('rbmq_host')

            self.rbmq_port = config['ariane_server']['rbmq_port']
            if self.rbmq_port is None or not self.rbmq_port:
                ariane_server_missing_fields.append('rbmq_port')

            self.rbmq_user = config['ariane_server']['rbmq_user']
            if self.rbmq_user is None or not self.rbmq_user:
                ariane_server_missing_fields.append('rbmq_user')

            self.rbmq_password = config['ariane_server']['rbmq_password']
            if self.rbmq_password is None or not self.rbmq_password:
                ariane_server_missing_fields.append('rbmq_password')

            self.rbmq_vhost = config['ariane_server']['rbmq_vhost']
            if self.rbmq_vhost is None or not self.rbmq_vhost:
                ariane_server_missing_fields.append('rbmq_vhost')

            if 'rpc_timeout' in config['ariane_server']:
                self.rpc_timeout = config['ariane_server']['rpc_timeout']

            if 'rpc_retry' in config['ariane_server']:
                self.rpc_retry = config['ariane_server']['rpc_retry']
        else:
            raise exceptions.ArianeProcOSConfigMandatorySectionMissingError('ariane_server')

        if ariane_server_missing_fields.__len__() > 0:
            raise exceptions.ArianeProcOSConfigMandatoryFieldsMissingError(ariane_server_missing_fields)

        ariane_procos_missing_fields = []
        if 'ariane_procos' in config:
            self.sleeping_period = config['ariane_procos']['sleeping_period']
            if self.sleeping_period is None or not self.sleeping_period:
                ariane_procos_missing_fields.append('sleeping_period')
            else:
                try:
                    self.sleeping_period = int(self.sleeping_period)
                except ValueError:
                    raise exceptions.ArianeProcOSConfigMandatoryFieldsValueError('sleeping_period',
                                                                                 'should be an integer !')
            if 'log_conf_file_path' in config['ariane_procos']:
                self.log_conf_file_path = config['ariane_procos']['log_conf_file_path']

            if 'processes_name_filter' in config['ariane_procos']:
                processes = config['ariane_procos']['processes_name_filter']
                if processes is not None and isinstance(processes, str):
                    self.processes_filter = []
                    self.processes_filter.append(processes)
                elif processes is not None and isinstance(processes, list):
                    self.processes_filter = processes

            if 'injector_driver' in config['ariane_procos']:
                injector_dt = config['ariane_procos']['injector_driver']
                if injector_dt == DriverFactory.DRIVER_RBMQ:
                    self.injector_driver_type = DriverFactory.DRIVER_RBMQ

            if 'mapping_driver' in config['ariane_procos']:
                mapping_dt = config['ariane_procos']['mapping_driver']
                if mapping_dt == DriverFactory.DRIVER_REST:
                    self.mapping_driver_type = DriverFactory.DRIVER_REST
                elif mapping_dt == DriverFactory.DRIVER_RBMQ:
                    self.mapping_driver_type = DriverFactory.DRIVER_RBMQ

            if ariane_procos_missing_fields.__len__() == 0:
                if config['ariane_procos']['local_routingarea'] is not None:
                    self.local_routing_area = RoutingAreaConfig(
                        name=config['ariane_procos']['local_routingarea']['name'],
                        description=config['ariane_procos']['local_routingarea']['description'],
                        multicast=config['ariane_procos']['local_routingarea']['multicast'],
                        ra_type=config['ariane_procos']['local_routingarea']['type'],
                    )
                    for subnet in config['ariane_procos']['local_routingarea']['subnets']:
                        subnet_config = SubnetConfig(
                            name=subnet['name'],
                            description=subnet['description'],
                            subnet_ip=subnet['subnet_ip'],
                            subnet_mask=subnet['subnet_mask']
                        )
                        self.local_routing_area.subnets.append(subnet_config)
                if config['ariane_procos']['potential_locations'] is not None:
                    for location in config['ariane_procos']['potential_locations']:
                        location_config = LocationConfig(
                            name=location['name'],
                            description=location['description'],
                            type=location['type'],
                            address=location['address'],
                            zipcode=location['zipcode'],
                            town=location['town'],
                            country=location['country'],
                            gps_lat=location['gps_lat'],
                            gps_lng=location['gps_lng']
                        )
                        for routing_area in location['routing_areas']:
                            routing_area_config = RoutingAreaConfig(
                                name=routing_area['name'],
                                description=routing_area['description'],
                                multicast=routing_area['multicast'],
                                ra_type=routing_area['type']
                            )
                            for subnet in routing_area['subnets']:
                                subnet_config = SubnetConfig(
                                    name=subnet['name'],
                                    description=subnet['description'],
                                    subnet_ip=subnet['subnet_ip'],
                                    subnet_mask=subnet['subnet_mask']
                                )
                                routing_area_config.subnets.append(subnet_config)
                            location_config.routing_areas.append(routing_area_config)
                        self.potential_locations.append(location_config)

                if config['ariane_procos']['system_context'] is not None:
                    ost_company = CompanyConfig(
                        name=config['ariane_procos']['system_context']['type']['supporting_company']['name'],
                        description=config['ariane_procos']['system_context']['type']['supporting_company']['description']
                    )
                    ost = SystemTypeConfig(
                        name=config['ariane_procos']['system_context']['type']['name'],
                        architecture=config['ariane_procos']['system_context']['type']['architecture'],
                        company=ost_company
                    )
                    self.system_context = SystemContextConfig(
                        description=config['ariane_procos']['system_context']['description'],
                        admin_gate_protocol=config['ariane_procos']['system_context']['admin_gate']['protocol'],
                        admin_gate_port=config['ariane_procos']['system_context']['admin_gate']['port'],
                        embedding_osi_hostname=config['ariane_procos']['system_context']['embedding_osi_hostname'],
                        os_type=ost
                    )

                if config['ariane_procos']['organization_context'] is not None:
                    team = None
                    environment = None
                    if config['ariane_procos']['organization_context']['team']:
                        team = TeamConfig(
                            name=config['ariane_procos']['organization_context']['team']['name'],
                            color_code=config['ariane_procos']['organization_context']['team']['color_code'],
                            description=config['ariane_procos']['organization_context']['team']['description']
                        )
                    if config['ariane_procos']['organization_context']['environment'] is not None:
                        environment = EnvironmentConfig(
                            name=config['ariane_procos']['organization_context']['environment']['name'],
                            color_code=config['ariane_procos']['organization_context']['environment']['color_code'],
                            description=config['ariane_procos']['organization_context']['environment']['description']
                        )
                    self.organisation_context = OrganizationContextConfig(team=team, environment=environment)

        else:
            raise exceptions.ArianeProcOSConfigMandatorySectionMissingError('ariane_server')

        if ariane_procos_missing_fields.__len__() > 0:
            raise exceptions.ArianeProcOSConfigMandatoryFieldsMissingError(ariane_procos_missing_fields)

        return self
