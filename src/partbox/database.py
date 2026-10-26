from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


SCHEMA = """
CREATE TABLE IF NOT EXISTS components (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_code TEXT,
    brand TEXT NOT NULL DEFAULT '',
    product_type TEXT NOT NULL DEFAULT '',
    product_name TEXT NOT NULL DEFAULT '',
    model TEXT NOT NULL DEFAULT '',
    package TEXT NOT NULL DEFAULT '',
    unit TEXT NOT NULL DEFAULT '',
    current_stock INTEGER NOT NULL DEFAULT 0,
    total_purchased INTEGER NOT NULL DEFAULT 0,
    total_spent REAL NOT NULL DEFAULT 0,
    latest_unit_price REAL NOT NULL DEFAULT 0,
    latest_order_time TEXT,
    location TEXT NOT NULL DEFAULT '',
    notes TEXT NOT NULL DEFAULT '',
    inactive INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS ux_components_product_code
ON components(product_code) WHERE product_code IS NOT NULL AND product_code <> '';

CREATE TABLE IF NOT EXISTS import_batches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename TEXT NOT NULL,
    file_sha256 TEXT NOT NULL,
    imported_at TEXT NOT NULL,
    forced INTEGER NOT NULL DEFAULT 0,
    product_count INTEGER NOT NULL DEFAULT 0,
    fee_count INTEGER NOT NULL DEFAULT 0,
    duplicate_count INTEGER NOT NULL DEFAULT 0,
    issue_count INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'success',
    summary TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS purchase_lines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    component_id INTEGER NOT NULL REFERENCES components(id),
    batch_id INTEGER NOT NULL REFERENCES import_batches(id),
    line_fingerprint TEXT NOT NULL,
    source_sheet TEXT NOT NULL DEFAULT '',
    source_row INTEGER NOT NULL DEFAULT 0,
    order_number TEXT NOT NULL DEFAULT '',
    order_status TEXT NOT NULL DEFAULT '',
    order_time TEXT,
    recipient TEXT NOT NULL DEFAULT '',
    customer_part_number TEXT NOT NULL DEFAULT '',
    product_code TEXT NOT NULL DEFAULT '',
    brand TEXT NOT NULL DEFAULT '',
    product_type TEXT NOT NULL DEFAULT '',
    product_name TEXT NOT NULL DEFAULT '',
    model TEXT NOT NULL DEFAULT '',
    package TEXT NOT NULL DEFAULT '',
    quantity INTEGER NOT NULL,
    unit TEXT NOT NULL DEFAULT '',
    unit_price REAL NOT NULL DEFAULT 0,
    subtotal REAL NOT NULL DEFAULT 0,
    shipping_date TEXT,
    courier TEXT NOT NULL DEFAULT '',
    tracking_number TEXT NOT NULL DEFAULT '',
    receipt_date TEXT,
    invoice_number TEXT NOT NULL DEFAULT '',
    invoice_time TEXT,
    customer_representative TEXT NOT NULL DEFAULT '',
    original_order TEXT NOT NULL DEFAULT '',
    bom_flag TEXT NOT NULL DEFAULT '',
    contract_number TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS ix_purchase_fingerprint ON purchase_lines(line_fingerprint);

CREATE TABLE IF NOT EXISTS stock_movements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    component_id INTEGER NOT NULL REFERENCES components(id),
    movement_type TEXT NOT NULL,
    quantity_delta INTEGER NOT NULL,
    stock_before INTEGER NOT NULL,
    stock_after INTEGER NOT NULL,
    occurred_at TEXT NOT NULL,
    notes TEXT NOT NULL DEFAULT '',
    purchase_line_id INTEGER REFERENCES purchase_lines(id),
    reverses_movement_id INTEGER REFERENCES stock_movements(id)
);

CREATE TABLE IF NOT EXISTS fee_lines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    batch_id INTEGER NOT NULL REFERENCES import_batches(id),
    fee_name TEXT NOT NULL,
    amount REAL NOT NULL DEFAULT 0,
    source_sheet TEXT NOT NULL DEFAULT '',
    source_row INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS comparison_components (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    component_id INTEGER NOT NULL UNIQUE REFERENCES components(id) ON DELETE CASCADE,
    added_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL COLLATE NOCASE UNIQUE,
    build_quantity INTEGER NOT NULL DEFAULT 1 CHECK(build_quantity >= 1),
    source_bom_path TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
    , inactive INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS project_components (
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    component_id INTEGER NOT NULL REFERENCES components(id),
    quantity INTEGER NOT NULL DEFAULT 1 CHECK(quantity >= 1),
    synced_quantity INTEGER NOT NULL DEFAULT 0 CHECK(synced_quantity >= 0),
    reference_designator TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY(project_id, component_id)
);

CREATE TABLE IF NOT EXISTS project_bom_lines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    source_row INTEGER NOT NULL,
    source_values_json TEXT NOT NULL DEFAULT '{}',
    per_build_quantity INTEGER NOT NULL CHECK(per_build_quantity >= 1),
    required_quantity INTEGER NOT NULL CHECK(required_quantity >= 1),
    designator TEXT NOT NULL DEFAULT '',
    product_code TEXT NOT NULL DEFAULT '',
    product_type TEXT NOT NULL DEFAULT '',
    description TEXT NOT NULL DEFAULT '',
    model TEXT NOT NULL DEFAULT '',
    package TEXT NOT NULL DEFAULT '',
    brand TEXT NOT NULL DEFAULT '',
    matched_component_id INTEGER REFERENCES components(id),
    match_status TEXT NOT NULL,
    allocated_quantity INTEGER NOT NULL DEFAULT 0 CHECK(allocated_quantity >= 0),
    purchase_quantity INTEGER NOT NULL DEFAULT 0 CHECK(purchase_quantity >= 0)
);

CREATE TABLE IF NOT EXISTS project_operations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    occurred_at TEXT NOT NULL,
    changed_lines INTEGER NOT NULL DEFAULT 0,
    stock_delta INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS project_operation_lines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    operation_id INTEGER NOT NULL REFERENCES project_operations(id) ON DELETE CASCADE,
    component_id INTEGER NOT NULL REFERENCES components(id),
    quantity_before INTEGER NOT NULL,
    quantity_after INTEGER NOT NULL,
    quantity_delta INTEGER NOT NULL,
    stock_before INTEGER NOT NULL,
    stock_after INTEGER NOT NULL,
    movement_id INTEGER NOT NULL REFERENCES stock_movements(id)
);
"""


class Database:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.path)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON")

    def initialize(self) -> None:
        self.connection.executescript(SCHEMA)
        project_columns = {row[1] for row in self.connection.execute("PRAGMA table_info(projects)")}
        if "inactive" not in project_columns:
            self.connection.execute("ALTER TABLE projects ADD COLUMN inactive INTEGER NOT NULL DEFAULT 0")
        if "build_quantity" not in project_columns:
            self.connection.execute("ALTER TABLE projects ADD COLUMN build_quantity INTEGER NOT NULL DEFAULT 1")
        if "source_bom_path" not in project_columns:
            self.connection.execute("ALTER TABLE projects ADD COLUMN source_bom_path TEXT NOT NULL DEFAULT ''")
        project_component_columns = {
            row[1] for row in self.connection.execute("PRAGMA table_info(project_components)")
        }
        if "reference_designator" not in project_component_columns:
            self.connection.execute(
                "ALTER TABLE project_components "
                "ADD COLUMN reference_designator TEXT NOT NULL DEFAULT ''"
            )
        # Versions before 1.2 created project rows with quantity 0. Project
        # quantities now represent a real BOM line and therefore start at 1.
        self.connection.execute("UPDATE project_components SET quantity=1 WHERE quantity<1")
        self.connection.executemany(
            "INSERT OR IGNORE INTO settings(key, value) VALUES(?, ?)",
            [("allow_negative_stock", "0"), ("low_stock_threshold", "5")],
        )
        self.connection.commit()

    def get_setting(self, key: str) -> str | None:
        row = self.connection.execute(
            "SELECT value FROM settings WHERE key = ?", (key,)
        ).fetchone()
        return None if row is None else str(row[0])

    def set_setting(self, key: str, value: str) -> None:
        self.connection.execute(
            "INSERT INTO settings(key, value) VALUES(?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, value),
        )
        self.connection.commit()

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        try:
            self.connection.execute("BEGIN")
            yield self.connection
        except Exception:
            self.connection.rollback()
            raise
        else:
            self.connection.commit()

    def close(self) -> None:
        self.connection.close()
