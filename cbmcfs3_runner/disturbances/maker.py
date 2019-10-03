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
from autopaths.auto_paths import AutoPaths
from plumbing.cache import property_cached

# Internal modules #

###############################################################################
class DisturbanceMaker(object):
    """
    Will create new disturbances for the simulation period
    and modify the file input file "disturbance_events.csv".
    """

    all_paths = """
    /input/csv/disturbance_events_filtered.csv
    /input/csv/disturbance_events_combined.csv
    """
    name_of_dist_future = 'empty_dist'

    def __init__(self, parent):
        # Default attributes #
        self.parent  = parent
        self.country = parent.country
        # Directories #
        self.paths = AutoPaths(self.parent.data_dir, self.all_paths)

    def __call__(self):
        self.add_events()


    @property_cached
    def disturbance_events_raw(self):
        """ Note: self.country.orig_data.disturbance_events was modified
        after we loaded it, we added additional variables.
        To get the un-modified column order, we reload the original
        "disturbance_events.csv" without extra columns.
        We only rename the classifier columns"""
        df = pandas.read_csv(self.paths.disturbance_events_filtered)
        df = df.rename(columns = self.country.classifiers.mapping)
        # Change column types to match those of generated future disturbances
        df['step'] = df['step'].astype(int)
        df['dist_type_name'] = df['dist_type_name'].astype(str)
        return df

    @property
    def empty_dist(self):
        """empty disturbance table used to add as a default
        for the historical scenario"""
        return pandas.DataFrame()


    @property
    def dist_irw(self):
        """
        Allocate industrial roundwood disturbances.
        Also calculate the fuel wood amount generated
        by these Industrial Round wood disturbances, columns:
        'owc_amount_from_IRW' and 'snag_amount_from_IRW'

        Columns are:
        ['hwp', 'year_text', 'value_ob', 'year_max', 'year', 'step',
         'forest_type', 'status', 'management_type', 'management_strategy',
         'conifers_broadleaves', 'dist_type_name', 'sort_type', 'efficiency',
         'min_age', 'max_age', 'min_since_last', 'max_since_last', 'regen_delay',
         'reset_age', 'wd', 'owc_perc', 'snag_perc', 'man_nat',
         'stock_available', 'stock_tot', 'prop', 'db', 'value_tc', 'amount',
         'owc_amount_from_IRW', 'snag_amount_from_IRW']
        """
        # Allocation:
        # Join the GFTM demand and the allocation table
        # This will generate a much longer table, containing different
        # combinations of classifiers and disturbance ids for each HWP and year.
        df = (self.country.demand.gftm_irw
             .set_index('hwp')
             .join(self.country.silviculture.harvest_proportion.set_index('hwp'))
             .reset_index())
        # Convert value_ob from m3 to tonnes of C
        # 'db' is the volumeric mass density in t/m3 of the given species
        # Tons of dry matter are converted to C applying a 0.5 conversion factor
        df['value_tc'] = df['value_ob'] * df['db'] / 2
        # Calculate the disturbance amount based on the proportion
        # Each proportion is different for each combination of classifiers.
        df['amount'] = df['value_tc'] * df['prop']
        # Calculate the 'owc_perc' and 'snag_perc' generating fuel wood
        df['owc_amount_from_IRW'] = df['amount'] * df['owc_perc']
        df['snag_amount_from_IRW'] = df['amount'] * df['snag_perc']
        return df


    @property
    def dist_fw(self):
        """
        Calculate the fuel wood disturbance amount based on the proportion
        Deducing the amout of owc and snag generated by the FW disturbances
        Also deduce the fuel wood amount generated by IRW disturbances.
        """        
        # Aggregate fuel wood amount generated by IRW disturbances
        # on the classifier and coniferous broadleaves index
        # Also keep the db coefficient
        # In case there is no silviculture.treatments for fuel wood
        index = ['step', 'conifers_broadleaves']
        dist_irw_fw = (self.dist_irw
                       .groupby(index)
                       .agg({'owc_amount_from_IRW':sum,
                             'snag_amount_from_IRW':sum})
                       .reset_index())
        # Rename con, broad to hwp column containing fw_c, fw_b, used later as a join index
        dist_irw_fw['hwp'] = dist_irw_fw['conifers_broadleaves'].replace(['Con', 'Broad'], ['fw_c', 'fw_b'])
        dist_irw_fw = dist_irw_fw.drop(columns='conifers_broadleaves')
        
        # Join aggreagated outcome of the IRW harvest
        # on combinations of year and the hwp classifier
        index = ['hwp', 'step']
        df = (self.country.demand.gftm_fw
                   .set_index(index)
                   .join(dist_irw_fw.set_index(index))
                   .reset_index())
        
        # Now use this table to generate fuel wood disturbances
        # The suffix will serve to re-use some of the IRW columns
        # in case of missing FW harvest proportion data
        harvest_proportion = self.country.silviculture.harvest_proportion
        df = (df
                   .set_index('hwp')
                   .join(harvest_proportion.set_index('hwp'), lsuffix='_irw')
                   .reset_index())
        
        # Deal with missing information from the harvest_proportion table
        # Retrieve db values from the coefficients table
        coefficients = self.country.coefficients[['forest_type','db']]
        df = (df
                   .set_index('forest_type')
                   .join(coefficients.set_index('forest_type'),lsuffix='_2')
                   .reset_index())

        # Convert value_ob from m3 to tonnes of carbon
        df['value_tc'] = df['value_ob'] * df['db_2'] / 2
        # Deduce the amount of owc and snag already generated by the IRW disturbances
        df['value_tc'] = df['value_tc'] - df['owc_amount_from_IRW'] - df['snag_amount_from_IRW']
        
        # If value_tc is negative change it to zero
        df['value_tc'] =  [a if a > 0 else 0 for a in df['value_tc']]
        
        # Calculate the disturbance amount based on the proportion
        # Deducing the amout of owc and snag generated by the FW disturbances
        df['amount'] = df['value_tc'] * df['prop'] / (1 + df['owc_perc'] + df['snag_perc'])
        
        # Then remove negative amounts from the disturbance table
        # TODO: make this a threshold maybe equal to 200 or some higher value?
        df = df.query("amount>0").copy()
        return df

    def check_dist_irw(self):
        """Check that the industrial round wood disturbances
        weight in tonnes of carbon correspond
        to the demand volume in m3 over bark for each year.
        i.e. the requested demand from the economic model"""
        df = self.dist_irw
        # density different by species
        df['amount_m3'] = df['amount'] / df['db'] * 2
        index = ['step', 'conifers_broadleaves']
        df = (df
                        .groupby(index)
                        .agg({'amount_m3':sum})
                        .reset_index())
        df['hwp'] = (df['conifers_broadleaves']
                     .replace(['Con', 'Broad'], ['irw_c', 'irw_b']))
        index = ['step', 'hwp']
        df = (df
              .set_index(index)
              # outer join to capture all demand values,
              # even if step or con_broad is not present in dist anymore
              .join(self.country.demand.gftm_irw.set_index(index), how='outer')
              .reset_index())
        # Assert that these values are close
        numpy.testing.assert_allclose(df['amount_m3'], df['value_ob'],
                                      rtol=1e-03)

    def check_dist_fw(self):
        """Chek that the fuel wood disturbance weight in tonnes of carbon
        correspond to the demand volume in m3 over bark for each year.
        i.e. the requested demand from the economic model.
        Note the diffence to irw, we incluse branches and snags
        in the calculation here.
        Since the fuel wood harvest may already be satisfied by the
        branches and snags of the irw harvest alone. We only check
        that the amount generated by the disturbance is greater than
        the requested amount.
        """
        # Assemble the fuel wood amount generated by the IRW disturbances
        columns_of_interest = ['step', 'conifers_broadleaves', 'dist_amount_m3']
        irw_agg = self.dist_irw
        irw_agg['amount_total'] = (irw_agg['owc_amount_from_IRW']
                                           + irw_agg['snag_amount_from_IRW'])
        irw_agg['dist_amount_m3'] = irw_agg['amount_total'] / irw_agg['db'] * 2
        irw_agg = irw_agg[columns_of_interest]
        
        # Assemble the fuel wood amount generated by the fuel wood disturbances
        df = self.dist_fw
        df['amount_total'] = (df['amount'] * (1 + df['snag_perc'] + df['owc_perc']))
        df['dist_amount_m3'] = df['amount_total'] / df['db'] * 2
        df = df[columns_of_interest]
        
        # Concatenate the fuel wood and irw tables
        df = pandas.concat([df, irw_agg])
        # display(df.query("step==18"))
        # Aggregate based on the step and con broad classifier
        index = ['step', 'conifers_broadleaves']
        df = (df
             .groupby(index)
             .agg({'dist_amount_m3':sum})
             .reset_index())
        
        # Join with the demand
        index = ['step', 'hwp']
        df['hwp'] = df['conifers_broadleaves'].replace(['Con', 'Broad'], ['fw_c', 'fw_b'])
        df = (df
              .set_index(index)
              # outer join to capture all demand values,
              # even if step or con_broad is not present in dist anymore
              .join(self.country.demand.gftm_fw.set_index(index),  how='outer')
              .reset_index())
        # Compare amount 
        df['diff'] = df['dist_amount_m3'] - df['value_ob']
        df['diff_prop'] = df['diff'] / df['value_ob']
        # Assert that the difference is strictly positive or close to zero
        assert (df['diff_prop']>-0.02).all()

    @property
    def demand_to_dist(self):
        """
        Disturbance allocation proceeds by steps.
        Roundwood disturbances are allocated first,
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
        Conifers and Broadleaves are independent in their processing.

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
        giving the proportion of merchantablebiomass to harvest :

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

            df['value_tc'] = df['value_ob'] * df['db'] / 2

        Then we add the column: IRW_amount = prop * value_tc
        As well as the:          owc_amount_from_IRW  = IRW_amount * OWC_Perc
                                 snag_amount_from_IRW = IRW_amount * Snag_perc

            prod   prop  dist  _1  _2  _3    _7 Snag_Perc OWC_Perc IRW_amount  owc_amount_from_IRW  snag_amount_from_IRW  year
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
        # Check the correspondance between
        # disturbance tables expressed in tonnnes of carbon
        # and the original demand volumes in cubic meters of wood over bark.
        self.check_dist_irw()
        self.check_dist_fw()
        # Allocation:
        # Concatenate IRW and FW disturbance tables
        # Keep only the columns of interest for distubances
        columns_of_interest = ['status', 'forest_type', 'management_type', 'management_strategy',
                               'conifers_broadleaves', 'dist_type_name',
                               'sort_type', 'efficiency',
                               'min_age', 'max_age', 'min_since_last', 'max_since_last', 'regen_delay',
                               'reset_age', 'man_nat', 'amount', 'step']
        df = pandas.concat([self.dist_irw[columns_of_interest],
                            self.dist_fw[columns_of_interest]])
        # Add and re-order columns
        # These classifiers are ignored when interacting with the economic model only
        df['climatic_unit'] = '?'
        df['region']        = '?'

        # Min age max age are distinguished by hardwood and soft wood
        df['sw_start'] = df['min_age']
        df['sw_end']   = df['max_age']
        df['hw_start'] = df['min_age']
        df['hw_end']   = df['max_age']

        # Rename
        df = df.rename(columns = {'min_since_last': 'min_since_last_dist',
                                  'max_since_last': 'max_since_last_dist'})

        # Constant values expected by CBM_CFS3
        # See file "silviculture.sas"
        df['using_id']          = False
        df['measurement_type']  = 'M'
        df['last_dist_id']                   = -1
        df['min_tot_biom_c']                 = -1
        df['max_tot_biom_c']                 = -1
        df['min_merch_soft_biom_c']          = -1
        df['max_merch_soft_biom_c']          = -1
        df['min_merch_hard_biom_c']          = -1
        df['max_merch_hard_biom_c']          = -1
        df['min_tot_stem_snag_c']            = -1
        df['max_tot_stem_snag_c']            = -1
        df['min_tot_soft_stem_snag_c']       = -1
        df['max_tot_soft_stem_snag_c']       = -1
        df['min_tot_hard_stem_snag_c']       = -1
        df['max_tot_hard_stem_snag_c']       = -1
        df['min_tot_merch_stem_snag_c']      = -1
        df['max_tot_merch_stem_snag_c']      = -1
        df['min_tot_merch_soft_stem_snag_c'] = -1
        df['max_tot_merch_soft_stem_snag_c'] = -1
        df['min_tot_merch_hard_stem_snag_c'] = -1
        df['max_tot_merch_hard_stem_snag_c'] = -1
        # Check consistency of Sort_Type with measurement type
        # TODO move this to check any disturbances just before SIT is called
        df_random = df.query('sort_type==6')
        msg = "Random sort type: 6 not allowed with disturbances expressed in terms "
        msg += "of Measurement Type 'M' merchantable carbon. \n"
        msg += "The issue is present for dist_type_name: %s \n"
        msg += "CBM error in this case is "
        msg += "Error: 'Illegal target type for RANDOM sort in timestep...'"
        if len(df_random) > 0:
            raise Exception(msg % (df_random['dist_type_name'].unique()))
        # Rearrange columns according to the raw "disturbance_events.csv" file
        dist_calib_columns = list(self.disturbance_events_raw.columns)
        # Return #
        return df[dist_calib_columns]

    def add_events(self):
        """Append the new disturbances to the disturbance file."""
        # Load data
        dist_past = self.disturbance_events_raw
        dist_future = getattr(self, self.name_of_dist_future)
        # Concatenate
        df = pandas.concat([dist_past, dist_future])
        # Write the result
        df.to_csv(str(self.paths.disturbance_events_combined), index=False)

