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
from plumbing.dataframes import string_to_df

# Internal modules #

###############################################################################
class Silviculture(object):
    """
    This class gives access to information contained in the file
    "silviculture.sas".

    The silviculture treatments table is used to transform economic demand
    into disturbances. A list of disturbances specifies in which set of stands
    to harvest at which time step.

    The economic model provides future demand volumes distinguished only
    by the coniferous/broadleaves classifier.

    To allocate the harvest across disturbance
    types (clear cut, thinning) and additional classifiers (forest type,
    management type, management strategy) we use a proportion method based
    on the historical inventory and yield curve within a country.

    In essence we will harvest proportionally to what is found in a country.
    In terms of volume, if a country has 90% of firs, we will harvest 90% there.
    Of course this is within the harvestable range, we will exclude trees that are
    too young.
    """

    all_paths = """
    /orig/silv_treatments.csv
    /orig/harvest_corr_fact.csv
    """

    # Ignore some disturbances that are of type "natural"
    # when calculating the harvest proportion.
    # This is the same for all countries.
    dist_to_ignore = ['5', '7', '21', 'DISTID1', 'DISTID5', 'DISTID7',
                      'DISTID9b_H', 'DISTID9c_H']

    def __init__(self, parent):
        # Default attributes #
        self.parent = parent
        # Automatically access paths based on a string of many subpaths #
        self.paths = AutoPaths(self.parent.data_dir, self.all_paths)

    @property_cached
    def treatments(self):
        """Load the CSV that is 'silv_treatments.csv'.
        The column "Man_Nat" represents either 'Man-made disturbance'
        or a Natural disturbance.
        'Perc_merch_biom_rem' is redundant with 'Dist_ID' and simply shows
        the percent of thinning.
        """
        df = pandas.read_csv(str(self.paths.treatments))
        # Dist_Type_ID can be given as either a numeric or a character variable
        # convert to string to prevent issues when merging and filtering
        df['Dist_Type_ID'] = df['Dist_Type_ID'].astype(str)
        # Rename the classifier columns to full names #
        df = df.rename(columns = self.parent.classifiers.mapping)
        # Return #
        return df

    @property_cached
    def corr_fact(self):
        """Load the CSV that is 'harvest_corr_fact.csv'."""
        return pandas.read_csv(str(self.paths.corr_fact))

    @property_cached
    def pool_allocation(self):
        """
        Allocation of harvested pools to different
        co-products, based on the main harvested wood product.

        The merchantable volume 'Tot_V_Merch' always goes
        to the product that is harvested.
        The sub merchantable and snag volume 'Tot_V_SubMerch' and 'Tot_V_Snags'
        go to the corresponding fuel wood pool, either coniferous or broadleaved.

        * IRW stands for Industrial Round Wood
        * FW stands for Fuel Wood
        * C stands for coniferous
        * B stands for broadleaved
        """
        s = """     pool  |   HWP  |  co_product
             Tot_V_Merch  |  FW_C  |  FW_C
          Tot_V_SubMerch  |  FW_C  |  FW_C
             Tot_V_Snags  |  FW_C  |  FW_C
             Tot_V_Merch  | IRW_C  | IRW_C
          Tot_V_SubMerch  | IRW_C  |  FW_C
             Tot_V_Snags  | IRW_C  |  FW_C
             Tot_V_Merch  |  FW_B  |  FW_B
          Tot_V_SubMerch  |  FW_B  |  FW_B
             Tot_V_Snags  |  FW_B  |  FW_B
             Tot_V_Merch  | IRW_B  | IRW_B
          Tot_V_SubMerch  | IRW_B  |  FW_B
             Tot_V_Snags  | IRW_B  |  FW_B
        """
        # Convert string to data frame #
        return string_to_df(s)

    @property_cached
    def stock_based_on_yield(self):
        """
        Calculate the theoretical stock based on the inventory area
        by age class multiplied by the corresponding volume-per-hectare for
        each age class producing "stock" in terms of m^3.

        Columns are: ['status', 'forest_type', 'region', 'management_type',
                      'management_strategy', 'climatic_unit',
                      'conifers_bradleaves', 'age_class', 'Area', 'volume',
                      'stock', 'age']
        """
        # Load data frames #
        inventory     = self.parent.orig_data.inventory
        h_yields_long = self.parent.orig_data.historical_yields_long
        # Index #
        index = ['status', 'forest_type', 'region', 'management_type',
                 'management_strategy', 'climatic_unit', 'conifers_bradleaves',
                 'age_class']
        # Join #
        df = (inventory
              .set_index(index)
              .join(h_yields_long.set_index(index))
              .reset_index())
        # Compute stock #
        df['stock'] = df['Area'] * df['volume']
        # We are not interested in these columns #
        cols_to_drop = ['UsingID', 'Age', 'Delay', 'UNFCCCL', 'HistDist', 'LastDist', 'Sp']
        df = df.drop(columns=cols_to_drop)
        # Compute the actual age #
        df['age'] = df['age_class'] * 10
        # Return #
        return df

    @property_cached
    def stock_available_by_age(self):
        """Calculate the stock available based on the harvest proportion
        in the silviculture_treatments table and multiplied by a correction factor.

        Note: the harvest proportion in the silviculture_treatments table should be
        the same as the proportion going to products in the disturbance matrix.
        See script "scripts/checking/check_harvest_prop.py".

        The status classifier does not have the same value between the data frames
        silviculture and stock_based_on_yield.

        Columns are: ['forest_type', 'management_type', 'management_strategy',
                      'conifers_bradleaves', 'status', 'region', 'climatic_unit',
                      'age_class', 'Area', 'volume', 'stock', 'age',
                      'Dist_Type_ID', 'Sort_Type', 'Efficency', 'Min_age',
                      'Max_age', 'Min_since_last', 'Max_since_last', 'HWP',
                      'RegenDelay', 'ResetAge', 'Percent', 'WD', 'OWC_Perc',
                      'Snag_Perc', 'Perc_Merch_Biom_rem', 'Man_Nat', 'corr_fact',
                      'stock_available']

        Min_since_last represents the minimum age since the last disturbance for
        a new disturbance to be applied.
        """
        # Join with correction factor #
        silviculture = (self.treatments
                        .set_index('forest_type')
                        .join(self.corr_fact
                              .set_index('forest_type'))
                        .reset_index())
        # Check that status is unique #
        if len(silviculture['status'].unique()) > 1:
            msg  = "Silviculture status is not unique. %s"
            msg += "Please check the merge with stock_based_on_yield"
            raise Exception(msg % silviculture['status'].unique())
        # As it's unique we can drop it, because there is also "status" in stock_based_on_yield #
        silviculture = silviculture.drop(columns=['status'])
        # Join only on these classifiers #
        index = ['forest_type', 'management_type', 'management_strategy', 'conifers_bradleaves']
        # Join #
        df = (self.stock_based_on_yield
              .set_index(index)
              .join(silviculture.set_index(index))
              .reset_index()
              .query('Min_age < age & age < Max_age')
              .query('stock > 0')
              .copy())
        # Compute the stock available #
        df['stock_available'] = (df['stock']
                                 * df['corr_fact']
                                 * df['Perc_Merch_Biom_rem']
                                 / df['Min_since_last'])
        # Return #
        return df

    @property_cached
    def stock_available_agg(self):
        """Aggregate stock_available_by_age and sum the stock available over
        all age classes. Some natural disturbances are ignored.

        Columns are: ['forest_type', 'management_type', 'management_strategy',
                      'conifers_bradleaves', 'Dist_Type_ID', 'stock_available',
                      'HWP', 'status']
        """
        # Index #
        index = ['forest_type', 'management_type', 'management_strategy',
                 'conifers_bradleaves', 'Dist_Type_ID']
        # Aggregate #
        df = (self.stock_available_by_age
              .query("Dist_Type_ID not in @self.dist_to_ignore")
              .groupby(index)
              .agg({'stock_available': 'sum'})
              .reset_index())
        # Add the harvested wood products column #
        silviculture = self.treatments[index + ['HWP']]
        # Join #
        df = (df
              .set_index(index)
              .join(silviculture.set_index(index))
              .reset_index())
        # Setting status to 'For' might not be necessary.
        # Just here as a reminder that status is homogeneous at the moment.
        # Harvest proportion calculation has to be changed once we deal with
        # forests available for thinning only status='th'
        # vs forests available for both thinning and clear cut status='CC'.
        df['status'] = 'For'
        # Return #
        return df

    @property_cached
    def harvest_proportion(self):
        """To allocate the harvest across
        disturbance types (clear cut, thinning)
        and additional classifiers (forest type, management type,
        management strategy) we use a proportion based
        on the historical inventory and yield curve.

        The harvest proportion is calculated from the stock available
        by combining two information sources:

            * The inventory provides an area by forest type and age class
            * The growth/yield curve provides a volume by forest type and age class

        We multiply those two values to obtain a
        "stock = area * volume" for each particular classifiers
        and age class combination.

        The stock available is then calculated based
        on the percentage moved in the disturbance matrix
        (also available in the silviculture table Perc_Merch_Biom_rem)
        and on an empirical harvest correction factor,
        for each disturbance and combination of classifiers:

            stock available = stock * percentage harvested

        by the disturbance * correction factor.

        The data frame below is the allocation of harvest
        along the classifiers used in self.stock_available_agg:

            ['forest_type', 'management_type', 'management_strategy',
             'conifers_bradleaves', 'Dist_Type_ID' ].

        The proportion is based on the available stock by
        harvested wood products (HWP) category.

        Columns are: ['forest_type', 'management_type', 'management_strategy',
                      'conifers_bradleaves', 'Dist_Type_ID', 'stock_available',
                      'HWP', 'status', 'stock_tot', 'prop']
        """
        # Load dataframe #
        df = self.stock_available_agg.copy()
        # Add column stock_tot #
        df['stock_tot'] = df.groupby(['HWP'])['stock_available'].transform('sum')
        # Add column prop #
        df['prop']      = df['stock_available'] / df['stock_tot']
        # Drop redundant total column #
        df.drop(columns=['stock_tot'])
        # Sort for readability #
        df = df.sort_values(by=['HWP'], ascending=False)
        # Return
        return df

    @property_cached
    def harvest_proportion_legacy(self):
        """Allocation of harvest along different classifiers
        with time step included and redundant proportions for each time step.
        This table has a legacy structure based on Roberto's SAS code
        between "data IRW_C_Const;set HWP_Const_IRW_FW;"
        and     "data Stock_Prop_C_Const;*Proportion based on available Stock;"

        Columns are: ['step', 'HWP', 'country', 'year', 'volume', 'forest_type',
                      'management_type', 'management_strategy',
                      'conifers_bradleaves', 'Dist_Type_ID',
                      'stock_available', 'status', 'stock_tot', 'prop']
        """
        # Join silv_stock on the HWP field.
        # This expands the data frame for each possible combinations of HWP.
        demand_hist = self.parent.demand.historical
        hwp_const_irw_fw = (demand_hist
                            .set_index('HWP')
                            .join(self.stock_available_agg.set_index('HWP'))
                            .reset_index())
        # Aggregate #
        index = ['step', 'HWP']
        stock_t_step_const = (hwp_const_irw_fw
                              .groupby(index)
                              .agg({'stock_available': 'sum'})
                              .reset_index())
        # Rename #
        stock_t_step_const = stock_t_step_const.rename(columns={'stock_available' : 'stock_tot'})
        # Join back the total data frame to the original data frame
        # to calculate the proportion of volume available amongst the total available volume
        # for each management_type, management_strategy, forest_type, disturbance_type_id
        # There probably is another way
        # to calculate the proportion by using "apply" over a group-by window.
        # Join #
        df = (hwp_const_irw_fw
              .set_index(index)
              .join(stock_t_step_const.set_index(index))
              .reset_index())
        # Compute proportion #
        df['prop'] = df['stock_available'] / df['stock_tot']
        # Return #
        return df
