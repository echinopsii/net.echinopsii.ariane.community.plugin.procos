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
        self.routing_area = None
        self.process_filter = None
        self.netstat_filter = None
        self.lsof_filter = None

    def parse(self, config_file):
        if not os.path.isfile(config_file):
            raise exceptions.ArianeProcOSConfigFileError(config_file)

        config = configparser.ConfigParser()
        config.read(config_file)

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
            self.datacenter_name = config['ariane_procos']['datacenter_name']
            if self.datacenter_name is None or not self.datacenter_name:
                ariane_procos_missing_fields.append('datacenter_name')

            self.routing_area = config['ariane_procos']['routing_area']
            if self.routing_area is None or not self.routing_area:
                ariane_procos_missing_fields.append('routing_area')

            if ariane_procos_missing_fields.__len__() == 0:
                self.process_filter = config['ariane_procos']['process_filter']
                self.netstat_filter = config['ariane_procos']['netstat_filter']
                self.lsof_filter = config['ariane_procos']['lsof_filter']
        else:
            raise exceptions.ArianeProcOSConfigMandatorySectionMissingError('ariane_server')

        if ariane_procos_missing_fields.__len__() > 0:
            raise exceptions.ArianeProcOSConfigMandatoryFieldsMissingError(ariane_procos_missing_fields)

        return self