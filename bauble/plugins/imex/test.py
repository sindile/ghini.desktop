# -*- coding: utf-8 -*-
#
# test imex plugins
#
import csv
import logging
import os
import shutil
import tempfile

import bauble.db as db
from bauble.plugins.plants import Family
import bauble.plugins.garden.test as garden_test
import bauble.plugins.plants.test as plants_test
from bauble.plugins.imex.csv_ import CSVImporter, CSVExporter, QUOTE_CHAR, \
    QUOTE_STYLE, UnicodeReader
from bauble.test import BaubleTestCase
from bauble.utils.log import debug


# TODO: test that when we export data we get what we expect
# TODO: test that importing and then exporting gives the same data
# TODO: test that exporting and then importing gives the same data
# TODO: test XMLExporter

# TODO: needs tests for UnicodeWriter and UnicodeReader, i'm pretty
# sure they are buggy, see the python csv module for examples of how
# they do a non-dict unicode reader/writer

csv_test_data = ({})


family_data = [{'id': 1, 'family': u'family1', 'notes': u'Gal\xe1pagos',
                'qualifier': None},
               {'id': 2, 'family': u'family2'},
               {'id': 3, 'family': u'family3', 'notes': u''},
               ]


class ImexTestCase(BaubleTestCase):

    def __init__(self, *args):
        super(ImexTestCase, self).__init__(*args)

    def setUp(self):
        super(ImexTestCase, self).setUp()
        plants_test.setUp_data()
        garden_test.setUp_data()


class CSVTests(ImexTestCase):


    def setUp(self):
        self.path = tempfile.mkdtemp()
        super(CSVTests, self).setUp()

    def tearDown(self):
        shutil.rmtree(self.path)
        super(CSVTests, self).tearDown()


    def _do_import(self, data):
        """
        Write data to family.txt and import into Family
        """
        filename = os.path.join(self.path, 'family.txt')
        f = open(filename, 'wb')
        format = {'delimiter': ',', 'quoting': QUOTE_STYLE,
                  'quotechar': QUOTE_CHAR}

        fields = data[0].keys()
        f.write('%s\n' % ','.join(fields))
        writer = csv.DictWriter(f, fields, **format)
        writer.writerows(data)
        f.close()

        #debug(open(filename).read())

        importer = CSVImporter()
        importer.start([filename], force=True)


    def test_import_use_default(self):
        """
        Test that if we import from a csv file that doesn't include a
        column and that column has a default value then that default
        value is executed.
        """
        self._do_import(family_data)
        family = self.session.query(Family).filter_by(id=1).one()
        self.assert_(family.qualifier == '')


    def test_import_no_default(self):
        """
        Test that if we import from a csv file that doesn't include a
        column and that column does not have a default value then that
        value is set to None
        """
        self._do_import(family_data)
        family = self.session.query(Family).filter_by(id=2).one()
        self.assert_(family.notes is None)


    def test_import_empty_is_none(self):
        """
        Test that if we import from a csv file that includes a column
        but that column is empty and doesn't have a default values
        then the column is set to None
        """
        self._do_import(family_data)
        family = self.session.query(Family).filter_by(id=2).one()
        self.assert_(family.notes is None)


    def test_import_empty_uses_default(self):
        """
        Test that if we import from a csv file that includes a column
        but that column is empty and has a default then the default is
        executed.
        """
        self._do_import(family_data)
        family = self.session.query(Family).filter_by(id=3).one()
        self.assert_(family.qualifier == '')


    def test_sequences(self):
        """
        Test that the sequences are set correctly after an import,
        bauble.util.test already has a method to test
        utils.reset_sequence but this test makes sure that its works
        correctly after an import
        """
        # turn off logger
        logging.getLogger('bauble.info').setLevel(logging.ERROR)
        self._do_import(family_data)
        highest_id = len(family_data)
        currval = None
        conn = db.engine.contextual_connect()
        if db.engine.name == 'postgres':
            stmt = "SELECT currval('family_id_seq');"
            currval = conn.execute(stmt).fetchone()[0]
        elif db.engine.name == 'sqlite':
            # max(id) isn't really safe in production use but is ok for a test
            stmt = "SELECT max(id) from family;"
            nextval = conn.execute(stmt).fetchone()[0] + 1
        else:
            raise "no test for engine type: %s" % db.engine.name

        #debug(list(conn.execute("SELECT * FROM family").fetchall()))
        maxid = conn.execute("SELECT max(id) FROM family").fetchone()[0]
        assert nextval > highest_id, \
               "bad sequence: highest_id(%s) > nexval(%s) -- %s" % \
               (highest_id, nextval, maxid)


    def test_import_unicode(self):
        """
        Test importing a unicode string.
        """
        self._do_import(family_data)
        family = self.session.query(Family).filter_by(id=1).one()
        self.assert_(family.notes == family_data[0]['notes'])


    def test_import_no_inherit(self):
        """
        That that when importing a row that has a None value in a
        column doesn't inherit the value from the previous row.
        """
        self._do_import(family_data)
        query = self.session.query(Family)
        self.assert_(query[1].notes != query[0].notes)


    def test_export_none_is_empty(self):
        """
        Test the exporting a None column exports a ''
        """
        family = Family(family=u'family')
        from tempfile import mkdtemp
        temp_path = mkdtemp()
        exporter = CSVExporter()
        exporter.start(temp_path)
        f = open(os.path.join(temp_path, 'family.txt'))
        reader = csv.DictReader(f, dialect=csv.excel)
        row = reader.next()
        self.assert_(row['notes'] == '')




# class CSVTests(ImexTestCase):


#     def test_sequences(self):
#         """
#         Test that the sequences are set correctly after an import,
#         bauble.util.test already has a method to test
#         utils.reset_sequence but this test makes sure that its works
#         correctly after an import

#         This test requires the PlantPlugin
#         """
#         # turn off logger
#         logging.getLogger('bauble.info').setLevel(logging.ERROR)
#         # import the family data
#         from bauble.plugins.plants.family import Family
#         from bauble.plugins.plants import PlantsPlugin
#         filename = os.path.join('bauble', 'plugins', 'plants', 'default',
#                                 'family.txt')
#         importer = CSVImporter()
#         importer.start([filename], force=True)
#         # the highest id number in the family file is assumed to be
#         # num(lines)-1 since the id numbers are sequential and
#         # subtract for the file header
#         highest_id = len(open(filename).readlines())-1
#         currval = None
#         conn = db.engine.contextual_connect()
#         if db.engine.name == 'postgres':
#             stmt = "SELECT currval('family_id_seq');"
#             currval = conn.execute(stmt).fetchone()[0]
#         elif db.engine.name == 'sqlite':
#             # max(id) isn't really safe in production use but is ok for a test
#             stmt = "SELECT max(id) from family;"
#             nextval = conn.execute(stmt).fetchone()[0] + 1
#         else:
#             raise "no test for engine type: %s" % db.engine.name

#         #debug(list(conn.execute("SELECT * FROM family").fetchall()))
#         maxid = conn.execute("SELECT max(id) FROM family").fetchone()[0]
#         assert nextval > highest_id, \
#                "bad sequence: highest_id(%s) > nexval(%s) -- %s" % \
#                (highest_id, nextval, maxid)


#     def test_import(self):
#         # TODO: create a test to check that we aren't using an insert
#         # statement for import that assumes a column value from the previous
#         # insert values, could probably create an insert statement from a
#         # row in the test data and then create an insert statement from some
#         # other dummy data that has different columns from the test data and
#         # see if any of the columns from the second insert statement has values
#         # from the first statement

#         # TODO: this test doesn't really test yet that any of the data was
#         # correctly imported or exported, only that export and importing
#         # run successfuly

#         # 1. write the test data to a temporary file or files
#         # 2. import the data and make sure the objects match field for field

#         # the exporters and importers show logging information, turn it off
#         import bauble.utils as utils
#         logging.getLogger('bauble.info').setLevel(logging.ERROR)
#         import tempfile
#         tempdir = tempfile.mkdtemp()

#         # export all the testdata
#         exporter = CSVExporter()
#         exporter.start(tempdir)

#         # import all the files in the temp directory
#         filenames = os.listdir(tempdir)
#         importer = CSVImporter()
#         # import twice to check for regression Launchpad #???
#         importer.start([os.path.join(tempdir, name) for name in filenames],
#                        force=True)
#         importer.start([os.path.join(tempdir, name) for name in filenames],
#                        force=True)
# #        utils.log.echo(False)

#     def test_unicode(self):
#         from bauble.plugins.plants.geography import Geography
#         geography_table = Geography.__table__
#         # u'Gal\xe1pagos' is the unencoded unicode object,
#         # calling u.encode('utf-8') will convert the \xe1 to the a
#         # with an accent
#         data = {'name': u'Gal\xe1pagos'}
#         geography_table.insert().execute(data)
#         query = self.session.query(Geography)
#         row = query[0]
# ##        print str(row)
# ##        print data['name']
#         assert row.name == data['name']


#     def test_export(self):
#         # 1. export the test data
#         # 2. read the exported data into memory and make sure its matches
#         # the test export string
#         pass




