from __future__ import annotations

from PySide6.QtCore import QEvent, QPoint, QRect, QSettings, QSize, QTimer, Signal, Qt
from PySide6.QtGui import QColor, QGuiApplication, QPainter, QPolygon
from PySide6.QtWidgets import (
    QAbstractItemDelegate, QAbstractItemView, QApplication, QFrame, QHeaderView,
    QHBoxLayout, QInputDialog, QLabel, QLineEdit, QListWidget, QListWidgetItem,
    QMenu, QMessageBox, QPushButton, QStyle, QStyledItemDelegate, QToolButton,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from partbox.projects import ProjectError, ProjectService
from partbox.ui.selection_header import SelectionHeader


PROJECT_COLUMNS = [
    ("product_code", "商品编号"),
    ("product_type", "商品类型"),
    ("product_name", "商品名称"),
    ("model", "商品型号"),
    ("package", "封装格式"),
    ("brand", "品牌"),
    ("project_quantity", "项目用量"),
    ("latest_unit_price", "单价"),
    ("subtotal", "小计"),
    ("reference_designator", "位号"),
    ("_action", "操作"),
]
ID_COLUMN = 0
QUANTITY_COLUMN = 6
PRICE_COLUMN = 7
SUBTOTAL_COLUMN = 8
REFERENCE_COLUMN = 9
ACTION_COLUMN = 10


class ProjectNumericItem(QTableWidgetItem):
    def __init__(self, text: str, sort_value: float):
        super().__init__(text)
        self.sort_value = float(sort_value)

    def __lt__(self, other):
        if isinstance(other, ProjectNumericItem):
            return self.sort_value < other.sort_value
        return super().__lt__(other)


class ProjectHeader(QHeaderView):
    """Compact dual-triangle sort indicator matching the inventory table."""

    def __init__(self, parent=None):
        super().__init__(Qt.Horizontal, parent)
        self.setSectionsMovable(True)
        self.setSectionsClickable(True)
        self.setSectionResizeMode(QHeaderView.Interactive)
        self.setSortIndicatorShown(False)
        self.sortIndicatorChanged.connect(lambda *_: self.viewport().update())

    def paintSection(self, painter: QPainter, rect: QRect, logical_index: int) -> None:
        super().paintSection(painter, rect, logical_index)
        if not rect.isValid():
            return
        painter.save()
        right = rect.right() - 8
        center_y = rect.center().y()
        active = logical_index == self.sortIndicatorSection()
        up = QColor("#2563eb") if active and self.sortIndicatorOrder() == Qt.AscendingOrder else QColor("#a9b7c9")
        down = QColor("#2563eb") if active and self.sortIndicatorOrder() == Qt.DescendingOrder else QColor("#a9b7c9")
        painter.setPen(Qt.NoPen)
        painter.setBrush(up)
        painter.drawPolygon(QPolygon([
            QPoint(right - 4, center_y - 2), QPoint(right + 4, center_y - 2), QPoint(right, center_y - 7)
        ]))
        painter.setBrush(down)
        painter.drawPolygon(QPolygon([
            QPoint(right - 4, center_y + 2), QPoint(right + 4, center_y + 2), QPoint(right, center_y + 7)
        ]))
        painter.restore()


class ReferenceDesignatorDelegate(QStyledItemDelegate):
    """Commit a designator and continue editing vertically with Up/Down."""

    def __init__(self, table: QTableWidget):
        super().__init__(table)
        self.table = table

    def createEditor(self, parent, option, index):
        editor = QLineEdit(parent)
        editor.setProperty("designatorRow", index.row())
        editor.installEventFilter(self)
        return editor

    def eventFilter(self, editor, event):
        if (
            isinstance(editor, QLineEdit)
            and event.type() == QEvent.KeyPress
            and event.key() in (Qt.Key_Up, Qt.Key_Down)
        ):
            row = int(editor.property("designatorRow"))
            direction = -1 if event.key() == Qt.Key_Up else 1
            current_item = self.table.item(row, ID_COLUMN)
            component_id = (
                int(current_item.data(Qt.UserRole))
                if current_item is not None and current_item.data(Qt.UserRole) is not None
                else None
            )
            self.commitData.emit(editor)
            self.closeEditor.emit(editor, QAbstractItemDelegate.NoHint)
            QTimer.singleShot(
                0,
                lambda: self._edit_relative_to_component(component_id, direction),
            )
            return True
        return super().eventFilter(editor, event)

    def _edit_relative_to_component(self, component_id: int | None, direction: int):
        current_row = next(
            (
                row
                for row in range(self.table.rowCount())
                if self.table.item(row, ID_COLUMN) is not None
                and self.table.item(row, ID_COLUMN).data(Qt.UserRole) == component_id
            ),
            None,
        )
        if current_row is None:
            return
        row = min(max(current_row + direction, 0), self.table.rowCount() - 1)
        item = self.table.item(row, REFERENCE_COLUMN)
        if item is None:
            return
        self.table.setCurrentItem(item)
        self.table.editItem(item)


class ProjectQuantityStepper(QWidget):
    """A compact, direct-click quantity editor for a project table cell."""

    valueChanged = Signal(int)

    def __init__(self, component_id: int, value: int, parent=None):
        super().__init__(parent)
        self._minimum = 1
        self._value = self._minimum
        self.setObjectName("projectQuantityStepper")
        self.setProperty("componentId", int(component_id))
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setFocusPolicy(Qt.NoFocus)
        self.setFixedHeight(32)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(1, 1, 1, 1)
        layout.setSpacing(0)
        self.value_label = QLabel(objectName="projectQuantityValue")
        self.value_label.setAlignment(Qt.AlignCenter)
        self.value_label.setFocusPolicy(Qt.NoFocus)
        layout.addWidget(self.value_label, 1)

        self.increase_button = QToolButton(objectName="projectQuantityIncrease")
        self.decrease_button = QToolButton(objectName="projectQuantityDecrease")
        for button, text, tooltip in (
            (self.increase_button, "▲", "项目用量加 1"),
            (self.decrease_button, "▼", "项目用量减 1"),
        ):
            button.setText(text)
            button.setToolTip(tooltip)
            button.setFocusPolicy(Qt.NoFocus)
            button.setAutoRepeat(True)
            button.setAutoRepeatDelay(450)
            button.setAutoRepeatInterval(90)
            button.setFixedSize(28, 28)
            layout.addWidget(button)
        self.increase_button.clicked.connect(lambda: self.setValue(self._value + 1))
        self.decrease_button.clicked.connect(lambda: self.setValue(self._value - 1))
        self.setValue(value)

    def minimum(self) -> int:
        return self._minimum

    def value(self) -> int:
        return self._value

    def setValue(self, value: int) -> None:
        value = max(self._minimum, int(value))
        if value == self._value and self.value_label.text():
            self.decrease_button.setEnabled(value > self._minimum)
            return
        self._value = value
        self.value_label.setText(str(value))
        self.decrease_button.setEnabled(value > self._minimum)
        self.valueChanged.emit(value)


class ProjectListRow(QWidget):
    def __init__(self, name: str, component_count: int, parent=None):
        super().__init__(parent)
        self.setObjectName("projectListRow")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 7, 10, 7)
        layout.setSpacing(8)
        self.name_label = QLabel(name, objectName="projectListName")
        self.count_badge = QLabel(str(component_count), objectName="projectCountBadge")
        self.count_badge.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.name_label, 1)
        layout.addWidget(self.count_badge)


class ProjectsPage(QWidget):
    inventory_changed = Signal()
    bom_requested = Signal()

    def __init__(self, service: ProjectService, settings: QSettings | None = None, parent=None):
        super().__init__(parent)
        self.service = service
        self.settings = settings
        self._updating = False
        self.current_project_id: int | None = None
        self.checked_component_ids: set[int] = set()
        self._selection_anchor_id: int | None = None
        self._saved_quantities: dict[int, int] = {}
        self._draft_quantities: dict[int, int] = {}
        self._saved_reference_designators: dict[int, str] = {}
        self._draft_reference_designators: dict[int, str] = {}
        self._draft_prices: dict[int, float] = {}
        self._reverting_project_selection = False
        self.setObjectName("projectsPage")

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(10)
        body = QWidget()
        body_layout = QHBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(10)
        self.project_sidebar = QFrame(objectName="projectSidebar")
        self.project_sidebar.setFixedWidth(240)
        sidebar_layout = QVBoxLayout(self.project_sidebar)
        sidebar_layout.setContentsMargins(10, 10, 10, 10)
        sidebar_layout.setSpacing(10)
        sidebar_header = QHBoxLayout()
        sidebar_header.setContentsMargins(2, 0, 0, 0)
        sidebar_header.setSpacing(6)
        self.project_sidebar_title = QLabel("我的项目", objectName="projectSidebarTitle", parent=self.project_sidebar)
        sidebar_header.addWidget(self.project_sidebar_title)
        sidebar_header.addStretch()
        self.project_sidebar_toggle = QPushButton("‹", objectName="projectSidebarToggle", parent=self.project_sidebar)
        self.project_sidebar_toggle.setFixedSize(28, 28)
        self.project_sidebar_toggle.setToolTip("收起／展开项目列表")
        sidebar_header.addWidget(self.project_sidebar_toggle)
        sidebar_layout.addLayout(sidebar_header)
        self.project_list = QListWidget(objectName="projectList")
        self.project_list.setContextMenuPolicy(Qt.CustomContextMenu)
        sidebar_layout.addWidget(self.project_list)
        self.new_button = QPushButton("＋ 新建项目", objectName="projectNewButton", parent=self.project_sidebar)
        sidebar_layout.addWidget(self.new_button)
        self.bom_button = QPushButton("导入BOM并计算", objectName="projectBomButton", parent=self.project_sidebar)
        sidebar_layout.addWidget(self.bom_button)
        body_layout.addWidget(self.project_sidebar)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(8, 0, 0, 0)
        action_row = QHBoxLayout()
        self.project_title = QLabel("请选择项目", objectName="projectTitle")
        action_row.addWidget(self.project_title)
        action_row.addStretch()
        self.project_total_label = QLabel("项目合计  ¥0.00", objectName="projectTotal")
        action_row.addWidget(self.project_total_label)
        self.save_configuration_button = QPushButton("保存元件配置", objectName="projectSaveButton")
        self.save_configuration_button.setEnabled(False)
        action_row.addWidget(self.save_configuration_button)
        self.sync_button = QPushButton("导出变更到元件库存", objectName="projectSyncButton")
        action_row.addWidget(self.sync_button)
        right_layout.addLayout(action_row)

        self.component_table = QTableWidget(0, len(PROJECT_COLUMNS), objectName="projectComponentTable")
        self.component_table.setProperty("projectTable", True)
        self.component_table.setHorizontalHeaderLabels([title for _, title in PROJECT_COLUMNS])
        self.component_table.setHorizontalHeader(ProjectHeader(self.component_table))
        self.component_table.setAlternatingRowColors(True)
        self.component_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.component_table.setEditTriggers(
            QAbstractItemView.SelectedClicked | QAbstractItemView.EditKeyPressed
        )
        self.component_table.setItemDelegateForColumn(
            REFERENCE_COLUMN, ReferenceDesignatorDelegate(self.component_table)
        )
        self.component_table.setSortingEnabled(True)
        self.component_table.horizontalHeader().setSortIndicatorShown(False)
        self.component_table.sortItems(ID_COLUMN, Qt.AscendingOrder)
        self.component_table.horizontalHeader().setSortIndicatorShown(False)
        self.component_table.horizontalHeader().setStretchLastSection(False)
        self.component_table.setVerticalHeader(SelectionHeader(
            Qt.Vertical, self.component_table, lambda: self.checked_component_ids, id_column=ID_COLUMN
        ))
        self.component_table.verticalHeader().setDefaultSectionSize(36)
        self.component_table.verticalHeader().setMinimumSectionSize(36)
        self.component_table.verticalHeader().setSectionResizeMode(QHeaderView.Fixed)
        self.component_table.verticalHeader().setFixedWidth(42)
        self.component_table.verticalHeader().setSectionsClickable(True)
        self.component_table.setColumnWidth(2, 260)
        self.component_table.setColumnWidth(QUANTITY_COLUMN, 112)
        self.component_table.setColumnWidth(PRICE_COLUMN, 100)
        self.component_table.setColumnWidth(SUBTOTAL_COLUMN, 110)
        self.component_table.setColumnWidth(REFERENCE_COLUMN, 150)
        self.component_table.setColumnWidth(ACTION_COLUMN, 54)
        right_layout.addWidget(self.component_table, 3)

        right_layout.addWidget(QLabel("项目操作记录", objectName="sectionTitle"))
        self.history_table = QTableWidget(0, 4, objectName="projectHistoryTable")
        self.history_table.setHorizontalHeaderLabels(["时间", "变更元件", "库存净变化", "记录号"])
        self.history_table.verticalHeader().setVisible(False)
        self.history_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.history_table.horizontalHeader().setStretchLastSection(True)
        right_layout.addWidget(self.history_table, 1)
        body_layout.addWidget(right, 1)
        root.addWidget(body, 1)

        sidebar_visible = self.settings.value("ui/projects_sidebar_visible", True, type=bool) if self.settings else True
        self._set_project_sidebar_expanded(sidebar_visible, persist=False)

        self.new_button.clicked.connect(self.create_project)
        self.bom_button.clicked.connect(self.bom_requested.emit)
        self.save_configuration_button.clicked.connect(self.save_configuration)
        self.sync_button.clicked.connect(self.sync_project)
        self.project_list.currentItemChanged.connect(self._project_selected)
        self.project_list.customContextMenuRequested.connect(self.show_project_menu)
        self.project_sidebar_toggle.clicked.connect(self.toggle_project_sidebar)
        self.component_table.verticalHeader().sectionClicked.connect(self.toggle_row_checked)
        self.component_table.model().layoutChanged.connect(self._table_sorted)
        self.component_table.itemChanged.connect(self._component_item_changed)
        self.component_table.cellClicked.connect(self._edit_designator_on_click)
        self.refresh()

    def refresh(self, project_id: int | None = None):
        projects = self.service.list_projects()
        target = project_id if project_id is not None else self.current_project_id
        reload_current = target is not None and target == self.current_project_id and not self.has_unsaved_configuration()
        self.project_list.blockSignals(True)
        self.project_list.clear()
        selected_row = -1
        for index, project in enumerate(projects):
            item = QListWidgetItem()
            item.setSizeHint(QSize(0, 44))
            item.setData(Qt.UserRole, project["id"])
            item.setData(Qt.UserRole + 1, project["name"])
            self.project_list.addItem(item)
            self.project_list.setItemWidget(
                item, ProjectListRow(project["name"], project["component_count"], self.project_list)
            )
            if project["id"] == target:
                selected_row = index
        self.project_list.blockSignals(False)
        if projects:
            self.project_list.setCurrentRow(selected_row if selected_row >= 0 else 0)
            if reload_current:
                self._load_project()
        else:
            self.current_project_id = None
            self._load_project()

    def _project_selected(self, current, previous):
        if self._reverting_project_selection:
            return
        target_id = int(current.data(Qt.UserRole)) if current else None
        if target_id == self.current_project_id:
            return
        if self.has_unsaved_configuration() and not self.confirm_unsaved_configuration():
            self._reverting_project_selection = True
            self.project_list.setCurrentItem(previous)
            self._reverting_project_selection = False
            return
        self.current_project_id = target_id
        self.checked_component_ids.clear()
        self._selection_anchor_id = None
        self._load_project()

    def _load_project(self):
        item = self.project_list.currentItem()
        self.project_title.setText(item.data(Qt.UserRole + 1) if item else "请选择项目")
        rows = self.service.list_components(self.current_project_id) if self.current_project_id else []
        self._saved_quantities = {
            int(row["id"]): max(1, int(row["project_quantity"]))
            for row in rows
        }
        self._draft_quantities = dict(self._saved_quantities)
        self._saved_reference_designators = {
            int(row["id"]): str(row["reference_designator"] or "")
            for row in rows
        }
        self._draft_reference_designators = dict(self._saved_reference_designators)
        self._draft_prices = {
            int(row["id"]): float(row["latest_unit_price"] or 0)
            for row in rows
        }
        visible_ids = {int(row["id"]) for row in rows}
        self.checked_component_ids.intersection_update(visible_ids)
        header = self.component_table.horizontalHeader()
        sort_section = header.sortIndicatorSection()
        sort_order = header.sortIndicatorOrder()
        self._updating = True
        self.component_table.setSortingEnabled(False)
        for old_row in range(self.component_table.rowCount()):
            old_stepper = self.component_table.cellWidget(old_row, QUANTITY_COLUMN)
            if old_stepper is not None:
                old_stepper.hide()
                self.component_table.removeCellWidget(old_row, QUANTITY_COLUMN)
                old_stepper.setParent(None)
                old_stepper.deleteLater()
        self.component_table.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            component_id = int(row["id"])
            quantity = max(1, int(row["project_quantity"]))
            subtotal = float(row["latest_unit_price"] or 0) * quantity
            values = {
                **row,
                "project_quantity": quantity,
                "subtotal": subtotal,
            }
            for column, (key, _) in enumerate(PROJECT_COLUMNS):
                value = values.get(key, "")
                if key == "latest_unit_price":
                    cell = ProjectNumericItem(f"¥{float(value or 0):,.4f}", float(value or 0))
                elif key == "subtotal":
                    cell = ProjectNumericItem(f"¥{float(value or 0):,.2f}", float(value or 0))
                elif key == "project_quantity":
                    cell = ProjectNumericItem("", int(value))
                else:
                    cell = QTableWidgetItem(str(value if value is not None else ""))
                cell.setData(Qt.UserRole, component_id)
                if key != "reference_designator":
                    cell.setFlags(cell.flags() & ~Qt.ItemIsEditable)
                else:
                    cell.setBackground(QColor("#fff2bd"))
                self.component_table.setItem(row_index, column, cell)
            stepper = ProjectQuantityStepper(component_id, quantity, self.component_table)
            stepper.valueChanged.connect(lambda value, cid=component_id: self.edit_quantity(cid, value))
            self.component_table.setCellWidget(row_index, QUANTITY_COLUMN, stepper)
            delete_button = QToolButton(self.component_table)
            delete_button.setObjectName("projectRowDeleteButton")
            delete_button.setProperty("componentId", component_id)
            delete_button.setIcon(self.style().standardIcon(QStyle.SP_TrashIcon))
            delete_button.setIconSize(QSize(16, 16))
            delete_button.setToolTip("删除该元件")
            delete_button.setFocusPolicy(Qt.NoFocus)
            delete_button.clicked.connect(
                lambda checked=False, cid=component_id: self.remove_component(cid)
            )
            self.component_table.setCellWidget(row_index, ACTION_COLUMN, delete_button)
            self.component_table.setRowHeight(row_index, 36)
            vertical = QTableWidgetItem()
            vertical.setData(Qt.UserRole, component_id)
            vertical.setCheckState(Qt.Checked if component_id in self.checked_component_ids else Qt.Unchecked)
            self.component_table.setVerticalHeaderItem(row_index, vertical)
        self.component_table.setSortingEnabled(True)
        self.component_table.horizontalHeader().setSortIndicatorShown(False)
        if 0 <= sort_section < self.component_table.columnCount():
            self.component_table.sortItems(sort_section, sort_order)
        self._updating = False
        self._sync_row_checkboxes()
        self._refresh_total()
        self._update_save_state()
        self._load_history()

    def _load_history(self):
        history = self.service.operation_history(self.current_project_id) if self.current_project_id else []
        self.history_table.setRowCount(len(history))
        for row_index, record in enumerate(history):
            for column, value in enumerate((
                record["occurred_at"], record["changed_lines"], record["stock_delta"], record["id"]
            )):
                self.history_table.setItem(row_index, column, QTableWidgetItem(str(value)))

    def _table_sorted(self):
        QTimer.singleShot(0, self._after_sort)

    def _edit_designator_on_click(self, row: int, column: int):
        if column == REFERENCE_COLUMN:
            self.component_table.editItem(self.component_table.item(row, column))

    def _component_item_changed(self, item: QTableWidgetItem):
        if self._updating or item.column() != REFERENCE_COLUMN:
            return
        component_id = item.data(Qt.UserRole)
        if component_id is None:
            return
        self._draft_reference_designators[int(component_id)] = item.text().strip()
        self._update_save_state()

    def _after_sort(self):
        self._sync_row_checkboxes()

    def _component_id_at(self, row: int) -> int | None:
        item = self.component_table.item(row, ID_COLUMN)
        return int(item.data(Qt.UserRole)) if item and item.data(Qt.UserRole) is not None else None

    def _row_for_component_id(self, component_id: int) -> int | None:
        return next(
            (row for row in range(self.component_table.rowCount()) if self._component_id_at(row) == component_id),
            None,
        )

    def toggle_row_checked(self, row: int, modifiers=None):
        component_id = self._component_id_at(row)
        if component_id is None:
            return
        modifiers = QGuiApplication.keyboardModifiers() if modifiers is None else modifiers
        anchor_row = self._row_for_component_id(self._selection_anchor_id) if self._selection_anchor_id is not None else None
        if modifiers & Qt.ShiftModifier and anchor_row is not None:
            low, high = sorted((anchor_row, row))
            for range_row in range(low, high + 1):
                range_id = self._component_id_at(range_row)
                if range_id is not None:
                    self.checked_component_ids.add(range_id)
        else:
            if component_id in self.checked_component_ids:
                self.checked_component_ids.remove(component_id)
            else:
                self.checked_component_ids.add(component_id)
            self._selection_anchor_id = component_id
        self._sync_row_checkboxes()

    def toggle_project_sidebar(self):
        self._set_project_sidebar_expanded(not self._project_sidebar_expanded)

    def _set_project_sidebar_expanded(self, expanded: bool, persist: bool = True):
        self._project_sidebar_expanded = bool(expanded)
        self.project_sidebar_title.setVisible(expanded)
        self.project_list.setVisible(expanded)
        self.new_button.setVisible(expanded)
        self.project_sidebar.setFixedWidth(240 if expanded else 52)
        self.project_sidebar_toggle.setText("‹" if expanded else "›")
        self.project_sidebar_toggle.setToolTip("收起项目列表" if expanded else "展开项目列表")
        if self.settings:
            if persist:
                self.settings.setValue("ui/projects_sidebar_visible", expanded)

    def _sync_row_checkboxes(self):
        for row in range(self.component_table.rowCount()):
            component_id = self._component_id_at(row)
            vertical = self.component_table.verticalHeaderItem(row)
            if component_id is not None and vertical is not None:
                vertical.setData(Qt.UserRole, component_id)
                vertical.setCheckState(Qt.Checked if component_id in self.checked_component_ids else Qt.Unchecked)
        self.component_table.verticalHeader().viewport().update()

    def selected_component_ids(self) -> list[int]:
        return [
            component_id
            for row in range(self.component_table.rowCount())
            if (component_id := self._component_id_at(row)) in self.checked_component_ids
        ]

    def edit_quantity(self, component_id: int, value: int):
        if self._updating or not self.current_project_id:
            return
        self._draft_quantities[component_id] = max(1, int(value))
        for row in range(self.component_table.rowCount()):
            if self._component_id_at(row) != component_id:
                continue
            quantity_item = self.component_table.item(row, QUANTITY_COLUMN)
            if isinstance(quantity_item, ProjectNumericItem):
                quantity_item.setText("")
                quantity_item.sort_value = value
            price_item = self.component_table.item(row, PRICE_COLUMN)
            subtotal_item = self.component_table.item(row, SUBTOTAL_COLUMN)
            price = price_item.sort_value if isinstance(price_item, ProjectNumericItem) else 0
            subtotal = price * value
            if isinstance(subtotal_item, ProjectNumericItem):
                subtotal_item.setText(f"¥{subtotal:,.2f}")
                subtotal_item.sort_value = subtotal
            break
        self._refresh_total()
        self._update_save_state()

    def has_unsaved_configuration(self) -> bool:
        return (
            self._draft_quantities != self._saved_quantities
            or self._draft_reference_designators != self._saved_reference_designators
        )

    def _update_save_state(self):
        dirty = self.current_project_id is not None and self.has_unsaved_configuration()
        self.save_configuration_button.setEnabled(dirty)
        self.save_configuration_button.setProperty("dirty", dirty)
        self.save_configuration_button.setToolTip(
            "保存当前项目的元件与用量配置" if dirty else "当前元件配置已保存"
        )
        self.save_configuration_button.style().unpolish(self.save_configuration_button)
        self.save_configuration_button.style().polish(self.save_configuration_button)

    def save_configuration(self) -> bool:
        if not self.current_project_id or not self.has_unsaved_configuration():
            return True
        try:
            self.service.save_configuration(
                self.current_project_id,
                self._draft_quantities,
                self._draft_reference_designators,
            )
        except ProjectError as error:
            QMessageBox.warning(self, "无法保存元件配置", str(error))
            return False
        self._saved_quantities = dict(self._draft_quantities)
        self._saved_reference_designators = dict(self._draft_reference_designators)
        self._update_save_state()
        return True

    def confirm_unsaved_configuration(self) -> bool:
        self.commit_active_editor()
        if not self.has_unsaved_configuration():
            return True
        answer = QMessageBox.question(
            self,
            "元件配置尚未保存",
            "当前项目的元件用量或位号尚未保存。",
            QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel,
            QMessageBox.Save,
        )
        if answer == QMessageBox.Save:
            return self.save_configuration()
        if answer == QMessageBox.Discard:
            self._apply_drafts_to_table(
                self._saved_quantities,
                self._saved_reference_designators,
            )
            return True
        return False

    def commit_active_editor(self):
        editor = next(
            (
                child
                for child in self.component_table.findChildren(QLineEdit)
                if child.isVisible()
            ),
            None,
        )
        if editor is None:
            return
        delegate = self.component_table.itemDelegateForColumn(REFERENCE_COLUMN)
        delegate.commitData.emit(editor)
        delegate.closeEditor.emit(editor, QAbstractItemDelegate.NoHint)
        QApplication.processEvents()

    def _apply_drafts_to_table(
        self,
        quantities: dict[int, int],
        reference_designators: dict[int, str],
    ):
        self._updating = True
        self._draft_quantities = dict(quantities)
        self._draft_reference_designators = dict(reference_designators)
        for row in range(self.component_table.rowCount()):
            component_id = self._component_id_at(row)
            if component_id is None or component_id not in quantities:
                continue
            quantity = quantities[component_id]
            stepper = self.component_table.cellWidget(row, QUANTITY_COLUMN)
            if isinstance(stepper, ProjectQuantityStepper):
                stepper.setValue(quantity)
            quantity_item = self.component_table.item(row, QUANTITY_COLUMN)
            if isinstance(quantity_item, ProjectNumericItem):
                quantity_item.sort_value = quantity
            reference_item = self.component_table.item(row, REFERENCE_COLUMN)
            if reference_item is not None:
                reference_item.setText(reference_designators.get(component_id, ""))
            price_item = self.component_table.item(row, PRICE_COLUMN)
            subtotal_item = self.component_table.item(row, SUBTOTAL_COLUMN)
            price = price_item.sort_value if isinstance(price_item, ProjectNumericItem) else 0
            if isinstance(subtotal_item, ProjectNumericItem):
                subtotal = price * quantity
                subtotal_item.setText(f"¥{subtotal:,.2f}")
                subtotal_item.sort_value = subtotal
        self._updating = False
        self._refresh_total()
        self._update_save_state()

    def _refresh_total(self):
        total = sum(
            quantity * self._draft_prices.get(component_id, 0)
            for component_id, quantity in self._draft_quantities.items()
        )
        self.project_total_label.setText(f"项目合计  ¥{total:,.2f}")

    def create_project(self):
        if not self.confirm_unsaved_configuration():
            return
        name, ok = QInputDialog.getText(self, "新建项目", "项目名称")
        if not ok:
            return
        try:
            project_id = self.service.create_project(name)
        except ProjectError as error:
            QMessageBox.warning(self, "无法新建", str(error))
            return
        self.refresh(project_id)

    def rename_project(self):
        if not self.current_project_id:
            return
        current = self.project_list.currentItem().data(Qt.UserRole + 1)
        name, ok = QInputDialog.getText(self, "重命名项目", "项目名称", text=current)
        if not ok:
            return
        try:
            self.service.rename_project(self.current_project_id, name)
        except ProjectError as error:
            QMessageBox.warning(self, "无法重命名", str(error))
            return
        self.refresh(self.current_project_id)

    def delete_project(self):
        if not self.current_project_id:
            return
        if not self.confirm_unsaved_configuration():
            return
        answer = QMessageBox.question(
            self, "删除项目", "从项目列表中隐藏该项目？库存和操作记录都会保留。"
        )
        if answer != QMessageBox.Yes:
            return
        try:
            self.service.delete_project(self.current_project_id)
        except ProjectError as error:
            QMessageBox.warning(self, "无法删除", str(error))
            return
        self.current_project_id = None
        self.refresh()

    def build_project_menu(self) -> QMenu:
        menu = QMenu(self)
        new_action = menu.addAction("新建项目")
        new_action.triggered.connect(self.create_project)
        rename_action = menu.addAction("重命名项目")
        rename_action.triggered.connect(self.rename_project)
        delete_action = menu.addAction("删除项目")
        delete_action.triggered.connect(self.delete_project)
        has_project = self.current_project_id is not None
        rename_action.setEnabled(has_project)
        delete_action.setEnabled(has_project)
        return menu

    def show_project_menu(self, position: QPoint):
        item = self.project_list.itemAt(position)
        if item is not None:
            target_id = int(item.data(Qt.UserRole))
            self.project_list.setCurrentItem(item)
            if self.current_project_id != target_id:
                return
        self.build_project_menu().exec(self.project_list.mapToGlobal(position))

    def remove_selected_components(self):
        component_ids = self.selected_component_ids()
        if not self.current_project_id or not component_ids:
            return
        answer = QMessageBox.question(
            self,
            "删除项目元件",
            f"删除选中的 {len(component_ids)} 行？已同步扣除的数量会退回元件库存，未同步编辑会忽略。",
        )
        if answer != QMessageBox.Yes:
            return
        try:
            result = self.service.remove_components(self.current_project_id, component_ids)
        except ProjectError as error:
            QMessageBox.warning(self, "无法删除", str(error))
            return
        self.checked_component_ids.difference_update(component_ids)
        self._load_project()
        self.refresh(self.current_project_id)
        if result.stock_delta:
            self.inventory_changed.emit()

    def remove_component(self, component_id: int):
        if not self.current_project_id:
            return
        row = self._row_for_component_id(component_id)
        if row is None:
            return
        code_item = self.component_table.item(row, ID_COLUMN)
        name_item = self.component_table.item(row, 2)
        code = code_item.text() if code_item is not None else str(component_id)
        name = name_item.text() if name_item is not None else ""
        label = f"{code}（{name}）" if name else code
        answer = QMessageBox.question(
            self,
            "删除项目元件",
            f"确定从当前项目删除 {label} 吗？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return

        remaining_quantities = {
            cid: quantity
            for cid, quantity in self._draft_quantities.items()
            if cid != component_id
        }
        remaining_designators = {
            cid: value
            for cid, value in self._draft_reference_designators.items()
            if cid != component_id
        }
        try:
            result = self.service.remove_components(self.current_project_id, [component_id])
        except ProjectError as error:
            QMessageBox.warning(self, "无法删除", str(error))
            return

        self.checked_component_ids.discard(component_id)
        if self._selection_anchor_id == component_id:
            self._selection_anchor_id = None
        self._saved_quantities.pop(component_id, None)
        self._saved_reference_designators.pop(component_id, None)
        self._draft_quantities = dict(self._saved_quantities)
        self._draft_reference_designators = dict(self._saved_reference_designators)
        project_id = self.current_project_id
        self.refresh(project_id)
        self._apply_drafts_to_table(remaining_quantities, remaining_designators)
        if result.stock_delta:
            self.inventory_changed.emit()

    def add_component_ids(self, component_ids: list[int], project_id: int | None = None):
        target = project_id or self.current_project_id
        if not target:
            projects = self.service.list_projects()
            target = projects[0]["id"] if projects else self.service.create_project("新项目")
        self.service.add_components(target, component_ids)
        self.refresh(target)

    def sync_project(self):
        if not self.current_project_id:
            return
        if self.has_unsaved_configuration():
            QMessageBox.warning(
                self,
                "元件配置尚未保存",
                "请先保存元件配置，再导出变更到元件库存。",
            )
            return
        try:
            result = self.service.sync(self.current_project_id)
        except ProjectError as error:
            QMessageBox.warning(self, "无法同步库存", str(error))
            return
        self._load_project()
        self.inventory_changed.emit()
        if result.changed_lines:
            QMessageBox.information(
                self, "同步完成", f"已同步 {result.changed_lines} 种元件，库存净变化 {result.stock_delta:+d}。"
            )
        else:
            QMessageBox.information(self, "无需同步", "项目用量没有新的变化。")
