"""
A test script to visualize the tail of the runner log for each country in one
summary markdown document.

Typically you would run this file from a command line like this:

     ipython.exe -i -- /deploy/cbm_runner/scripts/compile_logs.py
"""

# Built-in modules #

# Third party modules #
import pbs
# First party modules #

# Internal modules #
from cbm_runner.all_countries import all_runners, cbm_data_repos

###############################################################################
summary = cbm_data_repos + "logs_summary.md"
summary.open(mode='w')
summary.handle.write("# Summary of all log file tails\n\n")
summary.handle.writelines(r.summary for r in all_runners)
summary.close()

###############################################################################
#pandoc = pbs.Command("pandoc")
#pandoc('-s', '-o', summary.replace_extension('pdf'), summary)