#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Written by Lucas Sinclair and Paul Rougieux.

JRC biomass Project.
Unit D1 Bioeconomy.
"""

###############################################################################
def reshape_yields_long(yields_wide):
    """
    Columns are:

    ['status', 'forest_type', 'region', 'management_type',
     'management_strategy', 'climatic_unit', 'conifers_broadleaves', 'sp',
     'age_class', 'volume']
     """
    # Index #
    index = ['status', 'forest_type', 'region', 'management_type',
             'management_strategy', 'climatic_unit', 'conifers_broadleaves',
             'sp']
    # Add classifier 8 for the specific case of Bulgaria
    if 'yield_tables' in yields_wide.columns:
        index += ['yield_tables']
    # Melt #
    df = yields_wide.melt(id_vars    = index,
                          var_name   = "age_class",
                          value_name = "volume")
    # Remove suffixes and keep just the number #
    df['age_class'] = df['age_class'].str.lstrip("vol").astype('int')
    # Return #
    return df

###############################################################################
def left_join(first, other, on):
    """ Implement a common left join pattern with pandas set_index()
    on both data frames followed by a reset_index()
    """
    first  = first.set_index(on)
    other  = other.set_index(on)
    result = first.join(other)
    result = result.reset_index()
    return result
