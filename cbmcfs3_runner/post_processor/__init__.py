#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Written by Lucas Sinclair and Paul Rougieux.

JRC biomass Project.
Unit D1 Bioeconomy.
"""

# Built-in modules #

# Third party modules #

# First party modules #
from plumbing.databases.access_database import AccessDatabase
from plumbing.cache       import property_cached
from autopaths.auto_paths import AutoPaths

# Internal modules #
from cbmcfs3_runner.post_processor.harvest   import Harvest
from cbmcfs3_runner.post_processor.inventory import Inventory
from cbmcfs3_runner.post_processor.products  import Products

###############################################################################
class PostProcessor(object):
    """
    Provides access to the Access database.
    Computes aggregates and joins to facilitate analysis.
    """

    all_paths = """
    /output/cbm/project.mdb
    """

    def __init__(self, parent):
        # Default attributes #
        self.parent = parent
        # Directories #
        self.paths = AutoPaths(self.parent.data_dir, self.all_paths)

    def __call__(self):
        self.harvest.check_exp_prov()
        
    def sanitize_names(self, names):
        return names.lower().replace(' ', '_').replace('/','_')

    @property
    def database(self):
        """The CBM database, after the model is run."""
        return AccessDatabase(self.paths.mdb)

    @property_cached
    def classifiers(self):
        """Creates a mapping between 'UserDefdClassSetID'
        and the classifiers values:
         * species, site_quality and forest_type in tutorial six
         * status, forest_type, region, management_type, management_strategy, climatic_unit, conifers_bradleaves
         in the European dataset

         Columns are: ['UserDefdClassID', 'status', 'forest_type', 'region', 'management_type',
                       'management_strategy', 'climatic_unit', 'conifers_bradleaves']
        """
        # Load the three tables we will need #
        user_classes           = self.database["tblUserDefdClasses"]
        user_sub_classes       = self.database["tblUserDefdSubclasses"]
        user_class_sets_values = self.database["tblUserDefdClassSetValues"]
        # Join
        index = ['UserDefdClassID', 'UserDefdSubclassID']
        classifiers = user_sub_classes.set_index(index)
        classifiers = classifiers.join(user_class_sets_values.set_index(index))
        # Unstack
        index = ['UserDefdClassID', 'UserDefdClassSetID']
        classifiers = classifiers.reset_index().dropna().set_index(index)
        classifiers = classifiers[['UserDefdSubClassName']].unstack('UserDefdClassID')
        # Rename
        # This object will link: 1->species, 2->forest_type, etc.
        mapping = user_classes.set_index('UserDefdClassID')['ClassDesc']
        mapping = mapping.apply(self.sanitize_names)
        classifiers = classifiers.rename(mapping, axis=1)
        # Remove multilevel column index, replace by level(1) (second level)
        classifiers.columns = classifiers.columns.get_level_values(1)
        # Remove the confusing name #
        del classifiers.columns.name
        # In the calibration scenario we can't change names and there is a conflict #
        # This should not impact other scenarios hopefully #
        # C.f the "Broad/Conifers" to "Conifers/Bradleaves" problem in several countries #
        classifiers = classifiers.rename(columns={'broad_conifers': 'conifers_bradleaves'})
        # C.f the PL column problem #
        classifiers = classifiers.rename(columns={'natural_forest_region': 'management_type'})
        # Return result #
        return classifiers.reset_index()

    @property
    def coefficients(self):
        """Shortcut to the countries' conversion coefficients."""
        return self.parent.country.coefficients

    @property_cached
    def classifiers_coefs(self):
        """A join between the coefficients and the classifiers table.

        Columns are: ['index', 'forest_type', 'UserDefdClassSetID', 'status', 'region',
                      'management_type', 'management_strategy', 'climatic_unit',
                      'conifers_bradleaves', 'id', 'c', 'db', 'harvest_gr']
        """

        return (self.classifiers
                .set_index('forest_type')
                .join(self.coefficients.set_index('forest_type'))
                .reset_index())

    #-------------------------------------------------------------------------#
    @property_cached
    def classifiers_mapping(self):
        """
        Map classifiers columns to a better descriptive name
        This mapping table will enable us to rename
        classifier columns [_1, _2, _3] to ['forest_type', 'region', etc.]
        """
        # Load user_classes table from DB #
        df = self.database['tblUserDefdClasses']
        # Add an underscore to the classifier number so it can be used for renaming #
        df['id'] = '_' + df['UserDefdClassID'].astype(str)
        # This makes df a pandas.Series #
        df = df.set_index('id')['ClassDesc']
        # Lower case names everywhere #
        df = df.apply(self.sanitize_names)
        # Return #
        return df

    #-------------------------------------------------------------------------#
    @property_cached
    def inventory(self):
        return Inventory(self)

    @property_cached
    def harvest(self):
        return Harvest(self)

    @property_cached
    def products(self):
        return Products(self)

    #-------------------------------------------------------------------------#
    def timestep_to_years(self, timestep):
        """
        Will convert a Series containing simulation time-steps such as:
           [1, 2, 3, 4, 5]
        to actual corresponding simulation years such as:
           [1996, 1997, 1998, 1999, 2000]

        #TODO check that there is not an off by one error here
        """
        return timestep + self.parent.country.inventory_start_year - 1