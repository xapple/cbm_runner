#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Written by Lucas Sinclair and Paul Rougieux.

JRC biomass Project.
Unit D1 Bioeconomy.
"""

# Built-in modules #

# Third party modules #
import numpy

# First party modules #
from plumbing.cache import property_cached
from autopaths.auto_paths import AutoPaths

# Internal modules #

###############################################################################
class Harvest(object):
    """
    See notebook "simulated_harvest.ipynb" for more details about the methods below.
    """

    all_paths = """
    /output/harvest/
    """

    def __init__(self, parent):
        # Default attributes #
        self.parent = parent
        # Directories #
        self.paths = AutoPaths(self.parent.parent.data_dir, self.all_paths)

    #-------------------------------------------------------------------------#
    @property_cached
    def check(self):
        """
        Converts flux indicators in tons of carbon to harvested
        wood products volumes in cubic meters of wood.

        Based on Roberto's query `Harvest analysis check` visible in the original calibration database.

        What are the units?
        * TC is in terms of tons of carbon.
        * Vol_Merch are in terms of cubic meters of wood.

        Columns are: ['dist_type_id', 'dist_type_name', 'time_step', 'status', 'forest_type',
                      'management_type', 'management_strategy', 'conifers_broadleaves',
                      'dom_production', 'co2_production', 'merch_litter_input', 'oth_litter_input',
                      'db', 'soft_production', 'hard_production', 'tc', 'vol_merch',
                      'vol_sub_merch', 'vol_snags', 'vol_forest_residues']
        """
        # First ungrouped #
        ungrouped = self.parent.flux_indicators
        # The index we will use for grouping #
        index = ['dist_type_id',
                 'dist_type_name',
                 'time_step',
                 'status',
                 'forest_type',
                 'management_type',
                 'management_strategy',
                 'conifers_broadleaves']
        # Not real grouping variables only here to keep them in the final table
        # Their values should be unique for the all combination of the other grouping vars
        # But in fact they are not! But we will group again later with other vars
        secondary_index = ['dom_production',
                           'co2_production',
                           'merch_litter_input',
                           'oth_litter_input',
                           'db']
        # Check that we don't produce NaNs #
        # See ~/repos/examples/python_modules/pandas/join_and_produce_nan.py
        # Check for NaNs coming from a join tables to avoid using them in an aggregation index
        # (currently ES, HU have some in the secondary_index) #
        assert not ungrouped[index].isna().any().any()
        # Then group #
        df = (ungrouped
              .groupby(index + secondary_index)
              .agg({'soft_production': 'sum',
                    'hard_production': 'sum'})
              .reset_index())
        # Check conservation of total mass #
        flux_raw = self.parent.database['tblFluxIndicators']
        is_equal = numpy.testing.assert_allclose
        is_equal(flux_raw['soft_production'].sum(), df['soft_production'].sum())
        is_equal(flux_raw['hard_production'].sum(), df['hard_production'].sum())
        # Create new columns #
        df['tc']                  = df.SoftProduction + df.HardProduction
        df['prov_carbon']         = df.SoftProduction + df.HardProduction + df.DOMProduction
        df['vol_merch']           = (df.TC * 2) / df.db
        df['vol_sub_merch']        = (df.CO2Production * 2) / df.db
        df['vol_snags']           = (df.DOMProduction * 2) / df.db
        df['vol_forest_residues'] = ((df.MerchLitterInput + df.OthLitterInput) * 2) / df.db
        # Return #
        return df

    #-------------------------------------------------------------------------#
    @property_cached
    def provided_volume(self):
        """
        Based on Roberto's query `Harvest summary check` visible in the original calibration database.

        Columns are:    ['dist_type_id', 'dist_type_name', 'time_step', 'status', 'forest_type',
        (of the output)  'management_type', 'management_strategy', 'vol_merch', 'vol_snags',
                         'vol_sub_merch', 'vol_forest_residues', 'tc', 'tot_vol']

        This corresponds to the "provided" aspect of "expected_provided" harvest and contains
        only volumes ('M').
        """
        # Compute #
        df = (self.check
              .set_index('dist_type_id')
              .groupby(['dist_type_id',
                        'dist_type_name',
                        'time_step',
                        'status',
                        'forest_type',
                        'management_type',
                        'management_strategy'])
              .agg({'vol_merch':           'sum',
                    'vol_snags':           'sum',
                    'vol_sub_merch':        'sum',
                    'vol_forest_residues': 'sum',
                    'prov_carbon':         'sum',
                    'tc':                  'sum'})
              .reset_index())
        # Add the total volume column #
        df['tot_vol'] = df.Vol_Merch + df.Vol_SubMerch + df.Vol_Snags
        # Add the Measurement_type #
        df['measurement_type'] = 'M'
        # Return result #
        return df

    #-------------------------------------------------------------------------#
    @property_cached
    def provided_area(self):
        """
        Load area disturbed from the table 'TblDistIndicators'

        Columns are:    ['DistIndID', 'SPUID', 'dist_type_id', 'time_step', 'user_defd_class_set_id',
                         'LandClassID', 'kf2', 'kf3', 'kf4', 'kf5', 'kf6', 'dist_area',
                         'DistProduct']

        This corresponds to the "provided" aspect of "expected_provided" harvest and contains
        only areas ('A').
        """
        # Load #
        dist_indicators  = self.parent.database['TblDistIndicators']
        disturbance_type = self.parent.database['tblDisturbanceType']
        # First ungrouped #
        ungrouped = (dist_indicators
                     .set_index('dist_type_id')
                     .join(disturbance_type.set_index('dist_type_id'))
                     .reset_index()
                     .set_index('user_defd_class_set_id')
                     .join(self.parent.classifiers.set_index('user_defd_class_set_id'))
                     .reset_index())
        # The index we will use for grouping #
        index = ['dist_type_id',
                 'dist_type_name',
                 'time_step',
                 'status',
                 'forest_type',
                 'region',
                 'management_type',
                 'management_strategy',
                 'conifers_broadleaves']
        # Compute #
        df = (ungrouped
              .set_index('dist_type_id')
              .groupby(index)
              .agg({'dist_area':    'sum',
                    'DistProduct': 'sum'})
              .reset_index())
        # Add the Measurement_type #
        df['measurement_type'] = 'A'
        # Return result #
        return df

    #-------------------------------------------------------------------------#
    @property_cached
    def disturbances(self):
        """
        This corresponds to the "expected" aspect of "expected_provided" harvest
        and will contain both Area ('A') and Mass ('M'). The units for 'M' are
        tons of carbon and hectares for 'A'.

        This method Prepares the disturbance table for joining operations with
        harvest tables.

        It could be a good idea to check why some countries have dist_type_name as int64
        and others have dist_type_name as object.

        Columns are: ['status', 'forest_type', 'region', 'management_type',
                      'management_strategy', 'climatic_unit', 'conifers_broadleaves',
                      'using_id', 'sw_start', 'sw_end', 'hw_start', 'hw_end', 'last_dist_id',
                      'efficiency', 'sort_type', 'measurement_type', 'amount', 'dist_type_id',
                      'time_step'],
        """
        # Load disturbances table from excel file #
        df = self.parent.parent.input_data.disturbance_events
        # Rename classifier columns _1, _2, _3 to forest_type, region, etc. #
        df = df.rename(columns = self.parent.classifiers_mapping)
        # C.f the PL column problem #
        df = df.rename(columns = {'natural_forest_region': 'management_type'})
        # This column also need to be manually renamed #
        df = df.rename(columns = {'step': 'time_step'})
        # For joining with other data frames, DistType has to be of dtype object not int64 #
        df['dist_type_id'] = df['dist_type_id'].astype(str)
        # Remove columns that are not really used #
        df = df.drop(columns=[c for c in df.columns if c.startswith("Min") or c.startswith("Max")])
        # Remove slashes #
        df = df.rename(columns=lambda n:n.replace('/','_'))
        # dist_type_id is actually dist_type_name #
        df = df.rename(columns = {'dist_type_id': 'dist_type_name'})
        # Return result #
        return df

    #-------------------------------------------------------------------------#
    def compute_expected_provided(self, provided, meas_type, prov_col_name):
        """
        Compares the amount of harvest requested in the disturbance tables (an input to the simulation)
        to the amount of harvest actually performed by the model (extracted from the flux indicator table).

        Based on Roberto's query `Harvest_expected_provided` visible in the original calibration database.

        In this method we transform *df*, by adding:

         - Years instead of TimeSteps
         - Rows where expected and provided are both zero removed
         - An extra column indicating the delta between expected and provided
         - An extra column indicating the disturbance description sentence.
        """
        # Columns we will keep #
        index = ['time_step',
                 'dist_type_name',
                 'forest_type',
                 'measurement_type',
                 #'region',
                 #'management_type',
                 #'management_strategy',
                 #'conifers_broadleaves'
                 #'status'
                ]
        # Load #
        expected = self.disturbances
        # Filter for measurement type #
        selector = expected['measurement_type'] == meas_type
        expected = expected.loc[selector].copy()
        # Aggregate expected #
        expected = (expected
                    .groupby(index)
                    .agg({'amount': 'sum'})
                    .reset_index())
        # Aggregate provided #
        provided = (provided
                    .groupby(index)
                    .agg({prov_col_name: 'sum'})
                    .reset_index())
        # Index columns to join disturbances and harvest check #
        # Set the same index on both data frames #
        provided = provided.set_index(index)
        expected = expected.set_index(index)
        # Do the join #
        df = (provided.join(expected, how='outer')).reset_index()
        # Sum two columns #
        df = df.rename(columns = {'amount':      'expected',
                                  prov_col_name: 'provided'})
        # Remove rows where both expected and provided are zero #
        selector = (df['expected'] == 0.0) & (df['provided'] == 0.0)
        df = df.loc[~selector].copy()
        # Add the delta column #
        df['delta'] = (df.expected - df.provided)
        # Add year and remove TimeStep #
        df['year'] = self.parent.parent.country.timestep_to_year(df['time_step'])
        df = df.drop('time_step', axis=1)
        # Get the disturbances full name from their number #
        dist_type = (self.parent.parent.input_data.disturbance_types
                     .rename(columns={'disturbance_type_id': 'dist_type_name',
                                                   'name': 'DistDescription'})
                     .set_index('dist_type_name'))
        # Add a column named 'DistDescription' #
        df = (df.set_index('dist_type_name')
                .join(dist_type)
                .reset_index())
        # Only if we are in the calibration scenario #
        if self.parent.parent.scenario.short_name == 'calibration':
            # Patch the harvest data frame to stop at the simulation year #
            selector = df['year'] <= self.parent.parent.country.base_year
            df = df.loc[selector].copy()
        # Return result #
        return df

    #-------------------------------------------------------------------------#
    @property_cached
    def exp_prov_by_volume(self):
        """
        "Measurement_type == 'M'"

        Columns are: ['status', 'time_step', 'dist_type_name', 'forest_type', 'management_type',
                      'management_strategy', 'expected', 'provided', 'measurement_type',
                      'DistDescription']
        """
        # Compute #
        df = self.provided_volume
        return self.compute_expected_provided(df, 'M', 'prov_carbon')

    #-------------------------------------------------------------------------#
    @property_cached
    def exp_prov_by_area(self):
        """
        Same as above but for "Measurement_type == 'A'"

        Columns are: ['status', 'time_step', 'dist_type_name', 'forest_type', 'management_type',
                      'management_strategy', 'expected', 'provided', 'measurement_type',
                      'DistDescription']
        """
        # Compute #
        df = self.provided_area
        return self.compute_expected_provided(df, 'A', 'dist_area')

    #-------------------------------------------------------------------------#
    def check_exp_prov(self):
        """Check that the total quantities of area and volume are conserved."""
        # Load #
        area = self.exp_prov_by_area
        volu = self.exp_prov_by_volume
        # Check expected #
        processed = volu['expected'].sum() + area['expected'].sum()
        raw       = self.parent.parent.input_data.disturbance_events['amount'].sum()
        numpy.testing.assert_allclose(processed, raw, rtol=1e-03)
        # Check provided area #
        processed = area['provided'].sum()
        raw       = self.parent.database['TblDistIndicators']['dist_area'].sum()
        numpy.testing.assert_allclose(processed, raw, rtol=1e-03)
        # Check provided volume #
        processed = volu['provided'].sum()
        raw       = self.parent.database['TblFluxIndicators']
        raw       = raw['soft_production'].sum() + raw['hard_production'].sum() + raw['dom_production'].sum()
        numpy.testing.assert_allclose(processed, raw, rtol=1e-03)