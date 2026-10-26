from PySide6.QtCore import QSettings, Qt
from PySide6.QtWidgets import (
    QAbstractItemView, QFrame, QInputDialog, QLabel, QLineEdit, QMessageBox,
    QPushButton, QWidget,
)

from partbox.database import Database
from partbox.projects import ProjectService
from partbox.ui.projects_page import ProjectsPage


def test_project_page_exposes_green_workspace_identity(qtbot, tmp_path):
    db = Database(tmp_path / "project-theme.db")
    db.initialize()
    page = ProjectsPage(ProjectService(db))
    qtbot.addWidget(page)
    margins = page.layout().contentsMargins()
    assert page.objectName() == "projectsPage"
    assert page.component_table.property("projectTable") is True
    assert (margins.left(), margins.top(), margins.right(), margins.bottom()) == (16, 16, 16, 16)


def test_projects_page_creates_project_adds_components_and_syncs(qtbot, tmp_path):
    db = Database(tmp_path / "project-ui.db"); db.initialize(); now = "2026-01-01 00:00:00"
    component_id = db.connection.execute(
        "INSERT INTO components(product_code,product_type,product_name,model,package,brand,current_stock,latest_unit_price,created_at,updated_at) "
        "VALUES('C1','贴片电阻','10kΩ','R10K','0603','品牌',10,0.25,?,?) RETURNING id",
        (now, now),
    ).fetchone()[0]
    second_id = db.connection.execute(
        "INSERT INTO components(product_code,product_type,product_name,model,package,brand,current_stock,latest_unit_price,created_at,updated_at) "
        "VALUES('C2','线性稳压器(LDO)','稳压器','LDO1','SOT-23','品牌2',10,1.5,?,?) RETURNING id",
        (now, now),
    ).fetchone()[0]
    db.connection.commit()
    service = ProjectService(db)
    project_id = service.create_project("复刻")
    page = ProjectsPage(service); qtbot.addWidget(page); page.resize(1100, 700); page.show()

    page.add_component_ids([component_id, second_id], project_id=project_id)
    assert page.component_table.columnCount() == 11
    assert [page.component_table.horizontalHeaderItem(i).text() for i in range(11)] == [
        "商品编号", "商品类型", "商品名称", "商品型号", "封装格式", "品牌",
        "项目用量", "单价", "小计", "位号", "操作",
    ]
    assert page.component_table.property("projectTable") is True
    assert page.component_table.horizontalHeader().isSortIndicatorShown() is False
    assert page.component_table.horizontalHeader().sortIndicatorSection() == 0
    first_row = next(
        row for row in range(page.component_table.rowCount())
        if page.component_table.item(row, 0).data(Qt.UserRole) == component_id
    )
    assert page.component_table.item(first_row, 1).text() == "贴片电阻"
    page.refresh(project_id)
    page.refresh(project_id)
    first_row = next(
        row for row in range(page.component_table.rowCount())
        if page.component_table.item(row, 0).data(Qt.UserRole) == component_id
    )
    quantity = page.component_table.cellWidget(first_row, 6)
    steppers = page.component_table.findChildren(QWidget, "projectQuantityStepper")
    assert len(steppers) == page.component_table.rowCount()
    assert quantity.objectName() == "projectQuantityStepper"
    assert quantity.testAttribute(Qt.WA_StyledBackground)
    assert page.component_table.item(first_row, 6).text() == ""
    assert quantity.minimum() == 1
    assert quantity.value() == 1
    assert quantity.height() <= 32
    assert all(page.component_table.rowHeight(row) == 36 for row in range(page.component_table.rowCount()))
    page.component_table.clearSelection()
    qtbot.mouseClick(quantity.increase_button, Qt.LeftButton)
    assert quantity.value() == 2
    assert service.list_components(project_id)[0]["project_quantity"] == 1
    assert page.save_configuration_button.isEnabled()
    assert page.component_table.selectionModel().selectedRows() == []
    qtbot.mouseClick(quantity.decrease_button, Qt.LeftButton)
    assert quantity.value() == 1
    assert not quantity.decrease_button.isEnabled()
    assert not page.save_configuration_button.isEnabled()
    quantity.setValue(4)
    assert page.component_table.item(first_row, 8).text() == "¥1.00"
    assert page.project_total_label.text().endswith("¥2.50")
    assert service.list_components(project_id)[0]["project_quantity"] == 1
    page.save_configuration_button.click()
    assert service.list_components(project_id)[0]["project_quantity"] == 4
    assert not page.save_configuration_button.isEnabled()
    result = service.sync(project_id)
    assert result.stock_delta == -5
    page.refresh(project_id)
    assert page.history_table.rowCount() == 1


def test_project_reference_designator_is_editable_and_saved_with_configuration(qtbot, tmp_path):
    db = Database(tmp_path / "project-designator.db"); db.initialize(); now = "2026-01-01 00:00:00"
    component_id = db.connection.execute(
        "INSERT INTO components(product_code,product_name,current_stock,created_at,updated_at) "
        "VALUES('C1','电阻',10,?,?) RETURNING id", (now, now)
    ).fetchone()[0]
    db.connection.commit()
    service = ProjectService(db); project_id = service.create_project("位号")
    service.add_components(project_id, [component_id])
    page = ProjectsPage(service); qtbot.addWidget(page); page.refresh(project_id)

    assert page.component_table.horizontalHeaderItem(9).text() == "位号"
    item = page.component_table.item(0, 9)
    assert item.flags() & Qt.ItemIsEditable
    item.setText("R1,R2")

    assert page.save_configuration_button.isEnabled()
    assert service.list_components(project_id)[0]["reference_designator"] == ""
    page.save_configuration_button.click()
    assert service.list_components(project_id)[0]["reference_designator"] == "R1,R2"
    assert not page.save_configuration_button.isEnabled()


def test_project_designator_arrow_key_commits_and_edits_adjacent_row(qtbot, tmp_path):
    db = Database(tmp_path / "project-designator-nav.db"); db.initialize(); now = "2026-01-01 00:00:00"
    component_ids = []
    for code in ("C1", "C2"):
        component_ids.append(db.connection.execute(
            "INSERT INTO components(product_code,product_name,current_stock,created_at,updated_at) "
            "VALUES(?,?,10,?,?) RETURNING id", (code, code, now, now)
        ).fetchone()[0])
    db.connection.commit()
    service = ProjectService(db); project_id = service.create_project("导航")
    service.add_components(project_id, component_ids)
    page = ProjectsPage(service); qtbot.addWidget(page); page.refresh(project_id); page.show()
    first_item = page.component_table.item(0, 9)
    page.component_table.setCurrentItem(first_item)
    page.component_table.editItem(first_item)
    editor = page.component_table.findChild(QLineEdit)
    assert editor is not None
    editor.setText("R1")

    qtbot.keyClick(editor, Qt.Key_Down)
    qtbot.waitUntil(lambda: page.component_table.currentRow() == 1)

    assert page.component_table.item(0, 9).text() == "R1"
    assert page.component_table.currentColumn() == 9
    assert page.component_table.state() == QAbstractItemView.EditingState


def test_project_designator_arrow_navigation_uses_post_sort_position(qtbot, tmp_path):
    db = Database(tmp_path / "project-designator-post-sort.db"); db.initialize(); now = "2026-01-01 00:00:00"
    component_ids = []
    for code in ("C1", "C2", "C3"):
        component_ids.append(db.connection.execute(
            "INSERT INTO components(product_code,product_name,current_stock,created_at,updated_at) "
            "VALUES(?,?,10,?,?) RETURNING id", (code, code, now, now)
        ).fetchone()[0])
    db.connection.commit()
    service = ProjectService(db); project_id = service.create_project("排序后导航")
    service.add_components(project_id, component_ids)
    service.save_configuration(
        project_id,
        {component_id: 1 for component_id in component_ids},
        dict(zip(component_ids, ("A", "B", "C"))),
    )
    page = ProjectsPage(service); qtbot.addWidget(page); page.refresh(project_id); page.show()
    page.component_table.sortItems(9, Qt.AscendingOrder)
    edited_component_id = page.component_table.item(0, 0).data(Qt.UserRole)
    first_item = page.component_table.item(0, 9)
    page.component_table.setCurrentItem(first_item)
    page.component_table.editItem(first_item)
    editor = page.component_table.findChild(QLineEdit)
    editor.setText("Z")

    qtbot.keyClick(editor, Qt.Key_Down)
    qtbot.waitUntil(lambda: page.component_table.state() == QAbstractItemView.EditingState)

    assert page.component_table.item(page.component_table.currentRow(), 0).data(Qt.UserRole) == edited_component_id
    assert page.component_table.currentColumn() == 9


def test_project_sort_keeps_checked_component_identity(qtbot, tmp_path):
    db = Database(tmp_path / "project-sort.db"); db.initialize(); now = "2026-01-01 00:00:00"
    ids = []
    for code in ("C1", "C2"):
        ids.append(db.connection.execute(
            "INSERT INTO components(product_code,product_type,product_name,current_stock,created_at,updated_at) "
            "VALUES(?,?,?,?,?,?) RETURNING id", (code, "精确类型", code, 10, now, now)
        ).fetchone()[0])
    db.connection.commit()
    service = ProjectService(db); project_id = service.create_project("排序")
    service.add_components(project_id, ids)
    page = ProjectsPage(service); qtbot.addWidget(page); page.refresh(project_id)

    first_row = next(
        row for row in range(page.component_table.rowCount())
        if page.component_table.item(row, 0).data(Qt.UserRole) == ids[0]
    )
    page.toggle_row_checked(first_row)
    page.component_table.sortItems(0, Qt.DescendingOrder)

    assert page.component_table.item(0, 0).data(Qt.UserRole) == ids[1]
    assert page.selected_component_ids() == [ids[0]]
    sorted_spin = page.component_table.cellWidget(0, 6)
    assert sorted_spin.property("componentId") == ids[1]
    sorted_spin.setValue(3)
    quantities = {row["id"]: row["project_quantity"] for row in service.list_components(project_id)}
    assert quantities == {ids[0]: 1, ids[1]: 1}
    page.save_configuration_button.click()
    quantities = {row["id"]: row["project_quantity"] for row in service.list_components(project_id)}
    assert quantities == {ids[0]: 1, ids[1]: 3}
    page.toggle_row_checked(0)
    assert set(page.selected_component_ids()) == set(ids)


def test_project_shift_click_selects_visible_range_by_component_identity(qtbot, tmp_path):
    db = Database(tmp_path / "project-range.db"); db.initialize(); now = "2026-01-01 00:00:00"
    ids = []
    for code in ("C1", "C2", "C3", "C4", "C5"):
        ids.append(db.connection.execute(
            "INSERT INTO components(product_code,product_name,current_stock,created_at,updated_at) "
            "VALUES(?,?,10,?,?) RETURNING id", (code, code, now, now)
        ).fetchone()[0])
    db.connection.commit()
    service = ProjectService(db); project_id = service.create_project("连续选择")
    service.add_components(project_id, ids)
    page = ProjectsPage(service); qtbot.addWidget(page); page.refresh(project_id)

    page.toggle_row_checked(1)
    page.toggle_row_checked(4, Qt.ShiftModifier)

    displayed = [int(page.component_table.item(row, 0).data(Qt.UserRole)) for row in range(1, 5)]
    assert page.selected_component_ids() == displayed

    page.checked_component_ids.clear()
    anchor_row = next(row for row in range(5) if page.component_table.item(row, 0).data(Qt.UserRole) == ids[1])
    page.toggle_row_checked(anchor_row)
    page.component_table.sortItems(0, Qt.DescendingOrder)
    target_row = next(row for row in range(5) if page.component_table.item(row, 0).data(Qt.UserRole) == ids[4])
    page.toggle_row_checked(target_row, Qt.ShiftModifier)
    anchor_row = next(row for row in range(5) if page.component_table.item(row, 0).data(Qt.UserRole) == ids[1])
    low, high = sorted((anchor_row, target_row))
    expected = {
        int(page.component_table.item(row, 0).data(Qt.UserRole))
        for row in range(low, high + 1)
    }
    assert expected.issubset(page.checked_component_ids)


def test_project_sidebar_visibility_is_persisted(qtbot, tmp_path):
    db = Database(tmp_path / "project-sidebar.db"); db.initialize()
    settings_path = tmp_path / "project-sidebar.ini"
    first_settings = QSettings(str(settings_path), QSettings.IniFormat)
    first = ProjectsPage(ProjectService(db), first_settings); qtbot.addWidget(first); first.show()

    sidebar = first.findChild(QFrame, "projectSidebar")
    toggle = first.findChild(QPushButton, "projectSidebarToggle")
    assert sidebar.isVisible()
    toggle.click()
    assert sidebar.isVisible()
    assert not first.project_list.isVisible()
    assert sidebar.width() <= 56
    first_settings.sync()

    restored = ProjectsPage(ProjectService(db), QSettings(str(settings_path), QSettings.IniFormat))
    qtbot.addWidget(restored); restored.show()
    assert restored.findChild(QFrame, "projectSidebar").isVisible()
    assert not restored.project_list.isVisible()
    assert restored.findChild(QFrame, "projectSidebar").width() <= 56
    assert restored.findChild(QPushButton, "projectSidebarToggle").text() == "›"


def test_project_sidebar_and_action_row_match_approved_layout(qtbot, tmp_path):
    db = Database(tmp_path / "project-layout.db"); db.initialize()
    service = ProjectService(db); project_id = service.create_project("示例项目")
    page = ProjectsPage(service); qtbot.addWidget(page); page.refresh(project_id); page.show()

    assert page.findChild(QPushButton, "projectRenameButton") is None
    assert page.findChild(QPushButton, "projectDeleteButton") is None
    assert page.new_button.objectName() == "projectNewButton"
    assert page.new_button.parent() is page.project_sidebar
    assert page.project_sidebar_toggle.parent() is page.project_sidebar
    assert page.findChild(QLabel, "projectSidebarTitle").text() == "我的项目"
    assert page.save_configuration_button.text() == "保存元件配置"
    assert page.findChildren(QWidget, "projectListRow")
    assert page.findChild(QLabel, "projectCountBadge").text() == "0"


def test_export_rejects_unsaved_project_configuration(qtbot, tmp_path, monkeypatch):
    db = Database(tmp_path / "project-dirty-export.db"); db.initialize(); now = "2026-01-01 00:00:00"
    component_id = db.connection.execute(
        "INSERT INTO components(product_code,product_name,current_stock,created_at,updated_at) "
        "VALUES('C1','电阻',10,?,?) RETURNING id", (now, now)
    ).fetchone()[0]
    db.connection.commit()
    service = ProjectService(db); project_id = service.create_project("未保存")
    service.add_components(project_id, [component_id])
    page = ProjectsPage(service); qtbot.addWidget(page); page.refresh(project_id)
    warnings = []
    monkeypatch.setattr(QMessageBox, "warning", lambda *args, **kwargs: warnings.append(args[2]))
    monkeypatch.setattr(QMessageBox, "information", lambda *args, **kwargs: None)

    page.component_table.cellWidget(0, 6).setValue(2)
    page.sync_project()

    assert warnings == ["请先保存元件配置，再导出变更到元件库存。"]
    assert db.connection.execute("SELECT current_stock FROM components WHERE id=?", (component_id,)).fetchone()[0] == 10
    assert service.operation_history(project_id) == []


def test_project_switch_can_cancel_unsaved_configuration(qtbot, tmp_path, monkeypatch):
    db = Database(tmp_path / "project-switch-dirty.db"); db.initialize(); now = "2026-01-01 00:00:00"
    component_id = db.connection.execute(
        "INSERT INTO components(product_code,product_name,current_stock,created_at,updated_at) "
        "VALUES('C1','电阻',10,?,?) RETURNING id", (now, now)
    ).fetchone()[0]
    db.connection.commit()
    service = ProjectService(db)
    first_id = service.create_project("项目一"); service.add_components(first_id, [component_id])
    second_id = service.create_project("项目二")
    page = ProjectsPage(service); qtbot.addWidget(page); page.refresh(first_id)
    page.component_table.cellWidget(0, 6).setValue(2)
    monkeypatch.setattr(QMessageBox, "question", lambda *args, **kwargs: QMessageBox.Cancel)
    second_row = next(
        row for row in range(page.project_list.count())
        if page.project_list.item(row).data(Qt.UserRole) == second_id
    )

    page.project_list.setCurrentRow(second_row)

    assert page.current_project_id == first_id
    assert page.has_unsaved_configuration()


def test_project_switch_can_save_unsaved_configuration(qtbot, tmp_path, monkeypatch):
    db = Database(tmp_path / "project-switch-save.db"); db.initialize(); now = "2026-01-01 00:00:00"
    component_id = db.connection.execute(
        "INSERT INTO components(product_code,product_name,current_stock,created_at,updated_at) "
        "VALUES('C1','电阻',10,?,?) RETURNING id", (now, now)
    ).fetchone()[0]
    db.connection.commit()
    service = ProjectService(db)
    first_id = service.create_project("项目一"); service.add_components(first_id, [component_id])
    second_id = service.create_project("项目二")
    page = ProjectsPage(service); qtbot.addWidget(page); page.refresh(first_id)
    page.component_table.cellWidget(0, 6).setValue(3)
    monkeypatch.setattr(QMessageBox, "question", lambda *args, **kwargs: QMessageBox.Save)
    second_row = next(
        row for row in range(page.project_list.count())
        if page.project_list.item(row).data(Qt.UserRole) == second_id
    )

    page.project_list.setCurrentRow(second_row)

    assert page.current_project_id == second_id
    assert page.project_list.currentItem().data(Qt.UserRole) == second_id
    assert page.project_title.text() == "项目二"
    assert page.component_table.rowCount() == 0
    assert service.list_components(first_id)[0]["project_quantity"] == 3


def test_project_context_menu_does_not_open_for_cancelled_project_switch(qtbot, tmp_path, monkeypatch):
    db = Database(tmp_path / "project-menu-cancel.db"); db.initialize(); now = "2026-01-01 00:00:00"
    component_id = db.connection.execute(
        "INSERT INTO components(product_code,product_name,current_stock,created_at,updated_at) "
        "VALUES('C1','电阻',10,?,?) RETURNING id", (now, now)
    ).fetchone()[0]
    db.connection.commit()
    service = ProjectService(db)
    first_id = service.create_project("项目一"); service.add_components(first_id, [component_id])
    second_id = service.create_project("项目二")
    page = ProjectsPage(service); qtbot.addWidget(page); page.refresh(first_id); page.show()
    page.component_table.cellWidget(0, 6).setValue(2)
    monkeypatch.setattr(QMessageBox, "question", lambda *args, **kwargs: QMessageBox.Cancel)
    menu_opened = []

    class FakeMenu:
        def exec(self, *args):
            menu_opened.append(args)

    monkeypatch.setattr(page, "build_project_menu", lambda: FakeMenu())
    second_item = next(
        page.project_list.item(row) for row in range(page.project_list.count())
        if page.project_list.item(row).data(Qt.UserRole) == second_id
    )

    page.show_project_menu(page.project_list.visualItemRect(second_item).center())

    assert page.current_project_id == first_id
    assert page.project_list.currentItem().data(Qt.UserRole) == first_id
    assert menu_opened == []


def test_new_project_can_cancel_before_discarding_unsaved_configuration(qtbot, tmp_path, monkeypatch):
    db = Database(tmp_path / "project-new-cancel.db"); db.initialize(); now = "2026-01-01 00:00:00"
    component_id = db.connection.execute(
        "INSERT INTO components(product_code,product_name,current_stock,created_at,updated_at) "
        "VALUES('C1','电阻',10,?,?) RETURNING id", (now, now)
    ).fetchone()[0]
    db.connection.commit()
    service = ProjectService(db); project_id = service.create_project("现有项目")
    service.add_components(project_id, [component_id])
    page = ProjectsPage(service); qtbot.addWidget(page); page.refresh(project_id)
    page.component_table.cellWidget(0, 6).setValue(2)
    monkeypatch.setattr(QMessageBox, "question", lambda *args, **kwargs: QMessageBox.Cancel)
    monkeypatch.setattr(QInputDialog, "getText", lambda *args, **kwargs: ("不应创建", True))

    page.create_project()

    assert [project["name"] for project in service.list_projects()] == ["现有项目"]
    assert page.current_project_id == project_id


def test_project_context_menu_contains_management_actions(qtbot, tmp_path):
    db = Database(tmp_path / "project-menu.db"); db.initialize()
    page = ProjectsPage(ProjectService(db)); qtbot.addWidget(page)
    assert [action.text() for action in page.build_project_menu().actions() if not action.isSeparator()] == [
        "新建项目", "重命名项目", "删除项目"
    ]


def test_project_page_deletes_checked_rows_and_returns_synced_stock(qtbot, tmp_path, monkeypatch):
    db = Database(tmp_path / "project-delete.db"); db.initialize(); now = "2026-01-01 00:00:00"
    component_id = db.connection.execute(
        "INSERT INTO components(product_code,product_name,current_stock,created_at,updated_at) "
        "VALUES('C1','电阻',10,?,?) RETURNING id", (now, now)
    ).fetchone()[0]
    db.connection.commit()
    service = ProjectService(db); project_id = service.create_project("删除")
    service.add_components(project_id, [component_id]); service.sync(project_id)
    page = ProjectsPage(service); qtbot.addWidget(page); page.refresh(project_id)
    page.toggle_row_checked(0)
    monkeypatch.setattr(QMessageBox, "question", lambda *args, **kwargs: QMessageBox.Yes)

    page.remove_selected_components()

    assert page.component_table.rowCount() == 0
    assert db.connection.execute("SELECT current_stock FROM components WHERE id=?", (component_id,)).fetchone()[0] == 10
    assert service.operation_history(project_id, lines=True)[0]["movement_type"] == "project_return"


def test_project_row_delete_button_requires_confirmation(qtbot, tmp_path, monkeypatch):
    db = Database(tmp_path / "project-row-delete-cancel.db"); db.initialize(); now = "2026-01-01 00:00:00"
    component_id = db.connection.execute(
        "INSERT INTO components(product_code,product_name,current_stock,created_at,updated_at) "
        "VALUES('C1','电阻',10,?,?) RETURNING id", (now, now)
    ).fetchone()[0]
    db.connection.commit()
    service = ProjectService(db); project_id = service.create_project("取消删除")
    service.add_components(project_id, [component_id])
    page = ProjectsPage(service); qtbot.addWidget(page); page.refresh(project_id)
    questions = []
    monkeypatch.setattr(
        QMessageBox,
        "question",
        lambda *args, **kwargs: questions.append(args[2]) or QMessageBox.No,
    )

    button = page.component_table.cellWidget(0, 10)
    assert button.property("componentId") == component_id
    button.click()

    assert "C1" in questions[0]
    assert [row["id"] for row in service.list_components(project_id)] == [component_id]
    assert page.component_table.rowCount() == 1


def test_project_row_delete_preserves_other_drafts_after_sort(qtbot, tmp_path, monkeypatch):
    db = Database(tmp_path / "project-row-delete-drafts.db"); db.initialize(); now = "2026-01-01 00:00:00"
    component_ids = []
    for code in ("C1", "C2"):
        component_ids.append(db.connection.execute(
            "INSERT INTO components(product_code,product_name,current_stock,created_at,updated_at) "
            "VALUES(?,?,10,?,?) RETURNING id", (code, code, now, now)
        ).fetchone()[0])
    db.connection.commit()
    service = ProjectService(db); project_id = service.create_project("保留草稿")
    service.add_components(project_id, component_ids)
    page = ProjectsPage(service); qtbot.addWidget(page); page.refresh(project_id)
    page.component_table.sortItems(0, Qt.DescendingOrder)
    target_id, other_id = component_ids
    target_row = next(
        row for row in range(page.component_table.rowCount())
        if page.component_table.item(row, 0).data(Qt.UserRole) == target_id
    )
    other_row = next(
        row for row in range(page.component_table.rowCount())
        if page.component_table.item(row, 0).data(Qt.UserRole) == other_id
    )
    page.component_table.cellWidget(other_row, 6).setValue(4)
    page.component_table.item(other_row, 9).setText("R4")
    monkeypatch.setattr(QMessageBox, "question", lambda *args, **kwargs: QMessageBox.Yes)

    page.component_table.cellWidget(target_row, 10).click()

    assert [row["id"] for row in service.list_components(project_id)] == [other_id]
    assert page._draft_quantities == {other_id: 4}
    assert page._draft_reference_designators == {other_id: "R4"}
    assert page.has_unsaved_configuration()
    remaining_row = next(
        row for row in range(page.component_table.rowCount())
        if page.component_table.item(row, 0).data(Qt.UserRole) == other_id
    )
    assert page.component_table.cellWidget(remaining_row, 6).value() == 4
    assert page.component_table.item(remaining_row, 9).text() == "R4"


def test_project_row_delete_returns_synced_stock_without_checkbox(qtbot, tmp_path, monkeypatch):
    db = Database(tmp_path / "project-row-delete-synced.db"); db.initialize(); now = "2026-01-01 00:00:00"
    component_id = db.connection.execute(
        "INSERT INTO components(product_code,product_name,current_stock,created_at,updated_at) "
        "VALUES('C1','电阻',10,?,?) RETURNING id", (now, now)
    ).fetchone()[0]
    db.connection.commit()
    service = ProjectService(db); project_id = service.create_project("直接删除")
    service.add_components(project_id, [component_id]); service.sync(project_id)
    page = ProjectsPage(service); qtbot.addWidget(page); page.refresh(project_id)
    monkeypatch.setattr(QMessageBox, "question", lambda *args, **kwargs: QMessageBox.Yes)
    inventory_updates = []
    page.inventory_changed.connect(lambda: inventory_updates.append(True))

    assert page.selected_component_ids() == []
    page.component_table.cellWidget(0, 10).click()

    assert page.component_table.rowCount() == 0
    assert db.connection.execute(
        "SELECT current_stock FROM components WHERE id=?", (component_id,)
    ).fetchone()[0] == 10
    assert inventory_updates == [True]
    assert service.operation_history(project_id, lines=True)[0]["movement_type"] == "project_return"
