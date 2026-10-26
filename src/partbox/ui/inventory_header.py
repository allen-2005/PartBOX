from __future__ import annotations

from PySide6.QtCore import QPoint, QRect, QSettings, Qt, Signal
from PySide6.QtGui import QAction, QColor, QPainter, QPolygon
from PySide6.QtWidgets import QHeaderView, QMenu


class InventoryHeader(QHeaderView):
    """Movable inventory header with persistent Excel-like column controls."""

    sort_requested = Signal(int, Qt.SortOrder)

    def __init__(self, columns, default_widths, settings: QSettings, parent=None):
        super().__init__(Qt.Horizontal, parent)
        self.columns = list(columns)
        self.default_widths = list(default_widths)
        self.settings = settings
        self._restoring = False
        self.setSectionsMovable(True)
        self.setSectionsClickable(True)
        self.setSectionResizeMode(QHeaderView.Interactive)
        self.setSortIndicatorShown(False)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_column_menu)
        self.sectionMoved.connect(self.save_layout)
        self.sectionResized.connect(self.save_layout)
        self.sortIndicatorChanged.connect(self._sort_changed)

    def _settings_valid(self) -> bool:
        return self.settings.value("inventory/header/columns", []) == [key for key, _ in self.columns]

    def restore_layout(self) -> None:
        self._restoring = True
        try:
            if self._settings_valid():
                state = self.settings.value("inventory/header/state")
                restored = bool(state) and self.restoreState(state)
            else:
                restored = False
            if not restored:
                self._apply_defaults()
            section = int(self.settings.value("inventory/header/sort_section", 0)) if self._settings_valid() else 0
            direction = str(self.settings.value("inventory/header/sort_order", "asc")) if self._settings_valid() else "asc"
            if not 0 <= section < len(self.columns):
                section = 0
            self.setSortIndicator(section, Qt.DescendingOrder if direction == "desc" else Qt.AscendingOrder)
        except (TypeError, ValueError):
            self._apply_defaults()
            self.setSortIndicator(0, Qt.AscendingOrder)
        finally:
            self._restoring = False
        self.save_layout()
        self.viewport().update()

    def _apply_defaults(self) -> None:
        for visual in range(self.count()):
            logical = self.logicalIndex(visual)
            if logical != visual:
                self.moveSection(visual, self.visualIndex(visual))
        # Moving while iterating above is not sufficient for every permutation.
        for logical in range(self.count()):
            self.moveSection(self.visualIndex(logical), logical)
            self.setSectionHidden(logical, False)
            if logical < len(self.default_widths):
                self.resizeSection(logical, self.default_widths[logical])

    def save_layout(self, *_args) -> None:
        if self._restoring or self.count() != len(self.columns):
            return
        self.settings.setValue("inventory/header/columns", [key for key, _ in self.columns])
        self.settings.setValue("inventory/header/state", self.saveState())
        self.settings.setValue("inventory/header/sort_section", self.sortIndicatorSection())
        order = "desc" if self.sortIndicatorOrder() == Qt.DescendingOrder else "asc"
        self.settings.setValue("inventory/header/sort_order", order)

    def _sort_changed(self, section: int, order: Qt.SortOrder) -> None:
        if not self._restoring:
            self.save_layout()
            self.sort_requested.emit(section, order)
        self.viewport().update()

    def set_sort(self, section: int, order: Qt.SortOrder) -> None:
        if 0 <= section < self.count():
            self.setSortIndicator(section, order)
            self.save_layout()

    def set_column_visible(self, logical: int, visible: bool) -> bool:
        if not 0 <= logical < self.count():
            return False
        if not visible:
            visible_count = sum(not self.isSectionHidden(index) for index in range(self.count()))
            if visible_count <= 1 and not self.isSectionHidden(logical):
                return False
        self.setSectionHidden(logical, not visible)
        self.save_layout()
        return True

    def show_all_columns(self) -> None:
        self._restoring = True
        try:
            for logical in range(self.count()):
                self.setSectionHidden(logical, False)
        finally:
            self._restoring = False
        self.save_layout()

    def reset_layout(self) -> None:
        self._restoring = True
        try:
            self._apply_defaults()
            self.setSortIndicator(0, Qt.AscendingOrder)
        finally:
            self._restoring = False
        self.save_layout()
        self.sort_requested.emit(0, Qt.AscendingOrder)
        self.viewport().update()

    def show_column_menu(self, position: QPoint) -> None:
        self.build_column_menu().exec(self.mapToGlobal(position))

    def build_column_menu(self) -> QMenu:
        menu = QMenu(self)
        for logical, (_, title) in enumerate(self.columns):
            action = QAction(title, menu)
            action.setCheckable(True)
            action.setChecked(not self.isSectionHidden(logical))
            action.toggled.connect(lambda checked, column=logical: self._toggle_from_menu(column, checked))
            menu.addAction(action)
        menu.addSeparator()
        show_all = menu.addAction("全部显示")
        show_all.triggered.connect(self.show_all_columns)
        reset = menu.addAction("恢复默认列布局")
        reset.triggered.connect(self.reset_layout)
        return menu

    def _toggle_from_menu(self, logical: int, visible: bool) -> None:
        if not self.set_column_visible(logical, visible):
            # The menu is transient; repainting is enough for the next opening
            # to reflect that the last visible column remained checked.
            self.viewport().update()

    def paintSection(self, painter: QPainter, rect: QRect, logical_index: int) -> None:
        super().paintSection(painter, rect, logical_index)
        if not rect.isValid():
            return
        painter.save()
        right = rect.right() - 8
        center_y = rect.center().y()
        active = logical_index == self.sortIndicatorSection()
        up_color = QColor("#2563eb") if active and self.sortIndicatorOrder() == Qt.AscendingOrder else QColor("#a9b7c9")
        down_color = QColor("#2563eb") if active and self.sortIndicatorOrder() == Qt.DescendingOrder else QColor("#a9b7c9")
        painter.setPen(Qt.NoPen)
        painter.setBrush(up_color)
        painter.drawPolygon(QPolygon([QPoint(right - 4, center_y - 2), QPoint(right + 4, center_y - 2), QPoint(right, center_y - 7)]))
        painter.setBrush(down_color)
        painter.drawPolygon(QPolygon([QPoint(right - 4, center_y + 2), QPoint(right + 4, center_y + 2), QPoint(right, center_y + 7)]))
        painter.restore()
