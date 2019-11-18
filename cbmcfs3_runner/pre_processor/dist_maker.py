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
import pandas

# First party modules #
from plumbing.cache import property_cached

# Internal modules #

###############################################################################
class DisturbanceMaker(object):
    """
    Will create new disturbances for the simulation period.
    """

    def __init__(self, parent):
        # Default attributes #
        self.parent  = parent
        self.runner  = parent.parent
        self.country = parent.parent.country

    # Artificially increase or decrease the demand by this ratio #
    irw_artificial_ratio = 1.0
    fw_artificial_ratio  = 1.0

    @property
    def dist_irw(self):
        """
        Allocate industrial round-wood disturbances.
        Also, calculate the fuel wood amount generated by these
        industrial round wood disturbances. See columns:

            ['owc_amount_from_irw' and 'snag_amount_from_irw']

        Columns are:

            ['hwp', 'year_text', 'value_ob', 'year_max', 'year', 'step',
             'forest_type', 'status', 'management_type', 'management_strategy',
             'conifers_broadleaves', 'dist_type_name', 'sort_type', 'efficiency',
             'min_age', 'max_age', 'min_since_last', 'max_since_last', 'regen_delay',
             'reset_age', 'wd', 'owc_perc', 'snag_perc', 'man_nat',
             'stock_available', 'stock_tot', 'prop', 'density', 'amount_m3',
             'owc_amount_from_irw', 'snag_amount_from_irw']

        Allocation:
            Join the GFTM demand and the allocation table.
            This will generate a much longer table, containing different
            combinations of classifiers and disturbance ids for each HWP and year.
        """
        # Load #
        harv_prop = self.country.silviculture.harvest_proportion
        gftm_irw  = self.country.demand.gftm_irw.copy()
        # Artificially increase demand for scenarios #
        gftm_irw['value_ob'] = gftm_irw['value_ob'] * self.irw_artificial_ratio
        gftm_irw['value_ub'] = gftm_irw['value_ub'] * self.irw_artificial_ratio
        # Artificially increase demand for scenarios #
        df['value'] = df['value'] * self.fw_artificial_ratio
        # Join #
        df = gftm_irw.left_join(harv_prop, 'hwp')
        # Calculate the disturbance amount based on the proportion
        # Each proportion is different for each combination of classifiers.
        df['amount_m3'] = df['value_ob'] * df['prop']
        # Calculate the 'owc_perc' and 'snag_perc' generating fuel wood
        # TODO adjust these OWC and snag proportions which were defined in
        # terms of tons of carbon and are now in terms of m3
        df['owc_amount_from_irw']  = df['amount_m3'] * df['owc_perc']
        df['snag_amount_from_irw'] = df['amount_m3'] * df['snag_perc']
        return df

    @property
    def dist_fw(self):
        """
        Calculate the fuel wood disturbance amount based on the proportion
        Deducing the amount of owc and snag generated by the FW disturbances
        Also deduce the fuel wood amount generated by IRW disturbances.
        """
        # Load #
        dist_irw = self.dist_irw
        gftm_fw  = self.country.demand.gftm_fw.copy()

        # Artificially increase demand for scenarios #
        gftm_fw['value_ob'] = gftm_fw['value_ob'] * self.fw_artificial_ratio
        gftm_fw['value_ub'] = gftm_fw['value_ub'] * self.fw_artificial_ratio

        # Aggregate fuel wood amount generated by IRW disturbances
        # on the classifier and coniferous broadleaves index
        # Also keep the db coefficient
        # In case there is no silviculture.treatments for fuel wood
        index = ['step', 'conifers_broadleaves']
        dist_irw_fw = (dist_irw
                       .groupby(index)
                       .agg({'owc_amount_from_irw':sum,
                             'snag_amount_from_irw':sum})
                       .reset_index())
        # Rename con, broad to hwp column containing fw_c, fw_b, used later as a join index
        dist_irw_fw['hwp'] = dist_irw_fw['conifers_broadleaves'].replace(['Con', 'Broad'], ['fw_c', 'fw_b'])
        dist_irw_fw = dist_irw_fw.drop(columns='conifers_broadleaves')

        # Join aggregated outcome of the IRW harvest
        # on combinations of year and the hwp classifier
        df = gftm_fw.left_join(dist_irw_fw, ['hwp', 'step'])

        # Now use this table to generate fuel wood disturbances
        # The suffix will serve to re-use some of the IRW columns
        # in case of missing FW harvest proportion data
        harvest_proportion = self.country.silviculture.harvest_proportion
        df = (df
              .set_index('hwp')
              .join(harvest_proportion.set_index('hwp'), lsuffix='_irw')
              .reset_index())

        # Deduce the amount of owc and snag already generated by the IRW disturbances
        df['amount_m3_minus_irw'] = df['value_ob'] - df['owc_amount_from_irw'] - df['snag_amount_from_irw']

        # If amount_m3_minus_irw is negative change it to zero
        df['amount_m3_minus_irw'] =  [a if a > 0 else 0 for a in df['amount_m3_minus_irw']]

        # Calculate the disturbance amount based on the proportion
        # Deducing the amount of owc and snag generated by the FW disturbances
        df['amount_m3'] = df['amount_m3_minus_irw'] * df['prop'] / (1 + df['owc_perc'] + df['snag_perc'])

        # Then remove negative amounts from the disturbance table
        # TODO: make this a threshold maybe equal to 200 or some higher value?
        df = df.query("amount_m3>0").copy()
        return df

    @property
    def dist_irw_converted(self):
        """
        Convert industrial round wood disturbances
        weight in tonnes and  of carbon to m3 over bark
        to the demand volume in m3 over bark for each year.
        i.e. the requested demand from the economic model.
        """
        # Load #
        df = self.dist_irw
        # Group #
        index = ['step', 'conifers_broadleaves']
        df = (df.groupby(index)
                .agg({'amount_m3': sum})
                .reset_index())
        # Add products column #
        df['hwp'] = (df['conifers_broadleaves'].replace(['Con', 'Broad'], ['irw_c', 'irw_b']))
        # outer join to capture all demand values,
        # even if step or con_broad is not present in dist anymore
        df = df.outer_join(self.country.demand.gftm_irw, ['step', 'hwp']
)       # Return #
        return df

    def check_dist_irw(self):
        """
        Check that the industrial round wood disturbances
        weight in tonnes of carbon correspond to the demand
        volume in m^3 over bark, for each year.
        """
        # Load #
        df = self.dist_irw_converted
        # Assert that these values are all close to each other #
        all_close = numpy.testing.assert_allclose
        all_close(df['amount_m3'], df['value_ob'], rtol=1e-03)

    @property
    def dist_fw_converted(self):
        """
        Check that the fuel wood disturbance weight in tonnes of carbon
        correspond to the demand volume in m3 over bark for each year.
        i.e. the requested demand from the economic model.
        Note the difference to irw, we include branches and snags
        in the calculation here.
        Since the fuel wood harvest may already be satisfied by the
        branches and snags of the irw harvest alone. We only check
        that the amount generated by the disturbance is greater than
        the requested amount.
        """
        # Load #
        irw_agg = self.dist_irw

        # Assemble the fuel wood amount generated by the IRW disturbances #
        columns_of_interest = ['step', 'conifers_broadleaves', 'amount_m3']
        irw_agg['amount_m3'] = (irw_agg['owc_amount_from_irw']
                                + irw_agg['snag_amount_from_irw'])
        irw_agg = irw_agg[columns_of_interest]

        # Assemble the fuel wood amount generated by the fuel wood disturbances #
        df = self.dist_fw
        df['amount_m3'] = (df['amount_m3'] * (1 + df['snag_perc'] + df['owc_perc']))
        df = df[columns_of_interest]

        # Concatenate the fuel wood and irw tables #
        df = pandas.concat([df, irw_agg])

        # Aggregate based on the step and con broad classifier #
        index = ['step', 'conifers_broadleaves']
        df = (df.groupby(index)
                .agg({'amount_m3':sum})
                .reset_index())

        # Add products column #
        df['hwp'] = df['conifers_broadleaves'].replace(['Con', 'Broad'], ['fw_c', 'fw_b'])

        # Outer join to capture all demand values,
        # even if step or con_broad is not present in dist anymore
        df = df.outer_join(self.country.demand.gftm_fw, ['step', 'hwp'])

        # Compare amount #
        df['diff'] = df['amount_m3'] - df['value_ob']
        df['diff_prop'] = df['diff'] / df['value_ob']

        # Return #
        return df

    def check_dist_fw(self):
        """Assert that the difference is strictly positive or close to zero
        In other words, it is ok if there is a higher fuel wood volume generated
        By industrial round wood disturbance diff>0
        But it's not ok if there is a smaller fuel wood volume.
        That would mean there is an issue with fuel wood disturbance generation
        """
        df = self.dist_fw_converted
        assert (df['diff_prop'] > -0.02).all()

    cols_always_minus_one = [
        'last_dist_id', 'min_tot_biom_c', 'max_tot_biom_c', 'min_merch_soft_biom_c',
        'max_merch_soft_biom_c', 'min_merch_hard_biom_c', 'max_merch_hard_biom_c',
        'min_tot_stem_snag_c', 'max_tot_stem_snag_c', 'min_tot_soft_stem_snag_c',
        'max_tot_soft_stem_snag_c', 'min_tot_hard_stem_snag_c',
        'max_tot_hard_stem_snag_c', 'min_tot_merch_stem_snag_c',
        'max_tot_merch_stem_snag_c', 'min_tot_merch_soft_stem_snag_c',
        'max_tot_merch_soft_stem_snag_c', 'min_tot_merch_hard_stem_snag_c',
        'max_tot_merch_hard_stem_snag_c'
    ]

    def add_constants(self, df):
        """Add constant values expected by CBM_CFS3
        See file "silviculture.sas" """
        # Copy #
        df = df.copy()
        # Special cases #
        df['using_id']          = False
        df['measurement_type']  = 'M'
        # Set a lot of them to one #
        for col in self.cols_always_minus_one: df[col] = -1
        # Return #
        return df

    @property
    def demand_to_dist(self):
        """
        Disturbance allocation proceeds by steps.
        Round wood disturbances are allocated first,
        During the model run, CBM will select eligible stands.
        On an eligible stand, CBM will transfer wood
        from the merchantable biomass pool to the product pool.
        On the same stand there are some branches and snags.
        These branches and snags are also harvested for fuel-wood products
        which generate a first amount of fuel wood harvest.
        We deduce this amount from the fuel wood demand.
        Then we allocate the remaining amount of fuel wood demand.
        This time taking into account the full
        merchantable biomass + branches and snags.
        Conifers and broadleaves are independent in their processing.

        The demands matrix comes in this format:

           year     _7   prod    volume
           1999  Broad    IRW  121400.0
           1999    Con    IRW  120300.0
           1999  Broad     FW   16900.0
           1999    Con     FW    1100.0

        We take only the round-wood lines:

           year     _7   prod    volume
           1999  Broad    IRW  121400.0
           1999    Con    IRW  120300.0

        We will join with an allocation matrix
        giving the proportion of merchantable biomass to harvest :

            prod   prop  dist _1  _2  _3     _7 Snag_Perc OWC_Perc  Min_Age Max_Age    db
            IRW    0.9      7 AA  MT  AR  Broad      0.02     0.14       20      80  0.40
            IRW    0.1     12 BB  MT  AR  Broad      0.03     0.12       20      80  0.45
            IRW    0.5     29 ZZ  MT  AR    Con      0.02     0.14       20      80  0.58
            IRW    0.5      3 YY  MT  AR    Con      0.03     0.12       20      80  0.58

        We keep 'Snag_Perc' and 'OWC_Perc' separated because
        we want to be able to switch one or the other on or off.

        Result of the join:

            prod   prop  dist   _1  _2  _3    _7 Snag_Perc OWC_Perc     volume  year    db
            IRW    0.9      7  AA  MT  AR  Broad      0.02     0.14   121400.0  1999  0.40
            IRW    0.1     12  BB  MT  AR  Broad      0.03     0.12   121400.0  1999  0.45
            IRW    0.5     29  ZZ  MT  AR    Con      0.02     0.14   120300.0  1999  0.58
            IRW    0.5      3  YY  MT  AR    Con      0.03     0.12   120300.0  1999  0.58

        We convert disturbance volumes from m3 over bark to tonnes of carbon.
        TODO : correct these values based on code update

            df['value_tc'] = df['value_ob'] * df['density'] / 2

        Then we add the column: IRW_amount = prop * value_tc
        As well as the:          owc_amount_from_irw  = IRW_amount * OWC_Perc
                                 snag_amount_from_irw = IRW_amount * Snag_perc

            prod   prop  dist  _1  _2  _3    _7 Snag_Perc OWC_Perc IRW_amount  owc_amount_from_irw  snag_amount_from_irw  year
            IRW    0.9      7 AA  MT  AR  Broad      0.02     0.14     110000       5000  1999
            IRW    0.1     12 BB  MT  AR  Broad      0.03     0.12       1000         90  1999
            IRW    0.5     29 ZZ  MT  AR    Con      0.02     0.14      60000       4000  1999
            IRW    0.5      3 YY  MT  AR    Con      0.03     0.12       6000        600  1999

        Here we can check that sum(IRW_amount) == sum(value_tc)
        By doing df.groupby('year', '_7').agg({'fw_amount': 'sum'}) we get:

                _7 FW_amount  year
             Broad      5090  1999
               Con      4600  1999

        Now we take the original demand matrix for FW and join with the matrix above.
        Finally we subtract what is already produced:

        We set: volume = volume - FW_amount

           year     _7   prod    volume   FW_amount  year
           1999  Broad     FW   11423.0        5090  1999
           1999    Con     FW   -3045.0        4600  1999

        Check that volume has to always be positive. Otherwise set it to zero.
        Now we will join again with an allocation matrix but that has "FW" instead "IRW":

            prod  prop  dist  _1  _2  _3    _7 Snag_Perc OWC_Perc
            FW    0.8      7  AA  MT  AR Broad      0.01     0.14
            FW    0.2     12  BB  MT  AR Broad      0.03     0.12
            FW    0.6     29  ZZ  MT  AR   Con      0.02     0.14
            FW    0.4      3  YY  MT  AR   Con      0.03     0.12

        Result of the join:

            prod  prop  dist  _1  _2  _3    _7 Snag_Perc OWC_Perc   volume  year
            FW    0.8      7  AA  MT  AR Broad      0.01     0.14  11423.0  1999
            FW    0.2     12  BB  MT  AR Broad      0.03     0.12  11423.0  1999
            FW    0.6     29  ZZ  MT  AR   Con      0.02     0.14      0.0  1999
            FW    0.4      3  YY  MT  AR   Con      0.03     0.12      0.0  1999

        Then we add the column:  FW_amount = prop * volume / (1 + Snag_Perc + OWC_Perc)
        We do this since the fuel wood harvest also generates extra fuel wood.

            prod  prop dist  _1  _2  _3    _7 Snag_Perc OWC_Perc FW_amount  year
            FW    0.8     7 AA  MT  AR  Broad      0.01     0.14      5000  1999
            FW    0.2    12 BB  MT  AR  Broad      0.03     0.12        90  1999
            FW    0.6    29 ZZ  MT  AR    Con      0.02     0.14      4000  1999
            FW    0.4     3 YY  MT  AR    Con      0.03     0.12       600  1999

        We can check that FW_amount is equal to the sum of demand / (1 + Snag_Perc + OWC_Perc)
        Finally we combine the dataframe (4) and (7) with both columns becoming amount.

            prod dist  _1  _2  _3    _7 Snag_Perc OWC_Perc    amount  year
            FW      7 AA  MT  AR  Broad      0.01     0.14      5000  1999
            FW     12 BB  MT  AR  Broad      0.03     0.12        90  1999
            FW     29 ZZ  MT  AR    Con      0.02     0.14      4000  1999
            FW      3 YY  MT  AR    Con      0.03     0.12       600  1999
            IRW     7 AA  MT  AR  Broad      0.02     0.14    110000  1999
            IRW    12 BB  MT  AR  Broad      0.03     0.12      1000  1999
            IRW    29 ZZ  MT  AR    Con      0.02     0.14     60000  1999
            IRW     3 YY  MT  AR    Con      0.03     0.12      6000  1999

        We have dropped 'prop'
        To create disturbances we are still missing "SWStart", "SWEnd", "HWStart", "HWEnd".
        In this case SW == Conifer and HW == Broad. Both values are always the same.
        """
        # Check the correspondence between
        # disturbance tables expressed in tonnes of carbon
        # and the original demand volumes in cubic meters of wood over bark.
        self.check_dist_irw()
        self.check_dist_fw()

        # Allocation:
        # Concatenate IRW and FW disturbance tables
        # Keep only the columns of interest for disturbances
        silv_classif = ['status', 'forest_type', 'management_type', 'management_strategy',
                        'conifers_broadleaves']
        columns_of_interest = ['dist_type_name', 'sort_type', 'efficiency', 'min_age',
                               'max_age', 'min_since_last', 'max_since_last', 'regen_delay',
                               'reset_age', 'man_nat', 'amount_m3', 'step', 'density']
        df = pandas.concat([self.dist_irw[silv_classif + columns_of_interest],
                            self.dist_fw[ silv_classif + columns_of_interest]])

        # Convert amount_m3 from m3 to tonnes of carbon
        # 'density' is the volumetric mass density in t/m3 of the given species
        # Tons of dry matter are converted to tons of carbon by applying
        # a 0.5 conversion factor
        # TODO rename amount to amount_tc, this needs to be done also in
        #  orig data for the historical period because these
        #  disturbances will be concatenated to the historical disturbances
        df['amount'] = df['amount_m3'] * df['density'] / 2

        # Drop columns unused by the CBM input format #
        df = df.drop(columns = ['density', 'amount_m3'])

        # Add and re-order columns
        # These classifiers are ignored when interacting with the economic model only
        missing_classif = set(self.country.classifiers.names) - set(silv_classif)
        for col in missing_classif: df[col] = '?'

        # Min age max age are distinguished by hardwood and soft wood #
        df['sw_start'] = df['min_age']
        df['sw_end']   = df['max_age']
        df['hw_start'] = df['min_age']
        df['hw_end']   = df['max_age']

        # Rename #
        df = df.rename(columns = {'min_since_last': 'min_since_last_dist',
                                  'max_since_last': 'max_since_last_dist'})

        # Add constant values required by CBM #
        df = self.add_constants(df)

        # Check consistency of Sort_Type with measurement type
        # TODO move this to check any disturbances just before SIT is called
        df_random = df.query('sort_type==6')
        msg = ("Random sort type: 6 not allowed with disturbances expressed in terms "
               "of Measurement Type 'M' merchantable carbon. \n"
               "The issue is present for dist_type_name: %s \n"
               "CBM error in this case is "
               "Error: 'Illegal target type for RANDOM sort in timestep...'")

        # Sanity check #
        if len(df_random) > 0:
            raise Exception(msg % (df_random['dist_type_name'].unique()))

        # Return #
        return df

    @property_cached
    def df(self):
        """Append the new disturbances to the old disturbances."""
        # Load data #
        dist_past   = self.parent.disturbance_filter.df
        dist_future = self.demand_to_dist
        # Rearrange columns accordingly so they match #
        dist_columns = list(dist_past)
        dist_future = dist_future[dist_columns]
        # Concatenate #
        df = pandas.concat([dist_past, dist_future])
        # Return #
        return df

    @property_cached
    def df_auto_allocation(self):
        """Aggregate disturbances on the species, management type and
        management strategy classifiers for the `auto_allocation` scenario."""
        # Take reference #
        df = self.df
        # Index #
        index = ['status', 'conifers_broadleaves', 'dist_type_name', 'step']
        columns_to_keep = ['efficiency']
        # Group and aggregate #
        df = (df
              .groupby(index + columns_to_keep)
              .agg({'amount':    sum,
                    'sw_start':  min,
                    'sw_end':    max,
                    'hw_start':  min,
                    'hw_end':    max,
                    'sort_type': lambda x: x.value_counts().index[0]})
              .reset_index())
        # Return #
        return df

    @property_cached
    def df_max_supply(self):
        """
        """
        pass
