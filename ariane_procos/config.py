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
from ariane_procos import exceptions

__author__ = 'mffrench'


class Config(object):

    def __init__(self):
        self.rest_base_url = None
        self.rest_user = None
        self.rest_password = None

        self.rbmq_host = None
        self.rbmq_port = None
        self.rbmq_user = None
        self.rbmq_password = None
        self.rbmq_vhost = None

        self.sleeping_period = None

        self.datacenter_name = None
        self.datacenter_description = None
        self.datacenter_address = None
        self.datacenter_zipcode = None
        self.datacenter_town = None
        self.datacenter_country = None
        self.datacenter_gps_lat = None
        self.datacenter_gps_lng = None

        self.routing_area_name = None
        self.routing_area_multicast = None
        self.routing_area_type = None
        self.routing_area_description = None

        self.subnet_name = None
        self.subnet_description = None

        self.osi_description = None
        self.osi_admin_gate_uri_proto = None
        self.environment = None
        self.team = None

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
            if self.rbmq_password is None or not self.rest_password:
                ariane_server_missing_fields.append('rbmq_password')

            self.rbmq_vhost = config['ariane_server']['rbmq_vhost']
            if self.rbmq_vhost is None or not self.rbmq_vhost:
                ariane_server_missing_fields.append('rbmq_vhost')
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

            if ariane_procos_missing_fields.__len__() == 0:
                self.datacenter_name = config['ariane_procos']['datacenter_name']
                self.datacenter_description = config['ariane_procos']['datacenter_description']
                self.datacenter_address = config['ariane_procos']['datacenter_address']
                self.datacenter_zipcode = config['ariane_procos']['datacenter_zipcode']
                self.datacenter_town = config['ariane_procos']['datacenter_town']
                self.datacenter_country = config['ariane_procos']['datacenter_country']
                self.datacenter_gps_lat = config['ariane_procos']['datacenter_gps_lat']
                self.datacenter_gps_lng = config['ariane_procos']['datacenter_gps_lng']

                self.routing_area_name = config['ariane_procos']['routing_area_name']
                self.routing_area_multicast = config['ariane_procos']['routing_area_multicast']
                self.routing_area_type = config['ariane_procos']['routing_area_type']
                self.routing_area_description = config['ariane_procos']['routing_area_description']

                self.subnet_name = config['ariane_procos']['subnet_name']
                self.subnet_description = config['ariane_procos']['subnet_description']

                self.osi_description = config['ariane_procos']['osi_description']
                self.osi_admin_gate_uri_proto = config['ariane_procos']['osi_admin_gate_uri_proto']
                self.environment = config['ariane_procos']['environment']
                self.team = config['ariane_procos']['team']
        else:
            raise exceptions.ArianeProcOSConfigMandatorySectionMissingError('ariane_server')

        if ariane_procos_missing_fields.__len__() > 0:
            raise exceptions.ArianeProcOSConfigMandatoryFieldsMissingError(ariane_procos_missing_fields)

        return self