import sqlite3

from partbox.database import Database


def test_initialize_creates_schema_and_defaults(tmp_path):
    db = Database(tmp_path / "partbox.db")
    db.initialize()

    tables = {
        row[0]
        for row in db.connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
    }
    assert {
        "components",
        "purchase_lines",
        "stock_movements",
        "import_batches",
        "fee_lines",
        "settings",
        "comparison_components",
        "projects",
        "project_components",
        "project_bom_lines",
    } <= tables
    assert db.get_setting("allow_negative_stock") == "0"
    assert db.get_setting("low_stock_threshold") == "5"
    assert db.connection.execute("PRAGMA foreign_keys").fetchone()[0] == 1


def test_initialize_migrates_existing_projects_table_for_bom_fields(tmp_path):
    path = tmp_path / "legacy.db"
    connection = sqlite3.connect(path)
    connection.execute(
        "CREATE TABLE projects(id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE, "
        "created_at TEXT NOT NULL, updated_at TEXT NOT NULL)"
    )
    connection.commit(); connection.close()

    db = Database(path)
    db.initialize()

    columns = {row[1] for row in db.connection.execute("PRAGMA table_info(projects)")}
    assert {"inactive", "build_quantity", "source_bom_path"} <= columns
    tables = {row[0] for row in db.connection.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    )}
    assert {"comparison_components", "project_bom_lines"} <= tables


def test_transaction_rolls_back_on_error(tmp_path):
    db = Database(tmp_path / "partbox.db")
    db.initialize()

    try:
        with db.transaction() as connection:
            connection.execute(
                "INSERT INTO settings(key, value) VALUES('temporary', 'yes')"
            )
            raise RuntimeError("stop")
    except RuntimeError:
        pass

    assert db.get_setting("temporary") is None
