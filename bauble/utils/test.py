#
# test.py
#
# Description: test for bauble.utils

import unittest

from sqlalchemy import *

import bauble
import bauble.utils as utils
from bauble.utils.log import debug
from bauble.test import BaubleTestCase

class UtilsGTKTests(unittest.TestCase):

    def test_search_tree_model(self):
        import gtk
        model = gtk.TreeStore(str)

        # the rows that should be found
        to_find = []

        row = model.append(None, ['1'])
        model.append(row, ['1.1'])
        to_find.append(model.append(row, ['something']))
        model.append(row, ['1.3'])

        row = model.append(None, ['2'])
        to_find.append(model.append(row, ['something']))
        model.append(row, ['2.1'])

        to_find.append(model.append(None, ['something']))

        root = model.get_iter_root()
        results = utils.search_tree_model(model[root], 'something')
        self.assert_(sorted([model.get_path(r) for r in results]),
                     sorted(to_find))



class UtilsTests(unittest.TestCase):

#     def setUp(self):
#         super(UtilsTests, self).setUp()
#         pass

##     def tearDown(self):
##         pass

    def test_xml_safe(self):
        # TODO: need to test passing object here
        assert utils.xml_safe('test string') == 'test string'
        assert utils.xml_safe(u'test string') == u'test string'
        assert utils.xml_safe(u'test< string') == u'test&lt; string'
        assert utils.xml_safe('test< string') == 'test&lt; string'

    def test_datetime_to_str(self):
        from datetime import datetime
        dt = datetime(2008, 12, 1)
        s = utils.date_to_str(dt, 'yyyy.m.d')
        assert s == '2008.12.1', s
        s = utils.date_to_str(dt, 'yyyy.mm.d')
        assert s == '2008.12.1', s
        s = utils.date_to_str(dt, 'yyyy.m.dd')
        assert s == '2008.12.01', s
        s = utils.date_to_str(dt, 'yyyy.mm.dd')
        assert s == '2008.12.01', s

        dt = datetime(2008, 12, 12)
        s = utils.date_to_str(dt, 'yyyy.m.d')
        assert s == '2008.12.12', s
        s = utils.date_to_str(dt, 'yyyy.mm.d')
        assert s == '2008.12.12', s
        s = utils.date_to_str(dt, 'yyyy.m.dd')
        assert s == '2008.12.12', s
        s = utils.date_to_str(dt, 'yyyy.mm.dd')
        assert s == '2008.12.12', s

        dt = datetime(2008, 1, 1)
        s = utils.date_to_str(dt, 'yyyy.m.d')
        assert s == '2008.1.1', s
        s = utils.date_to_str(dt, 'yyyy.mm.d')
        assert s == '2008.01.1', s
        s = utils.date_to_str(dt, 'yyyy.m.dd')
        assert s == '2008.1.01', s
        s = utils.date_to_str(dt, 'yyyy.mm.dd')
        assert s == '2008.01.01', s

        dt = datetime(2008, 1, 12)
        s = utils.date_to_str(dt, 'yyyy.m.d')
        assert s == '2008.1.12', s
        s = utils.date_to_str(dt, 'yyyy.mm.d')
        assert s == '2008.01.12', s
        s = utils.date_to_str(dt, 'yyyy.m.dd')
        assert s == '2008.1.12', s
        s = utils.date_to_str(dt, 'yyyy.mm.dd')
        assert s == '2008.01.12', s



class ResetSequenceTests(BaubleTestCase):


    def setUp(self):
        super(ResetSequenceTests, self).setUp()
        self.metadata = MetaData()
        self.metadata.bind  = bauble.engine
        self.currval_stmt = None

        # self.currval_stmt should return 2
        if bauble.engine.name == 'postgres':
            self.currval_stmt = "SELECT currval(%s)"
        elif bauble.engine.name == 'sqlite':
            # assume sqlite just works
            self.currval_stmt = 'select 2'
        self.conn = bauble.engine.contextual_connect()


    def tearDown(self):
        super(ResetSequenceTests, self).tearDown()
        self.metadata.drop_all()
        self.conn.close()


    def test_no_col_sequence(self):
        """
        test utils.reset_sequence on a column without a Sequence()
        """
        # test that a column without a sequence works
        self.table = Table('test_reset_sequence', self.metadata,
                           Column('id', Integer, primary_key=True))
        self.metadata.create_all()
        self.insert = self.table.insert().compile()
        self.conn.execute(self.insert, values=[{'id': 1}])
        utils.reset_sequence(self.table.c.id)
        currval = self.conn.execute(self.currval_stmt).fetchone()[0]
        self.assert_(currval > 1)


    def test_with_col_sequence(self):
        """
        test utils.reset_sequence on a column that has an Sequence()
        """
        self.table = Table('test_reset_sequence', self.metadata,
                           Column('id', Integer,
                                  Sequence('test_reset_sequence_id'),
                                  primary_key=True))
        self.metadata.create_all()
        self.insert = self.table.insert().compile()
        self.conn.execute(self.insert, values=[{'id': 1}])
        utils.reset_sequence(self.table.c.id)
        currval = self.conn.execute(self.currval_stmt).fetchone()[0]
        self.assert_(currval > 1)


