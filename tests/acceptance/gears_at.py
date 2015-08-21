import socket
import unittest
import time
from config import Config
from connector import ArianeConnector
from gears import SystemGear

__author__ = 'mffrench'


class GearsSkeletonTest(unittest.TestCase):

    def setUp(self):
        self.config = Config().parse("valid_config.json")
        self.ariane_connector = ArianeConnector(self.config)

    def test_gear_skeleton(self):
        if self.ariane_connector.ready:
            system_gear = SystemGear.start(config=self.config).proxy()
            time.sleep(100)

            directory_update_count = system_gear.directory_gear.get().update_count.get()
            self.assertTrue(directory_update_count >= 1)

            mapping_update_count = system_gear.mapping_gear.get().update_count.get()
            self.assertTrue(mapping_update_count >= 1)

            current_blob = system_gear.component.get().component_cache_actor.get().blob.get()
            self.assertTrue(current_blob is not None)

            system_gear.stop()
            system_gear = SystemGear.start(config=self.config).proxy()
            time.sleep(100)

            current_blob = system_gear.component.get().component_cache_actor.get().blob.get()
            self.assertTrue(current_blob is not None)
            system_gear.stop()

            self.ariane_connector.stop()

    def tearDown(self):
        self.ariane_connector.stop()
