from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox, QFileDialog, QHBoxLayout, QLabel, QMessageBox, QPushButton,
    QTabWidget, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from partbox.services import DataService, StockService


class HistoryPage(QWidget):
    changed = Signal()

    def __init__(self, data: DataService, stocks: StockService):
        super().__init__(); self.setObjectName("historyPage"); self.data = data; self.stocks = stocks
        layout = QVBoxLayout(self); layout.setContentsMargins(16, 16, 16, 16); layout.setSpacing(10)
        title = QLabel("库存流水", objectName="pageTitle")
        layout.addWidget(title)
        self.table = QTableWidget(0, 10, objectName="historyTable"); self.table.setHorizontalHeaderLabels(["时间", "商品编号", "元件", "类型", "变化数量", "修改前", "修改后", "单位", "备注", "流水号"])
        self.table.setSelectionBehavior(QTableWidget.SelectRows); layout.addWidget(self.table)
        row = QHBoxLayout(); undo = QPushButton("撤销选中流水"); undo.clicked.connect(self.reverse_selected); refresh = QPushButton("刷新"); refresh.clicked.connect(self.refresh)
        row.addWidget(undo); row.addWidget(refresh); row.addStretch(); layout.addLayout(row); self.refresh()

    def refresh(self):
        rows = self.data.stock_history(); self.table.setRowCount(len(rows))
        for r, item in enumerate(rows):
            values = [item["occurred_at"], item["product_code"], item["model"] or item["product_name"], item["movement_type"], item["quantity_delta"], item["stock_before"], item["stock_after"], item["unit"], item["notes"], item["id"]]
            for c, value in enumerate(values): self.table.setItem(r, c, QTableWidgetItem(str(value or "")))
        self.table.resizeColumnsToContents()

    def reverse_selected(self):
        row = self.table.currentRow()
        if row < 0: return
        movement_id = int(self.table.item(row, 9).text())
        try: self.stocks.reverse(movement_id, "用户撤销")
        except Exception as error: QMessageBox.warning(self, "无法撤销", str(error)); return
        self.refresh(); self.changed.emit()


class ImportsPage(QWidget):
    def __init__(self, data: DataService):
        super().__init__(); self.setObjectName("importsPage"); self.data = data; layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16); layout.setSpacing(10)
        title = QLabel("导入记录", objectName="pageTitle"); layout.addWidget(title)
        tabs = QTabWidget(); layout.addWidget(tabs)
        self.table = QTableWidget(0, 8, objectName="importsTable"); self.table.setHorizontalHeaderLabels(["导入时间", "文件名", "商品", "费用", "重复", "异常", "强制", "状态"]); tabs.addTab(self.table, "导入批次")
        self.purchase_table = QTableWidget(0, 25, objectName="purchaseDetailsTable")
        self.purchase_fields = ["order_number", "order_status", "order_time", "recipient", "customer_part_number", "product_code", "brand", "product_type", "product_name", "model", "package", "quantity", "unit", "unit_price", "subtotal", "shipping_date", "courier", "tracking_number", "receipt_date", "invoice_number", "invoice_time", "customer_representative", "original_order", "bom_flag", "contract_number"]
        self.purchase_table.setHorizontalHeaderLabels(["订单编号", "订单状态", "下单时间", "收货人", "客户料号", "商品编号", "品牌", "商品类型", "商品名称", "商品型号", "封装格式", "订购数量", "商品单位", "单价（人民币含税）", "小计金额（人民币含税）", "发货日期", "快递公司", "快递单号", "签收日期", "发票号", "开票时间", "客户代表", "归属原订单", "bom标识", "订单合同编号"])
        tabs.addTab(self.purchase_table, "采购明细（完整 25 列）")

    def refresh(self):
        rows = self.data.import_batches(); self.table.setRowCount(len(rows))
        for r, item in enumerate(rows):
            values = [item["imported_at"], item["filename"], item["product_count"], item["fee_count"], item["duplicate_count"], item["issue_count"], "是" if item["forced"] else "否", item["status"]]
            for c, value in enumerate(values): self.table.setItem(r, c, QTableWidgetItem(str(value)))
        self.table.resizeColumnsToContents()
        purchases = self.data.purchase_lines(); self.purchase_table.setRowCount(len(purchases))
        for r, item in enumerate(purchases):
            for c, field in enumerate(self.purchase_fields): self.purchase_table.setItem(r, c, QTableWidgetItem(str(item.get(field) or "")))
        self.purchase_table.resizeColumnsToContents()


class SettingsPage(QWidget):
    changed = Signal()

    def __init__(self, data: DataService, default_backup_dir: Path):
        super().__init__(); self.setObjectName("settingsPage"); self.data = data; self.default_backup_dir = Path(default_backup_dir)
        layout = QVBoxLayout(self); layout.setContentsMargins(16, 16, 16, 16); layout.setSpacing(10)
        title = QLabel("设置与数据安全", objectName="pageTitle"); layout.addWidget(title)
        self.allow_negative = QCheckBox("允许负库存")
        self.allow_negative.setChecked(data.db.get_setting("allow_negative_stock") == "1")
        self.allow_negative.toggled.connect(lambda checked: data.db.set_setting("allow_negative_stock", "1" if checked else "0")); layout.addWidget(self.allow_negative)
        layout.addWidget(QLabel(f"数据库位置：{data.db.path}"))
        backup = QPushButton("立即备份数据库"); backup.clicked.connect(self.backup); restore = QPushButton("从备份恢复"); restore.clicked.connect(self.restore)
        export = QPushButton("导出库存表 Excel"); export.clicked.connect(self.export); reset = QPushButton("重建空数据库"); reset.clicked.connect(self.reset)
        for button in (backup, restore, export, reset): button.setMaximumWidth(220); layout.addWidget(button)
        layout.addStretch()

    def backup(self):
        target = self.data.backup(self.default_backup_dir); QMessageBox.information(self, "备份完成", f"已保存到：\n{target}")

    def restore(self):
        source, _ = QFileDialog.getOpenFileName(self, "选择 PartBOX 备份", str(self.default_backup_dir), "数据库 (*.db)")
        if not source: return
        if QMessageBox.question(self, "确认恢复", "当前数据将被备份文件替换。是否继续？", QMessageBox.Yes | QMessageBox.No) != QMessageBox.Yes: return
        if QMessageBox.question(self, "再次确认恢复", "请再次确认：使用所选备份替换当前全部数据？", QMessageBox.Yes | QMessageBox.No) != QMessageBox.Yes: return
        self.data.backup(self.default_backup_dir); self.data.restore(Path(source)); self.changed.emit(); QMessageBox.information(self, "恢复完成", "数据库已恢复。")

    def export(self):
        target, _ = QFileDialog.getSaveFileName(self, "导出库存", "PartBOX-库存.xlsx", "Excel (*.xlsx)")
        if target: self.data.export_inventory(Path(target)); QMessageBox.information(self, "导出完成", target)

    def reset(self):
        if QMessageBox.question(self, "重建空数据库", "这会清空全部元件和历史。程序会先自动备份。是否继续？", QMessageBox.Yes | QMessageBox.No) != QMessageBox.Yes: return
        if QMessageBox.question(self, "再次确认清空", "请再次确认：清空全部元件、采购记录和库存流水？", QMessageBox.Yes | QMessageBox.No) != QMessageBox.Yes: return
        self.data.backup(self.default_backup_dir); self.data.reset_database(); self.changed.emit(); QMessageBox.information(self, "完成", "数据库已恢复为空库。")
