# Built-in modules #

# Third party modules #
import pandas

# First party modules #
from plumbing.cache import property_cached
from autopaths.auto_paths import AutoPaths
from plumbing.databases.access_database import AccessDatabase

# Internal modules #

###############################################################################
class MiddleProcessor(object):
    """
    Will modify the access database after its creation by SIT but before its
    usage by CBM.
    """

    all_paths = """
    /output/cbm_formatted_db/project.mdb
    """

    def __init__(self, parent):
        # Default attributes #
        self.parent = parent
        # Directories #
        self.paths = AutoPaths(self.parent.data_dir, self.all_paths)

    def __call__(self):
        self.extend_simulation(100)

    @property_cached
    def project_database(self):
        return AccessDatabase(self.paths.project_mdb)

    def extend_simulation(self, num_steps):
        """Will extend the simulation by num_steps time steps so that it runs extra
        years without any disturbances."""
        # Log message #
        self.parent.log.info("Adjusting the simulation length with extra %i steps" % num_steps)
        # Get the current end timestep of the siumlation #
        query = "SELECT RunLength FROM tblRunTableDetails"
        current_run_length = self.project_database.cursor.execute(query).fetchone()[0]
        # Update the value in the database #
        updated_run_length = current_run_length + num_steps
        query = "UPDATE tblRunTableDetails SET tblRunTableDetails.RunLength = %i"
        query = query % updated_run_length
        # Execute the query #
        self.project_database.cursor.execute(query)
        self.project_database.cursor.commit()
