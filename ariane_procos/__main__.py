# Ariane ProcOS plugin
# main
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
import argparse
import logging
import sys
import signal
import time
from config import Config
from connector import ArianeConnector
from gears import SystemGear

__author__ = 'mffrench'

LOGGER = logging.getLogger(__name__)

ariane_connector = None
config_path = "/etc/ariane/procos.json"
config = None
system_gear = None


def shutdown_handle(signum, frame):
    if system_gear is not None:
        system_gear.stop().get()
    if ariane_connector is not None:
        ariane_connector.stop()

parser = argparse.ArgumentParser()
parser.add_argument("-c", "--configuration",
                    help="define your Ariane ProcOS configuration file path")
args = parser.parse_args()

if args.configuration:
    config_path = args.configuration

try:
    config = Config().parse(config_path)
except Exception as e:
    print('Ariane ProcOS plugin config issue: ' + e.__str__())

if config is not None:
    ariane_connector = ArianeConnector(config)
    if ariane_connector.ready:
        signal.signal(signal.SIGINT, shutdown_handle)
        signal.signal(signal.SIGTERM, shutdown_handle)
        system_gear = SystemGear.start(config=config).proxy()
        signal.pause()