from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QEvent, QSettings, Qt, Signal
from PySide6.QtGui import QBitmap, QColor, QGuiApplication, QPixmap, QRegion
from PySide6.QtWidgets import (
    QAbstractItemView, QDialog, QFileDialog, QFrame, QHBoxLayout, QLabel, QLineEdit,
    QListWidget, QMainWindow, QPushButton, QScrollArea, QSplitter, QStackedWidget, QVBoxLayout,
    QTableWidget, QTableWidgetItem, QWidget, QMessageBox, QToolTip, QInputDialog,
)

from partbox.database import Database
from partbox.categories import available_categories, component_category
from partbox.services import ImportService, InventoryService, StockService
from partbox.services import DataService
from partbox.paths import AppPaths
from partbox.importer import parse_statement
from partbox.projects import ProjectService
from partbox.comparison import ComparisonService
from partbox.ui.aux_pages import HistoryPage, ImportsPage, SettingsPage
from partbox.ui.theme import APP_STYLESHEET
from partbox.ui.import_dialog import ImportDialog
from partbox.ui.stock_dialog import StockDialog
from partbox.ui.inventory_header import InventoryHeader
from partbox.ui.ui_loader import load_main_ui
from partbox.ui.projects_page import ProjectsPage
from partbox.ui.comparison_page import ComparisonPage
from partbox.ui.bom_optimizer import BomOptimizerDialog
from partbox.ui.selection_header import SelectionHeader


@dataclass
class ServiceContainer:
    db: Database
    inventory: InventoryService
    importer: ImportService
    stocks: StockService
    data: DataService | None = None
    paths: AppPaths | None = None
    projects: ProjectService | None = None
    comparison: ComparisonService | None = None


COLUMNS = [
    ("product_code", "商品编号"), ("product_type", "商品类型"),
    ("product_name", "商品名称"), ("model", "商品型号"),
    ("package", "封装格式"), ("brand", "品牌"),
    ("current_stock", "当前库存"), ("total_purchased", "累计购买"),
    ("unit", "商品单位"), ("latest_unit_price", "最近单价（含税）"),
    ("total_spent", "累计采购金额"), ("latest_order_time", "最近下单时间"),
    ("location", "存放位置"), ("notes", "备注"), ("updated_at", "最后修改时间"),
]
DEFAULT_COLUMN_WIDTHS = [100, 110, 260, 150, 150, 140, 90, 90, 70, 120, 120, 150, 120, 180, 150]
LOGO_WIDTH = 112


def logo_asset_path(name: str) -> Path:
    project_asset = Path(__file__).resolve().parents[3] / "assets" / name
    if getattr(sys, "frozen", False):
        candidates = (
            Path(sys.executable).resolve().parent / "logo" / name,
            Path(sys._MEIPASS) / "assets" / name,
        )
    else:
        candidates = (
            Path.home() / "Desktop" / "PartBOX" / "logo" / name,
            project_asset,
        )
    return next((path for path in candidates if path.exists()), candidates[-1])


def trimmed_logo_pixmap(path: Path) -> QPixmap:
    pixmap = QPixmap(str(path))
    if pixmap.isNull():
        return pixmap
    alpha_mask = QBitmap.fromImage(pixmap.toImage().createAlphaMask())
    visible = QRegion(alpha_mask).boundingRect()
    return pixmap.copy(visible) if visible.isValid() and not visible.isEmpty() else pixmap


def set_logo_pixmap(label: QLabel, source: QPixmap, width: int) -> None:
    scaled = source.scaled(
        width,
        10_000,
        Qt.KeepAspectRatio,
        Qt.SmoothTransformation,
    )
    label.setFixedSize(scaled.size())
    label.setScaledContents(False)
    label.setPixmap(scaled)


class NumericTableWidgetItem(QTableWidgetItem):
    def __init__(self, text: str, sort_value: float):
        super().__init__(text)
        self.sort_value = sort_value

    def __lt__(self, other):
        if isinstance(other, NumericTableWidgetItem):
            return self.sort_value < other.sort_value
        return super().__lt__(other)


class CopyLabel(QLabel):
    clicked = Signal()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


class MainWindow(QMainWindow):
    def __init__(self, services: ServiceContainer, settings: QSettings | None = None):
        super().__init__()
        self.services = services
        self.settings = settings or QSettings()
        self.columns = COLUMNS
        self.rows: list[dict] = []
        self.checked_component_ids: set[int] = set()
        self._selection_anchor_id: int | None = None
        self._updating = False
        self.active_filter = ""
        self._build()
        self.refresh()

    def _build(self):
        loaded, self.ui_path = load_main_ui()
        self.setWindowTitle(loaded.windowTitle())
        self.resize(loaded.size())
        self.setMinimumSize(loaded.minimumSize())
        self.setCentralWidget(loaded.takeCentralWidget())
        loaded.deleteLater()
        self.setStyleSheet(APP_STYLESHEET)

        self.search_input = self.findChild(QLineEdit, "searchInput")
        self.material_import_button = self.findChild(QPushButton, "materialImportButton")
        self.nav_list = self.findChild(QListWidget, "navigation")
        self.pages = self.findChild(QStackedWidget, "pages")
        self.inventory_page = self.findChild(QWidget, "inventoryPage")
        self.filter_scroll = self.findChild(QScrollArea, "filterScroll")
        self.filter_bar = self.findChild(QWidget, "filterBar")
        self.filter_row = self.findChild(QHBoxLayout, "filterRow")
        self.component_table = self.findChild(QTableWidget, "componentTable")
        self.summary_title = self.findChild(QLabel, "summaryTitle")
        self.summary_panel = self.findChild(QFrame, "summaryPanel")
        self.summary_toggle_button = self.findChild(QPushButton, "summaryToggleButton")
        self.stock_in_button = self.findChild(QPushButton, "stockInButton")
        self.stock_out_button = self.findChild(QPushButton, "stockOutButton")
        self.history_button = self.findChild(QPushButton, "historyButton")
        self.project_import_button = self.findChild(QPushButton, "projectImportButton")
        self.comparison_add_button = self.findChild(QPushButton, "comparisonAddButton")

        self.stat_values = {
            "kinds": self.findChild(QLabel, "statKindsValue"),
            "stock": self.findChild(QLabel, "statStockValue"),
            "spent": self.findChild(QLabel, "statSpentValue"),
            "orders": self.findChild(QLabel, "statOrdersValue"),
        }
        self.summary_labels = {
            "product_code": self.findChild(QLabel, "summaryProductCode"),
            "product_type": self.findChild(QLabel, "summaryProductType"),
            "package": self.findChild(QLabel, "summaryPackage"),
            "brand": self.findChild(QLabel, "summaryBrand"),
            "current_stock": self.findChild(QLabel, "summaryCurrentStock"),
            "latest_order_time": self.findChild(QLabel, "summaryLatestOrderTime"),
            "location": self.findChild(QLabel, "summaryLocation"),
        }
        self._configure_brand_artwork()

        data_service = self.services.data or DataService(self.services.db)
        project_service = self.services.projects or ProjectService(self.services.db)
        self.services.projects = project_service
        comparison_service = self.services.comparison or ComparisonService(self.services.db)
        self.services.comparison = comparison_service
        self.comparison_page = ComparisonPage(comparison_service); self.pages.addWidget(self.comparison_page)
        self.projects_page = ProjectsPage(project_service, self.settings)
        self.projects_page.inventory_changed.connect(self.refresh)
        self.projects_page.bom_requested.connect(self.open_bom_optimizer)
        self.pages.addWidget(self.projects_page)
        self.history_page = HistoryPage(data_service, self.services.stocks); self.history_page.changed.connect(self.refresh); self.pages.addWidget(self.history_page)
        self.imports_page = ImportsPage(data_service); self.pages.addWidget(self.imports_page)
        backup_dir = self.services.paths.backups if self.services.paths else self.services.db.path.parent / "backups"
        self.settings_page = SettingsPage(data_service, backup_dir); self.settings_page.changed.connect(self.refresh); self.pages.addWidget(self.settings_page)
        self.nav_list.setCurrentRow(0)

        self.filter_buttons = []
        self._rebuild_filter_buttons([])
        self.component_table.setColumnCount(len(COLUMNS))
        self.component_table.setHorizontalHeaderLabels([title for _, title in COLUMNS])
        self.component_table.setSortingEnabled(True)
        self.inventory_header = InventoryHeader(COLUMNS, DEFAULT_COLUMN_WIDTHS, self.settings, self.component_table)
        self.component_table.setHorizontalHeader(self.inventory_header)
        self.inventory_header.restore_layout()
        self.inventory_header.setSortIndicatorShown(False)
        self.component_table.setVerticalHeader(SelectionHeader(
            Qt.Vertical, self.component_table, lambda: self.checked_component_ids
        ))
        self.component_table.verticalHeader().setDefaultSectionSize(36)
        self.component_table.verticalHeader().setFixedWidth(42)
        self.component_table.verticalHeader().setSectionsClickable(True)
        self.component_table.verticalHeader().setToolTip("点击方框选择元件，之后可导入项目")
        self.project_import_button.setEnabled(False)
        self.comparison_add_button.setEnabled(False)
        stats_layout = self.findChild(QHBoxLayout, "statsLayout")
        for index in range(4):
            stats_layout.setStretch(index, 1)
        stats_layout.setStretch(4, 0)
        visible = self.settings.value("ui/summary_visible", True, type=bool)
        self.summary_panel.setVisible(visible)
        self.summary_toggle_button.setText("›" if visible else "‹")

        self.nav_list.currentRowChanged.connect(self.change_page)
        self.material_import_button.clicked.connect(self.choose_material_files)
        self.summary_toggle_button.clicked.connect(self.toggle_summary_panel)
        self.search_input.textChanged.connect(self.refresh)
        self.stock_in_button.clicked.connect(lambda: self.open_stock_dialog("in"))
        self.stock_out_button.clicked.connect(lambda: self.open_stock_dialog("out"))
        self.component_table.itemSelectionChanged.connect(self.update_summary)
        self.component_table.itemChanged.connect(self.save_cell_edit)
        self.component_table.verticalHeader().sectionClicked.connect(self.toggle_row_checked)
        self.component_table.model().layoutChanged.connect(self._sync_row_checkboxes)
        self.project_import_button.clicked.connect(self.import_selected_to_project)
        self.comparison_add_button.clicked.connect(self.add_selected_to_comparison)
        self.copyable_labels = [self.summary_title, *self.summary_labels.values()]
        for label in self.copyable_labels:
            label.setCursor(Qt.PointingHandCursor)
            label.installEventFilter(self)

    def _configure_brand_artwork(self):
        top_bar = self.findChild(QFrame, "topBar")
        brand_block = self.findChild(QWidget, "brandBlock")
        brand_english = self.findChild(QLabel, "brandEnglish")
        brand_chinese = self.findChild(QWidget, "brandChinese")
        top_bar_layout = self.findChild(QHBoxLayout, "topBarLayout")

        english = trimmed_logo_pixmap(logo_asset_path("partbox-wordmark-v1.png"))
        chinese = trimmed_logo_pixmap(logo_asset_path("partbox-chinese-wordmark-v1.png"))
        if english.isNull() or chinese.isNull():
            return

        top_bar.setFixedHeight(88)
        top_bar_layout.setSpacing(20)
        top_bar_layout.setContentsMargins(24, 12, 20, 12)
        brand_block.setFixedWidth(180)

        brand_english.clear()
        set_logo_pixmap(brand_english, english, LOGO_WIDTH)

        chinese_layout = brand_chinese.layout()
        while chinese_layout.count():
            item = chinese_layout.takeAt(0)
            if item.widget() is not None:
                item.widget().hide()
        chinese_label = QLabel(brand_chinese)
        chinese_label.setObjectName("brandChineseLogo")
        set_logo_pixmap(chinese_label, chinese, LOGO_WIDTH)
        brand_chinese.setFixedSize(chinese_label.size())
        chinese_layout.addWidget(chinese_label)

    def change_page(self, index: int):
        self.pages.setCurrentIndex(index)
        if index == 1: self.comparison_page.refresh()
        elif index == 2: self.projects_page.refresh()
        elif index == 3: self.history_page.refresh()
        elif index == 4: self.imports_page.refresh()

    def apply_filter(self, selected):
        self.active_filter = selected.property("filterValue")
        self.refresh()

    def _rebuild_filter_buttons(self, rows):
        categories = available_categories(rows)
        valid_values = {"", *categories}
        if self.active_filter not in valid_values:
            self.active_filter = ""
        while self.filter_row.count():
            item = self.filter_row.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.filter_buttons = []
        entries = [("全部", ""), *((name, name) for name in categories)]
        for text, value in entries:
            button = QPushButton(text, objectName="filterButton")
            button.setCheckable(True); button.setProperty("filterValue", value)
            button.setChecked(value == self.active_filter)
            button.clicked.connect(lambda checked=False, b=button: self.apply_filter(b))
            self.filter_buttons.append(button); self.filter_row.addWidget(button)
        self.filter_row.addStretch()

    def choose_material_files(self):
        self._choose_import_files()

    def _choose_import_files(self):
        paths, _ = QFileDialog.getOpenFileNames(self, "选择立创商城物料明细", "", "Excel 文件 (*.xls *.xlsx)")
        if not paths: return
        self.import_files(paths)

    def import_files(self, paths):
        try:
            preview = self.services.importer.preview(paths, parser=parse_statement)
        except Exception as error:
            message = str(error)
            if "文件已导入" in message:
                force = QMessageBox.question(
                    self,
                    "检测到重复文件",
                    message + "\n\n是否重新读取？已记录的采购不会重复累计。",
                    QMessageBox.Yes | QMessageBox.No,
                )
                if force != QMessageBox.Yes: return
                try: preview = self.services.importer.preview(paths, force=True, parser=parse_statement)
                except Exception as second_error: QMessageBox.critical(self, "读取失败", str(second_error)); return
            else:
                QMessageBox.critical(self, "物料明细读取失败", message); return
        dialog = ImportDialog(self.services.importer, self); dialog.set_format_name("物料明细"); dialog.set_preview(preview)
        if dialog.exec() == QDialog.Accepted:
            self.refresh(); QMessageBox.information(self, "导入完成", "订单已成功导入。")

    def open_stock_dialog(self, mode: str):
        data = self.current_row_data()
        if not data:
            QMessageBox.information(self, "请选择元件", "请先在表格中选择一个元件。")
            return
        dialog = StockDialog(self.services.stocks, data["id"], data["model"] or data["product_name"], data["current_stock"], data["unit"], mode, self)
        if dialog.exec() == QDialog.Accepted: self.refresh()

    def clear_filters(self):
        self.active_filter = ""
        self.search_input.blockSignals(True); self.search_input.clear(); self.search_input.blockSignals(False)
        self.refresh()

    def refresh(self):
        all_rows = self.services.inventory.list_components()
        self._rebuild_filter_buttons(all_rows)
        self.rows = self.services.inventory.list_components(self.search_input.text())
        if self.active_filter:
            self.rows = [row for row in self.rows if component_category(row) == self.active_filter]
        visible_ids = {int(row["id"]) for row in self.rows}
        self.checked_component_ids.intersection_update(visible_ids)
        self._updating = True; self.component_table.setSortingEnabled(False); self.component_table.setRowCount(len(self.rows))
        editable = {"current_stock", "location", "notes"}
        for row_index, row in enumerate(self.rows):
            vertical = QTableWidgetItem()
            vertical.setFlags(Qt.ItemIsEnabled | Qt.ItemIsUserCheckable)
            vertical.setCheckState(Qt.Checked if row["id"] in self.checked_component_ids else Qt.Unchecked)
            vertical.setData(Qt.UserRole, row["id"])
            self.component_table.setVerticalHeaderItem(row_index, vertical)
            for column, (key, _) in enumerate(COLUMNS):
                value = row.get(key, "")
                if key in {"latest_unit_price", "total_spent"}: text = f"¥{float(value or 0):,.4f}" if key == "latest_unit_price" else f"¥{float(value or 0):,.2f}"
                else: text = str(value if value is not None else "")
                numeric_keys = {"current_stock", "total_purchased", "latest_unit_price", "total_spent"}
                item = NumericTableWidgetItem(text, float(value or 0)) if key in numeric_keys else QTableWidgetItem(text)
                item.setData(Qt.UserRole, row["id"])
                if key not in editable: item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                else: item.setBackground(QColor("#eef5ff"))
                self.component_table.setItem(row_index, column, item)
        self.component_table.setSortingEnabled(True); self._updating = False
        stats = self.services.inventory.stats()
        self.stat_values["kinds"].setText(f"{stats['kinds']:,}"); self.stat_values["stock"].setText(f"{stats['stock']:,}")
        self.stat_values["spent"].setText(f"¥{stats['spent']:,.2f}"); self.stat_values["orders"].setText(f"{stats['orders']:,}")
        self.update_summary()

    def current_row_data(self):
        row = self.component_table.currentRow()
        if row < 0: return None
        item = self.component_table.item(row, 0)
        if not item: return None
        component_id = item.data(Qt.UserRole)
        return next((data for data in self.rows if data["id"] == component_id), None)

    def _row_for_component_id(self, component_id: int) -> int | None:
        return next((
            row
            for row in range(self.component_table.rowCount())
            if (item := self.component_table.item(row, 0)) is not None
            and item.data(Qt.UserRole) is not None
            and int(item.data(Qt.UserRole)) == component_id
        ), None)

    def toggle_row_checked(self, row: int, modifiers=None):
        item = self.component_table.item(row, 0)
        if item is None or item.data(Qt.UserRole) is None:
            return
        component_id = int(item.data(Qt.UserRole))
        modifiers = QGuiApplication.keyboardModifiers() if modifiers is None else modifiers
        anchor_row = self._row_for_component_id(self._selection_anchor_id) if self._selection_anchor_id is not None else None
        if modifiers & Qt.ShiftModifier and anchor_row is not None:
            low, high = sorted((anchor_row, row))
            for range_row in range(low, high + 1):
                range_item = self.component_table.item(range_row, 0)
                if range_item is not None and range_item.data(Qt.UserRole) is not None:
                    self.checked_component_ids.add(int(range_item.data(Qt.UserRole)))
        else:
            if component_id in self.checked_component_ids:
                self.checked_component_ids.remove(component_id)
            else:
                self.checked_component_ids.add(component_id)
            self._selection_anchor_id = component_id
        self._sync_row_checkboxes()
        self.project_import_button.setEnabled(bool(self.checked_component_ids))
        self.comparison_add_button.setEnabled(bool(self.checked_component_ids))

    def selected_component_ids(self) -> list[int]:
        return [
            int(item.data(Qt.UserRole))
            for row in range(self.component_table.rowCount())
            if (item := self.component_table.item(row, 0)) is not None
            and int(item.data(Qt.UserRole)) in self.checked_component_ids
        ]

    def _sync_row_checkboxes(self):
        for row in range(self.component_table.rowCount()):
            cell = self.component_table.item(row, 0)
            vertical = self.component_table.verticalHeaderItem(row)
            if cell is not None and vertical is not None:
                component_id = int(cell.data(Qt.UserRole))
                vertical.setData(Qt.UserRole, component_id)
                vertical.setCheckState(Qt.Checked if component_id in self.checked_component_ids else Qt.Unchecked)
        self.component_table.verticalHeader().viewport().update()

    def toggle_summary_panel(self):
        visible = not self.summary_panel.isVisible()
        self.summary_panel.setVisible(visible)
        self.summary_toggle_button.setText("›" if visible else "‹")
        self.settings.setValue("ui/summary_visible", visible)

    def import_selected_to_project(self):
        component_ids = self.selected_component_ids()
        if not component_ids: return
        projects = self.services.projects.list_projects()
        if not projects:
            name, ok = QInputDialog.getText(self, "新建项目", "项目名称")
            if not ok: return
            try: project_id = self.services.projects.create_project(name)
            except Exception as error: QMessageBox.warning(self, "无法新建项目", str(error)); return
        else:
            names = [project["name"] for project in projects]
            name, ok = QInputDialog.getItem(self, "导入到项目", "选择目标项目", names, 0, False)
            if not ok: return
            project_id = next(project["id"] for project in projects if project["name"] == name)
        if self.projects_page.has_unsaved_configuration():
            if not self.projects_page.confirm_unsaved_configuration():
                return
        added = self.services.projects.add_components(project_id, component_ids)
        self.projects_page.refresh(project_id)
        self.nav_list.setCurrentRow(2)
        QMessageBox.information(self, "已导入项目", f"已加入 {added} 种新元件；重复元件已跳过。")

    def open_bom_optimizer(self):
        dialog = BomOptimizerDialog(self.services.projects, parent=self)
        dialog.project_created.connect(self._bom_project_created)
        dialog.inventory_changed.connect(self.refresh)
        dialog.exec()

    def _bom_project_created(self, project_id: int):
        self.projects_page.refresh(project_id)
        self.nav_list.setCurrentRow(2)

    def add_selected_to_comparison(self):
        component_ids = self.selected_component_ids()
        if not component_ids:
            return
        added = self.services.comparison.add_components(component_ids)
        self.comparison_page.refresh()
        self.nav_list.setCurrentRow(1)
        QMessageBox.information(
            self,
            "已加入对比",
            f"新增 {added} 个元件；已在对比清单中的元件保持不变。",
        )

    def copy_summary_label(self, label: QLabel):
        value = label.text().strip()
        if not value or value == "—": return
        QGuiApplication.clipboard().setText(value)
        QToolTip.showText(label.mapToGlobal(label.rect().bottomLeft()), "已复制", label)

    def eventFilter(self, watched, event):
        if watched in self.copyable_labels and event.type() == QEvent.MouseButtonPress:
            if event.button() == Qt.LeftButton:
                self.copy_summary_label(watched)
                return True
        return super().eventFilter(watched, event)

    @staticmethod
    def clipboard_text() -> str:
        return QGuiApplication.clipboard().text()

    def update_summary(self):
        data = self.current_row_data()
        if not data:
            self.summary_title.setText("未选择元件")
            for label in self.summary_labels.values(): label.setText("—")
            return
        self.summary_title.setText(data["model"] or data["product_name"] or "未命名元件")
        for key, label in self.summary_labels.items():
            if key == "current_stock": text = f"{data[key]} {data['unit']}"
            elif key == "location": text = " · ".join(filter(None, [data["location"], data["notes"]])) or "—"
            else: text = str(data.get(key) or "—")
            label.setText(text)

    def save_cell_edit(self, item):
        if self._updating: return
        component_id = item.data(Qt.UserRole); key = COLUMNS[item.column()][0]
        if key not in {"current_stock", "location", "notes"}: return
        if key == "current_stock":
            try: self.services.stocks.calibrate(component_id, int(item.text()), "表格直接修改")
            except Exception: self.refresh(); return
        else:
            self.services.inventory.update_component(component_id, {key: item.text()})
        self.refresh()

    def closeEvent(self, event):
        if hasattr(self, "projects_page") and not self.projects_page.confirm_unsaved_configuration():
            event.ignore()
            return
        super().closeEvent(event)
