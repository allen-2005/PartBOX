from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import json

from partbox.database import Database


def now_text() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


class ProjectError(RuntimeError):
    pass


@dataclass(frozen=True)
class ProjectSyncResult:
    operation_id: int | None
    changed_lines: int
    stock_delta: int


class ProjectService:
    def __init__(self, db: Database):
        self.db = db

    def list_projects(self) -> list[dict]:
        return [dict(row) for row in self.db.connection.execute(
            "SELECT p.*, COUNT(pc.component_id) component_count "
            "FROM projects p LEFT JOIN project_components pc ON pc.project_id=p.id "
            "WHERE p.inactive=0 GROUP BY p.id ORDER BY p.updated_at DESC, p.id DESC"
        )]

    def create_project(self, name: str) -> int:
        name = (name or "").strip()
        if not name:
            raise ProjectError("项目名称不能为空")
        timestamp = now_text()
        try:
            cursor = self.db.connection.execute(
                "INSERT INTO projects(name,created_at,updated_at) VALUES(?,?,?)",
                (name, timestamp, timestamp),
            )
            self.db.connection.commit()
        except Exception as error:
            self.db.connection.rollback()
            if "UNIQUE" in str(error).upper():
                raise ProjectError("项目名称已存在") from error
            raise
        return int(cursor.lastrowid)

    def create_from_bom(
        self,
        name: str,
        build_quantity: int,
        source_bom_path: str,
        rows: list[dict],
    ) -> int:
        name = (name or "").strip()
        if not name:
            raise ProjectError("项目名称不能为空")
        try:
            build_quantity = int(build_quantity)
        except (TypeError, ValueError) as error:
            raise ProjectError("项目制作数量必须是大于等于 1 的整数") from error
        if build_quantity < 1:
            raise ProjectError("项目制作数量必须是大于等于 1 的整数")
        if not rows:
            raise ProjectError("BOM中没有可保存的元件")

        timestamp = now_text()
        try:
            with self.db.transaction() as connection:
                project_id = int(connection.execute(
                    "INSERT INTO projects(name,build_quantity,source_bom_path,created_at,updated_at) "
                    "VALUES(?,?,?,?,?) RETURNING id",
                    (name, build_quantity, str(source_bom_path or ""), timestamp, timestamp),
                ).fetchone()[0])
                allocations: dict[int, int] = {}
                designators: dict[int, list[str]] = {}
                for workflow_row in rows:
                    line = workflow_row["line"]
                    required = int(workflow_row["required_quantity"])
                    allocated = int(workflow_row.get("allocated_quantity") or 0)
                    purchase = int(workflow_row.get("purchase_quantity") or 0)
                    component_id = workflow_row.get("matched_component_id")
                    if required < 1 or allocated < 0 or purchase < 0:
                        raise ProjectError("BOM数量配置无效")
                    if component_id is not None:
                        component_id = int(component_id)
                        if not connection.execute(
                            "SELECT 1 FROM components WHERE id=? AND inactive=0", (component_id,)
                        ).fetchone():
                            raise ProjectError("匹配元件不存在")
                        if allocated:
                            allocations[component_id] = allocations.get(component_id, 0) + allocated
                            if line.designator:
                                designators.setdefault(component_id, []).append(line.designator)
                    connection.execute(
                        "INSERT INTO project_bom_lines("
                        "project_id,source_row,source_values_json,per_build_quantity,required_quantity,"
                        "designator,product_code,product_type,description,model,package,brand,"
                        "matched_component_id,match_status,allocated_quantity,purchase_quantity"
                        ") VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                        (
                            project_id,
                            int(line.source_row),
                            json.dumps(line.source_values, ensure_ascii=False, default=str),
                            int(line.quantity),
                            required,
                            line.designator,
                            line.product_code,
                            line.product_type,
                            line.description,
                            line.model,
                            line.package,
                            line.brand,
                            component_id,
                            str(workflow_row.get("match_status") or "unmatched"),
                            allocated,
                            purchase,
                        ),
                    )
                for component_id, quantity in allocations.items():
                    reference = ",".join(dict.fromkeys(designators.get(component_id, [])))
                    connection.execute(
                        "INSERT INTO project_components("
                        "project_id,component_id,quantity,synced_quantity,reference_designator,created_at,updated_at"
                        ") VALUES(?,?,?,0,?,?,?)",
                        (project_id, component_id, quantity, reference, timestamp, timestamp),
                    )
        except ProjectError:
            raise
        except Exception as error:
            if "UNIQUE" in str(error).upper():
                raise ProjectError("项目名称已存在") from error
            raise
        return project_id

    def list_bom_lines(self, project_id: int) -> list[dict]:
        result = []
        for row in self.db.connection.execute(
            "SELECT * FROM project_bom_lines WHERE project_id=? ORDER BY source_row,id",
            (project_id,),
        ):
            item = dict(row)
            item["source_values"] = json.loads(item.pop("source_values_json") or "{}")
            result.append(item)
        return result

    def issue_bom_allocations(self, project_id: int) -> ProjectSyncResult:
        return self.sync(project_id)

    def rename_project(self, project_id: int, name: str) -> None:
        name = (name or "").strip()
        if not name:
            raise ProjectError("项目名称不能为空")
        try:
            cursor = self.db.connection.execute(
                "UPDATE projects SET name=?,updated_at=? WHERE id=?",
                (name, now_text(), project_id),
            )
            if not cursor.rowcount:
                raise ProjectError("项目不存在")
            self.db.connection.commit()
        except ProjectError:
            self.db.connection.rollback()
            raise
        except Exception as error:
            self.db.connection.rollback()
            if "UNIQUE" in str(error).upper():
                raise ProjectError("项目名称已存在") from error
            raise

    def delete_project(self, project_id: int) -> None:
        pending = self.db.connection.execute(
            "SELECT COUNT(*) FROM project_components WHERE project_id=? AND quantity<>synced_quantity",
            (project_id,),
        ).fetchone()[0]
        if pending:
            raise ProjectError("项目还有未同步的用量变更，请先导出变更到元件库存")
        cursor = self.db.connection.execute(
            "UPDATE projects SET inactive=1,updated_at=? WHERE id=? AND inactive=0",
            (now_text(), project_id),
        )
        if not cursor.rowcount:
            raise ProjectError("项目不存在")
        self.db.connection.commit()

    def add_components(self, project_id: int, component_ids: list[int]) -> int:
        unique_ids = list(dict.fromkeys(int(value) for value in component_ids))
        timestamp = now_text()
        inserted = 0
        with self.db.transaction() as connection:
            if not connection.execute("SELECT 1 FROM projects WHERE id=?", (project_id,)).fetchone():
                raise ProjectError("项目不存在")
            for component_id in unique_ids:
                if not connection.execute("SELECT 1 FROM components WHERE id=?", (component_id,)).fetchone():
                    raise ProjectError("元件不存在")
                cursor = connection.execute(
                    "INSERT OR IGNORE INTO project_components(project_id,component_id,quantity,synced_quantity,created_at,updated_at) "
                    "VALUES(?,?,1,0,?,?)",
                    (project_id, component_id, timestamp, timestamp),
                )
                inserted += cursor.rowcount
            connection.execute("UPDATE projects SET updated_at=? WHERE id=?", (timestamp, project_id))
        return inserted

    def list_components(self, project_id: int) -> list[dict]:
        return [dict(row) for row in self.db.connection.execute(
            "SELECT c.*, pc.quantity project_quantity, pc.synced_quantity, "
            "pc.reference_designator "
            "FROM project_components pc JOIN components c ON c.id=pc.component_id "
            "WHERE pc.project_id=? ORDER BY pc.created_at, c.id",
            (project_id,),
        )]

    def set_quantity(self, project_id: int, component_id: int, quantity: int) -> None:
        try:
            quantity = int(quantity)
        except (TypeError, ValueError) as error:
            raise ProjectError("项目用量必须是大于等于 1 的整数") from error
        if quantity < 1:
            raise ProjectError("项目用量必须是大于等于 1 的整数")
        cursor = self.db.connection.execute(
            "UPDATE project_components SET quantity=?,updated_at=? WHERE project_id=? AND component_id=?",
            (quantity, now_text(), project_id, component_id),
        )
        if not cursor.rowcount:
            raise ProjectError("项目元件不存在")
        self.db.connection.commit()

    def save_configuration(
        self,
        project_id: int,
        quantities: dict[int, int],
        reference_designators: dict[int, str] | None = None,
    ) -> None:
        try:
            normalized = {}
            for component_id, quantity in quantities.items():
                if isinstance(quantity, bool):
                    raise ValueError
                normalized_quantity = int(quantity)
                if isinstance(quantity, str):
                    if quantity.strip() != str(normalized_quantity):
                        raise ValueError
                elif quantity != normalized_quantity:
                    raise ValueError
                normalized[int(component_id)] = normalized_quantity
        except (AttributeError, TypeError, ValueError) as error:
            raise ProjectError("项目用量必须是大于等于 1 的整数") from error
        if any(quantity < 1 for quantity in normalized.values()):
            raise ProjectError("项目用量必须是大于等于 1 的整数")
        try:
            normalized_designators = None if reference_designators is None else {
                int(component_id): str(value or "").strip()
                for component_id, value in reference_designators.items()
            }
        except (AttributeError, TypeError, ValueError) as error:
            raise ProjectError("位号配置无效") from error

        with self.db.transaction() as connection:
            if not connection.execute(
                "SELECT 1 FROM projects WHERE id=? AND inactive=0", (project_id,)
            ).fetchone():
                raise ProjectError("项目不存在")
            existing = {
                int(row[0])
                for row in connection.execute(
                    "SELECT component_id FROM project_components WHERE project_id=?",
                    (project_id,),
                )
            }
            if existing != set(normalized):
                raise ProjectError("项目元件配置已变化，请刷新后重试")
            if normalized_designators is None:
                normalized_designators = {
                    int(row[0]): str(row[1] or "")
                    for row in connection.execute(
                        "SELECT component_id,reference_designator "
                        "FROM project_components WHERE project_id=?",
                        (project_id,),
                    )
                }
            elif existing != set(normalized_designators):
                raise ProjectError("项目元件配置已变化，请刷新后重试")
            timestamp = now_text()
            for component_id, quantity in normalized.items():
                connection.execute(
                    "UPDATE project_components SET quantity=?,reference_designator=?,updated_at=? "
                    "WHERE project_id=? AND component_id=?",
                    (
                        quantity,
                        normalized_designators[component_id],
                        timestamp,
                        project_id,
                        component_id,
                    ),
                )
            connection.execute(
                "UPDATE projects SET updated_at=? WHERE id=?", (timestamp, project_id)
            )

    def project_total(self, project_id: int) -> float:
        row = self.db.connection.execute(
            "SELECT COALESCE(SUM(pc.quantity*c.latest_unit_price),0) "
            "FROM project_components pc JOIN components c ON c.id=pc.component_id "
            "WHERE pc.project_id=?",
            (project_id,),
        ).fetchone()
        return float(row[0] or 0)

    def remove_components(self, project_id: int, component_ids: list[int]) -> ProjectSyncResult:
        unique_ids = list(dict.fromkeys(int(value) for value in component_ids))
        if not unique_ids:
            return ProjectSyncResult(None, 0, 0)
        timestamp = now_text()
        operation_id: int | None = None
        stock_delta_total = 0
        changed_lines = 0
        placeholders = ",".join("?" for _ in unique_ids)
        with self.db.transaction() as connection:
            project = connection.execute(
                "SELECT * FROM projects WHERE id=? AND inactive=0", (project_id,)
            ).fetchone()
            if project is None:
                raise ProjectError("项目不存在")
            rows = connection.execute(
                "SELECT pc.component_id,pc.synced_quantity,c.current_stock "
                "FROM project_components pc JOIN components c ON c.id=pc.component_id "
                f"WHERE pc.project_id=? AND pc.component_id IN ({placeholders})",
                (project_id, *unique_ids),
            ).fetchall()
            synced_rows = [row for row in rows if int(row["synced_quantity"]) > 0]
            if synced_rows:
                operation_id = int(connection.execute(
                    "INSERT INTO project_operations(project_id,occurred_at,changed_lines,stock_delta) VALUES(?,?,0,0)",
                    (project_id, timestamp),
                ).lastrowid)
                for row in synced_rows:
                    component_id = int(row["component_id"])
                    synced = int(row["synced_quantity"])
                    before = int(row["current_stock"])
                    after = before + synced
                    connection.execute(
                        "UPDATE components SET current_stock=?,updated_at=? WHERE id=?",
                        (after, timestamp, component_id),
                    )
                    movement_id = int(connection.execute(
                        "INSERT INTO stock_movements(component_id,movement_type,quantity_delta,stock_before,stock_after,occurred_at,notes) "
                        "VALUES(?,?,?,?,?,?,?)",
                        (component_id, "project_return", synced, before, after, timestamp,
                         f"项目删除元件退回：{project['name']}"),
                    ).lastrowid)
                    connection.execute(
                        "INSERT INTO project_operation_lines(operation_id,component_id,quantity_before,quantity_after,quantity_delta,stock_before,stock_after,movement_id) "
                        "VALUES(?,?,?,?,?,?,?,?)",
                        (operation_id, component_id, synced, 0, -synced, before, after, movement_id),
                    )
                    stock_delta_total += synced
                changed_lines = len(synced_rows)
                connection.execute(
                    "UPDATE project_operations SET changed_lines=?,stock_delta=? WHERE id=?",
                    (changed_lines, stock_delta_total, operation_id),
                )
            connection.execute(
                f"DELETE FROM project_components WHERE project_id=? AND component_id IN ({placeholders})",
                (project_id, *unique_ids),
            )
            connection.execute("UPDATE projects SET updated_at=? WHERE id=?", (timestamp, project_id))
        return ProjectSyncResult(operation_id, changed_lines, stock_delta_total)

    def sync(self, project_id: int) -> ProjectSyncResult:
        rows = self.list_components(project_id)
        changed = [row for row in rows if row["project_quantity"] != row["synced_quantity"]]
        if not changed:
            return ProjectSyncResult(None, 0, 0)
        project = self.db.connection.execute("SELECT * FROM projects WHERE id=?", (project_id,)).fetchone()
        if project is None:
            raise ProjectError("项目不存在")
        allow_negative = self.db.get_setting("allow_negative_stock") == "1"
        shortages = []
        for row in changed:
            used_delta = int(row["project_quantity"]) - int(row["synced_quantity"])
            if used_delta > int(row["current_stock"]) and not allow_negative:
                shortages.append(f"{row['product_code'] or row['model']}（缺 {used_delta-int(row['current_stock'])}）")
        if shortages:
            raise ProjectError("库存不足：" + "、".join(shortages))

        timestamp = now_text()
        stock_delta_total = 0
        with self.db.transaction() as connection:
            operation_id = connection.execute(
                "INSERT INTO project_operations(project_id,occurred_at,changed_lines,stock_delta) VALUES(?,?,0,0)",
                (project_id, timestamp),
            ).lastrowid
            for row in changed:
                old_quantity = int(row["synced_quantity"])
                new_quantity = int(row["project_quantity"])
                used_delta = new_quantity - old_quantity
                stock_delta = -used_delta
                before = int(row["current_stock"])
                after = before + stock_delta
                movement_type = "project_out" if used_delta > 0 else "project_return"
                notes = f"项目：{project['name']}"
                connection.execute(
                    "UPDATE components SET current_stock=?,updated_at=? WHERE id=?",
                    (after, timestamp, row["id"]),
                )
                movement_id = connection.execute(
                    "INSERT INTO stock_movements(component_id,movement_type,quantity_delta,stock_before,stock_after,occurred_at,notes) "
                    "VALUES(?,?,?,?,?,?,?)",
                    (row["id"], movement_type, stock_delta, before, after, timestamp, notes),
                ).lastrowid
                connection.execute(
                    "INSERT INTO project_operation_lines(operation_id,component_id,quantity_before,quantity_after,quantity_delta,stock_before,stock_after,movement_id) "
                    "VALUES(?,?,?,?,?,?,?,?)",
                    (operation_id, row["id"], old_quantity, new_quantity, used_delta, before, after, movement_id),
                )
                connection.execute(
                    "UPDATE project_components SET synced_quantity=?,updated_at=? WHERE project_id=? AND component_id=?",
                    (new_quantity, timestamp, project_id, row["id"]),
                )
                stock_delta_total += stock_delta
            connection.execute(
                "UPDATE project_operations SET changed_lines=?,stock_delta=? WHERE id=?",
                (len(changed), stock_delta_total, operation_id),
            )
            connection.execute("UPDATE projects SET updated_at=? WHERE id=?", (timestamp, project_id))
        return ProjectSyncResult(int(operation_id), len(changed), stock_delta_total)

    def operation_history(self, project_id: int, lines: bool = False) -> list[dict]:
        if lines:
            query = (
                "SELECT pol.*, po.occurred_at, sm.movement_type, c.product_code, c.product_name "
                "FROM project_operation_lines pol "
                "JOIN project_operations po ON po.id=pol.operation_id "
                "JOIN stock_movements sm ON sm.id=pol.movement_id "
                "JOIN components c ON c.id=pol.component_id "
                "WHERE po.project_id=? ORDER BY pol.id DESC"
            )
        else:
            query = "SELECT * FROM project_operations WHERE project_id=? ORDER BY id DESC"
        return [dict(row) for row in self.db.connection.execute(query, (project_id,))]
