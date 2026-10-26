from pathlib import Path

from PySide6.QtWidgets import QLabel

from partbox.database import Database
from partbox.services import DataService, StockService
from partbox.ui.aux_pages import HistoryPage, ImportsPage, SettingsPage
import pytest


def test_auxiliary_pages_expose_distinct_workspace_identities(qtbot, tmp_path):
    db = Database(tmp_path / "aux-theme.db")
    db.initialize()
    data = DataService(db)
    pages = (
        HistoryPage(data, StockService(db)),
        ImportsPage(data),
        SettingsPage(data, tmp_path / "backups"),
    )
    for page in pages:
        qtbot.addWidget(page)
    assert [page.objectName() for page in pages] == [
        "historyPage", "importsPage", "settingsPage"
    ]
    for page in pages:
        title = page.findChild(QLabel, "pageTitle")
        assert title is not None
        assert title.styleSheet() == ""
        margins = page.layout().contentsMargins()
        assert (margins.left(), margins.top(), margins.right(), margins.bottom()) == (16, 16, 16, 16)


def test_backup_export_and_reset_use_requested_paths(tmp_path):
    db = Database(tmp_path / "partbox.db"); db.initialize()
    now = "2026-01-01 00:00:00"
    db.connection.execute(
        "INSERT INTO components(product_code,product_name,current_stock,unit,created_at,updated_at) VALUES('C1','电阻',10,'个',?,?)",
        (now, now),
    ); db.connection.commit()
    service = DataService(db)

    backup = service.backup(tmp_path / "backups")
    assert backup.exists() and backup.stat().st_size > 0
    exported = service.export_inventory(tmp_path / "库存.xlsx")
    assert exported.exists()
    service.reset_database()
    assert db.connection.execute("SELECT COUNT(*) FROM components").fetchone()[0] == 0


def test_history_and_import_batches_are_queryable(tmp_path):
    db = Database(tmp_path / "partbox.db"); db.initialize()
    now = "2026-01-01 00:00:00"
    component_id = db.connection.execute(
        "INSERT INTO components(product_code,product_name,current_stock,created_at,updated_at) VALUES('C1','电阻',10,?,?) RETURNING id",
        (now, now),
    ).fetchone()[0]; db.connection.commit()
    StockService(db).adjust(component_id, -2, "manual_out", "项目")
    data = DataService(db)
    assert data.stock_history()[0]["notes"] == "项目"
    assert data.import_batches() == []
    assert data.purchase_lines() == []


def test_restore_rejects_invalid_database_without_damaging_current_data(tmp_path):
    db = Database(tmp_path / "partbox.db"); db.initialize()
    now = "2026-01-01 00:00:00"
    db.connection.execute("INSERT INTO components(product_code,created_at,updated_at) VALUES('C1',?,?)", (now, now)); db.connection.commit()
    invalid = tmp_path / "invalid.db"; invalid.write_text("not sqlite", encoding="utf-8")
    with pytest.raises(ValueError):
        DataService(db).restore(invalid)
    assert db.connection.execute("SELECT product_code FROM components").fetchone()[0] == "C1"


def test_reset_database_clears_project_records_before_inventory(tmp_path):
    from partbox.projects import ProjectService
    db = Database(tmp_path / "reset-project.db"); db.initialize(); now = "2026-01-01 00:00:00"
    component_id = db.connection.execute(
        "INSERT INTO components(product_code,current_stock,created_at,updated_at) VALUES('C1',10,?,?) RETURNING id",
        (now, now),
    ).fetchone()[0]; db.connection.commit()
    projects = ProjectService(db); project_id = projects.create_project("P")
    projects.add_components(project_id, [component_id]); projects.set_quantity(project_id, component_id, 1); projects.sync(project_id)
    DataService(db).reset_database()
    for table in (
        "project_operation_lines", "project_operations", "project_bom_lines",
        "project_components", "projects", "comparison_components",
        "stock_movements", "components",
    ):
        assert db.connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] == 0


def test_restore_old_backup_runs_current_schema_migrations(tmp_path):
    old = tmp_path / "old.db"
    old_db = Database(old); old_db.initialize()
    old_db.connection.executescript(
        "DROP TABLE project_operation_lines;"
        "DROP TABLE project_operations;"
        "DROP TABLE project_components;"
        "DROP TABLE projects;"
    ); old_db.connection.commit(); old_db.close()
    db = Database(tmp_path / "current.db"); db.initialize()
    DataService(db).restore(old)
    tables = {row[0] for row in db.connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {
        "projects", "project_components", "project_bom_lines", "project_operations",
        "project_operation_lines", "comparison_components",
    } <= tables
