from pathlib import Path

import pandas as pd
import pytest

from partbox.importer import MissingHeadersError, _line_fingerprint, parse_statement


HEADERS = [
    "订单编号", "订单状态", "下单时间", "收货人", "客户料号", "商品编号", "品牌",
    "商品类型", "商品名称", "商品型号", "封装格式", "订购数量", "商品单位",
    "单价（人民币含税）", "小计金额（人民币含税）", "发货日期", "快递公司",
    "快递单号", "签收日期", "发票号", "开票时间", "客户代表", "归属原订单",
    "bom标识", "订单合同编号",
]


def excel_display_text(value) -> str:
    if value is None or pd.isna(value):
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def make_statement(path: Path):
    rows = [
        [None] * 25,
        HEADERS,
        ["SO1", "已发货", "2026/01/02 03:04", "张三", "", " C123 ", "Brand", "贴片电阻", "10kΩ ±1%", "R10K", "0603", 100, "个", 0.01, 1.0] + [""] * 10,
        [""] * 8 + ["价外费用（配送费）"] + [""] * 5 + [5.0] + [""] * 10,
    ]
    pd.DataFrame(rows).to_excel(path, header=False, index=False)


def test_parser_discovers_header_and_extracts_product_and_fee(tmp_path):
    path = tmp_path / "statement.xlsx"
    make_statement(path)
    parsed = parse_statement(path)
    assert parsed.header_row == 2
    assert len(parsed.order_lines) == 1
    assert parsed.order_lines[0].product_code == "C123"
    assert parsed.order_lines[0].quantity == 100
    assert parsed.order_lines[0].line_fingerprint
    assert len(parsed.fee_lines) == 1
    assert parsed.fee_lines[0].amount == 5.0


def test_parser_preserves_material_detail_display_text_exactly(tmp_path):
    path = tmp_path / "exact-statement.xlsx"
    row = [
        "SO1", "已发货", "2026/01/02 03:04", "张三", "", "C123",
        " FOJAN(富捷) ", "贴片电阻", " 100Ω ±1% 125mW 厚膜电阻 编带 ",
        " FRC0805F1000TS ", " 0805 ", 100, " 个 ", 0.01, 1.0,
    ] + [""] * 10
    pd.DataFrame([HEADERS, row]).to_excel(path, header=False, index=False)

    line = parse_statement(path).order_lines[0]

    assert line.brand == " FOJAN(富捷) "
    assert line.product_type == "贴片电阻"
    assert line.product_name == " 100Ω ±1% 125mW 厚膜电阻 编带 "
    assert line.model == " FRC0805F1000TS "
    assert line.package == " 0805 "
    assert line.unit == " 个 "


def test_parser_reports_missing_required_headers(tmp_path):
    path = tmp_path / "bad.xlsx"
    pd.DataFrame([["商品名称", "订购数量"], ["电阻", 2]]).to_excel(path, header=False, index=False)
    with pytest.raises(MissingHeadersError) as exc:
        parse_statement(path)
    assert "订单编号" in str(exc.value)
    assert "商品编号" in str(exc.value)


def test_parser_merges_all_qualifying_worksheets(tmp_path):
    path = tmp_path / "multi.xlsx"
    row1 = ["SO1", "已发货", "2026/01/01", "A", "", "C1", "B", "电阻", "10k", "R1", "0603", 10, "个", .01, .1] + [""] * 10
    row2 = ["SO2", "已发货", "2026/01/02", "A", "", "C2", "B", "电容", "1uF", "C1", "0603", 20, "个", .02, .4] + [""] * 10
    with pd.ExcelWriter(path) as writer:
        pd.DataFrame([HEADERS, row1]).to_excel(writer, sheet_name="物料一", header=False, index=False)
        pd.DataFrame([HEADERS, row2]).to_excel(writer, sheet_name="物料二", header=False, index=False)
    parsed = parse_statement(path)
    assert {line.product_code for line in parsed.order_lines} == {"C1", "C2"}


@pytest.mark.parametrize("filename", [
    "(20251001-20251031)立创商城物料明细对账单.xls",
    "(20251201-20251231)立创商城物料明细对账单.xls",
    "(20260501-20260531)立创商城物料明细对账单.xls",
    "(20260601-20260630)立创商城物料明细对账单.xls",
    "(20260701-20260731)立创商城物料明细对账单.xls",
    "(20260801-20260831)立创商城物料明细对账单.xls",
])
def test_real_lcsc_xls_format_is_supported(filename):
    path = Path.home() / "Desktop" / "立创商城物料订单" / "物料明细" / filename
    if not path.exists():
        pytest.skip("local format sample unavailable")
    parsed = parse_statement(path)
    assert parsed.order_lines
    assert all(line.product_code for line in parsed.order_lines)
    sheets = pd.read_excel(path, sheet_name=None, header=None, dtype=object, engine="xlrd")
    source_columns = {
        "brand": "品牌",
        "product_type": "商品类型",
        "product_name": "商品名称",
        "model": "商品型号",
        "package": "封装格式",
        "unit": "商品单位",
    }
    headers_by_sheet = {}
    for sheet_name, frame in sheets.items():
        for row_index in range(min(20, len(frame))):
            headers = [excel_display_text(value).strip() for value in frame.iloc[row_index].tolist()]
            if {"订单编号", "商品编号", "商品名称", "订购数量"} <= set(headers):
                headers_by_sheet[str(sheet_name)] = headers
                break
    for line in parsed.order_lines:
        headers = headers_by_sheet[line.source_sheet]
        row = sheets[line.source_sheet].iloc[line.source_row - 1].tolist()
        source = {header: row[index] for index, header in enumerate(headers) if header and index < len(row)}
        for attribute, column in source_columns.items():
            assert getattr(line, attribute) == excel_display_text(source.get(column))


def test_fingerprint_normalizes_cross_format_timestamp_precision():
    base = {"订单编号": "SO1", "商品编号": "C1", "订购数量": 10, "小计金额（人民币含税）": 1.2}
    assert _line_fingerprint({**base, "下单时间": "2026-08-10 04:18"}) == _line_fingerprint(
        {**base, "下单时间": "2026/08/10 04:18:59"}
    )
