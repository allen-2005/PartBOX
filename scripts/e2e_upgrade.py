from __future__ import annotations

import sys
from pathlib import Path

from partbox.database import Database
from partbox.importer import parse_statement
from partbox.projects import ProjectService
from partbox.services import ImportService, InventoryService


def main(database_path: Path, files: list[Path]) -> int:
    db = Database(database_path); db.initialize()
    importer = ImportService(db)
    importer.commit(importer.preview(files, parser=parse_statement), {})
    inventory = InventoryService(db)
    projects = ProjectService(db)
    project_id = projects.create_project("端到端验证")
    component = inventory.list_components()[0]
    projects.add_components(project_id, [component["id"]])
    projects.set_quantity(project_id, component["id"], 2)
    first = projects.sync(project_id)
    repeated = projects.sync(project_id)
    projects.set_quantity(project_id, component["id"], 1)
    returned = projects.sync(project_id)
    assert first.stock_delta == -2 and repeated.changed_lines == 0 and returned.stock_delta == 1
    assert len(projects.operation_history(project_id)) == 2
    db.close()

    reopened = Database(database_path); reopened.initialize()
    assert ProjectService(reopened).list_projects()[0]["name"] == "端到端验证"
    assert len(ProjectService(reopened).operation_history(project_id)) == 2
    assert InventoryService(reopened).stats()["orders"] > 0
    reopened.close()
    print("E2E upgrade verification passed: material statements, project delta sync, reopen persistence.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(Path(sys.argv[1]), [Path(value) for value in sys.argv[2:]]))
