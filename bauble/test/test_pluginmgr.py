#
# test_pluginmgr.py
#
import os
import sys
import unittest

from sqlalchemy import *

import bauble
from bauble.view import SearchParser
from bauble.utils.pyparsing import *
from bauble.view import SearchView, MapperSearch, ResultSet
from bauble.utils.log import debug
from bauble.test import BaubleTestCase, uri
import bauble.pluginmgr as pluginmgr
from bauble.pluginmgr import RegistryEmptyError, Registry, RegistryEntry

# TODO: need tests for
# 1. what happens when a plugin is in the plugins dict but not the registry
# 2. what happens when a plugin has an error on init()
# 3. what happens when a plugin has an error on install()
# 4. what happens when a plugin is in the registry but not in plugins

class A(pluginmgr.Plugin):
    initialized = False
    installed = False
    @classmethod
    def init(cls):
        cls.initialized = True
    @classmethod
    def install(cls):
        cls.installed = True

class B(pluginmgr.Plugin):
    depends = ['A']
    initialized = False
    installed = False
    @classmethod
    def init(cls):
        assert A.initialized and not C.initialized, \
               '%s, %s' % (A.initialized, C.instalialized)
        cls.initialized = True
    @classmethod
    def install(cls):
        assert A.installed and not C.installed, \
               '%s, %s' % (A.installed, C.installed)
        cls.installed = True

class C(pluginmgr.Plugin):
    depends = ['B']
    initialized = False
    installed = False
    @classmethod
    def init(cls):
        assert A.initialized and B.initialized
        cls.initialized = True
    @classmethod
    def install(cls):
        assert A.installed and B.installed
        cls.installed = True

class PluginMgrTests(unittest.TestCase):

    def setUp(self):
        A.initialized = A.installed = False
        B.initialized = B.installed = False
        C.initialized = C.installed = False

    def tearDown(self):
        A.initialized = A.installed = False
        B.initialized = B.installed = False
        C.initialized = C.installed = False

    def test_init(self):
        """
        Test bauble.pluginmgr.init()
        """
        bauble.pluginmgr.plugins[C.__name__] = C
        bauble.pluginmgr.plugins[B.__name__] = B
        bauble.pluginmgr.plugins[A.__name__] = A
        bauble.open_database(uri, verify=False)
        bauble.create_database(False)
        bauble.pluginmgr.init()
        self.assert_(A.initialized and B.initialized and C.initialized)

    def test_install(self):
        """
        Test bauble.pluginmgr.init()
        """
        bauble.pluginmgr.plugins[C.__name__] = C
        bauble.pluginmgr.plugins[B.__name__] = B
        bauble.pluginmgr.plugins[A.__name__] = A
        bauble.open_database(uri, verify=False)
        bauble.create_database(False)
        #bauble.pluginmgr.install((A, B, C), force=True)
        self.assert_(A.installed and B.installed and C.installed)

class RegistryTests(BaubleTestCase):

    def test_registry(self):
        """
        Test bauble.pluginmgr.Registry
        """
        # should always be True once pluginmgr.install() is called
        self.assert_(Registry.exists)

        # test that adding works
        registry = Registry(self.session)
        registry.add(RegistryEntry(name='TestPlugin', version='0.0'))
        self.assert_('TestPlugin' in registry)

        # test that removing works
        registry.remove('TestPlugin')
        self.assert_('TestPlugin' not in registry)



