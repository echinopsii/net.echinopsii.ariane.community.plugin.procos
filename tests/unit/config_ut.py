import unittest
from config import Config
from ariane_procos import exceptions

__author__ = 'mffrench'


class ConfigurationTest(unittest.TestCase):

    def test_bad_conf_file(self):
        try:
            Config().parse("some_unknown_file")
        except exceptions.ArianeProcOSConfigFileError:
            pass
        except Exception as e:
            self.fail('unexpected exception thrown: ' + str(e))
        else:
            self.fail('no exception thrown')

    def test_ariane_good_conf(self):
        try:
            config = Config().parse("aprocos_conf.json")
        except Exception as e:
            self.fail('unexpected exception thrown: ' + str(e))
        else:
            pass

    def test_ariane_server_not_in_conf_file(self):
        try:
            Config().parse("invalid_conf_10.json")
        except exceptions.ArianeProcOSConfigMandatorySectionMissingError:
            pass
        except Exception as e:
            self.fail('unexpected exception thrown: ' + str(e))
        else:
            self.fail('no exception thrown')

    def test_ariane_server_missing_mandatory_fields(self):
        try:
            Config().parse("invalid_conf_11.json")
        except exceptions.ArianeProcOSConfigMandatoryFieldsMissingError:
            pass
        except Exception as e:
            self.fail('unexpected exception thrown: ' + str(e))
        else:
            self.fail('no exception thrown')

        try:
            Config().parse("invalid_conf_12.json")
        except exceptions.ArianeProcOSConfigMandatoryFieldsMissingError:
            pass
        except Exception as e:
            self.fail('unexpected exception thrown: ' + str(e))
        else:
            self.fail('no exception thrown')

    def test_ariane_procos_not_in_conf_file(self):
        try:
            Config().parse("invalid_conf_20.json")
        except exceptions.ArianeProcOSConfigMandatorySectionMissingError:
            pass
        except Exception as e:
            self.fail('unexpected exception thrown: ' + str(e))
        else:
            self.fail('no exception thrown')

    def test_ariane_procos_missing_mandatory_fields(self):
        try:
            Config().parse("invalid_conf_21.json")
        except exceptions.ArianeProcOSConfigMandatoryFieldsMissingError:
            pass
        except Exception as e:
            self.fail('unexpected exception thrown: ' + str(e))
        else:
            self.fail('no exception thrown')

    def test_ariane_procos_bad_sleeping_period_value(self):
        try:
            Config().parse("invalid_conf_22.json")
        except exceptions.ArianeProcOSConfigMandatoryFieldsValueError:
            pass
        except Exception as e:
            self.fail('unexpected exception thrown: ' + str(e))
        else:
            self.fail('no exception thrown')