#
# csv import/export
#
# Description: have to name this module csv_ in order to avoid conflict
# with the system csv module
#

import os
import csv
import traceback

import gtk
import gobject
from sqlalchemy import *

import bauble
import bauble.db as db
from bauble.error import BaubleError
import bauble.utils as utils
import bauble.pluginmgr as pluginmgr
import bauble.task
from bauble.utils.log import log, debug, error

from sqlalchemy.sql.util import sort_tables
# TODO: i've also had a problem with bad insert statements, e.g. importing a
# geography table after creating a new database and it doesn't use the
# 'name' column in the insert so there is an error, if  you then import the
# same table immediately after then everything seems to work fine

# TODO: should check that if we're dropping a table because of a
# dependency that we expect that data to be imported in this same
# task, or at least let the user know that the table is empty

# TODO: don't ask if we want to drop empty tables
# https://bugs.launchpad.net/bauble/+bug/103923

# TODO: allow the user set the unicode encoding on import, exports should
# always us UTF-8, import, exports should always use UTF-8, need to figure
# out how to extend the file open dialog,
# http://evanjones.ca/python-utf8.html
# import codecs
# fileObj = codecs.open( "someFile", "r", "utf-8" )
# u = fileObj.read() # Returns a Unicode string from the UTF-8 bytes in
# the file

# TODO: what happens when you export from one database type and try
# and import into a different database, e.g. postgres->sqlite

QUOTE_STYLE = csv.QUOTE_MINIMAL
QUOTE_CHAR = '"'

def pb_set_fraction(fraction):
    """
    provides a safe way to handle the progress bar if the gui isn't started,
    we use this in the tests where there is not gui
    """
    if bauble.gui is not None and bauble.gui.progressbar is not None:
        bauble.gui.progressbar.set_fraction(fraction)



class UnicodeReader(object):

    def __init__(self, f, dialect=csv.excel, encoding="utf-8", **kwds):
        self.reader = csv.DictReader(f, dialect=dialect, **kwds)
        self.encoding = encoding


    def next(self):
        row = self.reader.next()
        t = {}
        for k, v in row.iteritems():
            if v == '':
                t[k] = None
            else:
                t[k] = utils.to_unicode(v, self.encoding)

        return t


    def __iter__(self):
        return self


# TODO: UnicodeWriter needs to be more thoroughly needs to be more
# tested, i came across a small problem once when createing a tempory
# geography table from _topsort_file and it exported the numbers in
# some strange format
class UnicodeWriter(object):

    def __init__(self, f, dialect=csv.excel, encoding="utf-8", **kwds):
        self.writer = csv.writer(f, dialect=dialect, **kwds)
        self.encoding = encoding


    def writerow(self, row):
        if isinstance(row, dict):
            row = row.values()
        t = []
        for s in row:
            if s == None:
                t.append(None)
            else:
                t.append(utils.to_unicode(s, self.encoding))
        self.writer.writerow(t)


    def writerows(self, rows):
        for row in rows:
            self.writerow(row)


class Importer(object):

    def start(self, **kwargs):
        '''
        start the import process, this is a non blocking method, queue the
        process as a bauble task
        '''
        return bauble.task.queue(self.run, **kwargs)


    def run(self, **kwargs):
        '''
        where all the action happens
        '''
        raise NotImplementedError


class CSVImporter(Importer):

    """
    The CSVImporter imports comma seperated value files into a Bauble
    database.

    The CSVImporter imports the rows of the CSV file in
    chunks rather than one row at a time.  The non-server side column
    defaults are determined before the INSERT statement is generated
    instead of getting new defaults for each row.  This shouldn't be a
    problem but it also means that your column default should change
    depending on the value of previously inserted rows.
    """
    def __init__(self):
        super(CSVImporter, self).__init__()
        self.__error = False  # flag to indicate error on import
        self.__cancel = False # flag to cancel importing
        self.__pause = False  # flag to pause importing
        self.__error_exc = False


    def start(self, filenames=None, metadata=None, force=False):
        '''
        start the import process, this is a non blocking method queue the
        process as a bauble task
        '''
        if metadata is None:
            metadata = db.metadata  # use the default metadata

        if filenames is None:
            filenames = self._get_filenames()
        if filenames is None:
            return

        bauble.task.queue(self.run(filenames, metadata, force))


    @staticmethod
    def _toposort_file(filename, key_pairs):
        """
        filename: the csv file to sort

        key_pairs: tuples of the form (parent, child) where for each
        line in the file the line[parent] needs to be sorted before
        any of the line[child].  parent is usually the name of the
        foreign_key column and child is usually the column that the
        foreign key points to, e.g ('parent_id', 'id')
        """
        f = open(filename, 'rb')
        reader = UnicodeReader(f, quotechar=QUOTE_CHAR,
                               quoting=QUOTE_STYLE)

        # create a dictionary of the lines mapped to the child field
        bychild = {}
        for line in reader:
            for parent, child in key_pairs:
                bychild[line[child]] = line
        f.close()
        fields = reader.reader.fieldnames
        del reader

        # create pairs from the values in the lines where pair[0]
        # should come before pair[1] when the lines are sorted
        pairs = []
        for line in bychild.values():
            for parent, child in key_pairs:
                if line[parent] and line[child]:
                    pairs.append((line[parent], line[child]))

        # sort the keys and flatten the lines back into a list
        sorted_keys = utils.topological_sort(bychild.keys(), pairs)
        sorted_lines = []
        for key in sorted_keys:
            sorted_lines.append(bychild[key])

        # write a temporary file of the sorted lines
        import tempfile
        tmppath = tempfile.mkdtemp()
        head, tail = os.path.split(filename)
        filename = os.path.join(tmppath, tail)
        tmpfile = open(filename, 'wb')
        tmpfile.write('%s\n' % ','.join(fields))
        #writer = UnicodeWriter(tmpfile, fields, quotechar=QUOTE_CHAR,
        writer = csv.DictWriter(tmpfile, fields, quotechar=QUOTE_CHAR,
                                quoting=QUOTE_STYLE)
        writer.writerows(sorted_lines)
        tmpfile.flush()
        tmpfile.close()
        del writer
        return filename


    def run(self, filenames, metadata, force=False):
        '''
        A generator method for importing filenames into the database.
        This method periodically yields control so that the GUI can
        update.

        @params filenames:
        @param metadata:
        @param force: default=False
        '''
        transaction = None
        connection = None
        self.__error_exc = BaubleError(_('Unknown Error.'))

        try:
            # user a contextual connect in case whoever called this
            # method called it inside a transaction then we can pick
            # up the parent connection and the transaction
            connection = metadata.bind.connect()
            transaction = connection.begin()
        except Exception, e:
            msg = _('Error connecting to database.\n\n%s') % \
                  utils.xml_safe_utf8(e)
            utils.message_dialog(msg, gtk.MESSAGE_ERROR)
            return

        # create a mapping of table names to filenames
        filename_dict = {}
        for f in filenames:
            path, base = os.path.split(f)
            table_name, ext = os.path.splitext(base)
            if table_name in filename_dict:
                safe = utils.xml_safe_utf8
                values = dict(table_name=safe(table_name),
                              file_name=safe(filename_dict[table_name]),
                              file_name2=safe(f))
                msg = _('More than one file given to import into table '\
                        '<b>%(table_name)s</b>: %(file_name)s, '\
                        '(file_name2)s') % values
                utils.message_dialog(msg, gtk.MESSAGE_ERROR)
                return
            filename_dict[table_name] = f


        # resolve filenames to table names and return them in sorted order
        sorted_tables = []
        for table in metadata.sorted_tables:
            try:
                sorted_tables.insert(0, (table, filename_dict.pop(table.name)))
            except KeyError, e:
                # table.name not in list of filenames
                pass

        if len(filename_dict) > 0:
            msg = _('Could not match all filenames to table names.\n\n%s') \
                  % filename_dict
            utils.message_dialog(msg, gtk.MESSAGE_ERROR)
            return

        total_lines = 0
        filesizes = {}
        for filename in filenames:
            #get the total number of lines for all the files
            nlines = len(open(filename).readlines())
            filesizes[filename] = nlines
            total_lines += nlines

        created_tables = []
        def create_table(table):
            table.create(bind=connection)
            if table.name not in created_tables:
                created_tables.append(table.name)
#             created_tables.extend([n for n in names \
#                                    if n not in created_tables])

        steps_so_far = 0
        cleaned = None
        insert = None
        depends = set() # the type will be changed to a [] later
        try:
            # get all the dependencies
            for table, filename in sorted_tables:
                #debug(table.name)
                d = utils.find_dependent_tables(table)
                depends.update(list(d))

            # drop all of the dependencies together
            if len(depends) > 0:
                if not force:
                    msg = _('In order to import the files the following '\
                                'tables will need to be dropped:' \
                                '\n\n<b>%s</b>\n\n' \
                                'Would you like to continue?' \
                                % ', '.join(sorted([d.name for d in depends])))
                    response = utils.yes_no_dialog(msg)
                else:
                    response = True

                if response and len(depends)>0:
                    # debug('dropping: %s' \
                    #           % ', '.join([d.name for d in depends]))
                    metadata.drop_all(bind=connection, tables=depends)
                else:
                    # user doesn't want to drop dependencies so we just quit
                    return

            # commit the dependency drops
            transaction.commit()
            transaction = connection.begin()

            # update_every determines how many rows we will insert at
            # a time and consequently how often we update the gui
            update_every = 127

            # import the tables one at a time, breaking every so often
            # so the GUI can update
            for table, filename in reversed(sorted_tables):
                if self.__cancel or self.__error:
                    break
                msg = _('importing %(table)s table from %(filename)s') \
                        % {'table': table.name, 'filename': filename}
                #log.info(msg)
                bauble.task.set_message(msg)
                yield # allow progress bar update

                # don't do anything if the file is empty:
                if filesizes[filename] <= 1:
                    if not table.exists():
                        create_table(table)
                    continue
                # check if the table was in the depends because they
                # could have been dropped whereas table.exists() can
                # return true for a dropped table if the transaction
                # hasn't been committed
                if table in depends or not table.exists():
                    #log.info('%s does not exist. creating.' % table.name)
                    #debug('%s does not exist. creating.' % table.name)
                    create_table(table)
                elif table.name not in created_tables and table not in depends:
                    # we get here if the table wasn't previously
                    # dropped because it was a dependency of another
                    # table
                    if not force:
                        msg = _('The <b>%s</b> table already exists in the '\
                                'database and may contain some data. If a '\
                                'row the import file has the same id as a '
                                'row in the database then the file will not '\
                                'import correctly.\n\n<i>Would you like to '
                                'drop the table in the database first. You '\
                                'will lose the data in your database if you '\
                                'do this?</i>') % table.name
                        response = utils.yes_no_dialog(msg)
                    else:
                        response = True
                    if response:
                        table.drop(bind=connection)
                        create_table(table)

                if self.__cancel or self.__error:
                    break

                # commit the drop of the table we're importing
                transaction.commit()
                transaction = connection.begin()

                # open a temporary reader to get the column keys so we
                # can later precompile our insert statement
                f = open(filename, "rb")
                tmp = UnicodeReader(f, quotechar=QUOTE_CHAR,
                                    quoting=QUOTE_STYLE)
                tmp.next()
                csv_columns = set(tmp.reader.fieldnames)
                del tmp
                f.close()

                # precompute the defaults...this assumes that the
                # default function doesn't depend on state after each
                # row...it shouldn't anyways since we do an insert
                # many instead of each row at a time
                defaults = {}
                for column in table.c:
                    if isinstance(column.default, ColumnDefault):
                        defaults[column.name] = column.default.execute()
                column_names = table.c.keys()

                # check if there are any foreign keys to on the table
                # that refer to itself, if so create a new file with
                # the lines sorted in order of dependency so that we
                # don't get errors about imporint values into a
                # foreign_key that don't reference and existin row
                self_keys = filter(lambda f: f.column.table==table, \
                                      table.foreign_keys)
                if self_keys:
                    key_pairs = map(lambda x: (x.parent.name, x.column.name),
                                    self_keys)
                    filename = self._toposort_file(filename, key_pairs)

                # the column keys for the insert are a union of the
                # columns in the CSV file and the columns with
                # defaults
                column_keys = list(csv_columns.union(defaults.keys()))
                insert = table.insert(bind=connection).\
                    compile(column_keys=column_keys)

                values = []
                def do_insert():
                    if values:
                        connection.execute(insert, *values)
                    del values[:]
                    percent = float(steps_so_far)/float(total_lines)
                    if 0 < percent < 1.0: # avoid warning
                        if bauble.gui is not None:
                            pb_set_fraction(percent)

                isempty = lambda v: v in ('', None)

                f = open(filename, "rb")
                reader = UnicodeReader(f, quotechar=QUOTE_CHAR,
                                       quoting=QUOTE_STYLE)
                # NOTE: we shouldn't get this far if the file doesn't
                # have any rows to import but if so there is a chance
                # that this loop could cause problems
                for line in reader:
                    while self.__pause:
                        yield
                    if self.__cancel or self.__error:
                        break

                    # fill in default values and None for "empty"
                    # columns in line
                    for column in table.c.keys():
                        if column in defaults \
                                and (column not in line \
                                         or isempty(line[column])):
                            line[column] = defaults[column]
                        elif column in line and isempty(line[column]):
                            line[column] = None
                        elif column in line and line[column] == 'False' and \
                                isinstance(table.c[column].type, Boolean):
                            # in SA 0.5.5 and only on an SQLite
                            # database the 'False' will import as True
                            # for some reason whereas True will import
                            # as True automatically
                            line[column] = False
                    values.append(line)

                    steps_so_far += 1
                    if steps_so_far % update_every == 0:
                        do_insert()
                        yield

                if self.__error or self.__cancel:
                    break

                # insert the remainder that were less than update every
                do_insert()

                # we have commit after create after each table is imported
                # or Postgres will complain if two tables that are
                # being imported have a foreign key relationship
                transaction.commit()
                #debug('%s: %s' % (table.name, table.select().alias().count().execute().fetchone()[0]))
                transaction = connection.begin()

            #debug('creating: %s' % ', '.join([d.name for d in depends]))
            # TODO: need to get those tables from depends that need to
            # be created but weren't created already
            metadata.create_all(connection, depends, checkfirst=True)
        except (bauble.task.TaskQuitting, GeneratorExit), e:
            # UPDATE 2009.06.18: i'm not sure TaskQuitting is still
            # relevant since we switched the task system to use
            # fibra...but it doesn't hurt having it here until we can
            # make sure
            transaction.rollback()
            raise
        except Exception, e:
            error(e)
            error(traceback.format_exc())
            transaction.rollback()
            self.__error = True
            self.__error_exc = e
            raise
        else:
            transaction.commit()

        # unfortunately inserting an explicit value into a column that
        # has a sequence doesn't update the sequence, we shortcut this
        # by setting the sequence manually to the max(column)+1
        col = None
        try:
            for table, filename in sorted_tables:
                for col in table.c:
                    utils.reset_sequence(col)
        except Exception, e:
            col_name = None
            try:
                col_name = col.name
            except Exception:
                pass
            msg = _('Error: Could not set the sequence for column: %s') \
                  % col_name
            utils.message_details_dialog(_(utils.xml_safe_utf8(msg)),
                                         traceback.format_exc(),
                                         type=gtk.MESSAGE_ERROR)


# TODO: we don't use the progress dialog any more but we'll leave this
# around to remind us when we support cancelling via the progress statusbar
#
#     def _cancel_import(self, *args):
#         '''
#         called by the progress dialog to cancel the current import
#         '''
#         msg = _('Are you sure you want to cancel importing?\n\n<i>All '
#                 'changes so far will be rolled back.</i>')
#         self.__pause = True
#         if utils.yes_no_dialog(msg, parent=self.__progress_dialog):
#             self.__cancel = True
##         self.__pause = False


    def _get_filenames(self):
        def on_selection_changed(filechooser, data=None):
            """
            only make the ok button sensitive if the selection is a file
            """
            f = filechooser.get_preview_filename()
            if f is None:
                return
            ok = filechooser.action_area.get_children()[1]
            ok.set_sensitive(os.path.isfile(f))
        fc = gtk.FileChooserDialog(_("Choose file(s) to import..."),
                                  None,
                                  gtk.FILE_CHOOSER_ACTION_OPEN,
                                  (gtk.STOCK_OK, gtk.RESPONSE_ACCEPT,
                                   gtk.STOCK_CANCEL, gtk.RESPONSE_REJECT))
        fc.set_select_multiple(True)
        fc.connect("selection-changed", on_selection_changed)
        r = fc.run()
        if r != gtk.RESPONSE_ACCEPT:
            fc.destroy()
            return None
        filenames = fc.get_filenames()
        fc.destroy()
        return filenames


    def on_response(self, widget, response, data=None):
        debug('on_response')
        debug(response)


# TODO: add support for exporting only specific tables

class CSVExporter(object):

    def start(self, path=None):
        if path == None:
            d = gtk.FileChooserDialog(_("Select a directory"), None,
                                      gtk.FILE_CHOOSER_ACTION_SELECT_FOLDER,
                                      (gtk.STOCK_OK, gtk.RESPONSE_ACCEPT,
                                      gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL))
            response = d.run()
            path = d.get_filename()
            d.destroy()
            if response != gtk.RESPONSE_ACCEPT:
                return

        if not os.path.exists(path):
            raise ValueError(_("CSVExporter: path does not exist.\n%s" % path))

        try:
            # TODO: should we support exporting other metadata
            # besides db.metadata
            bauble.task.queue(self.__export_task(path))
        except Exception, e:
            debug(e)


    def __export_task(self, path):
#        if not os.path.exists(path):
#            raise ValueError("CSVExporter: path does not exist.\n" + path)
        filename_template = os.path.join(path, "%s.txt")
#        timeout = tasklet.WaitForTimeout(12)
        steps_so_far = 0
        ntables = 0
        for table in db.metadata.sorted_tables:
            ntables += 1
            filename = filename_template % table.name
            if os.path.exists(filename):
                msg = _('Export file <b>%(filename)s</b> for '\
                        '<b>%(table)s</b> table already exists.\n\n<i>Would '\
                        'you like to continue?</i>') \
                        % {'filename': filename, 'table': table.name}
                if utils.yes_no_dialog(msg):
                    return

        def replace(s):
            if isinstance(s, (str, unicode)):
                s.replace('\n', '\\n')
            return s

        def write_csv(filename, rows):
            f = open(filename, 'wb')
            #writer = csv.writer(f, quotechar=QUOTE_CHAR, quoting=QUOTE_STYLE)
            writer = UnicodeWriter(f, quotechar=QUOTE_CHAR,quoting=QUOTE_STYLE)
            writer.writerows(rows)
            f.close()

        update_every = 30
        for table in db.metadata.sorted_tables:
            filename = filename_template % table.name
            steps_so_far+=1
            fraction = float(steps_so_far)/float(ntables)
            pb_set_fraction(fraction)
            msg = _('exporting %(table)s table to %(filename)s') \
                    % {'table': table.name, 'filename': filename}
            bauble.task.set_message(msg)
            #log.info("exporting %s" % table.name)

            # get the data
            results = table.select().execute().fetchall()

            # create empty files with only the column names
            if len(results) == 0:
                write_csv(filename, [table.c.keys()])
                yield
                #yield timeout
                #tasklet.get_event()
                continue

            rows = []
            rows.append(table.c.keys()) # append col names
            ctr = 0
            for row in results:
                values = map(replace, row.values())
                rows.append(values)
                if ctr == update_every:
                    yield
                    #yield timeout
                    #tasklet.get_event()
                    ctr=0
                ctr += 1
            write_csv(filename, rows)


class CSVImportCommandHandler(pluginmgr.CommandHandler):

    command = 'imcsv'

    def __call__(self, arg):
        importer = CSVImporter()
        importer.start(arg)


class CSVExportCommandHandler(pluginmgr.CommandHandler):

    command = 'excsv'

    def __call__(self, arg):
        exporter = CSVExporter()
        exporter.start(arg)

#
# plugin classes
#

class CSVImportTool(pluginmgr.Tool):
    category = _('Import')
    label = _('Comma Separated Value')

    @classmethod
    def start(cls):
        """
        Start the CSV importer.  This tool will also reinitialize the
        plugins after importing.
        """
        msg = _('It is possible that importing data into this database could '\
                'destroy or corrupt your existing data.\n\n<i>Would you '\
                'like to continue?</i>')
        if utils.yes_no_dialog(msg):
            c = CSVImporter()
            c.start()

        # reinitialized the plugins now that the data has changed
        pluginmgr.init()



class CSVExportTool(pluginmgr.Tool):
    category = _('Export')
    label = _('Comma Separated Value')

    @classmethod
    def start(cls):
        c = CSVExporter()
        c.start()


# TODO: importing from the command line isn't finished, i think the only thing
# that really need to be done for it to work is to create a gobject.mainloop()
# or implement blocking in the importer to have it's own mainloop

#def main():
#    # should allow you to export or import from a database from the
#    # command line, you would just have to pass the connection uri
#    # and the name of the directory to export to
#    # TODO: allow -i for import, -e for export
#    # TODO: need to pass in a database connection string
#    # postgres://bbg:garden@ceiba.test
#
#    # TODO: ****** i think the only reason this isn't working is because of using the
#    # connection manager so we can either 1. figure out how to use the connection
#    # manager from a tasklet or 2. don't use the connection manager and get
#    # connection paramaters from the command line including the passwd
#
#    import sys
#    from sqlobject import sqlhub, connectionForURI
#    from bauble.conn_mgr import ConnectionManager#Dialog
#    from bauble.prefs import prefs
#    from optparse import OptionParser
#    parser = OptionParser()
#    parser.add_option('--force', dest='force', action='store_true',
#                      default=False, help='force import')
#    parser.add_option('-c', '--connection', dest='conn',
#                      help='named connection from prefs')
#    options, args = parser.parse_args()
#
#    if len(args) == 0:
#        print '** Error: need a list of files to import'
#        return
#
#    prefs.init() # intialize the preferences
#
#    if options.conn is None:
#        default_conn = prefs[prefs.conn_default_pref]
#        cm = ConnectionManager(default_conn)
#        conn_name, uri = cm.start()
#        if conn_name is None: return
#    else:
#        params = prefs[prefs.conn_list_pref][options.conn]
#        uri = ConnectionManager().parameters_to_uri(params)
#
#    sqlhub.processConnection = connectionForURI(uri)
#    sqlhub.processConnection.getConnection()
#    sqlhub.processConnection = sqlhub.processConnection.transaction()
#
#    if not options.force:
#        msg = 'Importing to this connection (%s) will destroy any existing data '\
#              ' in the database. Are you sure this is what you want to do? ' % uri
#        response = raw_input(msg)
#        if response not in ('Y', 'y'):
#            return
##        if not utils.yes_no_dialog(msg):
##            return
#
#    # check that the database version are the same
#    from bauble._app import BaubleApp
#    BaubleApp.open_database(uri)
#
#    bauble.plugins.load()
#    importer = CSVImporter()
#    print 'importing....'
#    importer.start(args, force=options.force)
#    sqlhub.processConnection.commit()
#    print '...finished importing'


#if __name__ == "__main__":
#    tasklet.run(main())
#    gtk.main()

