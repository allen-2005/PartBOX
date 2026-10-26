from __future__ import annotations

from datetime import datetime

from partbox.database import Database


def now_text() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")


class ComparisonService:
    def __init__(self, db: Database):
        self.db = db

    def add_components(self, component_ids: list[int]) -> int:
        inserted = 0
        unique_ids = list(dict.fromkeys(int(value) for value in component_ids))
        with self.db.transaction() as connection:
            for component_id in unique_ids:
                cursor = connection.execute(
                    "INSERT OR IGNORE INTO comparison_components(component_id,added_at) "
                    "SELECT id,? FROM components WHERE id=? AND inactive=0",
                    (now_text(), component_id),
                )
                inserted += cursor.rowcount
        return inserted

    def remove_components(self, component_ids: list[int]) -> int:
        unique_ids = list(dict.fromkeys(int(value) for value in component_ids))
        if not unique_ids:
            return 0
        placeholders = ",".join("?" for _ in unique_ids)
        cursor = self.db.connection.execute(
            f"DELETE FROM comparison_components WHERE component_id IN ({placeholders})",
            unique_ids,
        )
        self.db.connection.commit()
        return int(cursor.rowcount)

    def clear(self) -> None:
        self.db.connection.execute("DELETE FROM comparison_components")
        self.db.connection.commit()

    def list_components(self) -> list[dict]:
        return [dict(row) for row in self.db.connection.execute(
            "SELECT c.* FROM comparison_components cc "
            "JOIN components c ON c.id=cc.component_id "
            "WHERE c.inactive=0 ORDER BY cc.id"
        )]

    def price_history(self, component_ids: list[int]) -> dict[int, list[dict]]:
        unique_ids = list(dict.fromkeys(int(value) for value in component_ids))
        result: dict[int, list[dict]] = {component_id: [] for component_id in unique_ids}
        if not unique_ids:
            return result
        placeholders = ",".join("?" for _ in unique_ids)
        rows = self.db.connection.execute(
            "SELECT component_id,order_time,unit_price,quantity,order_number "
            f"FROM purchase_lines WHERE component_id IN ({placeholders}) "
            "AND order_time IS NOT NULL ORDER BY order_time,id",
            unique_ids,
        )
        for row in rows:
            result[int(row["component_id"])].append(dict(row))
        return result

