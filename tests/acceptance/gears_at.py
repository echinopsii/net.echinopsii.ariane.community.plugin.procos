import socket
import unittest
import time
from config import Config
from connector import ArianeConnector
from gears import DirectoryGear, SystemGear, MappingGear

__author__ = 'mffrench'


class GearsSkeletonTest(unittest.TestCase):

    def setUp(self):
        self.config = Config().parse("valid_config.ini")
        client_properties = {
            'product': 'Ariane Plugin ProcOS Test',
            'information': 'Ariane Plugin ProcOS Test - Acceptance test on ariane_connector',
            'ariane.pgurl': 'ssh://' + socket.gethostname(),
            'ariane.osi': socket.gethostname(),
            'ariane.otm': 'ArianeOPS',
            'ariane.app': 'Ariane',
            'ariane.cmp': 'echinopsii'
        }
        self.rbmq_args = {
            'type': 'RBMQ',
            'user': self.config.rbmq_user,
            'password': self.config.rbmq_password,
            'host': self.config.rbmq_host,
            'port': self.config.rbmq_port,
            'vhost': self.config.rbmq_vhost,
            'client_properties': client_properties
        }
        self.ariane_connector = ArianeConnector(self.config)

    def tearDown(self):
        self.ariane_connector.stop()

    def test_gear_skeleton(self):
        system_gear = SystemGear.start(config=self.config).proxy()
        time.sleep(5)
        self.assertTrue(system_gear.directory_gear.get().update_count.get() == 1)
        self.assertTrue(system_gear.mapping_gear.get().update_count.get() == 1)