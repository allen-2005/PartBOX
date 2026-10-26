from __future__ import annotations

from dataclasses import dataclass, field

from partbox.bom import BomLine
from partbox.bom_matching import MatchCandidate, MatchKind, match_bom


@dataclass
class BomWorkflowRow:
    line: BomLine
    required_quantity: int
    match_kind: MatchKind
    matched_component_id: int | None
    allocated_quantity: int
    shortage_quantity: int
    candidates: tuple[MatchCandidate, ...] = ()
    rejected: bool = False
    extra_purchase_quantity: int = 0
    exhausts_stock: bool = False

    @property
    def unresolved(self) -> bool:
        return (
            self.match_kind is MatchKind.SIMILAR
            and self.matched_component_id is None
            and not self.rejected
        )

    @property
    def purchase_quantity(self) -> int:
        return self.shortage_quantity + self.extra_purchase_quantity


class BomWorkflow:
    def __init__(self, lines: list[BomLine], inventory: list[dict], build_quantity: int):
        self.lines = list(lines)
        self.inventory = [dict(component) for component in inventory]
        self.inventory_by_id = {
            int(component["id"]): component for component in self.inventory
        }
        self.build_quantity = int(build_quantity)
        self._history: list[tuple[int, int | None, bool, int]] = []
        self.rows: list[BomWorkflowRow] = []
        self._initialize_rows()

    def _initialize_rows(self) -> None:
        results = match_bom(self.lines, self.inventory, self.build_quantity)
        self.rows = [
            BomWorkflowRow(
                line=result.line,
                required_quantity=result.required_quantity,
                match_kind=result.kind,
                matched_component_id=result.matched_component_id,
                allocated_quantity=result.allocated_quantity,
                shortage_quantity=result.shortage_quantity,
                candidates=result.candidates,
            )
            for result in results
        ]
        self._reallocate()

    @property
    def unresolved_count(self) -> int:
        return sum(row.unresolved for row in self.rows)

    @property
    def can_undo(self) -> bool:
        return bool(self._history)

    @property
    def shortage_rows(self) -> list[BomWorkflowRow]:
        return [row for row in self.rows if row.shortage_quantity > 0]

    @property
    def exhausted_rows(self) -> list[BomWorkflowRow]:
        return [row for row in self.rows if row.exhausts_stock]

    def _remember(self, row_index: int) -> None:
        row = self.rows[row_index]
        self._history.append((
            row_index,
            row.matched_component_id,
            row.rejected,
            row.extra_purchase_quantity,
        ))

    def choose_candidate(self, row_index: int, component_id: int) -> None:
        row = self.rows[row_index]
        component_id = int(component_id)
        if component_id not in {candidate.component_id for candidate in row.candidates}:
            raise ValueError("所选元件不是该BOM行的候选项")
        self._remember(row_index)
        row.matched_component_id = component_id
        row.rejected = False
        self._reallocate()

    def reject_candidates(self, row_index: int) -> None:
        row = self.rows[row_index]
        if row.match_kind is not MatchKind.SIMILAR:
            raise ValueError("该BOM行没有待处理的相似元件")
        self._remember(row_index)
        row.matched_component_id = None
        row.rejected = True
        self._reallocate()

    def set_extra_purchase(self, row_index: int, quantity: int) -> None:
        try:
            quantity = int(quantity)
        except (TypeError, ValueError) as error:
            raise ValueError("额外补货数量必须是大于等于 0 的整数") from error
        if quantity < 0:
            raise ValueError("额外补货数量必须是大于等于 0 的整数")
        self._remember(row_index)
        self.rows[row_index].extra_purchase_quantity = quantity

    def undo(self) -> bool:
        if not self._history:
            return False
        row_index, matched_component_id, rejected, extra_purchase = self._history.pop()
        row = self.rows[row_index]
        row.matched_component_id = matched_component_id
        row.rejected = rejected
        row.extra_purchase_quantity = extra_purchase
        self._reallocate()
        return True

    def _reallocate(self) -> None:
        remaining = {
            component_id: max(0, int(component.get("current_stock") or 0))
            for component_id, component in self.inventory_by_id.items()
        }
        for row in self.rows:
            row.exhausts_stock = False
            component_id = row.matched_component_id
            if component_id is None:
                row.allocated_quantity = 0
                row.shortage_quantity = row.required_quantity
                continue
            available = remaining.get(component_id, 0)
            allocated = min(row.required_quantity, available)
            row.allocated_quantity = allocated
            row.shortage_quantity = row.required_quantity - allocated
            remaining[component_id] = available - allocated
            row.exhausts_stock = (
                remaining[component_id] == 0
                and allocated > 0
                and row.shortage_quantity == 0
            )

    def export_rows(self) -> list[dict]:
        return [
            {
                "line": row.line,
                "required_quantity": row.required_quantity,
                "match_status": (
                    "rejected" if row.rejected else row.match_kind.value
                ),
                "matched_component_id": row.matched_component_id,
                "allocated_quantity": row.allocated_quantity,
                "shortage_quantity": row.shortage_quantity,
                "extra_purchase_quantity": row.extra_purchase_quantity,
                "purchase_quantity": row.purchase_quantity,
            }
            for row in self.rows
        ]
