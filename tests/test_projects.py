from decimal import Decimal

import pytest

from partbox.database import Database
from partbox.projects import ProjectError, ProjectService


@pytest.fixture
def project_env(tmp_path):
    db = Database(tmp_path / "projects.db")
    db.initialize()
    now = "2026-08-14 00:00:00"
    ids = []
    for index, (code, stock) in enumerate((("C1", 20), ("C2", 3)), start=1):
        ids.append(db.connection.execute(
            "INSERT INTO components(product_code,product_type,product_name,model,package,brand,current_stock,latest_unit_price,created_at,updated_at) "
            "VALUES(?,?,?,?,?,?,?,?,?,?) RETURNING id",
            (code, "贴片电阻", f"{code} name", f"{code}M", "0603", "品牌", stock, index * 0.25, now, now),
        ).fetchone()[0])
    db.connection.commit()
    return db, ProjectService(db), ids


def test_database_migrates_project_tables(project_env):
    db, _, _ = project_env
    tables = {row[0] for row in db.connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"projects", "project_components", "project_operations", "project_operation_lines"} <= tables


def test_database_migrates_project_reference_designator(project_env):
    db, _, _ = project_env

    columns = {
        row[1] for row in db.connection.execute("PRAGMA table_info(project_components)")
    }

    assert "reference_designator" in columns


def test_database_migrates_old_project_components_without_losing_data(tmp_path):
    path = tmp_path / "old-projects.db"
    old_db = Database(path)
    old_db.initialize()
    old_db.connection.executescript(
        "INSERT INTO components(product_code,created_at,updated_at) "
        "VALUES('C1','2026-01-01','2026-01-01');"
        "INSERT INTO projects(id,name,created_at,updated_at) "
        "VALUES(1,'旧项目','2026-01-01','2026-01-01');"
        "DROP TABLE project_components;"
        "CREATE TABLE project_components("
        "project_id INTEGER NOT NULL,component_id INTEGER NOT NULL,"
        "quantity INTEGER NOT NULL DEFAULT 1,synced_quantity INTEGER NOT NULL DEFAULT 0,"
        "created_at TEXT NOT NULL,updated_at TEXT NOT NULL,"
        "PRIMARY KEY(project_id,component_id));"
        "INSERT INTO project_components "
        "VALUES(1,1,7,3,'2026-01-01','2026-01-01');"
    )
    old_db.connection.commit(); old_db.close()

    db = Database(path)
    db.initialize()

    row = db.connection.execute(
        "SELECT quantity,synced_quantity,reference_designator "
        "FROM project_components WHERE project_id=1 AND component_id=1"
    ).fetchone()
    assert tuple(row) == (7, 3, "")


def test_project_name_validation_and_component_deduplication(project_env):
    _, service, ids = project_env
    with pytest.raises(ProjectError):
        service.create_project("  ")
    project_id = service.create_project("开源电源")
    with pytest.raises(ProjectError):
        service.create_project("开源电源")
    assert service.add_components(project_id, [ids[0], ids[0]]) == 1
    rows = service.list_components(project_id)
    assert len(rows) == 1
    assert rows[0]["project_quantity"] == 1
    assert rows[0]["product_type"] == "贴片电阻"
    with pytest.raises(ProjectError):
        service.set_quantity(project_id, ids[0], 0)


def test_save_configuration_updates_only_project_quantities(project_env):
    db, service, ids = project_env
    project_id = service.create_project("BOM 配置")
    service.add_components(project_id, ids)
    stock_before = [row[0] for row in db.connection.execute(
        "SELECT current_stock FROM components ORDER BY id"
    )]

    service.save_configuration(project_id, {ids[0]: 3, ids[1]: 5})

    rows = {row["id"]: row for row in service.list_components(project_id)}
    assert [rows[component_id]["project_quantity"] for component_id in ids] == [3, 5]
    assert [rows[component_id]["synced_quantity"] for component_id in ids] == [0, 0]
    assert [row[0] for row in db.connection.execute(
        "SELECT current_stock FROM components ORDER BY id"
    )] == stock_before
    assert db.connection.execute("SELECT COUNT(*) FROM stock_movements").fetchone()[0] == 0
    assert service.operation_history(project_id) == []


def test_save_configuration_updates_designators_without_inventory(project_env):
    db, service, ids = project_env
    project_id = service.create_project("位号配置")
    service.add_components(project_id, ids)
    stock_before = [row[0] for row in db.connection.execute(
        "SELECT current_stock FROM components ORDER BY id"
    )]

    service.save_configuration(
        project_id,
        {ids[0]: 2, ids[1]: 3},
        {ids[0]: "R1", ids[1]: "R2,R3"},
    )

    rows = {row["id"]: row for row in service.list_components(project_id)}
    assert rows[ids[0]]["reference_designator"] == "R1"
    assert rows[ids[1]]["reference_designator"] == "R2,R3"
    assert [rows[component_id]["project_quantity"] for component_id in ids] == [2, 3]
    assert [rows[component_id]["synced_quantity"] for component_id in ids] == [0, 0]
    assert [row[0] for row in db.connection.execute(
        "SELECT current_stock FROM components ORDER BY id"
    )] == stock_before
    assert db.connection.execute("SELECT COUNT(*) FROM stock_movements").fetchone()[0] == 0
    assert service.operation_history(project_id) == []


def test_save_configuration_rejects_partial_or_invalid_mapping_atomically(project_env):
    _, service, ids = project_env
    project_id = service.create_project("原子保存")
    service.add_components(project_id, ids)

    with pytest.raises(ProjectError):
        service.save_configuration(project_id, {ids[0]: 7})
    with pytest.raises(ProjectError):
        service.save_configuration(project_id, {ids[0]: 7, ids[1]: 0})
    with pytest.raises(ProjectError):
        service.save_configuration(project_id, {ids[0]: 7, ids[1]: 1.5})
    with pytest.raises(ProjectError):
        service.save_configuration(project_id, {ids[0]: 7, ids[1]: Decimal("1.5")})

    assert [row["project_quantity"] for row in service.list_components(project_id)] == [1, 1]


def test_remove_components_returns_only_synced_quantity_and_records_return(project_env):
    db, service, ids = project_env
    project_id = service.create_project("删除回补")
    service.add_components(project_id, ids)
    service.set_quantity(project_id, ids[0], 5)
    service.set_quantity(project_id, ids[1], 2)
    service.sync(project_id)
    service.set_quantity(project_id, ids[0], 9)  # 未同步编辑不能多退库存

    result = service.remove_components(project_id, [ids[0]])

    assert result.changed_lines == 1
    assert result.stock_delta == 5
    assert [row[0] for row in db.connection.execute(
        "SELECT current_stock FROM components ORDER BY id"
    )] == [20, 1]
    assert [row["id"] for row in service.list_components(project_id)] == [ids[1]]
    line = service.operation_history(project_id, lines=True)[0]
    assert line["movement_type"] == "project_return"
    assert line["quantity_before"] == 5
    assert line["quantity_after"] == 0


def test_remove_unsynced_component_creates_no_empty_operation(project_env):
    db, service, ids = project_env
    project_id = service.create_project("未同步删除")
    service.add_components(project_id, [ids[0]])

    result = service.remove_components(project_id, [ids[0]])

    assert result.operation_id is None
    assert result.stock_delta == 0
    assert db.connection.execute("SELECT COUNT(*) FROM project_operations").fetchone()[0] == 0


def test_project_sync_uses_delta_and_records_out_and_return(project_env):
    db, service, ids = project_env
    project_id = service.create_project("复刻项目")
    service.add_components(project_id, ids[:1])
    service.set_quantity(project_id, ids[0], 5)

    first = service.sync(project_id)
    assert first.changed_lines == 1
    assert first.stock_delta == -5
    assert db.connection.execute("SELECT current_stock FROM components WHERE id=?", (ids[0],)).fetchone()[0] == 15

    repeated = service.sync(project_id)
    assert repeated.changed_lines == 0
    assert db.connection.execute("SELECT COUNT(*) FROM stock_movements").fetchone()[0] == 1

    service.set_quantity(project_id, ids[0], 3)
    returned = service.sync(project_id)
    assert returned.stock_delta == 2
    assert db.connection.execute("SELECT current_stock FROM components WHERE id=?", (ids[0],)).fetchone()[0] == 17
    assert [row["movement_type"] for row in service.operation_history(project_id, lines=True)] == [
        "project_return", "project_out"
    ]


def test_project_sync_is_atomic_when_any_component_is_short(project_env):
    db, service, ids = project_env
    project_id = service.create_project("库存不足")
    service.add_components(project_id, ids)
    service.set_quantity(project_id, ids[0], 2)
    service.set_quantity(project_id, ids[1], 5)

    with pytest.raises(ProjectError, match="库存不足"):
        service.sync(project_id)

    stocks = [row[0] for row in db.connection.execute("SELECT current_stock FROM components ORDER BY id")]
    assert stocks == [20, 3]
    assert db.connection.execute("SELECT COUNT(*) FROM stock_movements").fetchone()[0] == 0
    assert db.connection.execute("SELECT COUNT(*) FROM project_operations").fetchone()[0] == 0


def test_project_rename_delete_and_history(project_env):
    _, service, ids = project_env
    project_id = service.create_project("旧名")
    service.rename_project(project_id, "新名")
    assert service.list_projects()[0]["name"] == "新名"
    service.add_components(project_id, [ids[0]])
    service.set_quantity(project_id, ids[0], 1)
    with pytest.raises(ProjectError, match="未同步"):
        service.delete_project(project_id)
    service.sync(project_id)
    assert service.operation_history(project_id)[0]["changed_lines"] == 1
    service.delete_project(project_id)
    assert service.list_projects() == []
    assert service.operation_history(project_id)[0]["changed_lines"] == 1
