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
            Config().parse("valid_config.ini")
        except Exception as e:
            self.fail('unexpected exception thrown: ' + str(e))
        else:
            pass

    def test_ariane_server_not_in_conf_file(self):
        try:
            Config().parse("invalid_config_10.ini")
        except exceptions.ArianeProcOSConfigMandatorySectionMissingError:
            pass
        except Exception as e:
            self.fail('unexpected exception thrown: ' + str(e))
        else:
            self.fail('no exception thrown')

    def test_ariane_server_missing_mandatory_fields(self):
        try:
            Config().parse("invalid_config_11.ini")
        except exceptions.ArianeProcOSConfigMandatoryFieldsMissingError:
            pass
        except Exception as e:
            self.fail('unexpected exception thrown: ' + str(e))
        else:
            self.fail('no exception thrown')

        try:
            Config().parse("invalid_config_12.ini")
        except exceptions.ArianeProcOSConfigMandatoryFieldsMissingError:
            pass
        except Exception as e:
            self.fail('unexpected exception thrown: ' + str(e))
        else:
            self.fail('no exception thrown')

    def test_ariane_procos_not_in_conf_file(self):
        try:
            Config().parse("invalid_config_20.ini")
        except exceptions.ArianeProcOSConfigMandatorySectionMissingError:
            pass
        except Exception as e:
            self.fail('unexpected exception thrown: ' + str(e))
        else:
            self.fail('no exception thrown')

    def test_ariane_procos_missing_mandatory_fields(self):
        try:
            Config().parse("invalid_config_21.ini")
        except exceptions.ArianeProcOSConfigMandatoryFieldsMissingError:
            pass
        except Exception as e:
            self.fail('unexpected exception thrown: ' + str(e))
        else:
            self.fail('no exception thrown')

    def test_ariane_procos_bad_sleeping_period_value(self):
        try:
            Config().parse("invalid_config_22.ini")
        except exceptions.ArianeProcOSConfigMandatoryFieldsValueError:
            pass
        except Exception as e:
            self.fail('unexpected exception thrown: ' + str(e))
        else:
            self.fail('no exception thrown')