# 
# need to create a test for all possible species strings
# 

# TODO: should also test that when we delete everything from an entry that
# the value is set as None in the database instead of as an empty string

import os, sys, unittest
from sqlobject import *
import bauble
from bauble.plugins import plugins, tables
from bauble.plugins.plants.species_model import Species
from testbase import BaubleTestCase

#bauble.plugins.load()

#Family = tables['Family']
#Genus = tables['Genus']
#Species = tables['Species']
#values = {'family': 'TestFamily',
#          'genus': 'TestGenus'}
#
#def set_up():    
#    ri = 'sqlite:///%s/test.sqlite' % os.path.dirname(os.path.abspath(__file__))
#    print uri
#    sqlhub.processConnection = connectionForURI(uri)    
#    sqlhub.processConnection.getConnection()
#    sqlhub.processConnection = sqlhub.processConnection.transaction()   
#    
#    f = Family(values['family'])
#    g = Genus(values['genus'])
#    
#    
#def tear_down():
#    f.destroySelf()
#    g.destroySelf()
    
    
class AttrDict(dict):
    
    def __init__(self, **kwargs):        
        dict.__init__(self)
        for name, value in kwargs.iteritems():
            self[name] = value        
            
    def __getattr__(self, attr):
        if attr in self:
            return dict.__getitem__(self, attr)
        else:
            return None
    
    def __setattr__(self, attr, value):
        return dict.__setitem__(self, attr, value)
    
    
# possible name formats
# TODO: need to also test unicode in the relevant fields

#def test_speciesStr(verbose=False):    
    
# all possible combinations of species values
sp_example_dicts = [AttrDict(genus='Genus', sp='species'), 
                     AttrDict(genus='Genus', sp='species', sp_author='SpAuthor'),
                     AttrDict(genus='Genus', sp='spname', sp_hybrid='x'),
                     AttrDict(genus='Genus', sp='spname', infrasp_rank='var.', infrasp='ispname'),
                     AttrDict(genus='Genus', sp='spname', infrasp_rank='cv.', infrasp='ispname'),
                     AttrDict(genus='Genus', sp='spname', cv_group='CvGroupName'), # TODO: should this be valid?
                     AttrDict(genus='Genus', sp='spname', cv_group='CvGroupName', infrasp_rank='cv.', infrasp='ispname'),
                     AttrDict(genus='Genus', sp='spname', cv_group='CvGroupName', infrasp_rank='cv.')
                     ]
sp_examples_no_authors_no_markup = (('Genus species', sp_example_dicts[0]),
                                     ('Genus species', sp_example_dicts[1]),
                                     ('Genus x spname', sp_example_dicts[2]),
                                     ('Genus spname var. ispname', sp_example_dicts[3]),
                                     ('Genus spname \'ispname\'', sp_example_dicts[4]),
                                     ('Genus spname CvGroupName Group', sp_example_dicts[5]),
                                     ('Genus spname (CvGroupName Group) \'ispname\'', sp_example_dicts[6]),
                                     ('Genus spname CvGroupName Group', sp_example_dicts[7])
                                     )
                         
sp_examples_yes_authors_no_markup = (('Genus species', sp_example_dicts[0]),
                                      ('Genus species SpAuthor', sp_example_dicts[1]),
                                      ('Genus x spname', sp_example_dicts[2]),
                                      ('Genus spname var. ispname', sp_example_dicts[3]),
                                      ('Genus spname \'ispname\'', sp_example_dicts[4]))
    
sp_examples_no_authors_yes_markup = (('<i>Genus</i> <i>species</i>', sp_example_dicts[0]), 
                                      ('<i>Genus</i> <i>species</i>', sp_example_dicts[1]),
                                      ('<i>Genus</i> x <i>spname</i>', sp_example_dicts[2]),
                                      ('<i>Genus</i> <i>spname</i> var. <i>ispname</i>', sp_example_dicts[3]),
                                      ('<i>Genus</i> <i>spname</i> \'ispname\'', sp_example_dicts[4]),
                                      ('<i>Genus</i> <i>spname</i> CvGroupName Group', sp_example_dicts[5]),
                                      ('<i>Genus</i> <i>spname</i> (CvGroupName Group) \'ispname\'', sp_example_dicts[6]))
    
sp_examples_yes_authors_yes_markup = (('<i>Genus</i> <i>species</i>', sp_example_dicts[0]),
                                       ('<i>Genus</i> <i>species</i> SpAuthor', sp_example_dicts[1]),
                                       ('<i>Genus</i> x <i>spname</i>', sp_example_dicts[2]),
                                       ('<i>Genus</i> <i>spname</i> var. <i>ispname</i>', sp_example_dicts[3]),
                                       ('<i>Genus</i> <i>spname</i> \'ispname\'', sp_example_dicts[4]),
                                       ('<i>Genus</i> <i>spname</i> CvGroupName Group', sp_example_dicts[5]),
                                       ('<i>Genus</i> <i>spname</i> (CvGroupName Group) \'ispname\'', sp_example_dicts[6]))
        
   
        
#def test_createSpecies():    
#    # insert genus
#    # insert species
#    # insert sp_author
#    # ... etc ...
#    # ok.clicked()
#    # test the committed species has the same value in the database as we
#    # put in the entries
#    
#    pass
#
#def profile():
#    example_dicts = [AttrDict(genus='Genus', sp='species'), 
#                     AttrDict(genus='Genus', sp='species', sp_author='SpAuthor'),
#                     AttrDict(genus='Genus', sp='spname', sp_hybrid='x'),
#                     AttrDict(genus='Genus', sp='spname', infrasp_rank='var.', infrasp='ispname'),
#                     AttrDict(genus='Genus', sp='spname', infrasp_rank='cv.', infrasp='ispname'),
#                     AttrDict(genus='Genus', sp='spname', cv_group='CvGroupName'), # TODO: should this be valid?
#                     AttrDict(genus='Genus', sp='spname', cv_group='CvGroupName', infrasp_rank='cv.', infrasp='ispname'),
#                     AttrDict(genus='Genus', sp='spname', cv_group='CvGroupName', infrasp_rank='cv.')
#                     ]
#    examples_yes_authors_yes_markup = (('<i>Genus</i> <i>species</i>', example_dicts[0]),
#                                       ('<i>Genus</i> <i>species</i> SpAuthor', example_dicts[1]),
#                                       ('<i>Genus</i> x <i>spname</i>', example_dicts[2]),
#                                       ('<i>Genus</i> <i>spname</i> var. <i>ispname</i>', example_dicts[3]),
#                                       ('<i>Genus</i> <i>spname</i> \'ispname\'', example_dicts[4]),
#                                       ('<i>Genus</i> <i>spname</i> CvGroupName Group', example_dicts[5]),
#                                       ('<i>Genus</i> <i>spname</i> (CvGroupName Group) \'ispname\'', example_dicts[6]))
#    for i in xrange(1, 1000):
#        for name, name_dict in examples_yes_authors_yes_markup:    
#            s = Species.str(name_dict, authors=True, markup=True)
#            assert(name == s)
#    
#    
#def main():    
#    from optparse import OptionParser
#    parser = OptionParser()
#    parser.add_option('-v', '--verbose', dest='verbose', action='store_true',
#                      help='verbose output')
#    parser.add_option('-p', '--profile', dest='profile', action='store_true',
#                      help='print run times')
#    options, args = parser.parse_args()
#    
#    import profile    
#    import time
#    if options.profile:
#        t1 = time.time()
#        #profile.run('test_speciesStr()')
#        profile.run('profile()')
#        t2 = time.time()
#        print 'time: %s' % (t2-t1)
#    else:
#        print 'starting tests...'
#        test_speciesStr(options.verbose)
#        print 'done.'
#    
#    
#if __name__ == '__main__':
#    main()


class PlantTestCase(BaubleTestCase):
    def setUp(self):
        pass
    def tearDown(self):
        pass
    
class SpeciesTestCase(PlantTestCase):
    
    def testString(self):
        '''
        test Species string conversion function
        '''
#        print '\ntest Species.str(authors=False, markup=False)\n----------------'
        for name, name_dict in sp_examples_no_authors_no_markup:    
            s = Species.str(name_dict, authors=False, markup=False)        
#            if verbose:
#                print '%s == %s %s' % (name, s, name_dict)
            assert(name == s), 'authors=False, markup=False, %s == %s' % (name, name_dict)
            
#        if verbose:
#            print '\ntest Species.str(authors=True, markup=False)\n----------------'
        for name, name_dict in sp_examples_yes_authors_no_markup:    
            s = Species.str(name_dict, authors=True, markup=False)
#            if verbose:
#                print '%s == %s %s' % (name, s, name_dict)
            assert(name == s)
            
#        if verbose:
#            print '\ntest Species.str(authors=False, markup=True)\n----------------'
        for name, name_dict in sp_examples_no_authors_yes_markup:    
            s = Species.str(name_dict, authors=False, markup=True)
#            if verbose:
#                print '%s == %s %s' % (name, s, name_dict)
            assert(name == s)
            
#        if verbose:
#            print '\ntest Species.str(authors=True, markup=True)\n----------------'
        for name, name_dict in sp_examples_yes_authors_yes_markup:    
            s = Species.str(name_dict, authors=True, markup=True)
#            if verbose:
#                print '%s == %s %s' % (name, s, name_dict)
            assert(name == s)
            
            
#    def runTest(self):
#        self.testString()
        
class PlantTestSuite(unittest.TestSuite):
   def __init__(self):
       unittest.TestSuite.__init__(self, map(SpeciesTestCase,
                                             ("testString",)))

testsuite = PlantTestSuite()
#testsuite = unittest.TestSuite()
#testsuite.addTest(SpeciesTestCase('testString'))
#testsuite.addTest(SchemaTestCase())



