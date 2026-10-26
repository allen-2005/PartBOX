from pathlib import Path

from PySide6.QtWidgets import QPushButton, QSpinBox, QStackedWidget, QTableWidget

from partbox.bom import BomLine, ParsedBom
from partbox.database import Database
from partbox.projects import ProjectService
from partbox.ui.bom_optimizer import BomOptimizerDialog


def parsed(tmp_path: Path, **line_values) -> ParsedBom:
    values = dict(
        source_row=2,
        source_values={"Comment": "100K", "Quantity": 3},
        quantity=3,
        designator="R1,R2,R3",
        product_code="",
        product_type="贴片电阻",
        description="100K ±5% 100mW",
        model="",
        package="0603",
        brand="FOJAN",
    )
    values.update(line_values)
    return ParsedBom(tmp_path / "source.xlsx", "BOM", list(values["source_values"]), [BomLine(**values)])


def add_component(db: Database, **values) -> int:
    defaults = dict(
        product_code="C100",
        product_type="贴片电阻",
        product_name="厚膜电阻 100kΩ 5% 100mW 编带",
        model="FRC0603J1003TS",
        package="0603",
        brand="FOJAN(富捷)",
        current_stock=6,
    )
    defaults.update(values)
    now = "2026-01-01 00:00:00"
    cursor = db.connection.execute(
        "INSERT INTO components(product_code,product_type,product_name,model,package,brand,current_stock,created_at,updated_at) "
        "VALUES(?,?,?,?,?,?,?,?,?)",
        (*defaults.values(), now, now),
    )
    db.connection.commit()
    return int(cursor.lastrowid)


def test_dialog_applies_build_quantity_before_matching(qtbot, tmp_path):
    db = Database(tmp_path / "bom-ui.db"); db.initialize(); add_component(db, current_stock=4)
    dialog = BomOptimizerDialog(ProjectService(db), parsed(tmp_path)); qtbot.addWidget(dialog)
    dialog.project_name_edit.setText("双板项目")
    dialog.build_quantity_spin.setValue(2)

    dialog.next_step()

    assert dialog.pages.currentIndex() == 1
    assert dialog.workflow.rows[0].required_quantity == 6
    assert dialog.match_table.item(0, 3).text() == "6"


def test_dialog_supports_candidate_reject_and_undo(qtbot, tmp_path):
    db = Database(tmp_path / "bom-candidate.db"); db.initialize(); add_component(db, package="0805")
    dialog = BomOptimizerDialog(ProjectService(db), parsed(tmp_path)); qtbot.addWidget(dialog)
    dialog.project_name_edit.setText("候选项目"); dialog.next_step()
    dialog.match_table.selectRow(0)

    assert dialog.candidate_table.rowCount() == 1
    dialog.reject_button.click()
    assert dialog.workflow.unresolved_count == 0
    dialog.undo_button.click()
    assert dialog.workflow.unresolved_count == 1


def test_review_highlights_exhausted_stock_and_extra_defaults_zero(qtbot, tmp_path):
    db = Database(tmp_path / "bom-exhaust.db"); db.initialize(); add_component(db, current_stock=6)
    dialog = BomOptimizerDialog(
        ProjectService(db), parsed(tmp_path, quantity=6)
    ); qtbot.addWidget(dialog)
    dialog.project_name_edit.setText("耗尽项目"); dialog.next_step(); dialog.next_step()

    assert dialog.pages.currentIndex() == 2
    assert "用光库存" in dialog.review_table.item(0, 0).text()
    extra = dialog.review_table.cellWidget(0, 5)
    assert isinstance(extra, QSpinBox)
    assert extra.value() == 0
    assert dialog.review_table.item(0, 6).text() == "0"

    extra.setValue(3)
    assert dialog.review_table.item(0, 6).text() == "3"
    assert dialog.undo_button.isVisibleTo(dialog)
    dialog.undo_button.click()
    assert dialog.review_table.cellWidget(0, 5).value() == 0
    assert dialog.review_table.item(0, 6).text() == "0"


def test_export_saves_project_then_optionally_issues_stock(qtbot, tmp_path):
    db = Database(tmp_path / "bom-export-ui.db"); db.initialize(); component_id = add_component(db, current_stock=4)
    service = ProjectService(db)
    source = parsed(tmp_path, quantity=3)
    dialog = BomOptimizerDialog(service, source); qtbot.addWidget(dialog)
    dialog.project_name_edit.setText("新BOM项目"); dialog.build_quantity_spin.setValue(2)
    dialog.next_step(); dialog.next_step()
    target = tmp_path / "shopping.xlsx"

    project_id = dialog.complete_export(target, issue_stock=True)

    assert target.exists()
    project = db.connection.execute("SELECT * FROM projects WHERE id=?", (project_id,)).fetchone()
    assert project["name"] == "新BOM项目"
    assert project["build_quantity"] == 2
    assert service.list_bom_lines(project_id)[0]["required_quantity"] == 6
    assert db.connection.execute(
        "SELECT current_stock FROM components WHERE id=?", (component_id,)
    ).fetchone()[0] == 0


def test_projects_page_exposes_bom_optimizer_entry(qtbot, tmp_path):
    from partbox.ui.projects_page import ProjectsPage

    db = Database(tmp_path / "bom-entry.db"); db.initialize()
    page = ProjectsPage(ProjectService(db)); qtbot.addWidget(page)

    button = page.findChild(QPushButton, "projectBomButton")
    assert button is not None
    assert button.text() == "导入BOM并计算"
