##############################################################################
#
# Copyright (c) 2012-2023 Federico Di Gregorio and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
#############################################################################

import os


DEFAULT_DSN = ('user=zpsycopgdatest '
               'password=zpsycopgdatest '
               'dbname=zpsycopgdatest')
DSN = os.environ.get('ZPSYCOPGDA_TEST_DSN', DEFAULT_DSN)
NO_DB_MSG = 'Please see the documentation for running functional tests.'
