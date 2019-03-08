#!/usr/bin/env python2
# -*- coding: utf-8 -*-

"""
Written by Lucas Sinclair and Paul Rougieux.

JRC biomass Project.
Unit D1 Bioeconomy.
"""

# Built-in modules #

# Third party modules #

# First party modules #
from autopaths.dir_path   import DirectoryPath
from autopaths.auto_paths import AutoPaths

# Internal modules #
from cbm_runner.country import Country

###############################################################################
class Continent(object):
    """Aggregates countries together. Enables access to dataframe containing
    concatenates data from all countries."""

    def __init__(self, cbm_data_repos):
        """Store the cbm_data_repos directory paths where there
        is a directory for every country."""
        self.cbm_data_repos = DirectoryPath(cbm_data_repos)
        self.all_countries = [Country(d) for d in self.cbm_data_repos.flat_directories if 'orig' in d]

    @property
    def input(self):
        """Return aggregated data frames from the input files."""
        return GroupInput(self)


