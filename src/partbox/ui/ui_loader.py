from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

from PySide6.QtCore import QFile, QIODevice
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QLineEdit, QListWidget, QMainWindow, QPushButton,
    QScrollArea, QStackedWidget, QTableWidget, QWidget,
)


REQUIRED_TYPES = {
    "brandEnglish": QLabel, "brandChinese": QWidget, "searchInput": QLineEdit,
    "materialImportButton": QPushButton,
    "navigation": QListWidget, "pages": QStackedWidget, "inventoryPage": QWidget,
    "filterScroll": QScrollArea, "filterBar": QWidget, "filterRow": QHBoxLayout,
    "statKindsValue": QLabel, "statStockValue": QLabel, "statSpentValue": QLabel,
    "statOrdersValue": QLabel, "componentTable": QTableWidget, "summaryPanel": QFrame,
    "projectImportCard": QFrame, "projectImportButton": QPushButton,
    "comparisonAddCard": QFrame, "comparisonAddButton": QPushButton,
    "summaryToggleButton": QPushButton,
    "summaryTitle": QLabel, "summaryProductCode": QLabel, "summaryProductType": QLabel,
    "summaryPackage": QLabel, "summaryBrand": QLabel, "summaryCurrentStock": QLabel,
    "summaryLatestOrderTime": QLabel, "summaryLocation": QLabel,
    "stockInButton": QPushButton, "stockOutButton": QPushButton, "historyButton": QPushButton,
}
REQUIRED_OBJECTS = tuple(REQUIRED_TYPES)
RETIRED_OBJECTS = ("orderDetailImportButton",)


def builtin_main_ui_path() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS) / "partbox" / "ui" / "forms" / "main_window.ui"
    return Path(__file__).resolve().parent / "forms" / "main_window.ui"


def external_main_ui_path() -> Path | None:
    override = os.environ.get("PARTBOX_UI_PATH")
    if override:
        return Path(override)
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent / "main_window.ui"
    return None


def _load(path: Path, parent=None) -> QMainWindow:
    source = QFile(str(path))
    if not source.open(QIODevice.ReadOnly):
        raise OSError(f"无法读取界面文件：{path}")
    try:
        window = QUiLoader().load(source, parent)
    finally:
        source.close()
    if not isinstance(window, QMainWindow):
        raise ValueError(f"界面根控件必须是 QMainWindow：{path}")
    invalid = [
        f"{name}（应为 {expected.__name__}）"
        for name, expected in REQUIRED_TYPES.items()
        if window.findChild(expected, name) is None
    ]
    invalid.extend(
        f"{name}（该控件已停用）"
        for name in RETIRED_OBJECTS
        if window.findChild(object, name) is not None
    )
    pages = window.findChild(QStackedWidget, "pages")
    navigation = window.findChild(QListWidget, "navigation")
    if pages is not None and pages.count() < 1:
        invalid.append("pages（必须包含库存页）")
    if navigation is not None and navigation.count() < 6:
        invalid.append("navigation（必须包含六个导航项）")
    if invalid:
        window.deleteLater()
        raise ValueError("界面控件无效：" + "、".join(invalid))
    return window


def load_main_ui(parent=None) -> tuple[QMainWindow, Path]:
    external = external_main_ui_path()
    if external:
        if external.exists():
            try:
                return _load(external, parent), external
            except Exception:
                logging.exception("External PartBOX UI is invalid; using builtin UI")
        else:
            logging.warning("External PartBOX UI is missing; using builtin UI: %s", external)
    builtin = builtin_main_ui_path()
    return _load(builtin, parent), builtin
