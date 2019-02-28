# Built-in modules #
import re
from StringIO import StringIO

# Third party modules #
import pandas

# First party modules #
from autopaths.auto_paths import AutoPaths
from plumbing.cache import property_cached

# Internal modules #

###############################################################################
class SilvicultureParser(object):
    """
    This class takes the file "silviculture.sas" as input and generate a CSV
    from it.
    This should somehow detail 'dist_events_scenario.csv'.
    """

    all_paths = """
    /orig/silviculture.sas
    """

    def __init__(self, parent):
        # Default attributes #
        self.parent = parent
        # Automatically access paths based on a string of many subpaths #
        self.paths = AutoPaths(self.parent.parent.data_dir, self.all_paths)

    def __call__(self):
        pass

    @property_cached
    def df(self):
        """Search the SAS file for the CSV that is hidden inside and return a
        pandas DataFrame. Yes, the SAS file has a CSV hidden somewhere in the middle."""
        # Search #
        query = '\n {3}input (.*?);\n {3}datalines;\n\n(.*?)\n;\nrun'
        column_names, all_rows = re.findall(query, self.paths.sas.contents, re.DOTALL)[0]
        # Format #
        all_rows     = StringIO(all_rows)
        column_names = [name.strip('$') for name in column_names.split()]
        # Parse into table #
        df = pandas.read_csv(all_rows, names=column_names, delim_whitespace=True)
        # Return #
        return df

    @property_cached
    def csv(self):
        """Create a new disturbance table with ``df` by matching columns
        and filling empty cells with information from the original disturbances
        (match rows that have the same classifiers together)."""
        pass