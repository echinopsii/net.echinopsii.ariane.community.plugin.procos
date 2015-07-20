# Ariane ProcOS plugin
# ProcOS exceptions
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
from ariane_clip3.exceptions import ArianeError

__author__ = 'mffrench'


class ArianeProcOSError(ArianeError):
    def __repr__(self):
        return "Unspecified Ariane ProcOS Error occurred"


class ArianeProcOSConfigFileError(ArianeProcOSError):
    def __repr__(self):
        return self.args[0] + " is not a file !"


class ArianeProcOSConfigMandatorySectionMissingError(ArianeProcOSError):
    def __repr__(self):
        return self.args[0] + " is not defined in Ariane ProcOS config file !"


class ArianeProcOSConfigMandatoryFieldsMissingError(ArianeProcOSError):
    def __repr__(self):
        return '['.join(self.args[0]) + "] (is | are) not defined in Ariane ProcOS config file !"


class ArianeProcOSConfigMandatoryFieldsValueError(ArianeProcOSError):
    def __repr__(self):
        return self.args[0] + " value is not correct. Reason: " + self.args[1]