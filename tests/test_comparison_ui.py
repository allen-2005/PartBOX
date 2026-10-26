from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QAbstractItemView

from partbox.comparison import ComparisonService
from partbox.database import Database
from partbox.ui.comparison_page import BASE_FILL, DIFFERENCE_FILL, ComparisonPage


def build_page(qtbot, tmp_path):
    db = Database(tmp_path / "comparison-ui.db"); db.initialize()
    now = "2026-08-27 10:00:00"
    first = int(db.connection.execute(
        "INSERT INTO components(product_code,product_type,product_name,model,package,brand,current_stock,created_at,updated_at) "
        "VALUES('C1','贴片电阻','100kΩ ±5%','R100K','0603','FOJAN',10,?,?) RETURNING id",
        (now, now),
    ).fetchone()[0])
    second = int(db.connection.execute(
        "INSERT INTO components(product_code,product_type,product_name,model,package,brand,current_stock,created_at,updated_at) "
        "VALUES('C2','贴片电阻','100kΩ ±5%','R100K','0805','FOJAN',8,?,?) RETURNING id",
        (now, now),
    ).fetchone()[0])
    batch = int(db.connection.execute(
        "INSERT INTO import_batches(filename,file_sha256,imported_at) VALUES('a.xlsx','sha','2026-08-27') RETURNING id"
    ).fetchone()[0])
    db.connection.execute(
        "INSERT INTO purchase_lines(component_id,batch_id,line_fingerprint,order_time,quantity,unit_price,order_number) "
        "VALUES(?,?, 'fp','2026-08-20 09:00:00',10,0.25,'O1')",
        (first, batch),
    )
    db.connection.commit()
    service = ComparisonService(db); service.add_components([first, second])
    page = ComparisonPage(service); qtbot.addWidget(page)
    return db, service, page, first, second


def row_named(page: ComparisonPage, title: str) -> int:
    return next(
        row for row in range(page.table.rowCount())
        if page.table.verticalHeaderItem(row).text() == title
    )


def test_comparison_page_exposes_yellow_workspace_identity(qtbot, tmp_path):
    db = Database(tmp_path / "comparison-theme.db")
    db.initialize()
    page = ComparisonPage(ComparisonService(db))
    qtbot.addWidget(page)
    margins = page.layout().contentsMargins()
    assert page.objectName() == "comparisonPage"
    assert (margins.left(), margins.top(), margins.right(), margins.bottom()) == (16, 16, 16, 16)


def test_comparison_page_is_transposed_scrollable_and_highlights_differences(qtbot, tmp_path):
    _, _, page, first, second = build_page(qtbot, tmp_path)

    assert page.table.columnCount() == 2
    assert page.table.horizontalScrollMode() == QAbstractItemView.ScrollPerPixel
    assert page.table.selectionBehavior() == QAbstractItemView.SelectColumns
    assert [page.table.horizontalHeaderItem(column).text() for column in range(2)] == ["C1", "C2"]

    brand_row = row_named(page, "品牌")
    package_row = row_named(page, "封装格式")
    assert page.table.item(brand_row, 0).background().color() == QColor(BASE_FILL)
    assert page.table.item(brand_row, 1).background().color() == QColor(BASE_FILL)
    assert page.table.item(package_row, 0).background().color() == QColor(DIFFERENCE_FILL)
    assert page.table.item(package_row, 1).background().color() == QColor(DIFFERENCE_FILL)
    assert set(page.chart.series) == {first, second}
    assert len(page.chart.series[first]["points"]) == 1


def test_comparison_page_removes_selected_columns_and_clears(qtbot, tmp_path):
    _, service, page, first, second = build_page(qtbot, tmp_path)

    page.table.selectColumn(0)
    page.remove_selected()
    assert [row["id"] for row in service.list_components()] == [second]
    assert page.table.columnCount() == 1

    page.clear_all()
    assert service.list_components() == []
    assert page.table.columnCount() == 0
    assert page.empty_label.isVisible() or not page.isVisible()
def test_comparison_palette_uses_warm_base_and_clear_difference_fill():
    assert BASE_FILL == "#FFFCF4"
    assert DIFFERENCE_FILL == "#F8EDC8"

