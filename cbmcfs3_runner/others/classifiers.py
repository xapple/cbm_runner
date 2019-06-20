#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Written by Lucas Sinclair and Paul Rougieux.

JRC biomass Project.
Unit D1 Bioeconomy.
"""

# Built-in modules #

# First party modules #
from plumbing.cache import property_cached

# Third party modules #

###############################################################################
class Classifiers(object):
    """
    This class takes care of parsing the file "classifiers.csv" to
    produce a data frame that links the classifier numbers to their
    names.

    You can test this class like this:

        from cbmcfs3_runner.core.continent import continent
        r = continent[('static_demand', 'ZZ', -1)]
        print(r.country.classifiers.mapping)
    """

    def __init__(self, parent):
        # Default attributes #
        self.parent = parent

    @property_cached
    def mapping(self):
        """
        Map classifiers columns to a better descriptive name
        This mapping table will enable us to rename
        classifier columns [_1, _2, _3] to ['forest_type', 'region', etc.]
        """
        # Load the CSV #
        self.df  = self.parent.orig_data['classifiers']
        # Get only classifier names #
        selector = self.df['ClassifierValueID'] == "_CLASSIFIER"
        self.df  = self.df.loc[selector].copy()
        # Drop the extra column #
        self.df  = self.df.drop('ClassifierValueID', axis=1)
        # Rename #
        self.df  = self.df.rename(columns={'ClassifierNumber': 'id'})
        self.df  = self.df.rename(columns={'Name': 'ClassDesc'})
        # Add an underscore to the classifier number so it can be used for renaming #
        self.df['id'] = '_' + self.df['id'].astype(str)
        # This makes df a pandas.Series #
        self.df = self.df.set_index('id')['ClassDesc']
        # Remove spaces and slashes from column names #
        self.df = self.df.apply(lambda x: x.lower().replace(' ', '_').replace('/','_'))
        # Return #
        return self.df
