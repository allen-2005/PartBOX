from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView, QDialog, QDialogButtonBox, QFrame, QGridLayout,
    QHeaderView, QLabel, QMessageBox, QTableWidget, QTableWidgetItem,
    QVBoxLayout,
)

from partbox.services import ImportPreview, ImportService


class ImportDialog(QDialog):
    def __init__(self, importer: ImportService, parent=None):
        super().__init__(parent)
        self.setObjectName("importDialog")
        self.importer = importer
        self.preview: ImportPreview | None = None
        self.setWindowTitle("导入立创订单")
        self.resize(1040, 700)
        layout = QVBoxLayout(self); layout.setContentsMargins(22, 20, 22, 20); layout.setSpacing(14)
        heading = QLabel("确认导入内容", objectName="dialogHeading"); layout.addWidget(heading)
        self.summary = QLabel("正在读取订单……", objectName="importSummary")
        self.summary.setWordWrap(True); layout.addWidget(self.summary)
        stats = QFrame(objectName="importStats"); stats_layout = QGridLayout(stats); stats_layout.setContentsMargins(12, 10, 12, 10); stats_layout.setSpacing(8)
        self.summary_counts = {}
        for column, (key, title) in enumerate((("files", "文件"), ("new", "新元件"), ("existing", "已有元件"), ("duplicate", "重复不计数"), ("fees", "费用"), ("issues", "异常"))):
            card = QFrame(objectName="importStatCard"); card_layout = QVBoxLayout(card); card_layout.setContentsMargins(10, 7, 10, 7); card_layout.setSpacing(1)
            value = QLabel("0", objectName="importStatValue"); label = QLabel(title, objectName="muted")
            card_layout.addWidget(value); card_layout.addWidget(label); stats_layout.addWidget(card, 0, column)
            self.summary_counts[key] = value
        layout.addWidget(stats)
        layout.addWidget(QLabel(
            "新元件将自动建立库存；已有元件可选择是否把本次购买数量加入库存；"
            "重复采购只校正商品信息，不会重复增加数量。",
            objectName="importHint",
        ))
        self.existing_table = QTableWidget(0, 6)
        self.existing_table.setObjectName("importPreviewTable")
        self.existing_table.setHorizontalHeaderLabels(["入库方式", "商品编号", "商品名称", "型号", "封装", "本次数量"])
        self.existing_table.setAlternatingRowColors(True); self.existing_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.existing_table.verticalHeader().setVisible(False)
        header = self.existing_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeToContents); header.setSectionResizeMode(2, QHeaderView.Stretch)
        layout.addWidget(self.existing_table, 1)
        self.buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.buttons.button(QDialogButtonBox.Ok).setText("确认导入")
        self.buttons.button(QDialogButtonBox.Ok).setObjectName("primary")
        self.buttons.button(QDialogButtonBox.Cancel).setText("取消")
        self.buttons.accepted.connect(self.commit_import); self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)

    def set_format_name(self, format_name: str):
        self.setWindowTitle(f"导入立创商城{format_name}")
        self.summary.setText(f"正在读取{format_name}……")

    def set_preview(self, preview: ImportPreview):
        self.preview = preview
        total_lines = len(preview.new_lines) + len(preview.existing_lines) + len(preview.duplicate_lines)
        duplicate_note = (
            f"；其中 {len(preview.duplicate_lines)} 条重复采购只校正商品信息，不重复累计"
            if preview.duplicate_lines else ""
        )
        self.summary.setText(
            f"共读取 {len(preview.statements)} 个文件，识别 {total_lines} 条元件明细{duplicate_note}。"
        )
        counts = {"files": len(preview.statements), "new": len(preview.new_lines), "existing": len(preview.existing_lines), "duplicate": len(preview.duplicate_lines), "fees": len(preview.fees), "issues": len(preview.issues)}
        for key, value in counts.items(): self.summary_counts[key].setText(str(value))
        lines = [(line, False) for line in preview.new_lines] + [(line, True) for line in preview.existing_lines]
        self.existing_table.setRowCount(len(lines))
        for row, (line, existing) in enumerate(lines):
            if existing:
                status = QTableWidgetItem("加入库存"); status.setCheckState(Qt.Checked)
                status.setData(Qt.UserRole, line.line_fingerprint); status.setData(Qt.UserRole + 1, "existing")
                status.setFlags(status.flags() & ~Qt.ItemIsEditable)
            else:
                status = QTableWidgetItem("自动入库"); status.setData(Qt.UserRole + 1, "new")
                status.setFlags(status.flags() & ~Qt.ItemIsEditable & ~Qt.ItemIsUserCheckable)
                status.setForeground(Qt.GlobalColor.darkBlue)
            self.existing_table.setItem(row, 0, status)
            for column, text in enumerate([line.product_code, line.product_name, line.model, line.package, str(line.quantity)], 1):
                item = QTableWidgetItem(text); item.setFlags(item.flags() & ~Qt.ItemIsEditable); self.existing_table.setItem(row, column, item)

    def stock_decisions(self) -> dict[str, bool]:
        result = {}
        for row in range(self.existing_table.rowCount()):
            item = self.existing_table.item(row, 0)
            if item.data(Qt.UserRole + 1) == "existing":
                result[str(item.data(Qt.UserRole))] = item.checkState() == Qt.Checked
        return result

    def commit_import(self):
        if self.preview is None: return
        try:
            self.importer.commit(self.preview, self.stock_decisions())
        except Exception as error:
            QMessageBox.critical(self, "导入失败", str(error)); return
        self.accept()
