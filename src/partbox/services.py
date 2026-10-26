from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable, Iterable

import pandas as pd

from partbox.database import Database
from partbox.importer import FeeLine, OrderLine, ParsedStatement, parse_statement


def now_text() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def normalize(value: str) -> str:
    return " ".join((value or "").strip().upper().split())


def match_key(line: OrderLine) -> str:
    if line.product_code:
        return normalize(line.product_code)
    return f"{normalize(line.model)}|{normalize(line.package)}"


def purchase_identity_key(
    order_number: str,
    product_code: str,
    quantity: int,
    order_time: str,
    model: str = "",
    package: str = "",
):
    """Identify a purchased SKU independently of export format and price rendering."""
    order = normalize(order_number)
    part = normalize(product_code)
    if not part:
        normalized_model = normalize(model)
        normalized_package = normalize(package)
        if normalized_model and normalized_package:
            part = f"{normalized_model}|{normalized_package}"
    if not order or not part:
        return None
    minute = (order_time or "").strip().replace("/", "-")[:16]
    return order, part, int(quantity), minute


class ImportErrorBase(RuntimeError):
    pass


class DuplicateFileError(ImportErrorBase):
    pass


class StockError(RuntimeError):
    pass


@dataclass
class ImportPreview:
    statements: list[ParsedStatement]
    new_lines: list[OrderLine] = field(default_factory=list)
    existing_lines: list[OrderLine] = field(default_factory=list)
    duplicate_lines: list[OrderLine] = field(default_factory=list)
    duplicate_files: list[Path] = field(default_factory=list)
    fees: list[FeeLine] = field(default_factory=list)
    issues: list = field(default_factory=list)
    force: bool = False


class ImportService:
    def __init__(self, db: Database, backup_dir: Path | None = None):
        self.db = db
        self.backup_dir = Path(backup_dir) if backup_dir else None

    def preview(
        self,
        paths: Iterable[Path],
        force: bool = False,
        parser: Callable[[Path], ParsedStatement] = parse_statement,
    ) -> ImportPreview:
        return self.preview_parsed([parser(Path(path)) for path in paths], force)

    def preview_parsed(self, statements: list[ParsedStatement], force: bool = False) -> ImportPreview:
        preview = ImportPreview(statements=statements, force=force)
        known_fingerprints = {
            row[0] for row in self.db.connection.execute("SELECT line_fingerprint FROM purchase_lines")
        }
        purchase_identity_keys = {
            purchase_identity_key(row[0], row[1], row[2], row[3], row[4], row[5])
            for row in self.db.connection.execute(
                "SELECT order_number,product_code,quantity,order_time,model,package FROM purchase_lines"
            )
        }
        purchase_identity_keys.discard(None)
        seen_purchase_identities = set(purchase_identity_keys)
        seen = set(known_fingerprints)
        known_hashes = {
            row[0] for row in self.db.connection.execute("SELECT file_sha256 FROM import_batches WHERE status='success'")
        }
        seen_hashes = set(known_hashes)
        for statement in statements:
            if statement.file_sha256 in seen_hashes:
                if not force:
                    raise DuplicateFileError(f"文件已导入：{statement.path.name}")
                preview.duplicate_files.append(statement.path)
            seen_hashes.add(statement.file_sha256)
            preview.fees.extend(statement.fee_lines)
            preview.issues.extend(statement.issues)
            for line in statement.order_lines:
                purchase_identity = purchase_identity_key(
                    line.order_number, line.product_code, line.quantity, line.order_time,
                    line.model, line.package,
                )
                same_purchase = (
                    purchase_identity is not None and purchase_identity in seen_purchase_identities
                )
                if same_purchase or (line.line_fingerprint in seen and not force):
                    preview.duplicate_lines.append(line)
                    continue
                seen.add(line.line_fingerprint)
                if purchase_identity is not None:
                    seen_purchase_identities.add(purchase_identity)
                if self._find_component(line):
                    preview.existing_lines.append(line)
                else:
                    preview.new_lines.append(line)
        return preview

    def _find_component(self, line: OrderLine):
        if line.product_code:
            return self.db.connection.execute(
                "SELECT * FROM components WHERE UPPER(TRIM(product_code)) = ?",
                (normalize(line.product_code),),
            ).fetchone()
        return self.db.connection.execute(
            "SELECT * FROM components WHERE (product_code IS NULL OR product_code='') "
            "AND UPPER(TRIM(model))=? AND UPPER(TRIM(package))=?",
            (normalize(line.model), normalize(line.package)),
        ).fetchone()

    @staticmethod
    def _refresh_component_metadata(connection, component_id: int, line: OrderLine, timestamp: str) -> None:
        connection.execute(
            "UPDATE components SET product_code=?, brand=?, product_type=?, product_name=?, "
            "model=?, package=?, unit=?, updated_at=? WHERE id=?",
            (line.product_code or None, line.brand, line.product_type, line.product_name,
             line.model, line.package, line.unit, timestamp, component_id),
        )

    def commit(self, preview: ImportPreview, stock_decisions: dict[str, bool]) -> None:
        if self.backup_dir and self.db.path.exists() and self.db.path.stat().st_size:
            self.backup_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(self.db.path, self.backup_dir / f"partbox-{datetime.now():%Y%m%d-%H%M%S}.db")

        by_path = {statement.path: statement for statement in preview.statements}
        accepted = preview.new_lines + preview.existing_lines
        preview_new_line_ids = {id(line) for line in preview.new_lines}
        with self.db.transaction() as connection:
            batches = {}
            for statement in preview.statements:
                statement_line_ids = {id(line) for line in statement.order_lines}
                cursor = connection.execute(
                    "INSERT INTO import_batches(filename,file_sha256,imported_at,forced,product_count,fee_count,duplicate_count,issue_count) VALUES(?,?,?,?,?,?,?,?)",
                    (statement.path.name, statement.file_sha256, now_text(), int(preview.force),
                     sum(1 for line in accepted if id(line) in statement_line_ids),
                     len(statement.fee_lines),
                     sum(1 for line in preview.duplicate_lines if id(line) in statement_line_ids),
                     len(statement.issues)),
                )
                batches[statement.path] = cursor.lastrowid

            statement_for_line = {}
            for statement in preview.statements:
                for original in statement.order_lines:
                    statement_for_line[id(original)] = statement

            # A material statement can repeat a line previously imported by the removed
            # order-detail format. Repair its descriptive fields without recounting it.
            for line in preview.duplicate_lines:
                component = self._find_component(line)
                if component is not None:
                    self._refresh_component_metadata(connection, component["id"], line, now_text())

            for line in accepted:
                component = self._find_component(line)
                is_new = component is None
                timestamp = now_text()
                if is_new:
                    cursor = connection.execute(
                        "INSERT INTO components(product_code,brand,product_type,product_name,model,package,unit,current_stock,total_purchased,total_spent,latest_unit_price,latest_order_time,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                        (line.product_code or None, line.brand, line.product_type, line.product_name,
                         line.model, line.package, line.unit, line.quantity, line.quantity,
                         line.subtotal, line.unit_price, line.order_time, timestamp, timestamp),
                    )
                    component_id = cursor.lastrowid
                    add_stock = True
                    stock_before = 0
                else:
                    component_id = component["id"]
                    add_stock = id(line) in preview_new_line_ids or bool(stock_decisions.get(line.line_fingerprint, False))
                    stock_before = int(component["current_stock"])
                    stock_after = stock_before + (line.quantity if add_stock else 0)
                    connection.execute(
                        "UPDATE components SET product_code=?, brand=?, product_type=?, product_name=?, "
                        "model=?, package=?, unit=?, current_stock=?, total_purchased=total_purchased+?, "
                        "total_spent=total_spent+?, latest_unit_price=?, latest_order_time=?, updated_at=? WHERE id=?",
                        (line.product_code or None, line.brand, line.product_type, line.product_name,
                         line.model, line.package, line.unit, stock_after, line.quantity, line.subtotal,
                         line.unit_price, line.order_time, timestamp, component_id),
                    )

                statement = statement_for_line[id(line)]
                batch_id = batches[statement.path]
                purchase_id = self._insert_purchase(connection, component_id, batch_id, line)
                if add_stock:
                    connection.execute(
                        "INSERT INTO stock_movements(component_id,movement_type,quantity_delta,stock_before,stock_after,occurred_at,notes,purchase_line_id) VALUES(?,?,?,?,?,?,?,?)",
                        (component_id, "order_in", line.quantity, stock_before, stock_before + line.quantity, timestamp, f"订单 {line.order_number}", purchase_id),
                    )
            for statement in preview.statements:
                batch_id = batches[statement.path]
                for fee in statement.fee_lines:
                    connection.execute(
                        "INSERT INTO fee_lines(batch_id,fee_name,amount,source_sheet,source_row) VALUES(?,?,?,?,?)",
                        (batch_id, fee.name, fee.amount, fee.source_sheet, fee.source_row),
                    )

    @staticmethod
    def _insert_purchase(connection, component_id: int, batch_id: int, line: OrderLine) -> int:
        values = [component_id, batch_id, line.line_fingerprint, line.source_sheet, line.source_row,
                  line.order_number, line.order_status, line.order_time, line.recipient,
                  line.customer_part_number, line.product_code, line.brand, line.product_type,
                  line.product_name, line.model, line.package, line.quantity, line.unit,
                  line.unit_price, line.subtotal, line.shipping_date, line.courier,
                  line.tracking_number, line.receipt_date, line.invoice_number,
                  line.invoice_time, line.customer_representative, line.original_order,
                  line.bom_flag, line.contract_number]
        placeholders = ",".join("?" for _ in values)
        return connection.execute(
            f"INSERT INTO purchase_lines(component_id,batch_id,line_fingerprint,source_sheet,source_row,order_number,order_status,order_time,recipient,customer_part_number,product_code,brand,product_type,product_name,model,package,quantity,unit,unit_price,subtotal,shipping_date,courier,tracking_number,receipt_date,invoice_number,invoice_time,customer_representative,original_order,bom_flag,contract_number) VALUES({placeholders})",
            values,
        ).lastrowid


class StockService:
    def __init__(self, db: Database):
        self.db = db

    def get_stock(self, component_id: int) -> int:
        row = self.db.connection.execute("SELECT current_stock FROM components WHERE id=?", (component_id,)).fetchone()
        if row is None:
            raise StockError("元件不存在")
        return int(row[0])

    def adjust(self, component_id: int, delta: int, movement_type: str, notes: str = "") -> int:
        if delta == 0:
            raise StockError("变动数量不能为 0")
        before = self.get_stock(component_id)
        after = before + int(delta)
        allow_negative = self.db.get_setting("allow_negative_stock") == "1"
        if after < 0 and not allow_negative:
            raise StockError("库存不足，不能出库")
        with self.db.transaction() as connection:
            connection.execute("UPDATE components SET current_stock=?, updated_at=? WHERE id=?", (after, now_text(), component_id))
            return connection.execute(
                "INSERT INTO stock_movements(component_id,movement_type,quantity_delta,stock_before,stock_after,occurred_at,notes) VALUES(?,?,?,?,?,?,?)",
                (component_id, movement_type, delta, before, after, now_text(), notes),
            ).lastrowid

    def calibrate(self, component_id: int, new_stock: int, notes: str = "") -> int | None:
        before = self.get_stock(component_id)
        if new_stock == before:
            return None
        return self.adjust(component_id, new_stock - before, "calibration", notes)

    def reverse(self, movement_id: int, notes: str = "") -> int:
        movement = self.db.connection.execute("SELECT * FROM stock_movements WHERE id=?", (movement_id,)).fetchone()
        if movement is None:
            raise StockError("库存流水不存在")
        if self.db.connection.execute("SELECT 1 FROM stock_movements WHERE reverses_movement_id=?", (movement_id,)).fetchone():
            raise StockError("该流水已经撤销")
        component_id = int(movement["component_id"])
        before = self.get_stock(component_id)
        delta = -int(movement["quantity_delta"])
        after = before + delta
        if after < 0 and self.db.get_setting("allow_negative_stock") != "1":
            raise StockError("撤销后库存会小于 0，不能撤销")
        with self.db.transaction() as connection:
            connection.execute("UPDATE components SET current_stock=?, updated_at=? WHERE id=?", (after, now_text(), component_id))
            return connection.execute(
                "INSERT INTO stock_movements(component_id,movement_type,quantity_delta,stock_before,stock_after,occurred_at,notes,reverses_movement_id) VALUES(?,?,?,?,?,?,?,?)",
                (component_id, "reversal", delta, before, after, now_text(), notes, movement_id),
            ).lastrowid


class InventoryService:
    def __init__(self, db: Database):
        self.db = db

    def list_components(self, search: str = "", category: str = "", stock_filter: str = "") -> list[dict]:
        rows = [dict(row) for row in self.db.connection.execute("SELECT * FROM components WHERE inactive=0 ORDER BY updated_at DESC, id DESC")]
        terms = [normalize(term) for term in search.split() if term.strip()]
        if terms:
            fields = ("product_code", "brand", "product_type", "product_name", "model", "package", "location", "notes")
            rows = [row for row in rows if all(term in " ".join(normalize(str(row.get(field, ""))) for field in fields) for term in terms)]
        if category:
            rows = [row for row in rows if category in row["product_type"]]
        threshold = int(self.db.get_setting("low_stock_threshold") or 5)
        if stock_filter == "low":
            rows = [row for row in rows if 0 < row["current_stock"] <= threshold]
        elif stock_filter == "zero":
            rows = [row for row in rows if row["current_stock"] == 0]
        return rows

    def stats(self) -> dict:
        row = self.db.connection.execute(
            "SELECT COUNT(*) kinds, COALESCE(SUM(current_stock),0) stock, COALESCE(SUM(total_spent),0) spent FROM components WHERE inactive=0"
        ).fetchone()
        orders = self.db.connection.execute("SELECT COUNT(DISTINCT order_number) FROM purchase_lines WHERE order_number<>''").fetchone()[0]
        return {"kinds": row["kinds"], "stock": row["stock"], "spent": row["spent"], "orders": orders}

    def update_component(self, component_id: int, values: dict) -> None:
        allowed = {"brand", "product_type", "product_name", "model", "package", "unit", "location", "notes"}
        updates = {key: value for key, value in values.items() if key in allowed}
        if not updates:
            return
        updates["updated_at"] = now_text()
        assignments = ",".join(f"{key}=?" for key in updates)
        self.db.connection.execute(f"UPDATE components SET {assignments} WHERE id=?", [*updates.values(), component_id])
        self.db.connection.commit()


class DataService:
    def __init__(self, db: Database):
        self.db = db

    def stock_history(self, limit: int = 1000) -> list[dict]:
        return [dict(row) for row in self.db.connection.execute(
            "SELECT m.*, c.product_code, c.product_name, c.model, c.unit "
            "FROM stock_movements m JOIN components c ON c.id=m.component_id "
            "ORDER BY m.id DESC LIMIT ?", (limit,)
        )]

    def import_batches(self) -> list[dict]:
        return [dict(row) for row in self.db.connection.execute(
            "SELECT * FROM import_batches ORDER BY id DESC"
        )]

    def purchase_lines(self, limit: int = 5000) -> list[dict]:
        return [dict(row) for row in self.db.connection.execute(
            "SELECT * FROM purchase_lines ORDER BY id DESC LIMIT ?", (limit,)
        )]

    def backup(self, target_dir: Path) -> Path:
        target_dir = Path(target_dir); target_dir.mkdir(parents=True, exist_ok=True)
        target = target_dir / f"partbox-backup-{datetime.now():%Y%m%d-%H%M%S-%f}.db"
        destination = Database(target)
        try:
            self.db.connection.backup(destination.connection)
        finally:
            destination.close()
        return target

    def restore(self, source: Path) -> None:
        import sqlite3
        source = Path(source)
        try:
            source_connection = sqlite3.connect(f"file:{source.as_posix()}?mode=ro", uri=True)
        except (sqlite3.DatabaseError, sqlite3.OperationalError) as error:
            raise ValueError("所选文件不是有效的 PartBOX 备份") from error
        try:
            integrity = source_connection.execute("PRAGMA quick_check").fetchone()[0]
            tables = {row[0] for row in source_connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            required = {"components", "purchase_lines", "stock_movements", "import_batches", "settings"}
            if integrity != "ok" or not required <= tables:
                raise ValueError("所选文件不是有效的 PartBOX 备份")
            source_connection.backup(self.db.connection)
        except (sqlite3.DatabaseError, sqlite3.OperationalError) as error:
            raise ValueError("所选文件不是有效的 PartBOX 备份") from error
        finally:
            source_connection.close()
        self.db.connection.execute("PRAGMA foreign_keys = ON")
        self.db.initialize()

    def export_inventory(self, target: Path) -> Path:
        target = Path(target); target.parent.mkdir(parents=True, exist_ok=True)
        rows = [dict(row) for row in self.db.connection.execute(
            "SELECT product_code AS 商品编号, product_type AS 商品类型, product_name AS 商品名称, "
            "model AS 商品型号, package AS 封装格式, brand AS 品牌, current_stock AS 当前库存, "
            "total_purchased AS 累计购买, unit AS 商品单位, latest_unit_price AS 最近单价含税, "
            "total_spent AS 累计采购金额, latest_order_time AS 最近下单时间, location AS 存放位置, "
            "notes AS 备注, updated_at AS 最后修改时间 FROM components WHERE inactive=0 ORDER BY id"
        )]
        columns = ["商品编号", "商品类型", "商品名称", "商品型号", "封装格式", "品牌", "当前库存", "累计购买", "商品单位", "最近单价含税", "累计采购金额", "最近下单时间", "存放位置", "备注", "最后修改时间"]
        pd.DataFrame(rows, columns=columns).to_excel(target, index=False, sheet_name="元件库存")
        return target

    def reset_database(self) -> None:
        with self.db.transaction() as connection:
            for table in (
                "project_operation_lines", "project_operations", "project_components", "projects",
                "stock_movements", "purchase_lines", "fee_lines", "import_batches", "components",
            ):
                connection.execute(f"DELETE FROM {table}")
