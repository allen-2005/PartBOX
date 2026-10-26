from __future__ import annotations

from collections.abc import Callable, Set

from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QHeaderView


class SelectionHeader(QHeaderView):
    """Vertical row selector whose check state is derived from component IDs."""

    def __init__(
        self,
        orientation: Qt.Orientation,
        parent=None,
        selected_ids_getter: Callable[[], Set[int]] | None = None,
        id_column: int = 0,
    ):
        super().__init__(orientation, parent)
        self.selected_ids_getter = selected_ids_getter
        self.id_column = id_column

    def paintSection(self, painter: QPainter, rect: QRect, logical_index: int) -> None:
        super().paintSection(painter, rect, logical_index)
        table = self.parentWidget()
        item = table.item(logical_index, self.id_column) if table else None
        raw_id = item.data(Qt.UserRole) if item else None
        component_id = int(raw_id) if raw_id is not None else None
        selected_ids = self.selected_ids_getter() if self.selected_ids_getter else set()
        checked = component_id in selected_ids
        size = 16
        box = QRect(rect.center().x() - size // 2, rect.center().y() - size // 2, size, size)
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(QPen(QColor("#2563eb"), 1))
        painter.setBrush(QColor("#2563eb") if checked else QColor("#ffffff"))
        painter.drawRoundedRect(box, 4, 4)
        if checked:
            painter.setPen(QPen(QColor("#ffffff"), 2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            painter.drawLine(box.left() + 4, box.center().y(), box.center().x() - 1, box.bottom() - 4)
            painter.drawLine(box.center().x() - 1, box.bottom() - 4, box.right() - 3, box.top() + 4)
        painter.restore()
