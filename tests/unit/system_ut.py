from pprint import pprint
import unittest
from system import OperatingSystem

__author__ = 'mffrench'


class SystemTest(unittest.TestCase):

    def test_operating_system_serialization_deserialization(self):
        os = OperatingSystem()
        os.sniff()
        os_json = os.operating_system_2_json()
        pprint(os_json)
        os_from_json = OperatingSystem.json_2_operating_system(os_json)