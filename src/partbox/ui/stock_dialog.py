from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QFrame, QGridLayout, QHBoxLayout, QLabel, QLineEdit, QMessageBox,
    QPushButton, QSpinBox, QVBoxLayout,
)

from partbox.services import StockService


class StockDialog(QDialog):
    def __init__(self, stocks: StockService, component_id: int, name: str, stock: int, unit: str, mode: str, parent=None):
        super().__init__(parent)
        self.stocks = stocks; self.component_id = component_id; self.stock = stock; self.unit = unit; self.mode = mode
        title = "入库" if mode == "in" else "出库"
        self.setWindowTitle(f"{title} · {name}")
        self.setObjectName("stockDialog"); self.setMinimumWidth(430)
        layout = QVBoxLayout(self); layout.setContentsMargins(22, 20, 22, 20); layout.setSpacing(14)

        heading = QHBoxLayout(); heading.setSpacing(10)
        operation = QLabel(title, objectName="stockDialogTitle"); operation.setProperty("mode", mode)
        component_name = QLabel(name, objectName="stockComponentName"); component_name.setTextInteractionFlags(Qt.TextSelectableByMouse)
        heading.addWidget(operation); heading.addWidget(component_name, 1); layout.addLayout(heading)

        stock_card = QFrame(objectName="stockInfoCard"); stock_layout = QHBoxLayout(stock_card); stock_layout.setContentsMargins(16, 12, 16, 12)
        stock_layout.addWidget(QLabel("当前库存", objectName="muted")); stock_layout.addStretch()
        current_value = QLabel(f"{stock} {unit}", objectName="currentStockValue"); stock_layout.addWidget(current_value)
        layout.addWidget(stock_card)

        fields = QFrame(objectName="stockFields"); grid = QGridLayout(fields); grid.setContentsMargins(0, 0, 0, 0); grid.setHorizontalSpacing(12); grid.setVerticalSpacing(10)
        quantity_label = QLabel("变动数量", objectName="fieldLabel")
        self.quantity = QSpinBox(objectName="stockQuantity"); self.quantity.setRange(1, 1_000_000); self.quantity.setValue(1); self.quantity.setSuffix(f" {unit}"); self.quantity.setMinimumHeight(44)
        notes_label = QLabel("用途／备注", objectName="fieldLabel")
        self.notes = QLineEdit(objectName="stockNotes"); self.notes.setPlaceholderText("例如：项目领用、补货、盘点校准"); self.notes.setMinimumHeight(42)
        grid.addWidget(quantity_label, 0, 0); grid.addWidget(self.quantity, 0, 1)
        grid.addWidget(notes_label, 1, 0); grid.addWidget(self.notes, 1, 1)
        grid.setColumnStretch(1, 1); layout.addWidget(fields)

        preview_card = QFrame(objectName="stockPreviewCard"); preview_layout = QHBoxLayout(preview_card); preview_layout.setContentsMargins(16, 12, 16, 12)
        preview_layout.addWidget(QLabel("库存变化", objectName="muted")); preview_layout.addStretch()
        self.preview = QLabel(objectName="stockPreviewValue"); preview_layout.addWidget(self.preview); layout.addWidget(preview_card)

        actions = QHBoxLayout(); actions.addStretch()
        self.cancel_button = QPushButton("取消"); self.confirm_button = QPushButton(f"确认{title}", objectName="primary")
        self.cancel_button.clicked.connect(self.reject); self.confirm_button.clicked.connect(self.apply_change)
        actions.addWidget(self.cancel_button); actions.addWidget(self.confirm_button); layout.addLayout(actions)
        self.quantity.valueChanged.connect(self.update_preview); self.update_preview()

    def update_preview(self):
        delta = self.quantity.value() if self.mode == "in" else -self.quantity.value()
        self.preview.setText(f"{self.stock} → {self.stock + delta} {self.unit}")

    def apply_change(self):
        delta = self.quantity.value() if self.mode == "in" else -self.quantity.value()
        try: self.stocks.adjust(self.component_id, delta, "manual_in" if self.mode == "in" else "manual_out", self.notes.text())
        except Exception as error: QMessageBox.warning(self, "操作失败", str(error)); return
        self.accept()
