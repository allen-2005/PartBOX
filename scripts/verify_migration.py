import sys
from pathlib import Path

from partbox.database import Database


database = Database(Path(sys.argv[1]))
database.initialize()
tables = {
    row[0]
    for row in database.connection.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    )
}
required = {"projects", "project_components", "project_operations", "project_operation_lines"}
assert required <= tables
database.close()
print("Existing database schema migration passed.")
