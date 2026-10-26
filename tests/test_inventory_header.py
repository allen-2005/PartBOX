from PySide6.QtCore import QPoint, QSettings, Qt
from PySide6.QtWidgets import QTableWidget

from partbox.ui.inventory_header import InventoryHeader


COLUMNS = [("code", "商品编号"), ("name", "商品名称"), ("stock", "当前库存")]
WIDTHS = [100, 220, 90]


def make_table(qtbot, settings):
    table = QTableWidget(0, len(COLUMNS))
    table.setHorizontalHeaderLabels([title for _, title in COLUMNS])
    header = InventoryHeader(COLUMNS, WIDTHS, settings, table)
    table.setHorizontalHeader(header)
    header.restore_layout()
    qtbot.addWidget(table)
    return table, header


def test_header_restores_order_width_visibility_and_sort(qtbot, tmp_path):
    settings = QSettings(str(tmp_path / "header.ini"), QSettings.IniFormat)
    table, header = make_table(qtbot, settings)
    header.moveSection(header.visualIndex(2), 0)
    header.resizeSection(1, 177)
    header.set_column_visible(0, False)
    header.set_sort(2, Qt.DescendingOrder)
    settings.sync()
    table.deleteLater(); qtbot.wait(1)

    _, restored = make_table(qtbot, QSettings(str(tmp_path / "header.ini"), QSettings.IniFormat))
    assert [restored.logicalIndex(i) for i in range(restored.count())] == [2, 0, 1]
    assert restored.sectionSize(1) == 177
    assert restored.isSectionHidden(0)
    assert restored.sortIndicatorSection() == 2
    assert restored.sortIndicatorOrder() == Qt.DescendingOrder


def test_header_visibility_actions_keep_one_column_and_show_all_preserves_layout(qtbot, tmp_path):
    settings = QSettings(str(tmp_path / "visibility.ini"), QSettings.IniFormat)
    _, header = make_table(qtbot, settings)
    header.moveSection(header.visualIndex(2), 0)
    header.resizeSection(1, 166)
    header.set_column_visible(0, False)
    header.set_column_visible(1, False)
    assert not header.set_column_visible(2, False)
    assert not header.isSectionHidden(2)

    header.show_all_columns()
    assert not any(header.isSectionHidden(index) for index in range(header.count()))
    assert [header.logicalIndex(i) for i in range(header.count())] == [2, 0, 1]
    assert header.sectionSize(1) == 166


def test_header_reset_restores_defaults_and_menu_lists_every_column(qtbot, tmp_path):
    settings = QSettings(str(tmp_path / "reset.ini"), QSettings.IniFormat)
    _, header = make_table(qtbot, settings)
    header.moveSection(2, 0); header.resizeSection(1, 150); header.set_column_visible(0, False)
    header.set_sort(2, Qt.DescendingOrder)

    menu = header.build_column_menu()
    captured = [action.text() for action in menu.actions() if not action.isSeparator()]
    assert captured[:3] == ["商品编号", "商品名称", "当前库存"]
    assert captured[-2:] == ["全部显示", "恢复默认列布局"]

    header.reset_layout()
    assert [header.logicalIndex(i) for i in range(header.count())] == [0, 1, 2]
    assert [header.sectionSize(i) for i in range(header.count())] == WIDTHS
    assert not any(header.isSectionHidden(index) for index in range(header.count()))
    assert header.sortIndicatorSection() == 0
    assert header.sortIndicatorOrder() == Qt.AscendingOrder
