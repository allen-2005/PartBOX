from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import QPointF, QRectF, Signal, Qt
from PySide6.QtGui import QColor, QMouseEvent, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QToolTip,
    QVBoxLayout,
    QWidget,
)

from partbox.comparison import ComparisonService


BASE_FILL = "#FFFCF4"
DIFFERENCE_FILL = "#F8EDC8"

COMPARE_FIELDS = [
    ("product_code", "商品编号"),
    ("product_type", "商品类型"),
    ("product_name", "商品名称"),
    ("model", "商品型号"),
    ("package", "封装格式"),
    ("brand", "品牌"),
    ("current_stock", "当前库存"),
    ("total_purchased", "累计购买"),
    ("unit", "商品单位"),
    ("latest_unit_price", "最近单价（含税）"),
    ("total_spent", "累计采购金额"),
    ("latest_order_time", "最近下单时间"),
    ("location", "存放位置"),
    ("notes", "备注"),
    ("updated_at", "最后修改时间"),
]


class PriceHistoryChart(QWidget):
    COLORS = ("#2563eb", "#0f9f7f", "#d97706", "#7c3aed", "#dc2626", "#0891b2")

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("comparisonPriceChart")
        self.setMinimumHeight(220)
        self.setMouseTracking(True)
        self.series: dict[int, dict] = {}
        self._hit_points: list[tuple[QPointF, str]] = []

    def set_data(self, components: list[dict], history: dict[int, list[dict]]) -> None:
        self.series = {}
        for index, component in enumerate(components):
            component_id = int(component["id"])
            self.series[component_id] = {
                "label": component.get("product_code") or component.get("model") or str(component_id),
                "color": self.COLORS[index % len(self.COLORS)],
                "points": list(history.get(component_id, [])),
            }
        self.update()

    @staticmethod
    def _time_value(value: str) -> float:
        try:
            return datetime.fromisoformat(str(value)).timestamp()
        except (TypeError, ValueError):
            return 0.0

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor(BASE_FILL))
        plot = QRectF(58, 28, max(1, self.width() - 82), max(1, self.height() - 72))
        painter.setPen(QPen(QColor("#b9c9dc"), 1))
        painter.drawLine(plot.bottomLeft(), plot.topLeft())
        painter.drawLine(plot.bottomLeft(), plot.bottomRight())

        all_points = [point for series in self.series.values() for point in series["points"]]
        self._hit_points = []
        if not all_points:
            painter.setPen(QColor("#60738d"))
            painter.drawText(self.rect(), Qt.AlignCenter, "暂无采购价格记录")
            return

        times = [self._time_value(point.get("order_time")) for point in all_points]
        prices = [float(point.get("unit_price") or 0) for point in all_points]
        min_time, max_time = min(times), max(times)
        min_price, max_price = min(prices), max(prices)
        time_span = max(max_time - min_time, 1.0)
        price_span = max(max_price - min_price, max(max_price * 0.05, 0.01))

        painter.setPen(QColor("#60738d"))
        painter.drawText(QRectF(4, plot.top() - 8, 50, 20), Qt.AlignRight, f"¥{max_price:.4f}")
        painter.drawText(QRectF(4, plot.bottom() - 10, 50, 20), Qt.AlignRight, f"¥{min_price:.4f}")
        min_date = datetime.fromtimestamp(min_time).strftime("%Y-%m-%d") if min_time else "未知"
        max_date = datetime.fromtimestamp(max_time).strftime("%Y-%m-%d") if max_time else "未知"
        painter.drawText(QRectF(plot.left(), plot.bottom() + 8, 100, 20), Qt.AlignLeft, min_date)
        painter.drawText(QRectF(plot.right() - 100, plot.bottom() + 8, 100, 20), Qt.AlignRight, max_date)

        legend_x = plot.left()
        for component_id, series in self.series.items():
            color = QColor(series["color"])
            painter.setPen(QPen(color, 3))
            painter.drawLine(QPointF(legend_x, 14), QPointF(legend_x + 18, 14))
            painter.setPen(QColor("#17345c"))
            painter.drawText(QRectF(legend_x + 22, 4, 120, 20), Qt.AlignLeft | Qt.AlignVCenter, series["label"])
            legend_x += 145

            plotted = []
            for point in series["points"]:
                x = plot.left() + (self._time_value(point.get("order_time")) - min_time) / time_span * plot.width()
                y = plot.bottom() - (float(point.get("unit_price") or 0) - min_price) / price_span * plot.height()
                plotted.append(QPointF(x, y))
            if not plotted:
                continue
            path = QPainterPath(plotted[0])
            for point in plotted[1:]:
                path.lineTo(point)
            painter.setBrush(Qt.NoBrush)
            painter.setPen(QPen(color, 2))
            painter.drawPath(path)
            painter.setBrush(color)
            for position, raw in zip(plotted, series["points"]):
                painter.drawEllipse(position, 4, 4)
                tooltip = (
                    f"{series['label']}\n{raw.get('order_time') or '未知时间'}\n"
                    f"单价：¥{float(raw.get('unit_price') or 0):.4f}\n"
                    f"数量：{raw.get('quantity') or 0}\n订单：{raw.get('order_number') or '—'}"
                )
                self._hit_points.append((position, tooltip))

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        position = event.position()
        for point, tooltip in self._hit_points:
            if abs(point.x() - position.x()) <= 8 and abs(point.y() - position.y()) <= 8:
                QToolTip.showText(event.globalPosition().toPoint(), tooltip, self)
                return
        QToolTip.hideText()


class ComparisonPage(QWidget):
    changed = Signal()

    def __init__(self, service: ComparisonService, parent=None):
        super().__init__(parent)
        self.service = service
        self.components: list[dict] = []
        self.setObjectName("comparisonPage")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)
        header = QHBoxLayout()
        header.addWidget(QLabel("物料对比", objectName="comparisonTitle"))
        header.addStretch()
        self.remove_button = QPushButton("移除选中元件", objectName="comparisonRemoveButton")
        self.clear_button = QPushButton("清空对比", objectName="comparisonClearButton")
        header.addWidget(self.remove_button)
        header.addWidget(self.clear_button)
        layout.addLayout(header)

        self.empty_label = QLabel("请在元件库存中勾选元件，然后点击“加入对比”", objectName="comparisonEmpty")
        self.empty_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.empty_label)

        self.table = QTableWidget(objectName="comparisonTable")
        self.table.setRowCount(len(COMPARE_FIELDS))
        self.table.setVerticalHeaderLabels([title for _, title in COMPARE_FIELDS])
        self.table.setSelectionBehavior(QAbstractItemView.SelectColumns)
        self.table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.table.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.table.setAlternatingRowColors(False)
        layout.addWidget(self.table, 3)

        layout.addWidget(QLabel("采购价格变化", objectName="comparisonChartTitle"))
        self.chart = PriceHistoryChart(self)
        layout.addWidget(self.chart, 2)

        self.remove_button.clicked.connect(self.remove_selected)
        self.clear_button.clicked.connect(self.clear_all)
        self.refresh()

    @staticmethod
    def _display_value(key: str, value) -> str:
        if value is None:
            return ""
        if key == "latest_unit_price":
            return f"¥{float(value or 0):,.4f}"
        if key == "total_spent":
            return f"¥{float(value or 0):,.2f}"
        return str(value)

    def refresh(self) -> None:
        self.components = self.service.list_components()
        self.table.setColumnCount(len(self.components))
        self.table.setHorizontalHeaderLabels([
            str(component.get("product_code") or component.get("model") or "未编号")
            for component in self.components
        ])
        for column in range(len(self.components)):
            self.table.setColumnWidth(column, 220)

        for row, (key, _) in enumerate(COMPARE_FIELDS):
            values = [self._display_value(key, component.get(key)) for component in self.components]
            different = len(set(values)) > 1
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setData(Qt.UserRole, int(self.components[column]["id"]))
                item.setBackground(QColor(DIFFERENCE_FILL if different else BASE_FILL))
                self.table.setItem(row, column, item)

        component_ids = [int(component["id"]) for component in self.components]
        self.chart.set_data(self.components, self.service.price_history(component_ids))
        empty = not self.components
        self.empty_label.setVisible(empty)
        self.table.setVisible(not empty)
        self.remove_button.setEnabled(not empty)
        self.clear_button.setEnabled(not empty)

    def remove_selected(self) -> None:
        columns = sorted({index.column() for index in self.table.selectionModel().selectedIndexes()})
        component_ids = [int(self.components[column]["id"]) for column in columns]
        if not component_ids:
            return
        self.service.remove_components(component_ids)
        self.refresh()
        self.changed.emit()

    def clear_all(self) -> None:
        if not self.components:
            return
        self.service.clear()
        self.refresh()
        self.changed.emit()
