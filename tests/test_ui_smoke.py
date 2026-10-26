from PySide6.QtCore import QPoint, QSettings, Qt
from PySide6.QtWidgets import QAbstractItemView, QInputDialog, QLabel, QFrame, QHBoxLayout, QLineEdit, QMessageBox, QPushButton, QScrollArea, QSplitter, QWidget

from partbox.database import Database
from partbox.services import ImportService, InventoryService, StockService
from partbox.projects import ProjectService
from partbox.ui.main_window import MainWindow, ServiceContainer
from partbox.ui.inventory_header import InventoryHeader
from partbox.ui.ui_loader import builtin_main_ui_path


def test_main_window_uses_clear_artwork_geometry(qtbot, tmp_path):
    db = Database(tmp_path / "a-style.db")
    db.initialize()
    services = ServiceContainer(db, InventoryService(db), ImportService(db), StockService(db))
    window = MainWindow(services, QSettings(str(tmp_path / "a-style.ini"), QSettings.IniFormat))
    qtbot.addWidget(window)
    assert window.findChild(QFrame, "topBar").height() == 88
    assert window.findChild(QWidget, "brandBlock").width() == 180
    assert window.findChild(QLabel, "brandEnglish").pixmap() is not None
    assert window.findChild(QLabel, "brandChineseLogo").pixmap() is not None


def test_main_window_has_approved_dashboard(qtbot, tmp_path):
    db = Database(tmp_path / "ui.db")
    db.initialize()
    services = ServiceContainer(db, InventoryService(db), ImportService(db), StockService(db), projects=ProjectService(db))
    window = MainWindow(services, QSettings(str(tmp_path / "ui.ini"), QSettings.IniFormat))
    qtbot.addWidget(window)
    assert window.ui_path == builtin_main_ui_path()
    assert window.windowTitle() == "小料仓 PartBOX"
    assert window.search_input.placeholderText().startswith("搜索")
    assert window.nav_list.count() == 6
    assert [window.nav_list.item(index).text() for index in range(window.nav_list.count())] == [
        "元件库存", "物料对比", "我的项目", "库存流水", "导入记录", "设置"
    ]
    assert window.pages.count() == 6
    assert window.component_table.columnCount() == 15
    assert isinstance(window.component_table.horizontalHeader(), InventoryHeader)
    assert window.component_table.horizontalHeader().sectionsMovable()
    assert len(window.stat_values) == 4
    assert window.findChild(QFrame, "statKindsCard").minimumHeight() >= 80
    stats = window.findChild(QHBoxLayout, "statsLayout")
    assert [stats.itemAt(i).widget().objectName() for i in range(stats.count())] == [
        "statOrdersCard", "statKindsCard", "statStockCard", "statSpentCard",
        "projectImportCard", "comparisonAddCard"
    ]
    assert window.summary_title.text() == "未选择元件"
    assert window.findChild(QWidget, "brandChinese") is not None
    brand_en = window.findChild(QLabel, "brandEnglish")
    brand_cn = window.findChild(QLabel, "brandChineseLogo")
    assert brand_en.text() == ""
    assert brand_cn is not None
    assert not brand_en.hasScaledContents()
    assert brand_en.pixmap() is not None
    assert not brand_cn.hasScaledContents()
    assert brand_cn.pixmap() is not None
    assert brand_en.pixmap().width() == 112
    assert brand_cn.pixmap().width() == 112
    assert brand_en.width() == brand_cn.width() == 112
    assert window.findChild(QFrame, "topBar").minimumHeight() == 88
    assert window.findChild(QHBoxLayout, "topBarLayout").spacing() >= 18
    assert window.search_input.maximumWidth() == 16777215
    assert window.search_input.height() == 48
    assert window.nav_list.width() == 168
    outer_splitters = [splitter for splitter in window.findChildren(QSplitter) if splitter.parent() is window.centralWidget()]
    assert outer_splitters == []
    window.show(); window.resize(1440, 820); qtbot.wait(20)
    statistic_cards = [stats.itemAt(i).widget() for i in range(4)]
    assert len({(card.width(), card.height()) for card in statistic_cards}) == 1
    assert window.findChild(QFrame, "projectImportCard").height() == statistic_cards[0].height()
    assert window.findChild(QPushButton, "projectImportButton").text() == "导入到项目"
    assert window.findChild(QPushButton, "comparisonAddButton").text() == "加入对比"
    assert window.nav_list.geometry().right() + 1 == window.pages.geometry().left()
    summary = window.findChild(QFrame, "summaryPanel")
    assert summary.minimumWidth() == summary.maximumWidth()
    assert window.findChild(QPushButton, "summaryToggleButton") is not None
    assert window.findChild(QPushButton, "clearFilterButton") is None
    assert window.material_import_button.text() == "＋ 导入物料明细"
    assert window.findChild(QPushButton, "orderDetailImportButton") is None
    assert "#2563eb" in window.summary_labels["current_stock"].styleSheet()
    assert "#07865f" not in window.summary_labels["current_stock"].styleSheet()
    assert "QScrollBar:vertical" in window.styleSheet()
    assert "width: 22px" in window.styleSheet()
    assert "height: 22px" in window.styleSheet()
    assert "QTableWidget QLineEdit" in window.styleSheet()
    assert "border: 2px solid #2563eb" in window.styleSheet()
    assert "selection-color: #ffffff" in window.styleSheet()
    assert "background: #f8fbff" in window.styleSheet()
    assert "font-size: 16px" in window.styleSheet()
    filter_scroll = window.findChild(QScrollArea, "filterScroll")
    assert filter_scroll.horizontalScrollBarPolicy() == Qt.ScrollBarAsNeeded
    assert filter_scroll.verticalScrollBarPolicy() == Qt.ScrollBarAlwaysOff
    assert filter_scroll.focusPolicy() == Qt.NoFocus
    assert filter_scroll.maximumHeight() == 66
    assert window.filter_row.contentsMargins().top() == window.filter_row.contentsMargins().bottom()
    assert window.component_table.horizontalScrollMode() == QAbstractItemView.ScrollPerPixel
    assert window.component_table.verticalScrollMode() == QAbstractItemView.ScrollPerPixel


def test_projects_bom_button_opens_optimizer(qtbot, tmp_path, monkeypatch):
    db = Database(tmp_path / "bom-window.db"); db.initialize()
    services = ServiceContainer(
        db, InventoryService(db), ImportService(db), StockService(db),
        projects=ProjectService(db),
    )
    window = MainWindow(services, QSettings(str(tmp_path / "bom-window.ini"), QSettings.IniFormat))
    qtbot.addWidget(window)
    opened = []
    monkeypatch.setattr(
        "partbox.ui.main_window.BomOptimizerDialog.exec",
        lambda dialog: opened.append(dialog.windowTitle()) or 0,
    )

    window.projects_page.bom_button.click()

    assert opened == ["导入BOM并计算"]


def test_summary_stock_actions_open_modal_with_selected_component(qtbot, tmp_path, monkeypatch):
    db = Database(tmp_path / "stock-link.db"); db.initialize(); now = "2026-01-01 00:00:00"
    db.connection.execute(
        "INSERT INTO components(product_code,product_name,model,current_stock,unit,created_at,updated_at) VALUES('C1','双运放','LM358P',8,'个',?,?)",
        (now, now),
    ); db.connection.commit()
    services = ServiceContainer(db, InventoryService(db), ImportService(db), StockService(db))
    window = MainWindow(services, QSettings(str(tmp_path / "link.ini"), QSettings.IniFormat)); qtbot.addWidget(window)
    opened = []
    monkeypatch.setattr("partbox.ui.main_window.StockDialog.exec", lambda dialog: opened.append(dialog.windowTitle()) or 0)
    window.component_table.selectRow(0)
    window.stock_out_button.click()
    assert opened == ["出库 · LM358P"]
    assert window.pages.currentIndex() == 0


def test_window_restores_only_table_header_preferences(qtbot, tmp_path):
    db = Database(tmp_path / "restore-ui.db"); db.initialize()
    services = ServiceContainer(db, InventoryService(db), ImportService(db), StockService(db))
    settings_path = tmp_path / "restore-ui.ini"
    first = MainWindow(services, QSettings(str(settings_path), QSettings.IniFormat)); qtbot.addWidget(first)
    first.inventory_header.moveSection(first.inventory_header.visualIndex(2), 0)
    first.inventory_header.set_column_visible(1, False)
    first.inventory_header.set_sort(6, Qt.DescendingOrder)
    first.settings.sync(); first.close(); qtbot.wait(1)

    restored = MainWindow(services, QSettings(str(settings_path), QSettings.IniFormat)); qtbot.addWidget(restored)
    assert restored.inventory_header.logicalIndex(0) == 2
    assert restored.inventory_header.isSectionHidden(1)
    assert restored.inventory_header.sortIndicatorSection() == 6
    assert restored.inventory_header.sortIndicatorOrder() == Qt.DescendingOrder
    assert restored.pages.count() == 6
    assert restored.pages.currentIndex() == 0


def test_inventory_numeric_columns_sort_as_numbers(qtbot, tmp_path):
    db = Database(tmp_path / "numeric-sort.db"); db.initialize(); now = "2026-01-01 00:00:00"
    for code, stock in (("C1", 2), ("C2", 10), ("C3", 1)):
        db.connection.execute(
            "INSERT INTO components(product_code,current_stock,unit,created_at,updated_at) VALUES(?,?, '个',?,?)",
            (code, stock, now, now),
        )
    db.connection.commit()
    services = ServiceContainer(db, InventoryService(db), ImportService(db), StockService(db))
    window = MainWindow(services, QSettings(str(tmp_path / "numeric.ini"), QSettings.IniFormat)); qtbot.addWidget(window)
    stock_column = next(i for i, (key, _) in enumerate(window.columns) if key == "current_stock")
    window.component_table.sortItems(stock_column, Qt.AscendingOrder)
    assert [int(window.component_table.item(row, stock_column).text()) for row in range(3)] == [1, 2, 10]


def test_dynamic_filters_and_only_stock_notes_are_editable(qtbot, tmp_path):
    db = Database(tmp_path / "ui-editable.db")
    db.initialize()
    now = "2026-01-01 00:00:00"
    db.connection.execute(
        "INSERT INTO components(product_code,product_type,product_name,current_stock,created_at,updated_at) "
        "VALUES('C1','贴片电阻','10kΩ ±1%',10,?,?)",
        (now, now),
    )
    db.connection.commit()
    services = ServiceContainer(db, InventoryService(db), ImportService(db), StockService(db))
    window = MainWindow(services, QSettings(str(tmp_path / "editable.ini"), QSettings.IniFormat))
    qtbot.addWidget(window)

    filter_texts = [button.text() for button in window.filter_buttons]
    assert filter_texts == ["全部", "电阻"]
    type_column = next(index for index, (key, _) in enumerate(window.columns) if key == "product_type")
    assert window.component_table.item(0, type_column).text() == "贴片电阻"
    editable_keys = {
        key
        for column, (key, _) in enumerate(window.columns)
        if window.component_table.item(0, column).flags() & Qt.ItemIsEditable
    }
    assert editable_keys == {"current_stock", "location", "notes"}

    location_column = next(index for index, (key, _) in enumerate(window.columns) if key == "location")
    location_item = window.component_table.item(0, location_column)
    location_item.setText("抽屉 A3")
    assert db.connection.execute("SELECT location FROM components WHERE product_code='C1'").fetchone()[0] == "抽屉 A3"


def test_inventory_row_checkboxes_and_summary_copy_collapse(qtbot, tmp_path):
    db = Database(tmp_path / "selection.db"); db.initialize(); now = "2026-01-01 00:00:00"
    first_id = db.connection.execute(
        "INSERT INTO components(product_code,product_name,current_stock,unit,created_at,updated_at) VALUES('C1','电阻',10,'个',?,?)",
        (now, now),
    ).lastrowid
    second_id = db.connection.execute(
        "INSERT INTO components(product_code,product_name,current_stock,unit,created_at,updated_at) VALUES('C2','电容',10,'个',?,?)",
        (now, now),
    ).lastrowid
    db.connection.commit()
    settings = QSettings(str(tmp_path / "selection.ini"), QSettings.IniFormat)
    window = MainWindow(ServiceContainer(db, InventoryService(db), ImportService(db), StockService(db), projects=ProjectService(db)), settings)
    qtbot.addWidget(window); window.show(); qtbot.wait(20)
    first_row = next(
        row for row in range(window.component_table.rowCount())
        if window.component_table.item(row, 0).data(Qt.UserRole) == first_id
    )
    header_item = window.component_table.verticalHeaderItem(first_row)
    assert header_item.checkState() == Qt.Unchecked
    window.toggle_row_checked(first_row)
    assert window.selected_component_ids() == [first_id]
    assert window.component_table.verticalHeaderItem(first_row).checkState() == Qt.Checked

    window.component_table.sortItems(0, Qt.DescendingOrder)
    assert window.component_table.item(0, 0).data(Qt.UserRole) == second_id
    window.toggle_row_checked(0)
    assert set(window.selected_component_ids()) == {first_id, second_id}

    window.component_table.selectRow(0)
    qtbot.mouseClick(window.summary_labels["product_code"], Qt.LeftButton)
    assert window.clipboard_text() == "C2"
    window.toggle_summary_panel()
    assert not window.summary_panel.isVisible()
    assert settings.value("ui/summary_visible", type=bool) is False


def test_inventory_shift_click_selects_visible_range_by_component_identity(qtbot, tmp_path):
    db = Database(tmp_path / "inventory-range.db"); db.initialize(); now = "2026-01-01 00:00:00"
    for code in ("C1", "C2", "C3", "C4", "C5"):
        db.connection.execute(
            "INSERT INTO components(product_code,product_name,current_stock,unit,created_at,updated_at) "
            "VALUES(?,?,10,'个',?,?)", (code, code, now, now),
        )
    db.connection.commit()
    services = ServiceContainer(db, InventoryService(db), ImportService(db), StockService(db), projects=ProjectService(db))
    window = MainWindow(services, QSettings(str(tmp_path / "inventory-range.ini"), QSettings.IniFormat))
    qtbot.addWidget(window)

    window.toggle_row_checked(1)
    window.toggle_row_checked(4, Qt.ShiftModifier)

    displayed = [int(window.component_table.item(row, 0).data(Qt.UserRole)) for row in range(1, 5)]
    assert window.selected_component_ids() == displayed

    window.checked_component_ids.clear()
    anchor_id = int(window.component_table.item(1, 0).data(Qt.UserRole))
    window.toggle_row_checked(1)
    window.component_table.sortItems(0, Qt.DescendingOrder)
    target_row = next(
        row for row in range(window.component_table.rowCount())
        if int(window.component_table.item(row, 0).data(Qt.UserRole)) != anchor_id
    )
    window.toggle_row_checked(target_row, Qt.ShiftModifier)
    anchor_row = next(
        row for row in range(window.component_table.rowCount())
        if int(window.component_table.item(row, 0).data(Qt.UserRole)) == anchor_id
    )
    low, high = sorted((anchor_row, target_row))
    expected = {
        int(window.component_table.item(row, 0).data(Qt.UserRole))
        for row in range(low, high + 1)
    }
    assert anchor_id in expected
    assert expected.issubset(window.checked_component_ids)


def test_inventory_header_accepts_real_shift_left_click(qtbot, tmp_path):
    db = Database(tmp_path / "inventory-mouse-range.db"); db.initialize(); now = "2026-01-01 00:00:00"
    for code in ("C1", "C2", "C3"):
        db.connection.execute(
            "INSERT INTO components(product_code,product_name,current_stock,created_at,updated_at) "
            "VALUES(?,?,1,?,?)", (code, code, now, now),
        )
    db.connection.commit()
    services = ServiceContainer(db, InventoryService(db), ImportService(db), StockService(db), projects=ProjectService(db))
    window = MainWindow(services, QSettings(str(tmp_path / "inventory-mouse-range.ini"), QSettings.IniFormat))
    qtbot.addWidget(window); window.show(); qtbot.wait(20)
    header = window.component_table.verticalHeader()

    def row_center(row):
        return QPoint(header.viewport().width() // 2, header.sectionViewportPosition(row) + header.sectionSize(row) // 2)

    qtbot.mouseClick(header.viewport(), Qt.LeftButton, Qt.NoModifier, row_center(0))
    qtbot.mouseClick(header.viewport(), Qt.LeftButton, Qt.ShiftModifier, row_center(2))

    displayed = {
        int(window.component_table.item(row, 0).data(Qt.UserRole))
        for row in range(3)
    }
    assert window.checked_component_ids == displayed


def test_inventory_selected_components_can_be_added_to_comparison(qtbot, tmp_path, monkeypatch):
    db = Database(tmp_path / "inventory-comparison.db"); db.initialize(); now = "2026-01-01 00:00:00"
    for code in ("C1", "C2"):
        db.connection.execute(
            "INSERT INTO components(product_code,product_name,current_stock,created_at,updated_at) "
            "VALUES(?,?,1,?,?)", (code, code, now, now),
        )
    db.connection.commit()
    services = ServiceContainer(db, InventoryService(db), ImportService(db), StockService(db), projects=ProjectService(db))
    window = MainWindow(services, QSettings(str(tmp_path / "comparison.ini"), QSettings.IniFormat))
    qtbot.addWidget(window)
    monkeypatch.setattr(QMessageBox, "information", lambda *args: QMessageBox.Ok)

    window.toggle_row_checked(0, Qt.NoModifier)
    window.toggle_row_checked(1, Qt.NoModifier)
    window.comparison_add_button.click()

    assert window.nav_list.currentRow() == 1
    assert [row["product_code"] for row in window.services.comparison.list_components()] == ["C1", "C2"]
    assert window.comparison_page.table.columnCount() == 2


def test_main_window_close_can_cancel_unsaved_project_configuration(qtbot, tmp_path, monkeypatch):
    db = Database(tmp_path / "close-dirty-project.db"); db.initialize(); now = "2026-01-01 00:00:00"
    component_id = db.connection.execute(
        "INSERT INTO components(product_code,product_name,current_stock,created_at,updated_at) "
        "VALUES('C1','电阻',10,?,?) RETURNING id", (now, now)
    ).fetchone()[0]
    db.connection.commit()
    projects = ProjectService(db); project_id = projects.create_project("关闭保护")
    projects.add_components(project_id, [component_id])
    services = ServiceContainer(db, InventoryService(db), ImportService(db), StockService(db), projects=projects)
    window = MainWindow(services, QSettings(str(tmp_path / "close-dirty.ini"), QSettings.IniFormat))
    qtbot.addWidget(window); window.show(); window.projects_page.refresh(project_id)
    window.projects_page.component_table.cellWidget(0, 6).setValue(2)
    monkeypatch.setattr(QMessageBox, "question", lambda *args, **kwargs: QMessageBox.Cancel)

    window.close()

    assert window.isVisible()


def test_main_window_close_commits_active_designator_before_prompt(qtbot, tmp_path, monkeypatch):
    db = Database(tmp_path / "close-active-designator.db"); db.initialize(); now = "2026-01-01 00:00:00"
    component_id = db.connection.execute(
        "INSERT INTO components(product_code,product_name,current_stock,created_at,updated_at) "
        "VALUES('C1','电阻',10,?,?) RETURNING id", (now, now)
    ).fetchone()[0]
    db.connection.commit()
    projects = ProjectService(db); project_id = projects.create_project("关闭位号保护")
    projects.add_components(project_id, [component_id])
    services = ServiceContainer(db, InventoryService(db), ImportService(db), StockService(db), projects=projects)
    window = MainWindow(services, QSettings(str(tmp_path / "close-designator.ini"), QSettings.IniFormat))
    qtbot.addWidget(window); window.show(); window.projects_page.refresh(project_id)
    window.nav_list.setCurrentRow(2)
    item = window.projects_page.component_table.item(0, 9)
    window.projects_page.component_table.setCurrentItem(item)
    window.projects_page.component_table.editItem(item)
    editor = window.projects_page.component_table.findChild(QLineEdit)
    editor.setText("R1")
    questions = []
    monkeypatch.setattr(
        QMessageBox,
        "question",
        lambda *args, **kwargs: questions.append(args[2]) or QMessageBox.Cancel,
    )

    window.close()

    assert window.isVisible()
    assert item.text() == "R1"
    assert window.projects_page.has_unsaved_configuration()
    assert "位号" in questions[0]


def test_inventory_import_can_cancel_when_project_configuration_is_unsaved(qtbot, tmp_path, monkeypatch):
    db = Database(tmp_path / "import-dirty-project.db"); db.initialize(); now = "2026-01-01 00:00:00"
    component_ids = []
    for code in ("C1", "C2"):
        component_ids.append(db.connection.execute(
            "INSERT INTO components(product_code,product_name,current_stock,created_at,updated_at) "
            "VALUES(?,?,10,?,?) RETURNING id", (code, code, now, now)
        ).fetchone()[0])
    db.connection.commit()
    projects = ProjectService(db); project_id = projects.create_project("目标项目")
    projects.add_components(project_id, [component_ids[0]])
    services = ServiceContainer(db, InventoryService(db), ImportService(db), StockService(db), projects=projects)
    window = MainWindow(services, QSettings(str(tmp_path / "import-dirty.ini"), QSettings.IniFormat))
    qtbot.addWidget(window); window.projects_page.refresh(project_id)
    window.projects_page.component_table.cellWidget(0, 6).setValue(2)
    target_row = next(
        row for row in range(window.component_table.rowCount())
        if int(window.component_table.item(row, 0).data(Qt.UserRole)) == component_ids[1]
    )
    window.toggle_row_checked(target_row)
    monkeypatch.setattr(QInputDialog, "getItem", lambda *args, **kwargs: ("目标项目", True))
    monkeypatch.setattr(QMessageBox, "question", lambda *args, **kwargs: QMessageBox.Cancel)
    monkeypatch.setattr(QMessageBox, "information", lambda *args, **kwargs: None)

    window.import_selected_to_project()

    assert [row["id"] for row in projects.list_components(project_id)] == [component_ids[0]]
    assert window.projects_page.has_unsaved_configuration()


def test_inventory_import_can_save_project_draft_before_adding_component(qtbot, tmp_path, monkeypatch):
    db = Database(tmp_path / "import-save-project.db"); db.initialize(); now = "2026-01-01 00:00:00"
    component_ids = []
    for code in ("C1", "C2"):
        component_ids.append(db.connection.execute(
            "INSERT INTO components(product_code,product_name,current_stock,created_at,updated_at) "
            "VALUES(?,?,10,?,?) RETURNING id", (code, code, now, now)
        ).fetchone()[0])
    db.connection.commit()
    projects = ProjectService(db); project_id = projects.create_project("目标项目")
    projects.add_components(project_id, [component_ids[0]])
    services = ServiceContainer(db, InventoryService(db), ImportService(db), StockService(db), projects=projects)
    window = MainWindow(services, QSettings(str(tmp_path / "import-save.ini"), QSettings.IniFormat))
    qtbot.addWidget(window); window.projects_page.refresh(project_id)
    window.projects_page.component_table.cellWidget(0, 6).setValue(2)
    target_row = next(
        row for row in range(window.component_table.rowCount())
        if int(window.component_table.item(row, 0).data(Qt.UserRole)) == component_ids[1]
    )
    window.toggle_row_checked(target_row)
    monkeypatch.setattr(QInputDialog, "getItem", lambda *args, **kwargs: ("目标项目", True))
    monkeypatch.setattr(QMessageBox, "question", lambda *args, **kwargs: QMessageBox.Save)
    monkeypatch.setattr(QMessageBox, "information", lambda *args, **kwargs: None)

    window.import_selected_to_project()

    rows = {row["id"]: row for row in projects.list_components(project_id)}
    assert set(rows) == set(component_ids)
    assert rows[component_ids[0]]["project_quantity"] == 2
    assert rows[component_ids[1]]["project_quantity"] == 1
    assert window.projects_page.component_table.rowCount() == 2
    assert not window.projects_page.has_unsaved_configuration()
