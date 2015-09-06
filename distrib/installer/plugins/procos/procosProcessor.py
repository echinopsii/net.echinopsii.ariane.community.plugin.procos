# installer plugin rabbitmq processor
#
# Copyright (C) 2014 Mathilde Ffrench
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
import os
from plugins.rabbitmq.dbRabbitmqDirectoryMySQLInitiator import dbRabbitmqDirectoryMySQLInitiator
from plugins.rabbitmq.dbIDMMySQLPopulator import dbIDMMySQLPopulator
from plugins.rabbitmq.cuRabbitmqInjectorManagedServiceProcessor import rabbitmqInjectorManagedServiceSyringe
from plugins.rabbitmq.cuRabbitmqInjectorComponentsCacheProcessor import cuInjectorComponentsCacheProcessor
from plugins.rabbitmq.cuRabbitmqInjectorGearsCacheProcessor import cuInjectorGearsCacheProcessor, cpInjectorGearsCacheDir

__author__ = 'mffrench'


class procosProcessor:

    def __init__(self, homeDirPath, directoryDBConfig, idmDBConfig, silent):
        print("\n%--%--%--%--%--%--%--%--%--%--%--%--%--%--%--%--%--%--%--%--%--%--%--%--%--%--%--%--%--%--%--%--%--%--%--%--%--%--%--%--%--%--%--\n")
        print("%-- Plugin ProcOS configuration : \n")
        self.homeDirPath = homeDirPath
        self.silent = silent
        if not os.path.exists(self.homeDirPath + "/ariane/cache/plugins/rabbitmq/"):
            os.makedirs(self.homeDirPath + "/ariane/cache/plugins/rabbitmq/", 0o755)
        self.procosIDMMySQLPopulator = dbIDMMySQLPopulator(idmDBConfig)

    def process(self):
        self.procosIDMMySQLPopulator.process()
        return self