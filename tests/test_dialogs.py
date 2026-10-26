from dataclasses import replace

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QPushButton

from partbox.database import Database
from partbox.importer import OrderLine, ParsedStatement
from partbox.services import ImportService, StockService
from partbox.ui.import_dialog import ImportDialog
from partbox.ui.stock_dialog import StockDialog


def make_line(code="C1", quantity=10, fingerprint="fp1"):
    return OrderLine(
        source_sheet="物料", source_row=3, order_number="SO1", order_status="已发货",
        order_time="2026-01-01", recipient="", customer_part_number="", product_code=code,
        brand="品牌", product_type="电阻", product_name="10k", model="R10K", package="0603",
        quantity=quantity, unit="个", unit_price=.01, subtotal=.1, line_fingerprint=fingerprint,
    )


def test_import_dialog_collects_existing_stock_decisions(qtbot, tmp_path):
    db = Database(tmp_path / "db.sqlite"); db.initialize(); importer = ImportService(db)
    first = ParsedStatement(tmp_path / "a.xls", "sha1", "物料", 2, [], order_lines=[make_line()])
    importer.commit(importer.preview_parsed([first]), {})
    second_line = replace(make_line(quantity=5, fingerprint="fp2"), order_number="SO2")
    second = ParsedStatement(tmp_path / "b.xls", "sha2", "物料", 2, [], order_lines=[second_line])
    preview = importer.preview_parsed([second])

    dialog = ImportDialog(importer); qtbot.addWidget(dialog); dialog.set_preview(preview)
    assert dialog.existing_table.rowCount() == 1
    dialog.existing_table.item(0, 0).setCheckState(Qt.Unchecked)
    assert dialog.stock_decisions() == {"fp2": False}


def test_import_dialog_shows_new_components_as_automatic_stock(qtbot, tmp_path):
    db = Database(tmp_path / "new.db"); db.initialize(); importer = ImportService(db)
    statement = ParsedStatement(tmp_path / "new.xls", "new-sha", "物料", 2, [], order_lines=[make_line()])
    preview = importer.preview_parsed([statement])
    dialog = ImportDialog(importer); qtbot.addWidget(dialog); dialog.set_preview(preview)

    assert dialog.existing_table.rowCount() == 1
    status = dialog.existing_table.item(0, 0)
    assert status.text() == "自动入库"
    assert not (status.flags() & Qt.ItemIsUserCheckable)
    assert not dialog.existing_table.verticalHeader().isVisible()
    assert dialog.stock_decisions() == {}
    button_texts = [button.text() for button in dialog.findChildren(QPushButton)]
    assert "已有元件全部加入" not in button_texts
    assert "已有元件全部不加入" not in button_texts


def test_import_dialog_mixed_preview_only_collects_existing_decisions(qtbot, tmp_path):
    db = Database(tmp_path / "mixed.db"); db.initialize(); importer = ImportService(db)
    first = ParsedStatement(tmp_path / "first.xls", "sha-first", "物料", 2, [], order_lines=[make_line(code="C1", fingerprint="first")])
    importer.commit(importer.preview_parsed([first]), {})
    existing = replace(make_line(code="C1", quantity=2, fingerprint="existing"), order_number="SO2")
    new = replace(make_line(code="C2", quantity=3, fingerprint="new"), order_number="SO3")
    preview = importer.preview_parsed([ParsedStatement(tmp_path / "mixed.xls", "sha-mixed", "物料", 2, [], order_lines=[new, existing])])
    dialog = ImportDialog(importer); qtbot.addWidget(dialog); dialog.set_preview(preview)

    assert dialog.existing_table.rowCount() == 2
    assert dialog.existing_table.item(0, 0).text() == "自动入库"
    assert dialog.existing_table.item(1, 0).checkState() == Qt.Checked
    assert not (dialog.existing_table.item(1, 0).flags() & Qt.ItemIsEditable)
    assert dialog.stock_decisions() == {"existing": True}


def test_import_dialog_explains_legacy_duplicates_only_repair_metadata(qtbot, tmp_path):
    db = Database(tmp_path / "legacy.db"); db.initialize(); importer = ImportService(db)
    coarse = replace(make_line(fingerprint="legacy"), product_type="电阻", subtotal=2.0)
    legacy = ParsedStatement(
        tmp_path / "立创商城订单详情-SO1.xls", "legacy-sha", "物料", 2, [], order_lines=[coarse]
    )
    importer.commit(importer.preview_parsed([legacy]), {})
    exact = replace(coarse, line_fingerprint="statement", product_type="贴片电阻", subtotal=1.0)
    statement = ParsedStatement(
        tmp_path / "立创商城物料明细对账单.xls", "statement-sha", "物料", 2, [], order_lines=[exact]
    )

    dialog = ImportDialog(importer); qtbot.addWidget(dialog)
    dialog.set_preview(importer.preview_parsed([statement]))

    assert "识别 1 条元件明细" in dialog.summary.text()
    assert "只校正商品信息" in dialog.summary.text()
    assert any(label.text() == "重复不计数" for label in dialog.findChildren(QLabel))


def test_stock_dialog_applies_outbound_change(qtbot, tmp_path):
    db = Database(tmp_path / "db.sqlite"); db.initialize()
    now = "2026-01-01 00:00:00"
    component_id = db.connection.execute(
        "INSERT INTO components(product_code,product_name,current_stock,unit,created_at,updated_at) VALUES('C9','测试元件',8,'个',?,?) RETURNING id",
        (now, now),
    ).fetchone()[0]; db.connection.commit()
    dialog = StockDialog(StockService(db), component_id, "测试元件", 8, "个", mode="out")
    qtbot.addWidget(dialog); dialog.quantity.setValue(3); dialog.apply_change()
    assert StockService(db).get_stock(component_id) == 5


def test_stock_dialog_has_refined_information_and_controls(qtbot, tmp_path):
    db = Database(tmp_path / "refined.db"); db.initialize()
    now = "2026-01-01 00:00:00"
    component_id = db.connection.execute(
        "INSERT INTO components(product_code,current_stock,unit,created_at,updated_at) VALUES('C7',5,'个',?,?) RETURNING id",
        (now, now),
    ).fetchone()[0]; db.connection.commit()
    dialog = StockDialog(StockService(db), component_id, "40N06D", 5, "个", mode="in")
    qtbot.addWidget(dialog)

    assert dialog.objectName() == "stockDialog"
    assert dialog.findChild(QLabel, "stockDialogTitle").text() == "入库"
    assert dialog.findChild(QLabel, "stockComponentName").text() == "40N06D"
    assert dialog.findChild(QLabel, "currentStockValue").text() == "5 个"
    assert dialog.quantity.suffix() == " 个"
    assert dialog.notes.placeholderText() == "例如：项目领用、补货、盘点校准"
    dialog.quantity.setValue(4)
    assert dialog.preview.text() == "5 → 9 个"
    assert dialog.confirm_button.text() == "确认入库"
