#
# Family table definition
#

import gtk
from sqlobject import *
import bauble
from bauble.plugins import BaubleTable, tables, editors
from bauble.plugins.editor import TreeViewEditorDialog
from datetime import datetime
from bauble.utils.log import debug

#
# *** playing around with sqlalchemy
#
#from sqlalchemy import *
#families = Table('family', bauble.app.db_engine,
#                 Column('family_id', Integer, primary_key=True),
#                 Column('user_name', String(16)))                 
#             
#             
#        
#
#class Family(BaubleTable):
#    
#    def __init__(self):
#        BaubleTable.__init__(self, families)
#        
#
#synonyms = Table('family_synonym', bauble.app.db_engine,
#                 Column('family_id', Integer, ForeignKey('families.family_id')),
#                 Column('synonym_id', Integer, ForeignKey('families.family_id')))
#                
#class FamilySynonym(BaubleTable):
#    def __init__(self):
#        BaubleTable.__init__(self, synonyms)
                        
class Family(BaubleTable):

    class sqlmeta(BaubleTable.sqlmeta):
	       defaultOrder = 'family'

    family = StringCol(length=45, notNull=True, alternateID="True")
    synonyms = MultipleJoin('FamilySynonym', joinColumn='family_id')
    notes = StringCol(default=None)
    genera = MultipleJoin("Genus", joinColumn="family_id")
    
    def __str__(self): 
        return self.family
    
    
    
class FamilySynonym(BaubleTable):
    
    # - deleting either of the families that this synonym refers to makes this
    # synonym irrelevant
    # - here default=None b/c this can only be edited as a sub editor of,
    # Family, thoughwe have to be careful this doesn't create a dangling record
    # with no parent
    family = ForeignKey('Family', default=None, cascade=True)
    synonym = ForeignKey('Family', cascade=True)
    
    def __str__(self): 
        return self.synonym


# 
# editor
#
class FamilyEditor(TreeViewEditorDialog):

    visible_columns_pref = "editor.family.columns"
    column_width_pref = "editor.family.column_width"
    default_visible_list = ['family', 'comments']
    
    label = 'Families'
    
    def __init__(self, parent=None, select=None, defaults={}):
        
        TreeViewEditorDialog.__init__(self, tables["Family"], "Family Editor", 
                                      parent, select=select, defaults=defaults)
        titles = {'family': 'Family',
                  'notes': 'Notes',
                  'synonyms': 'Synonyms'}
        self.columns.titles = titles
        self.columns['synonyms'].meta.editor = editors["FamilySynonymEditor"]



# 
# FamilySynonymEditor
#
class FamilySynonymEditor(TreeViewEditorDialog):

    visible_columns_pref = "editor.family_syn.columns"
    column_width_pref = "editor.family_syn.column_width"
    default_visible_list = ['synonym']
    
    standalone = False
    label = 'Family Synonym'
    
    def __init__(self, parent=None, select=None, defaults={}):        
        TreeViewEditorDialog.__init__(self, tables["FamilySynonym"], \
                                      "Family Synonym Editor", 
                                      parent, select=select, 
                                      defaults=defaults)
        titles = {'synonymID': 'Synonym of Family'}
                  
        # can't be edited as a standalone so the family should only be set by
        # the parent editor
        self.columns.pop('familyID')
        
        self.columns.titles = titles
        self.columns["synonymID"].meta.get_completions = self.get_family_completions

        
    def get_family_completions(self, text):
        model = gtk.ListStore(str, object)
        sr = tables["Family"].select("family LIKE '"+text+"%'")
        for row in sr:
            model.append([str(row), row])
        return model


#
# infobox for SearchView
# 
try:
    from bauble.plugins.searchview.infobox import InfoBox
except ImportError:
    pass
else:
    class FamiliesInfoBox(InfoBox):
        """
        - number of taxon in number of genera
        - references
        """
        def __init__(self):
            InfoBox.__init__(self)
