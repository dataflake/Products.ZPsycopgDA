# ZPsycopgDA/DA.py - ZPsycopgDA Zope product: Database Connection
#
# Copyright (C) 2004-2010 Federico Di Gregorio  <fog@debian.org>
#
# psycopg2 is free software: you can redistribute it and/or modify it
# under the terms of the GNU Lesser General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# psycopg2 is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public
# License for more details.

# Import modules needed by _psycopg to allow tools like py2exe to do
# their work without bothering about the module dependencies.


import re
import time
from operator import itemgetter

import psycopg2
import psycopg2.extensions
from psycopg2 import DATETIME
from psycopg2 import NUMBER
from psycopg2 import ROWID
from psycopg2 import STRING
from psycopg2.extensions import BOOLEAN
from psycopg2.extensions import DATE
from psycopg2.extensions import FLOAT
from psycopg2.extensions import INTEGER
from psycopg2.extensions import TIME
from psycopg2.extensions import new_type

import Acquisition
from AccessControl.class_init import InitializeClass
from AccessControl.Permissions import change_database_methods
from AccessControl.Permissions import use_database_methods
from AccessControl.Permissions import view_management_screens
from AccessControl.SecurityInfo import ClassSecurityInfo
from App.special_dtml import DTMLFile
from DateTime import DateTime
from ExtensionClass import Base
from Shared.DC.ZRDB.Connection import Connection as ConnectionBase

from .db import DB


# import psycopg and functions/singletons needed for date/time conversions


DEFAULT_TILEVEL = psycopg2.extensions.ISOLATION_LEVEL_REPEATABLE_READ

# add a new connection to a folder

manage_addZPsycopgConnectionForm = DTMLFile('dtml/add', globals())


def manage_addZPsycopgConnection(self, id, title, connection_string,
                                 zdatetime=None, tilevel=DEFAULT_TILEVEL,
                                 encoding='', check=None, REQUEST=None):
    """Add a DB connection to a folder."""
    self._setObject(id, Connection(id, title, connection_string,
                                   zdatetime, check, tilevel, encoding))
    if REQUEST is not None:
        return self.manage_main(self, REQUEST)


# the connection object

class Connection(ConnectionBase):
    """ZPsycopg Connection."""
    _isAnSQLConnection = 1

    database_type = 'Psycopg2'
    meta_type = 'Z Psycopg 2 Database Connection'
    security = ClassSecurityInfo()
    zmi_icon = 'fas fa-database'
    info = None

    security.declareProtected(view_management_screens,  # NOQA: D001
                              'manage_tables')
    manage_tables = DTMLFile('dtml/tables', globals())

    security.declareProtected(view_management_screens,  # NOQA: D001
                              'manage_browse')
    manage_browse = DTMLFile('dtml/browse', globals())

    security.declareProtected(change_database_methods,  # NOQA: D001
                              'manage_properties')
    manage_properties = DTMLFile('dtml/edit', globals())
    manage_properties._setName('manage_main')
    manage_main = manage_properties

    manage_options = (ConnectionBase.manage_options[1:] +
                      ({'label': 'Browse', 'action': 'manage_browse'},))

    def __init__(self, id, title, connection_string,
                 zdatetime, check=None, tilevel=DEFAULT_TILEVEL,
                 encoding='UTF-8'):
        self.id = str(id)
        self.edit(title, connection_string, zdatetime,
                  check=check, tilevel=tilevel, encoding=encoding)

    @security.protected(use_database_methods)
    def factory(self):
        return DB

    # connection parameter editing

    @security.protected(change_database_methods)
    def edit(self, title, connection_string,
             zdatetime, check=None, tilevel=DEFAULT_TILEVEL, encoding='UTF-8'):
        self.title = title
        self.connection_string = connection_string
        self.zdatetime = zdatetime
        self.tilevel = int(tilevel)
        self.encoding = encoding

        if check:
            self.connect(self.connection_string)

    @security.protected(change_database_methods)
    def manage_edit(self, title, connection_string,
                    zdatetime=None, check=None, tilevel=DEFAULT_TILEVEL,
                    encoding='UTF-8', REQUEST=None):
        """Edit the DB connection."""
        self.edit(title, connection_string, zdatetime,
                  check=check, tilevel=tilevel, encoding=encoding)
        if REQUEST is not None:
            msg = "Connection edited."
            return self.manage_main(self, REQUEST, manage_tabs_message=msg)

    @security.protected(use_database_methods)
    def connect(self, s):
        try:
            self._v_database_connection.close()
        except Exception:
            pass

        # check psycopg version and raise exception if does not match
        check_psycopg_version(psycopg2.__version__)

        self._v_connected = ''
        dbf = self.factory()

        # TODO: let the psycopg exception propagate, or not?
        self._v_database_connection = dbf(
            self.connection_string, self.tilevel,
            self.get_type_casts(), self.encoding)
        self._v_database_connection.open()
        self._v_connected = DateTime()

        return self

    @security.protected(use_database_methods)
    def get_type_casts(self):
        # note that in both cases order *is* important
        if self.zdatetime:
            return ZDATETIME, ZDATE, ZTIME
        else:
            return DATETIME, DATE, TIME

    @security.protected(view_management_screens)
    def table_info(self):
        return self._v_database_connection.table_info()

    def __getitem__(self, name):
        if name == 'tableNamed':
            if not hasattr(self, '_v_tables'):
                self.tpValues()
            return self._v_tables.__of__(self)
        raise KeyError(name)

    @security.protected(view_management_screens)
    def tpValues(self):
        res = []
        conn = self._v_database_connection
        for d in sorted(conn.tables(rdb=0), key=itemgetter('TABLE_NAME')):
            try:
                name = d['TABLE_NAME']
                b = TableBrowser()
                b.__name__ = name
                b._d = d
                b._c = conn
                b.icon = table_icons.get(d['TABLE_TYPE'], 'text')
                res.append(b)
            except Exception:
                pass
        return res


InitializeClass(Connection)


def check_psycopg_version(version):
    """
    Check that the psycopg version used is compatible with the zope adpter.
    """
    try:
        m = re.match(r'\d+\.\d+(\.\d+)?', version.split(' ')[0])
        tver = tuple(map(int, m.group().split('.')))
    except Exception:
        raise ImportError("failed to parse psycopg version %s" % version)

    if tver < (2, 4):
        raise ImportError("psycopg version %s is too old" % version)

    if tver in ((2, 4, 2), (2, 4, 3)):
        raise ImportError("psycopg version %s is known to be buggy" % version)


# database connection registration data

classes = (Connection,)

meta_types = ({'name': 'Z Psycopg 2 Database Connection',
               'action': 'manage_addZPsycopgConnectionForm'},)

folder_methods = {
    'manage_addZPsycopgConnection': manage_addZPsycopgConnection,
    'manage_addZPsycopgConnectionForm': manage_addZPsycopgConnectionForm}

__ac_permissions__ = (
    ('Add Z Psycopg Database Connections',
     ('manage_addZPsycopgConnectionForm', 'manage_addZPsycopgConnection')),)


# zope-specific psycopg typecasters

# convert an ISO timestamp string from postgres to a Zope DateTime object
def _cast_DateTime(iso, curs):
    if iso:
        if iso in ['-infinity', 'infinity']:
            return iso
        else:
            return DateTime(iso)


# convert an ISO date string from postgres to a Zope DateTime object
def _cast_Date(iso, curs):
    if iso:
        if iso in ['-infinity', 'infinity']:
            return iso
        else:
            return DateTime(iso)


# Convert a time string from postgres to a Zope DateTime object.
# NOTE: we set the day as today before feeding to DateTime so
# that it has the same DST settings.
def _cast_Time(iso, curs):
    if iso:
        if iso in ['-infinity', 'infinity']:
            return iso
        else:
            return DateTime(
                time.strftime('%Y-%m-%d %H:%M:%S',
                              time.localtime(time.time())[:3] +
                              time.strptime(iso[:8], "%H:%M:%S")[3:]))


# NOTE: we don't cast intervals anymore because they are passed
# untouched to Zope.
def _cast_Interval(iso, curs):
    return iso


ZDATETIME = new_type((1184, 1114), "ZDATETIME", _cast_DateTime)
ZINTERVAL = new_type((1186,), "ZINTERVAL", _cast_Interval)
ZDATE = new_type((1082,), "ZDATE", _cast_Date)
ZTIME = new_type((1083,), "ZTIME", _cast_Time)


# table browsing helpers

class Browser(Base):
    def __getattr__(self, name):
        try:
            return self._d[name]
        except KeyError:
            raise AttributeError(name)


class values:
    def len(self):
        return 1

    def __getitem__(self, i):
        try:
            return self._d[i]
        except AttributeError:
            pass
        self._d = self._f()
        return self._d[i]


class TableBrowser(Browser, Acquisition.Implicit):
    icon = 'what'
    Description = check = ''
    info = DTMLFile('dtml/table_info', globals())
    __allow_access_to_unprotected_subobjects__ = 1

    def tpValues(self):
        v = values()
        v._f = self.tpValues_
        return v

    def tpValues_(self):
        r = []
        tname = self.__name__
        for d in sorted(self._c.columns(tname), key=itemgetter('name')):
            b = ColumnBrowser()
            b._d = d
            try:
                b.icon = field_icons[d['type'].name]
            except Exception:
                pass
            b.TABLE_NAME = tname
            r.append(b)
        return r

    def tpId(self):
        return self._d['TABLE_NAME']

    def tpURL(self):
        return "Table/%s" % self._d['TABLE_NAME']

    def Name(self):
        return self._d['TABLE_NAME']

    def Type(self):
        return self._d['TABLE_TYPE']

    @staticmethod
    def vartype(inVar):
        "Get a type name for a variable suitable for use with dtml-sqlvar"
        outVar = type(inVar)
        if outVar == 'str':
            outVar = 'string'
        return outVar

    def manage_buildInput(self, id, source, default, REQUEST=None):
        "Create a database method for an input form"
        args = []
        values = []
        names = []
        columns = self._columns
        for i in range(len(source)):
            s = source[i]
            if s == 'Null':
                continue
            c = columns[i]
            d = default[i]
            t = c['Type']
            n = c['Name']
            names.append(n)
            if s == 'Argument':
                values.append("<dtml-sqlvar %s type=%s>'" %
                              (n, self.vartype(t)))
                a = '%s%s' % (n, self.vartype(t).title())
                if d:
                    a = "%s=%s" % (a, d)
                args.append(a)
            elif s == 'Property':
                values.append("<dtml-sqlvar %s type=%s>'" %
                              (n, self.vartype(t)))
            else:
                if isinstance(t, str):
                    if d.find("\'") >= 0:
                        d = "''".join(d.split("\'"))
                    values.append("'%s'" % d)
                elif d:
                    values.append(str(d))
                else:
                    raise ValueError(
                        'no default was given for <em>%s</em>' % n)


class ColumnBrowser(Browser):
    icon = 'field'

    def check(self):
        return ('\t<input type=checkbox name="%s.%s">' %
                (self.TABLE_NAME, self._d['name']))

    def tpId(self):
        return self._d['name']

    def tpURL(self):
        return "Column/%s" % self._d['name']

    def Name(self):
        return self._d['name']

    def Description(self):
        d = self._d
        d['type_name'] = d['type'].name
        if d['scale']:
            return " %(type_name)s(%(precision)s,%(scale)s) %(null)s" % d
        else:
            return " %(type_name)s(%(precision)s) %(null)s" % d


table_icons = {
    'TABLE': 'table',
    'VIEW': 'db_view',
    'SYSTEM_TABLE': 'stable',
}

field_icons = {
    NUMBER.name: 'int',
    STRING.name: 'text',
    DATETIME.name: 'date',
    INTEGER.name: 'int',
    FLOAT.name: 'float',
    BOOLEAN.name: 'bin',
    ROWID.name: 'int'
}
