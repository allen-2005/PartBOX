from pathlib import Path

from PySide6.QtWidgets import QFrame, QLineEdit, QListWidget, QMainWindow, QPushButton, QWidget

from partbox.ui.ui_loader import REQUIRED_OBJECTS, builtin_main_ui_path, load_main_ui


def test_designer_ui_exists_and_contains_business_controls(qtbot):
    path = builtin_main_ui_path()
    assert path.suffix == ".ui"
    assert path.exists()

    loaded, used_path = load_main_ui()
    qtbot.addWidget(loaded)
    assert isinstance(loaded, QMainWindow)
    assert used_path == path
    missing = [name for name in REQUIRED_OBJECTS if loaded.findChild(object, name) is None]
    assert missing == []
    assert loaded.findChild(QPushButton, "orderDetailImportButton") is None


def test_a_style_shell_geometry(qtbot):
    loaded, _ = load_main_ui()
    qtbot.addWidget(loaded)
    assert loaded.findChild(QFrame, "topBar").minimumHeight() == 88
    assert loaded.findChild(QLineEdit, "searchInput").minimumHeight() == 48
    assert loaded.findChild(QListWidget, "navigation").minimumWidth() == 168
    assert loaded.findChild(QWidget, "inventoryPage").objectName() == "inventoryPage"


def test_invalid_external_ui_falls_back_to_builtin(qtbot, tmp_path, monkeypatch):
    invalid = tmp_path / "broken.ui"
    invalid.write_text("<ui version='4.0'><class>Broken</class></ui>", encoding="utf-8")
    monkeypatch.setenv("PARTBOX_UI_PATH", str(invalid))

    loaded, used_path = load_main_ui()
    qtbot.addWidget(loaded)
    assert used_path == builtin_main_ui_path()
    assert loaded.findChild(object, "componentTable") is not None


def test_wrong_control_type_in_external_ui_falls_back_to_builtin(qtbot, tmp_path, monkeypatch):
    external = tmp_path / "wrong-type.ui"
    content = builtin_main_ui_path().read_text(encoding="utf-8")
    external.write_text(
        content.replace('class="QTableWidget" name="componentTable"',
                        'class="QTableView" name="componentTable"'),
        encoding="utf-8",
    )
    monkeypatch.setenv("PARTBOX_UI_PATH", str(external))

    loaded, used_path = load_main_ui()
    qtbot.addWidget(loaded)
    assert used_path == builtin_main_ui_path()


def test_external_ui_with_retired_order_detail_button_falls_back_to_builtin(qtbot, tmp_path, monkeypatch):
    external = tmp_path / "old-main-window.ui"
    content = builtin_main_ui_path().read_text(encoding="utf-8")
    material = '<item><widget class="QPushButton" name="materialImportButton"><property name="text"><string>＋ 导入物料明细</string></property></widget></item>'
    retired = '<item><widget class="QPushButton" name="orderDetailImportButton"><property name="text"><string>＋ 导入订单详情</string></property></widget></item>'
    external.write_text(content.replace(material, material + retired), encoding="utf-8")
    monkeypatch.setenv("PARTBOX_UI_PATH", str(external))

    loaded, used_path = load_main_ui()
    qtbot.addWidget(loaded)

    assert used_path == builtin_main_ui_path()
    assert loaded.findChild(QPushButton, "orderDetailImportButton") is None


def test_external_ui_without_project_import_card_falls_back_to_builtin(qtbot, tmp_path, monkeypatch):
    external = tmp_path / "pre-project-card.ui"
    content = builtin_main_ui_path().read_text(encoding="utf-8")
    card_start = content.index('<item><widget class="QFrame" name="projectImportCard">')
    card_end = content.index('</layout></widget></item>', card_start) + len('</layout></widget></item>')
    external.write_text(content[:card_start] + content[card_end:], encoding="utf-8")
    monkeypatch.setenv("PARTBOX_UI_PATH", str(external))

    loaded, used_path = load_main_ui()
    qtbot.addWidget(loaded)

    assert used_path == builtin_main_ui_path()
    assert loaded.findChild(QPushButton, "projectImportButton") is not None
