import socket
import unittest
from ariane_clip3.injector import InjectorUITreeService, InjectorService, InjectorGearSkeleton
from connector import ArianeConnector
from config import Config

__author__ = 'mffrench'


class ArianeConnectorTest(unittest.TestCase):

    def setUp(self):
        self.config = Config().parse("valid_config.json")
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

    def tearDown(self):
        pass

    def test_start_and_stop_with_no_gears(self):
        ariane_connector = ArianeConnector(self.config)
        injector_ui_procos_entity_id = ariane_connector.injector_ui_procos_entity.id
        self.assertIsNotNone(InjectorUITreeService.find_ui_tree_entity(injector_ui_procos_entity_id))
        ariane_connector.stop()
        test_injector_service = InjectorService(self.rbmq_args)
        self.assertIsNone(InjectorUITreeService.find_ui_tree_entity(injector_ui_procos_entity_id))
        test_injector_service.stop()

    def test_start_and_stop_with_one_gear(self):
        ariane_connector = ArianeConnector(self.config)
        injector_ui_procos_entity_id = ariane_connector.injector_ui_procos_entity.id
        self.assertIsNotNone(InjectorUITreeService.find_ui_tree_entity(injector_ui_procos_entity_id))

        gear = InjectorGearSkeleton.start(gear_id='ariane.community.plugin.procos.gears.cache.localhost',
                                          gear_name='procos@localhost',
                                          gear_description='Ariane remote injector for localhost',
                                          gear_admin_queue='ariane.community.plugin.procos.gears.cache.localhost',
                                          running=False).proxy()
        self.assertTrue(gear.cache(running=True).get())
        ariane_connector.stop()
        test_injector_service = InjectorService(self.rbmq_args)
        self.assertIsNotNone(InjectorUITreeService.find_ui_tree_entity(injector_ui_procos_entity_id))
        test_injector_service.stop()
