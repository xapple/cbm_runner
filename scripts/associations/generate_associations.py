#!/usr/bin/env python2
# -*- coding: utf-8 -*-

"""
This script takes the file "calibration.mdb" as well as the "aidb.mdb" and
creates a CSV containing mappings between names. It generates the
"associations.csv" file. This CSV is then manually edited to fix inconsistencies.

Typically you would run this file from a command line like this:

     ipython.exe -i -- /deploy/cbmcfs3_runner/scripts/generate_associations.py
"""

# Built-in modules #

# Third party modules #
import pandas

# First party modules #
from plumbing.cache import property_cached
from autopaths.auto_paths import AutoPaths
from plumbing.databases.access_database import AccessDatabase

# Internal modules #

# Constants #

###############################################################################
class AssociationsGenerator(object):

    keys = ['MapAdminBoundary', 'MapEcoBoundary', 'MapSpecies',
            'MapDisturbanceType', 'MapNonForestType']

    all_paths = """
    /orig/calibration.mdb
    /orig/aidb_eu.mdb
    /orig/associations.csv
    """

    def __init__(self, country):
        # Default attributes #
        self.country = country
        # Automatically access paths based on a string of many subpaths #
        self.paths = AutoPaths(self.country.data_dir, self.all_paths)

    @property_cached
    def aidb(self):
        """Shortcut to the AIDB."""
        return AccessDatabase(self.paths.aidb_eu_mdb)

    @property_cached
    def calib(self):
        """Shortcut to the Calibration DB."""
        return AccessDatabase(self.paths.calibration_mdb)

    #---------------------------- Methods ------------------------------------#
    def select_classifier_rows(self, classifier_name):
        """
        Returns a dataframe by running a query on the Calibration DB.
        Here is an example call:

        >>> self.select_classifier_rows('Climatic unit')
            ClassifierNumber ClassifierValueID   Name
        19                 6                25  CLU25
        20                 6                34  CLU34
        21                 6                35  CLU35
        22                 6                44  CLU44
        23                 6                45  CLU45
        """
        query  = "ClassifierValueID == '_CLASSIFIER' and Name == '%s'" % classifier_name
        number = self.calib['Classifiers'].query(query)['ClassifierNumber'].iloc[0]
        query  = "ClassifierValueID != '_CLASSIFIER' and ClassifierNumber == %i" % number
        rows   = self.calib['Classifiers'].query(query)
        return rows

    def __call__(self):
        """Run this once before manually fixing the CSVs.
        The keys of the dictionary are the names in the calibration.mdb
        The values of the dictionary are the names in the aidb.mdb to map to."""
        # Remove this warning if you must #
        raise Exception("Are you sure you want to regenerate the associations CSV?" + \
                        "They have been edited manually.")
        # Admin boundaries #
        self.admin   = [(k,k) for k in self.select_classifier_rows('Region')['Name']]
        # Eco boundaries #
        self.eco     = [(k,k) for k in self.select_classifier_rows('Climatic unit')['Name']]
        # Species #
        self.species = [(k,k) for k in self.select_classifier_rows('Forest type')['Name']]
        # Disturbances #
        left      = self.aidb['tblDisturbanceTypeDefault'].set_index('DistTypeID')
        right     = self.calib['tblDisturbanceType'].set_index('DefaultDistTypeID')
        self.dist = left.join(right, how='inner', lsuffix='_archive', rsuffix='_calib')
        self.dist = zip(self.dist['Description_calib'], self.dist['DistTypeName_archive'])
        # Filter empty disturbances #
        self.dist = [(calib, archive) for calib, archive in self.dist if calib]
        # Combine the four DataFrames #
        self.combined = [pandas.DataFrame(self.admin),
                         pandas.DataFrame(self.eco),
                         pandas.DataFrame(self.species),
                         pandas.DataFrame(self.dist)]
        # Concatenate the four DataFrames #
        self.combined = pandas.concat(self.combined, keys=self.keys).reset_index(0)
        # Write the CSV #
        self.combined.to_csv(str(self.paths.associations), header = ['A', 'B', 'C'], index=False)

###############################################################################
if __name__ == '__main__':
    raise Exception("This script needs to be finished and is missing a few parts.")