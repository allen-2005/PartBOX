from partbox.app import build_application
from PySide6.QtGui import QFontDatabase


def test_build_application_starts_with_empty_database(qtbot, tmp_path, monkeypatch):
    monkeypatch.setenv("PARTBOX_DATA_DIR", str(tmp_path))
    app, window, services = build_application([])
    qtbot.addWidget(window)
    assert services.inventory.stats() == {"kinds": 0, "stock": 0, "spent": 0, "orders": 0}
    assert window.component_table.rowCount() == 0
    assert not app.windowIcon().isNull()
    assert any("YaHei" in family or "雅黑" in family for family in QFontDatabase.families())
    services.db.close()
