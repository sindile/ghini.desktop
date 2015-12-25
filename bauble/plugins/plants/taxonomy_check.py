# -*- coding: utf-8 -*-
#
# Copyright 2015 Mario Frasca <mario@anche.no>.
#
# This file is part of bauble.classic.
#
# bauble.classic is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# bauble.classic is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with bauble.classic. If not, see <http://www.gnu.org/licenses/>.

import os
import logging
logger = logging.getLogger(__name__)
from bauble import db, paths


from bauble.editor import (
    GenericEditorView, GenericEditorPresenter)


def start_taxonomy_check():
    '''run the batch taxonomy check (BTC)
    '''

    view = GenericEditorView(
        os.path.join(paths.lib_dir(), 'plugins', 'plants',
                     'taxonomy_check.glade'),
        parent=None,
        root_widget_name='hbox1')
    l = []
    presenter = BatchTaxonomicCheckPresenter(l, view, refresh_view=True)
    error_state = presenter.start()
    if error_state:
        presenter.session.rollback()
    else:
        presenter.commit_changes()
    presenter.session.close()
    presenter.cleanup()
    return error_state


class BatchTaxonomicCheckPresenter(GenericEditorPresenter):
    '''
    the batch taxonomy check (BTC) can run if you have an equal rank
    selection of taxa in your search results. The BTC exports the names
    to the clipboard and opens the browser on the
    http://tnrs.iplantcollaborative.org/TNRSapp.html page.

    the user will run the service on the remote site, then save the results to
    a file. then back to Bauble's BTC, the user will open the file and finally
    interact with the BTC view.

    the Model of the BTC is a list of tuples.

    '''
    pass
