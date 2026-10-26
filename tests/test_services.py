from dataclasses import replace

import pytest

from partbox.database import Database
from partbox.importer import OrderLine, ParsedStatement
from partbox.services import DuplicateFileError, ImportService, StockError, StockService


def line(code="C1", quantity=10, fingerprint="fp1", model="M1", package="0603"):
    return OrderLine(
        source_sheet="物料", source_row=3, order_number="SO1", order_status="已发货",
        order_time="2026-01-01 10:00:00", recipient="A", customer_part_number="",
        product_code=code, brand="品牌", product_type="贴片电阻", product_name="10kΩ ±1%",
        model=model, package=package, quantity=quantity, unit="个", unit_price=0.01,
        subtotal=quantity * 0.01, line_fingerprint=fingerprint,
    )


def parsed(tmp_path, name="a.xls", sha="sha1", lines=None):
    return ParsedStatement(tmp_path / name, sha, "物料", 2, [], order_lines=lines or [line()])


@pytest.fixture
def services(tmp_path):
    db = Database(tmp_path / "db.sqlite")
    db.initialize()
    return db, ImportService(db), StockService(db)


def test_new_component_opens_with_purchased_stock(services, tmp_path):
    db, importer, _ = services
    preview = importer.preview_parsed([parsed(tmp_path)])
    importer.commit(preview, {})
    component = db.connection.execute("SELECT * FROM components").fetchone()
    assert component["current_stock"] == 10
    assert component["total_purchased"] == 10


def test_existing_component_requires_stock_decision_and_dedupes_line(services, tmp_path):
    db, importer, _ = services
    importer.commit(importer.preview_parsed([parsed(tmp_path)]), {})
    second = parsed(tmp_path, "b.xls", "sha2", [replace(line(), order_number="SO2", quantity=5, subtotal=.05, line_fingerprint="fp2")])
    preview = importer.preview_parsed([second])
    importer.commit(preview, {"C1": False})
    component = db.connection.execute("SELECT * FROM components").fetchone()
    assert component["current_stock"] == 10
    assert component["total_purchased"] == 15

    duplicate = parsed(tmp_path, "c.xls", "sha3", [replace(line(), line_fingerprint="fp2")])
    duplicate_preview = importer.preview_parsed([duplicate])
    assert len(duplicate_preview.duplicate_lines) == 1


def test_existing_component_metadata_is_repaired_from_material_detail(services, tmp_path):
    db, importer, _ = services
    now = "2026-01-01 00:00:00"
    db.connection.execute(
        "INSERT INTO components(product_code,brand,product_type,product_name,model,package,unit,current_stock,created_at,updated_at) "
        "VALUES('C1','旧品牌','电阻','旧名称','旧型号','旧封装','个',7,?,?)",
        (now, now),
    )
    db.connection.commit()
    exact = replace(
        line(quantity=3, fingerprint="repair"),
        brand=" FOJAN(富捷) ",
        product_type="贴片电阻",
        product_name=" 100Ω ±1% 125mW 厚膜电阻 编带 ",
        model=" FRC0805F1000TS ",
        package=" 0805 ",
        unit=" 个 ",
    )

    preview = importer.preview_parsed([parsed(tmp_path, lines=[exact])])
    importer.commit(preview, {"repair": False})

    component = db.connection.execute("SELECT * FROM components WHERE product_code='C1'").fetchone()
    assert component["brand"] == " FOJAN(富捷) "
    assert component["product_type"] == "贴片电阻"
    assert component["product_name"] == " 100Ω ±1% 125mW 厚膜电阻 编带 "
    assert component["model"] == " FRC0805F1000TS "
    assert component["package"] == " 0805 "
    assert component["unit"] == " 个 "
    assert component["current_stock"] == 7


def test_duplicate_purchase_line_repairs_metadata_without_recounting(services, tmp_path):
    db, importer, _ = services
    coarse = replace(
        line(quantity=3, fingerprint="legacy-detail"), subtotal=6.52, product_type="电阻"
    )
    importer.commit(importer.preview_parsed([
        parsed(tmp_path, name="用户重命名的旧文件.xls", lines=[coarse])
    ]), {})
    exact = replace(
        coarse,
        line_fingerprint="material-statement",
        subtotal=3.08,
        brand="FOJAN(富捷)",
        product_type="贴片电阻",
        product_name="100Ω ±1% 125mW 厚膜电阻 编带",
        model="FRC0805F1000TS",
        package="0805",
    )

    preview = importer.preview_parsed([parsed(
        tmp_path, name="立创商城物料明细对账单.xls", sha="statement", lines=[exact]
    )])
    assert preview.duplicate_lines == [exact]
    importer.commit(preview, {})

    component = db.connection.execute("SELECT * FROM components WHERE product_code='C1'").fetchone()
    assert component["product_type"] == "贴片电阻"
    assert component["product_name"] == "100Ω ±1% 125mW 厚膜电阻 编带"
    assert component["total_purchased"] == 3
    assert component["current_stock"] == 3


def test_code_less_purchase_identity_uses_model_and_package(services, tmp_path):
    db, importer, _ = services
    first = replace(
        line(code="", model="FRC0805F1000TS", package="0805", fingerprint="old"),
        subtotal=6.52,
    )
    importer.commit(importer.preview_parsed([parsed(tmp_path, lines=[first])]), {})
    same_purchase = replace(
        first,
        line_fingerprint="new-export",
        subtotal=3.08,
        product_type="贴片电阻",
    )

    preview = importer.preview_parsed([
        parsed(tmp_path, name="material.xls", sha="new-export", lines=[same_purchase])
    ], force=True)
    assert preview.duplicate_lines == [same_purchase]
    importer.commit(preview, {})

    component = db.connection.execute("SELECT * FROM components").fetchone()
    assert component["product_type"] == "贴片电阻"
    assert component["total_purchased"] == first.quantity
    assert component["current_stock"] == first.quantity


def test_duplicate_file_is_blocked_unless_forced(services, tmp_path):
    _, importer, _ = services
    statement = parsed(tmp_path)
    importer.commit(importer.preview_parsed([statement]), {})
    with pytest.raises(DuplicateFileError):
        importer.preview_parsed([statement])
    forced = importer.preview_parsed([statement], force=True)
    assert forced.duplicate_files
    assert forced.duplicate_lines == statement.order_lines
    assert forced.new_lines == []
    assert forced.existing_lines == []


def test_model_and_package_match_when_code_missing(services, tmp_path):
    db, importer, _ = services
    first = parsed(tmp_path, lines=[line(code="", fingerprint="fallback1")])
    importer.commit(importer.preview_parsed([first]), {})
    second_line = replace(line(code="", fingerprint="fallback2"), order_number="SO2", quantity=2)
    importer.commit(importer.preview_parsed([parsed(tmp_path, "b.xls", "sha2", [second_line])]), {"fallback2": True})
    assert db.connection.execute("SELECT COUNT(*) FROM components").fetchone()[0] == 1
    assert db.connection.execute("SELECT current_stock FROM components").fetchone()[0] == 12


def test_stock_adjustment_and_reversal(services):
    db, _, stocks = services
    now = "2026-01-01 00:00:00"
    component_id = db.connection.execute(
        "INSERT INTO components(product_code,current_stock,created_at,updated_at) VALUES('C9', 8, ?, ?) RETURNING id",
        (now, now),
    ).fetchone()[0]
    db.connection.commit()
    movement_id = stocks.adjust(component_id, -3, "manual_out", "项目")
    assert stocks.get_stock(component_id) == 5
    stocks.reverse(movement_id, "误操作")
    assert stocks.get_stock(component_id) == 8
    with pytest.raises(StockError):
        stocks.adjust(component_id, -20, "manual_out", "")


def test_repeated_sku_in_same_first_import_adds_all_stock(services, tmp_path):
    db, importer, _ = services
    first = line(quantity=10, fingerprint="same1")
    second = replace(line(quantity=5, fingerprint="same2"), order_number="SO2")
    statement = parsed(tmp_path, lines=[first, second])
    preview = importer.preview_parsed([statement])
    importer.commit(preview, {})
    component = db.connection.execute("SELECT * FROM components").fetchone()
    assert component["current_stock"] == 15
    assert component["total_purchased"] == 15


def test_code_less_match_requires_both_model_and_package(services, tmp_path):
    db, importer, _ = services
    importer.commit(importer.preview_parsed([parsed(tmp_path, lines=[line(code="", model="A", package="0603", fingerprint="a")])]), {})
    second = line(code="", model="B", package="0805", fingerprint="b")
    importer.commit(importer.preview_parsed([parsed(tmp_path, "b.xls", "sha2", [second])]), {})
    assert db.connection.execute("SELECT COUNT(*) FROM components").fetchone()[0] == 2


def test_search_uses_all_terms_across_fields(services):
    db, _, _ = services
    now = "2026-01-01 00:00:00"
    db.connection.execute(
        "INSERT INTO components(product_code,product_type,product_name,model,package,current_stock,created_at,updated_at) VALUES('C1','贴片电阻','10kΩ','R10K','0603',10,?,?)",
        (now, now),
    ); db.connection.commit()
    from partbox.services import InventoryService
    inventory = InventoryService(db)
    assert len(inventory.list_components("电阻")) == 1
    assert len(inventory.list_components("电阻 0603")) == 1
    assert inventory.list_components("电阻 0805") == []


def test_reversal_respects_negative_stock_setting(services):
    db, _, stocks = services
    now = "2026-01-01 00:00:00"
    component_id = db.connection.execute(
        "INSERT INTO components(product_code,current_stock,created_at,updated_at) VALUES('C8', 10, ?, ?) RETURNING id",
        (now, now),
    ).fetchone()[0]; db.connection.commit()
    incoming = stocks.adjust(component_id, 5, "manual_in", "补货")
    stocks.adjust(component_id, -13, "manual_out", "已使用")
    with pytest.raises(StockError):
        stocks.reverse(incoming, "撤销补货")
    assert stocks.get_stock(component_id) == 2


def test_duplicate_file_selected_twice_is_detected_in_preview(services, tmp_path):
    _, importer, _ = services
    statement = parsed(tmp_path)
    with pytest.raises(DuplicateFileError):
        importer.preview_parsed([statement, statement])


def test_existing_stock_decisions_are_per_purchase_line(services, tmp_path):
    db, importer, _ = services
    importer.commit(importer.preview_parsed([parsed(tmp_path)]), {})
    a = replace(line(quantity=3, fingerprint="a"), order_number="SO2")
    b = replace(line(quantity=4, fingerprint="b"), order_number="SO3")
    preview = importer.preview_parsed([parsed(tmp_path, "b.xls", "sha2", [a, b])])
    importer.commit(preview, {"a": True, "b": False})
    component = db.connection.execute("SELECT current_stock,total_purchased FROM components").fetchone()
    assert tuple(component) == (13, 17)


def test_preview_accepts_an_explicit_parser(services, tmp_path):
    _, importer, _ = services
    source = tmp_path / "detail.xls"
    source.write_bytes(b"detail")
    calls = []

    def parser(path):
        calls.append(path)
        return parsed(tmp_path, name=path.name, sha="detail-sha")

    preview = importer.preview([source], parser=parser)

    assert calls == [source]
    assert len(preview.new_lines) == 1
