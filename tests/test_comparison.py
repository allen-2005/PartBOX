from partbox.comparison import ComparisonService
from partbox.database import Database


def seed_components(db: Database) -> list[int]:
    now = "2026-08-27 10:00:00"
    ids = []
    for code in ("C1", "C2", "C3"):
        ids.append(int(db.connection.execute(
            "INSERT INTO components(product_code,product_name,current_stock,created_at,updated_at) "
            "VALUES(?,?,5,?,?) RETURNING id",
            (code, f"元件{code}", now, now),
        ).fetchone()[0]))
    db.connection.commit()
    return ids


def test_comparison_membership_is_deduplicated_ordered_and_persistent(tmp_path):
    path = tmp_path / "comparison.db"
    db = Database(path); db.initialize()
    first, second, third = seed_components(db)
    service = ComparisonService(db)

    assert service.add_components([second, first, second]) == 2
    assert [row["id"] for row in service.list_components()] == [second, first]
    db.close()

    reopened = Database(path); reopened.initialize()
    persisted = ComparisonService(reopened)
    assert [row["id"] for row in persisted.list_components()] == [second, first]
    assert persisted.add_components([third]) == 1
    assert persisted.remove_components([second, 999]) == 1
    assert [row["id"] for row in persisted.list_components()] == [first, third]
    persisted.clear()
    assert persisted.list_components() == []


def test_comparison_price_history_is_chronological(tmp_path):
    db = Database(tmp_path / "history.db"); db.initialize()
    component_id = seed_components(db)[0]
    batch_id = int(db.connection.execute(
        "INSERT INTO import_batches(filename,file_sha256,imported_at) VALUES('a.xlsx','sha','2026-08-27') RETURNING id"
    ).fetchone()[0])
    for fingerprint, order_time, price, quantity, order_number in (
        ("later", "2026-08-20 09:00:00", 0.30, 20, "O2"),
        ("earlier", "2026-08-10 09:00:00", 0.20, 10, "O1"),
    ):
        db.connection.execute(
            "INSERT INTO purchase_lines(component_id,batch_id,line_fingerprint,order_time,product_code,quantity,unit_price,order_number) "
            "VALUES(?,?,?,?,?,?,?,?)",
            (component_id, batch_id, fingerprint, order_time, "C1", quantity, price, order_number),
        )
    db.connection.commit()

    history = ComparisonService(db).price_history([component_id])

    assert [point["unit_price"] for point in history[component_id]] == [0.20, 0.30]
    assert history[component_id][0]["quantity"] == 10
    assert history[component_id][1]["order_number"] == "O2"

