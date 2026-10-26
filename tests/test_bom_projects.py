import pytest

from partbox.bom import BomLine
from partbox.database import Database
from partbox.projects import ProjectError, ProjectService


def row(component_id=1, allocated=4, required=10, purchase=6, status="exact"):
    return {
        "line": BomLine(
            source_row=2,
            source_values={"位号": "R1", "参数": "100k", "数量": 10},
            quantity=10,
            designator="R1",
            product_code="C100",
            product_type="贴片电阻",
            description="100kΩ ±5%",
            model="R100K",
            package="0603",
            brand="FOJAN",
        ),
        "required_quantity": required,
        "match_status": status,
        "matched_component_id": component_id,
        "allocated_quantity": allocated,
        "purchase_quantity": purchase,
    }


def seed_component(db: Database, stock=4) -> int:
    now = "2026-08-27 10:00:00"
    component_id = int(db.connection.execute(
        "INSERT INTO components(product_code,product_name,current_stock,created_at,updated_at) "
        "VALUES('C100','100k电阻',?,?,?) RETURNING id",
        (stock, now, now),
    ).fetchone()[0])
    db.connection.commit()
    return component_id


def test_create_project_from_bom_preserves_full_lines_and_build_quantity(tmp_path):
    db = Database(tmp_path / "bom-project.db"); db.initialize()
    component_id = seed_component(db)
    service = ProjectService(db)
    matched = row(component_id=component_id)
    unmatched = row(component_id=None, allocated=0, required=2, purchase=2, status="unmatched")
    unmatched["line"] = BomLine(
        source_row=3, source_values={"位号": "U1", "数量": 1}, quantity=1,
        designator="U1", product_code="C999", product_type="芯片", description="MCU",
    )

    project_id = service.create_from_bom("控制板", 2, "board.xlsx", [matched, unmatched])

    project = next(project for project in service.list_projects() if project["id"] == project_id)
    assert project["build_quantity"] == 2
    assert project["source_bom_path"] == "board.xlsx"
    lines = service.list_bom_lines(project_id)
    assert [line["match_status"] for line in lines] == ["exact", "unmatched"]
    assert lines[0]["source_values"]["参数"] == "100k"
    assert lines[1]["purchase_quantity"] == 2
    components = service.list_components(project_id)
    assert components[0]["project_quantity"] == 4
    assert components[0]["reference_designator"] == "R1"


def test_issue_bom_allocations_uses_existing_transactional_stock_sync(tmp_path):
    db = Database(tmp_path / "bom-issue.db"); db.initialize()
    component_id = seed_component(db, stock=4)
    service = ProjectService(db)
    project_id = service.create_from_bom("控制板", 1, "board.xlsx", [row(component_id=component_id)])

    result = service.issue_bom_allocations(project_id)

    assert result.changed_lines == 1
    assert result.stock_delta == -4
    assert db.connection.execute("SELECT current_stock FROM components WHERE id=?", (component_id,)).fetchone()[0] == 0
    assert service.list_components(project_id)[0]["synced_quantity"] == 4


def test_create_project_from_bom_rolls_back_invalid_component(tmp_path):
    db = Database(tmp_path / "bom-invalid.db"); db.initialize()
    service = ProjectService(db)

    with pytest.raises(ProjectError, match="匹配元件不存在"):
        service.create_from_bom("坏项目", 1, "bad.xlsx", [row(component_id=999)])

    assert service.list_projects() == []

