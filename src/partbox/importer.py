from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd


ALL_HEADERS = [
    "订单编号", "订单状态", "下单时间", "收货人", "客户料号", "商品编号", "品牌",
    "商品类型", "商品名称", "商品型号", "封装格式", "订购数量", "商品单位",
    "单价（人民币含税）", "小计金额（人民币含税）", "发货日期", "快递公司",
    "快递单号", "签收日期", "发票号", "开票时间", "客户代表", "归属原订单",
    "bom标识", "订单合同编号",
]
REQUIRED_HEADERS = {"订单编号", "商品编号", "商品名称", "订购数量"}


class StatementError(ValueError):
    pass


class MissingHeadersError(StatementError):
    pass


def _text(value: Any) -> str:
    if value is None or pd.isna(value):
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()


def _display_text(value: Any) -> str:
    """Return an Excel cell as display text without rewriting its contents."""
    if value is None or pd.isna(value):
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def _number(value: Any, default: float = 0.0) -> float:
    if value is None or pd.isna(value) or value == "":
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _date_text(value: Any) -> str:
    if value is None or pd.isna(value) or value == "":
        return ""
    if isinstance(value, (pd.Timestamp, datetime)):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    return str(value).strip().replace("/", "-")


@dataclass(frozen=True)
class OrderLine:
    source_sheet: str
    source_row: int
    order_number: str
    order_status: str
    order_time: str
    recipient: str
    customer_part_number: str
    product_code: str
    brand: str
    product_type: str
    product_name: str
    model: str
    package: str
    quantity: int
    unit: str
    unit_price: float
    subtotal: float
    shipping_date: str = ""
    courier: str = ""
    tracking_number: str = ""
    receipt_date: str = ""
    invoice_number: str = ""
    invoice_time: str = ""
    customer_representative: str = ""
    original_order: str = ""
    bom_flag: str = ""
    contract_number: str = ""
    line_fingerprint: str = ""


@dataclass(frozen=True)
class FeeLine:
    source_sheet: str
    source_row: int
    name: str
    amount: float


@dataclass(frozen=True)
class ImportIssue:
    source_sheet: str
    source_row: int
    message: str


@dataclass
class ParsedStatement:
    path: Path
    file_sha256: str
    source_sheet: str
    header_row: int
    headers: list[str]
    order_lines: list[OrderLine] = field(default_factory=list)
    fee_lines: list[FeeLine] = field(default_factory=list)
    issues: list[ImportIssue] = field(default_factory=list)


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _line_fingerprint(values: dict[str, Any]) -> str:
    order_time = _date_text(values.get("下单时间"))
    # LCSC statements can differ only by seconds when the same period is exported again.
    normalized_order_time = order_time[:16] if len(order_time) >= 16 else order_time
    identity = "|".join([
        _text(values.get("订单编号")),
        _text(values.get("商品编号")).upper(),
        str(int(_number(values.get("订购数量")))),
        f"{_number(values.get('小计金额（人民币含税）')):.4f}",
        normalized_order_time,
    ])
    return hashlib.sha256(identity.encode("utf-8")).hexdigest()


def _read_sheets(path: Path) -> dict[str, pd.DataFrame]:
    suffix = path.suffix.lower()
    if suffix not in {".xls", ".xlsx"}:
        raise StatementError("仅支持 .xls 和 .xlsx 文件")
    engine = "xlrd" if suffix == ".xls" else "openpyxl"
    return pd.read_excel(path, sheet_name=None, header=None, dtype=object, engine=engine)


def parse_statement(path: Path) -> ParsedStatement:
    path = Path(path)
    sheets = _read_sheets(path)
    candidates: list[tuple[str, int, pd.DataFrame, list[str]]] = []
    best_headers: set[str] = set()
    for sheet_name, frame in sheets.items():
        for index in range(min(20, len(frame))):
            headers = [_text(value) for value in frame.iloc[index].tolist()]
            present = {header for header in headers if header}
            if len(present & REQUIRED_HEADERS) > len(best_headers & REQUIRED_HEADERS):
                best_headers = present
            if REQUIRED_HEADERS <= present:
                candidates.append((str(sheet_name), index, frame, headers))
                break
    if not candidates:
        missing = sorted(REQUIRED_HEADERS - best_headers)
        raise MissingHeadersError("缺少必要表头：" + "、".join(missing))

    sheet_name, header_index, _, headers = candidates[0]
    parsed = ParsedStatement(
        path=path,
        file_sha256=file_sha256(path),
        source_sheet=sheet_name,
        header_row=header_index + 1,
        headers=headers,
    )
    for current_sheet, current_header_index, frame, current_headers in candidates:
        column_indexes = {header: index for index, header in enumerate(current_headers) if header}
        for row_index in range(current_header_index + 1, len(frame)):
            row = frame.iloc[row_index].tolist()
            values = {header: row[index] if index < len(row) else None for header, index in column_indexes.items()}
            name = _display_text(values.get("商品名称"))
            code = _text(values.get("商品编号")).upper()
            order = _text(values.get("订单编号"))
            if name.strip().startswith("价外费用"):
                parsed.fee_lines.append(FeeLine(current_sheet, row_index + 1, name, _number(values.get("小计金额（人民币含税）"))))
                continue
            if not any(_text(value) for value in row):
                continue
            if not order or not name or not _number(values.get("订购数量")):
                continue
            if not code and not (_text(values.get("商品型号")) and _text(values.get("封装格式"))):
                parsed.issues.append(ImportIssue(current_sheet, row_index + 1, "缺少商品编号，且型号或封装不完整"))
                continue
            parsed.order_lines.append(OrderLine(
                source_sheet=current_sheet, source_row=row_index + 1, order_number=order,
                order_status=_text(values.get("订单状态")), order_time=_date_text(values.get("下单时间")),
                recipient=_text(values.get("收货人")), customer_part_number=_text(values.get("客户料号")),
                product_code=code, brand=_display_text(values.get("品牌")),
                product_type=_display_text(values.get("商品类型")), product_name=name,
                model=_display_text(values.get("商品型号")), package=_display_text(values.get("封装格式")),
                quantity=int(_number(values.get("订购数量"))), unit=_display_text(values.get("商品单位")),
                unit_price=_number(values.get("单价（人民币含税）")), subtotal=_number(values.get("小计金额（人民币含税）")),
                shipping_date=_date_text(values.get("发货日期")), courier=_text(values.get("快递公司")),
                tracking_number=_text(values.get("快递单号")), receipt_date=_date_text(values.get("签收日期")),
                invoice_number=_text(values.get("发票号")), invoice_time=_date_text(values.get("开票时间")),
                customer_representative=_text(values.get("客户代表")), original_order=_text(values.get("归属原订单")),
                bom_flag=_text(values.get("bom标识")), contract_number=_text(values.get("订单合同编号")),
                line_fingerprint=_line_fingerprint(values),
            ))
    return parsed
