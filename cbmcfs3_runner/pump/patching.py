#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Written by Lucas Sinclair and Paul Rougieux.

JRC biomass Project.
Unit D1 Bioeconomy.
"""

# Built-in modules #

# First party modules #

# Third party modules #
import pandas

# Internal modules #

###############################################################################
def flexible_join(first, other, on, how=None, lsuffix='', rsuffix=''):
    """Implement a common join pattern with pandas set_index()
    on both data frames followed by a reset_index() at the end."""
    # Check if `on` is a set #
    if isinstance(on, set): on = list(on)
    # Set indexes #
    first  = first.set_index(on)
    other  = other.set_index(on)
    # TODO check the data types (dtypes) of all the index columns
    #  are matching on both sides of the join.
    result = first.join(other, how=how, lsuffix=lsuffix, rsuffix=rsuffix)
    result = result.reset_index()
    # Return #
    return result

###############################################################################
def left_join(*args, **kwargs):
    """This method is patched onto pandas.DataFrame for convenience."""
    return flexible_join(*args, **kwargs, how='left')

def right_join(*args, **kwargs):
    """This method is patched onto pandas.DataFrame for convenience."""
    return flexible_join(*args, **kwargs, how='right')

def inner_join(*args, **kwargs):
    """This method is patched onto pandas.DataFrame for convenience."""
    return flexible_join(*args, **kwargs, how='inner')

def outer_join(*args, **kwargs):
    """This method is patched onto pandas.DataFrame for convenience."""
    return flexible_join(*args, **kwargs, how='outer')

###############################################################################
# Add a nice method to pandas.DataFrame objects #
pandas.DataFrame.left_join  = left_join
pandas.DataFrame.right_join = right_join
pandas.DataFrame.inner_join = inner_join
pandas.DataFrame.outer_join = outer_join

