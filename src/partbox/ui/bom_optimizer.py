from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView, QDialog, QFileDialog, QFormLayout, QFrame, QHBoxLayout,
    QLabel, QLineEdit, QMessageBox, QPushButton, QSpinBox, QStackedWidget,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from partbox.bom import BomError, ParsedBom, export_lcsc_bom, parse_bom
from partbox.bom_matching import MatchKind
from partbox.bom_workflow import BomWorkflow
from partbox.projects import ProjectError, ProjectService


class BomOptimizerDialog(QDialog):
    project_created = Signal(int)
    inventory_changed = Signal()

    def __init__(
        self,
        project_service: ProjectService,
        parsed_bom: ParsedBom | None = None,
        parent=None,
    ):
        super().__init__(parent)
        self.setObjectName("bomOptimizerDialog")
        self.setWindowTitle("导入BOM并计算")
        self.resize(1180, 760)
        self.project_service = project_service
        self.parsed_bom = parsed_bom
        self.workflow: BomWorkflow | None = None
        self.created_project_id: int | None = None
        self._build_ui()
        if parsed_bom is not None:
            self.source_path_label.setText(str(parsed_bom.path))
            self.project_name_edit.setText(parsed_bom.path.stem)
        self._update_buttons()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 16, 18, 16)
        root.setSpacing(12)
        heading_row = QHBoxLayout()
        self.heading = QLabel("BOM库存计算", objectName="bomOptimizerHeading")
        self.step_label = QLabel("1 / 3  导入设置", objectName="bomOptimizerStep")
        heading_row.addWidget(self.heading)
        heading_row.addStretch()
        heading_row.addWidget(self.step_label)
        root.addLayout(heading_row)

        self.pages = QStackedWidget(objectName="bomOptimizerPages")
        self.pages.addWidget(self._setup_page())
        self.pages.addWidget(self._matching_page())
        self.pages.addWidget(self._review_page())
        root.addWidget(self.pages, 1)

        footer = QHBoxLayout()
        self.undo_button = QPushButton("撤销上一步", objectName="bomUndoButton")
        self.previous_button = QPushButton("上一步", objectName="bomPreviousButton")
        self.next_button = QPushButton("下一步", objectName="bomNextButton")
        self.export_button = QPushButton("导出立创商城BOM", objectName="bomExportButton")
        self.cancel_button = QPushButton("取消")
        footer.addWidget(self.undo_button)
        footer.addStretch()
        footer.addWidget(self.cancel_button)
        footer.addWidget(self.previous_button)
        footer.addWidget(self.next_button)
        footer.addWidget(self.export_button)
        root.addLayout(footer)

        self.pages.currentChanged.connect(self._page_changed)
        self.undo_button.clicked.connect(self.undo_last_action)
        self.previous_button.clicked.connect(self.previous_step)
        self.next_button.clicked.connect(self.next_step)
        self.export_button.clicked.connect(self._export_clicked)
        self.cancel_button.clicked.connect(self.reject)

    def _setup_page(self) -> QWidget:
        page = QFrame(objectName="bomSetupPage")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        layout.addWidget(QLabel(
            "先选择从立创EDA导出的BOM，并填写本次实际制作的板子数量。库存计算会在下一步开始。",
            objectName="bomHint",
        ))
        file_row = QHBoxLayout()
        self.source_path_label = QLabel("尚未选择BOM文件", objectName="bomSourcePath")
        self.source_path_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.choose_file_button = QPushButton("选择BOM文件", objectName="bomChooseFileButton")
        file_row.addWidget(self.source_path_label, 1)
        file_row.addWidget(self.choose_file_button)
        layout.addLayout(file_row)
        form = QFormLayout()
        self.project_name_edit = QLineEdit(objectName="bomProjectName")
        self.project_name_edit.setPlaceholderText("例如：温控器主板")
        self.build_quantity_spin = QSpinBox(objectName="bomBuildQuantity")
        self.build_quantity_spin.setRange(1, 999999)
        self.build_quantity_spin.setValue(1)
        self.build_quantity_spin.setSuffix(" 份")
        form.addRow("新项目名称", self.project_name_edit)
        form.addRow("制作数量", self.build_quantity_spin)
        layout.addLayout(form)
        layout.addStretch()
        self.choose_file_button.clicked.connect(self.choose_file)
        return page

    def _matching_page(self) -> QWidget:
        page = QFrame(objectName="bomMatchingPage")
        layout = QHBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        left = QVBoxLayout()
        self.match_summary = QLabel(objectName="bomMatchSummary")
        left.addWidget(self.match_summary)
        self.match_table = QTableWidget(0, 6, objectName="bomMatchTable")
        self.match_table.setHorizontalHeaderLabels([
            "匹配状态", "BOM商品编号", "BOM元件", "需要", "库存抵扣", "仍需采购",
        ])
        self.match_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.match_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.match_table.verticalHeader().setVisible(False)
        self.match_table.horizontalHeader().setStretchLastSection(True)
        for column, width in enumerate((132, 128, 290, 78, 92, 96)):
            self.match_table.setColumnWidth(column, width)
        left.addWidget(self.match_table, 1)
        layout.addLayout(left, 3)

        candidate_panel = QFrame(objectName="bomCandidatePanel")
        candidate_layout = QVBoxLayout(candidate_panel)
        candidate_layout.addWidget(QLabel("相似库存元件", objectName="bomPanelTitle"))
        candidate_layout.addWidget(QLabel(
            "只有规格完全一致的元件会自动匹配；下列相似项需要你确认。",
            objectName="bomHint",
        ))
        self.candidate_table = QTableWidget(0, 4, objectName="bomCandidateTable")
        self.candidate_table.setHorizontalHeaderLabels(["商品编号", "名称", "库存", "差异"])
        self.candidate_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.candidate_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.candidate_table.verticalHeader().setVisible(False)
        self.candidate_table.horizontalHeader().setStretchLastSection(True)
        for column, width in enumerate((112, 180, 72, 280)):
            self.candidate_table.setColumnWidth(column, width)
        candidate_layout.addWidget(self.candidate_table, 1)
        action_row = QHBoxLayout()
        self.accept_candidate_button = QPushButton("使用选中元件", objectName="bomAcceptCandidateButton")
        self.reject_button = QPushButton("以上均不匹配", objectName="bomRejectCandidatesButton")
        action_row.addWidget(self.accept_candidate_button)
        action_row.addWidget(self.reject_button)
        candidate_layout.addLayout(action_row)
        layout.addWidget(candidate_panel, 2)
        self.match_table.currentCellChanged.connect(lambda *_: self._show_candidates())
        self.accept_candidate_button.clicked.connect(self.accept_candidate)
        self.reject_button.clicked.connect(self.reject_candidates)
        return page

    def _review_page(self) -> QWidget:
        page = QFrame(objectName="bomReviewPage")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        self.review_summary = QLabel(objectName="bomReviewSummary")
        layout.addWidget(self.review_summary)
        self.review_table = QTableWidget(0, 7, objectName="bomReviewTable")
        self.review_table.setHorizontalHeaderLabels([
            "结果", "元件", "需要", "库存抵扣", "缺口", "额外补货", "导出数量",
        ])
        self.review_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.review_table.verticalHeader().setVisible(False)
        self.review_table.horizontalHeader().setStretchLastSection(True)
        for column, width in enumerate((150, 270, 90, 100, 90, 120, 110)):
            self.review_table.setColumnWidth(column, width)
        layout.addWidget(self.review_table, 1)
        return page

    def choose_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "选择立创EDA BOM", "", "BOM文件 (*.xlsx *.xls *.csv)"
        )
        if not path:
            return
        try:
            self.parsed_bom = parse_bom(path)
        except BomError as error:
            QMessageBox.warning(self, "无法读取BOM", str(error))
            return
        self.source_path_label.setText(path)
        if not self.project_name_edit.text().strip():
            self.project_name_edit.setText(Path(path).stem)

    def _inventory(self) -> list[dict]:
        return [dict(row) for row in self.project_service.db.connection.execute(
            "SELECT * FROM components WHERE inactive=0 ORDER BY id"
        )]

    def next_step(self) -> None:
        index = self.pages.currentIndex()
        if index == 0:
            if self.parsed_bom is None:
                QMessageBox.warning(self, "尚未选择BOM", "请先选择要计算的BOM文件。")
                return
            if not self.project_name_edit.text().strip():
                QMessageBox.warning(self, "缺少项目名称", "请填写新项目名称。")
                return
            self.workflow = BomWorkflow(
                self.parsed_bom.lines,
                self._inventory(),
                self.build_quantity_spin.value(),
            )
            self._render_matching()
            self.pages.setCurrentIndex(1)
            if self.match_table.rowCount():
                self.match_table.selectRow(0)
        elif index == 1:
            if self.workflow is None:
                return
            if self.workflow.unresolved_count:
                QMessageBox.warning(
                    self,
                    "仍有待确认元件",
                    f"还有 {self.workflow.unresolved_count} 行相似元件未处理，请选择库存元件或点击“以上均不匹配”。",
                )
                return
            self._render_review()
            self.pages.setCurrentIndex(2)

    def previous_step(self) -> None:
        index = self.pages.currentIndex()
        if index > 0:
            self.pages.setCurrentIndex(index - 1)

    def _page_changed(self, index: int) -> None:
        labels = ("1 / 3  导入设置", "2 / 3  匹配库存", "3 / 3  缺料复核")
        self.step_label.setText(labels[index])
        self._update_buttons()

    def _update_buttons(self) -> None:
        index = self.pages.currentIndex()
        self.previous_button.setVisible(index > 0)
        self.next_button.setVisible(index < 2)
        self.export_button.setVisible(index == 2)
        self.undo_button.setVisible(index > 0)
        self.undo_button.setEnabled(bool(self.workflow and self.workflow.can_undo))

    def _status(self, row) -> str:
        if row.unresolved:
            return "待手动确认"
        if row.rejected or row.matched_component_id is None:
            return "未匹配"
        if row.shortage_quantity:
            return "已匹配／库存不足"
        return "完全匹配"

    def _render_matching(self, preferred_row: int | None = None) -> None:
        if self.workflow is None:
            return
        current = self.match_table.currentRow() if preferred_row is None else preferred_row
        self.match_table.setRowCount(len(self.workflow.rows))
        colors = {
            "待手动确认": QColor("#fff1bf"),
            "未匹配": QColor("#fde2e2"),
            "已匹配／库存不足": QColor("#ffe8b0"),
            "完全匹配": QColor("#def4e5"),
        }
        for row_index, row in enumerate(self.workflow.rows):
            status = self._status(row)
            values = [
                status,
                row.line.product_code or "—",
                row.line.description or row.line.model or row.line.product_type or "—",
                str(row.required_quantity),
                str(row.allocated_quantity),
                str(row.shortage_quantity),
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                if column == 0:
                    item.setBackground(colors[status])
                self.match_table.setItem(row_index, column, item)
        self.match_summary.setText(
            f"共 {len(self.workflow.rows)} 行 · 自动完全匹配 "
            f"{sum(row.match_kind is MatchKind.EXACT for row in self.workflow.rows)} 行 · "
            f"待确认 {self.workflow.unresolved_count} 行"
        )
        if self.match_table.rowCount():
            self.match_table.selectRow(min(max(current, 0), self.match_table.rowCount() - 1))
        self._show_candidates()
        self._update_buttons()

    def _show_candidates(self) -> None:
        self.candidate_table.setRowCount(0)
        if self.workflow is None:
            return
        row_index = self.match_table.currentRow()
        if row_index < 0 or row_index >= len(self.workflow.rows):
            return
        workflow_row = self.workflow.rows[row_index]
        self.candidate_table.setRowCount(len(workflow_row.candidates))
        for candidate_row, candidate in enumerate(workflow_row.candidates):
            component = candidate.component
            values = [
                str(component.get("product_code") or "—"),
                str(component.get("product_name") or component.get("model") or "—"),
                str(component.get("current_stock") or 0),
                "；".join(candidate.differences) or "参数接近",
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setData(Qt.UserRole, candidate.component_id)
                self.candidate_table.setItem(candidate_row, column, item)
        if self.candidate_table.rowCount():
            selected = next(
                (
                    index for index, candidate in enumerate(workflow_row.candidates)
                    if candidate.component_id == workflow_row.matched_component_id
                ),
                0,
            )
            self.candidate_table.selectRow(selected)
        enabled = workflow_row.match_kind is MatchKind.SIMILAR
        self.accept_candidate_button.setEnabled(enabled and self.candidate_table.rowCount() > 0)
        self.reject_button.setEnabled(enabled)

    def accept_candidate(self) -> None:
        if self.workflow is None:
            return
        row_index = self.match_table.currentRow()
        candidate_row = self.candidate_table.currentRow()
        if row_index < 0 or candidate_row < 0:
            return
        component_id = self.candidate_table.item(candidate_row, 0).data(Qt.UserRole)
        self.workflow.choose_candidate(row_index, int(component_id))
        self._render_matching(row_index)

    def reject_candidates(self) -> None:
        if self.workflow is None:
            return
        row_index = self.match_table.currentRow()
        if row_index < 0:
            return
        try:
            self.workflow.reject_candidates(row_index)
        except ValueError:
            return
        self._render_matching(row_index)

    def undo_last_action(self) -> None:
        if self.workflow and self.workflow.undo():
            if self.pages.currentIndex() == 2:
                self._render_review()
            else:
                self._render_matching()

    def _render_review(self) -> None:
        if self.workflow is None:
            return
        self.review_table.setRowCount(len(self.workflow.rows))
        for row_index, row in enumerate(self.workflow.rows):
            if row.shortage_quantity:
                status = "需要补充库存"
                color = QColor("#ffe6b3")
            elif row.exhausts_stock:
                status = "本次将用光库存"
                color = QColor("#fff1bf")
            else:
                status = "库存满足"
                color = QColor("#e1f3e7")
            name = row.line.product_code or row.line.model or row.line.description or row.line.product_type
            values = [
                status,
                name or "—",
                str(row.required_quantity),
                str(row.allocated_quantity),
                str(row.shortage_quantity),
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                if column == 0:
                    item.setBackground(color)
                self.review_table.setItem(row_index, column, item)
            extra = QSpinBox(objectName="bomExtraPurchase")
            extra.setRange(0, 99999999)
            extra.setValue(row.extra_purchase_quantity)
            extra.setToolTip("可选：在实际缺口之外额外补货，默认 0")
            extra.valueChanged.connect(
                lambda value, index=row_index: self._extra_purchase_changed(index, value)
            )
            self.review_table.setCellWidget(row_index, 5, extra)
            self.review_table.setItem(row_index, 6, QTableWidgetItem(str(row.purchase_quantity)))
        self.review_summary.setText(
            f"需要补充库存 {len(self.workflow.shortage_rows)} 行；"
            f"本次会用光库存 {len(self.workflow.exhausted_rows)} 行。"
            "“额外补货”默认 0，可直接在表格中调整。"
        )

    def _extra_purchase_changed(self, row_index: int, value: int) -> None:
        if self.workflow is None:
            return
        self.workflow.set_extra_purchase(row_index, value)
        self.review_table.item(row_index, 6).setText(
            str(self.workflow.rows[row_index].purchase_quantity)
        )
        self._update_buttons()

    def complete_export(self, target: Path | str, issue_stock: bool = False) -> int:
        if self.workflow is None or self.parsed_bom is None:
            raise ValueError("BOM尚未完成计算")
        if self.workflow.unresolved_count:
            raise ValueError("仍有相似元件未处理")
        project_name = self.project_name_edit.text().strip()
        if not project_name:
            raise ProjectError("项目名称不能为空")
        export_rows = self.workflow.export_rows()
        export_lcsc_bom(target, export_rows)
        project_id = self.project_service.create_from_bom(
            project_name,
            self.workflow.build_quantity,
            str(self.parsed_bom.path),
            export_rows,
        )
        self.created_project_id = project_id
        if issue_stock:
            self.project_service.issue_bom_allocations(project_id)
            self.inventory_changed.emit()
        self.project_created.emit(project_id)
        return project_id

    def _export_clicked(self) -> None:
        if self.workflow is None:
            return
        path, _ = QFileDialog.getSaveFileName(
            self,
            "导出立创商城BOM",
            f"{self.project_name_edit.text().strip() or 'PartBOX优化BOM'}.xlsx",
            "Excel文件 (*.xlsx)",
        )
        if not path:
            return
        try:
            project_id = self.complete_export(path, issue_stock=False)
        except (BomError, ProjectError, ValueError, OSError) as error:
            QMessageBox.warning(self, "导出失败", str(error))
            return
        answer = QMessageBox.question(
            self,
            "是否占用库存",
            "优化BOM已导出，新项目也已保存。是否现在按本次制作数量将已匹配元件出库？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer == QMessageBox.Yes:
            try:
                self.project_service.issue_bom_allocations(project_id)
                self.inventory_changed.emit()
            except ProjectError as error:
                QMessageBox.warning(self, "项目已保存，但出库失败", str(error))
                return
        QMessageBox.information(self, "处理完成", f"已导出：{path}\n已保存为新项目。")
        self.accept()
