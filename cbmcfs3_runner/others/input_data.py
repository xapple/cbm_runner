#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Written by Lucas Sinclair and Paul Rougieux.

JRC biomass Project.
Unit D1 Bioeconomy.
"""

# Built-in modules #

# Third party modules #
import pandas

# First party modules #
from autopaths.auto_paths import AutoPaths
from plumbing.cache import property_cached

# Internal modules #

###############################################################################
class InputData(object):
    """
    This class will provide access to the input data of a Runner
    as a pandas dataframe.
    """

    all_paths = """
    /input/xls/default_tables.xls
    /input/xls/append_tables.xls
    """
 


    def __init__(self, parent):
        # Default attributes #
        self.parent = parent
        # Directories #
        self.paths = AutoPaths(self.parent.data_dir, self.all_paths)
        # Classifiers names
        self.classifiers_mapping = self.parent.post_processor.classifiers_mapping

    def copy_from_country(self):
        destination_dir = self.parent.paths.csv_dir
        destination_dir.remove()
        self.parent.country.paths.export_dir.copy(destination_dir)

    @property_cached
    def xls(self):
        """The first excel file"""
        return pandas.ExcelFile(str(self.paths.default))

    @property_cached
    def xls_append(self):
        """The second excel file"""
        return pandas.ExcelFile(str(self.paths.append))

    #-------------------------- Specific sheets ------------------------------#
    @property_cached
    def inventory(self):
        """
        Columns are:

        ['status', 'forest_type', 'region', 'management_type',
         'management_strategy', 'climatic_unit', 'conifers/bradleaves',
         'UsingID', 'Age', 'Area', 'Delay', 'UNFCCCL', 'HistDist', 'LastDist']
        """
        df = self.xls.parse("Inventory")
        return df.rename(columns = self.classifiers_mapping)

    @property_cached
    def disturbance_events(self):
        """
        Columns are:

        ['_1', '_2', '_3', '_4', '_5', '_6', '_7', 'UsingID', 'SWStart', 'SWEnd',
         'HWStart', 'HWEnd', 'Min_since_last_Dist', 'Max_since_last_Dist',
         'Last_Dist_ID', 'Min_tot_biom_C', 'Max_tot_biom_C',
         'Min_merch_soft_biom_C', 'Max_merch_soft_biom_C',
         'Min_merch_hard_biom_C', 'Max_merch_hard_biom_C', 'Min_tot_stem_snag_C',
         'Max_tot_stem_snag_C', 'Min_tot_soft_stem_snag_C',
         'Max_tot_soft_stem_snag_C', 'Min_tot_hard_stem_snag_C',
         'Max_tot_hard_stem_snag_C', 'Min_tot_merch_stem_snag_C',
         'Max_tot_merch_stem_snag_C', 'Min_tot_merch_soft_stem_snag_C',
         'Max_tot_merch_soft_stem_snag_C', 'Min_tot_merch_hard_stem_snag_C',
         'Max_tot_merch_hard_stem_snag_C', 'Efficency', 'Sort_Type',
         'Measurement_type', 'Amount', 'Dist_Type_ID', 'Step']
        """
        return self.xls.parse("DistEvents")

    @property_cached
    def disturbance_types(self):
        """
        Columns are: ['DisturbanceTypeID', 'Name']
        """
        # Get the sheet #
        df = self.xls.parse("DistType")
        # DisturbanceTypeID has to be strings for joining purposes #
        df.DisturbanceTypeID = df.DisturbanceTypeID.astype(str)
        # Return #
        return df

    @property_cached
    def yields(self):
        """
        Columns are:

        ['_1', '_2', '_3', '_4', '_5', '_6', '_7', 'Sp', 'Vol0', 'Vol1', 'Vol2',
         'Vol3', 'Vol4', 'Vol5', 'Vol6', 'Vol7', 'Vol8', 'Vol9', 'Vol10',
         'Vol11', 'Vol12', 'Vol13', 'Vol14', 'Vol15', 'Vol16', 'Vol17', 'Vol18',
         'Vol19', 'Vol20', 'Vol21', 'Vol22', 'Vol23', 'Vol24', 'Vol25', 'Vol26',
         'Vol27', 'Vol28', 'Vol29', 'Vol30']
        """
        df = self.xls.parse("Growth")
        return df.rename(columns = self.classifiers_mapping)

    @property_cached
    def historical_yields(self):
        """ Historical yield taken from the xls_append object. 
            The object used to append historical yield 
            to the Standard Import Tool 
            for the carbon pool initialisation period"""
        df = self.xls_append.parse("Growth")
        # Rename classifier _1, _2, _3 to forest_type, region, etc. #
        return df.rename(columns = self.classifiers_mapping)

    @property_cached
    def yields_long(self):
        return self.reshape_yields_long(self.yields)

    @property_cached
    def historical_yields_long(self):
        return self.reshape_yields_long(self.historical_yields)

    def reshape_yields_long(self, yields_wide):
        """
        Columns are:

        ['status', 'forest_type', 'region', 'management_type',
         'management_strategy', 'climatic_unit', 'conifers/bradleaves', 'Sp',
         'age_class', 'volume']
         """
        df = yields_wide.melt(id_vars=['status', 'forest_type', 'region',
                                       'management_type', 'management_strategy',
                                       'climatic_unit', 'conifers/bradleaves',
                                       'Sp'],
                              var_name="age_class",
                              value_name="volume")
        df['age_class'] = (df['age_class']
                           .replace("Vol", "", regex=True)
                           .astype('int'))
        return df



    @property_cached
    def ageclass(self):
        return self.xls.parse("AgeClasses")

    @property_cached
    def classifiers(self):
        df = self.xls.parse("Classifiers")
        sort_by = ['ClassifierNumber', 'ClassifierValueID']
        return df.sort_values(by=sort_by, ascending=[True, False])


