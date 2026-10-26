from __future__ import annotations

import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd


class BomError(ValueError):
    pass


@dataclass(frozen=True)
class BomLine:
    source_row: int
    source_values: dict[str, Any]
    quantity: int
    designator: str = ""
    product_code: str = ""
    product_type: str = ""
    description: str = ""
    model: str = ""
    package: str = ""
    brand: str = ""


@dataclass(frozen=True)
class ParsedBom:
    path: Path
    sheet_name: str
    columns: list[str]
    lines: list[BomLine]


ALIASES = {
    "quantity": ("数量", "用量", "采购数量", "quantity", "qty", "q'ty"),
    "designator": ("位号", "器件位号", "designator", "designators", "reference", "references", "refdes"),
    "product_code": (
        "立创编号", "立创商品编号", "商品编号", "lcsc", "lcscpart#", "lcscpartnumber",
        "lcscpartno", "lcsc#",
    ),
    "product_type": ("商品类型", "元件类型", "器件类型", "类型", "type", "category"),
    "description": (
        "参数", "数值", "商品名称", "元件名称", "器件名称", "名称", "comment", "value",
        "description", "productinfo",
    ),
    "model": (
        "商品型号", "厂家型号", "型号", "manufacturerpartnumber", "manufacturerpart#",
        "mfrpart", "mfr#", "mpn", "model",
    ),
    "package": ("封装", "封装格式", "封装规格", "footprint", "package", "packaging"),
    "brand": ("品牌", "厂家", "制造商", "brand", "manufacturer", "mfr"),
}


def _normalized_header(value: Any) -> str:
    text = "" if value is None else str(value).strip().lower()
    return re.sub(r"[\s_\-./（）()]+", "", text)


HEADER_KEYS = {
    _normalized_header(alias): key
    for key, aliases in ALIASES.items()
    for alias in aliases
}


def _text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and math.isnan(value):
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()


def _read_sources(path: Path) -> list[tuple[str, pd.DataFrame]]:
    suffix = path.suffix.lower()
    if suffix == ".csv":
        try:
            return [("CSV", pd.read_csv(path, header=None, dtype=object, keep_default_na=False, encoding="utf-8-sig"))]
        except UnicodeDecodeError:
            return [("CSV", pd.read_csv(path, header=None, dtype=object, keep_default_na=False, encoding="gb18030"))]
    if suffix not in {".xls", ".xlsx"}:
        raise BomError("BOM仅支持 .xls、.xlsx 或 .csv 文件")
    try:
        workbook = pd.ExcelFile(path)
        return [
            (sheet, pd.read_excel(path, sheet_name=sheet, header=None, dtype=object, keep_default_na=False))
            for sheet in workbook.sheet_names
        ]
    except Exception as error:
        raise BomError(f"无法读取BOM：{error}") from error


def _header_map(frame: pd.DataFrame) -> tuple[int, dict[str, int]] | None:
    best: tuple[int, int, dict[str, int]] | None = None
    for row_index in range(min(len(frame), 30)):
        mapping: dict[str, int] = {}
        for column, value in enumerate(frame.iloc[row_index].tolist()):
            key = HEADER_KEYS.get(_normalized_header(value))
            if key is not None and key not in mapping:
                mapping[key] = column
        valid = "quantity" in mapping and any(
            key in mapping for key in ("product_code", "model", "description")
        )
        if valid:
            candidate = (len(mapping), -row_index, mapping)
            if best is None or candidate[:2] > best[:2]:
                best = candidate
    if best is None:
        return None
    return -best[1], best[2]


def _quantity(value: Any, source_row: int) -> int:
    try:
        numeric = float(value)
        quantity = int(numeric)
    except (TypeError, ValueError) as error:
        raise BomError(f"第 {source_row} 行数量无效") from error
    if quantity < 1 or numeric != quantity:
        raise BomError(f"第 {source_row} 行数量必须是大于等于 1 的整数")
    return quantity


def parse_bom(path: Path | str) -> ParsedBom:
    path = Path(path)
    if not path.exists():
        raise BomError(f"BOM文件不存在：{path}")

    selected = None
    for sheet_name, frame in _read_sources(path):
        detected = _header_map(frame)
        if detected is None:
            continue
        header_row, mapping = detected
        if selected is None or len(mapping) > len(selected[3]):
            selected = (sheet_name, frame, header_row, mapping)
    if selected is None:
        raise BomError("未找到有效BOM表头：必须包含数量，以及商品编号、型号或名称中的至少一项")

    sheet_name, frame, header_row, mapping = selected
    columns = [_text(value) or f"未命名列{index + 1}" for index, value in enumerate(frame.iloc[header_row].tolist())]
    lines: list[BomLine] = []
    for row_index in range(header_row + 1, len(frame)):
        raw_values = frame.iloc[row_index].tolist()
        if not any(_text(value) for value in raw_values):
            continue
        source_row = row_index + 1
        source_values = {
            columns[index]: ("" if _text(value) == "" else value)
            for index, value in enumerate(raw_values)
        }
        fields = {
            key: _text(raw_values[column])
            for key, column in mapping.items()
        }
        if not any(fields.get(key) for key in ("product_code", "model", "description")):
            continue
        lines.append(BomLine(
            source_row=source_row,
            source_values=source_values,
            quantity=_quantity(raw_values[mapping["quantity"]], source_row),
            designator=fields.get("designator", ""),
            product_code=fields.get("product_code", ""),
            product_type=fields.get("product_type", ""),
            description=fields.get("description", ""),
            model=fields.get("model", ""),
            package=fields.get("package", ""),
            brand=fields.get("brand", ""),
        ))
    if not lines:
        raise BomError("BOM中没有可处理的元件行")
    return ParsedBom(path=path, sheet_name=sheet_name, columns=columns, lines=lines)


LCSC_EXPORT_COLUMNS = [
    "LCSC Part Number",
    "Manufacturer Part Number",
    "Description",
    "Quantity",
    "Package",
    "Manufacturer",
    "Reference Designator",
]


def export_lcsc_bom(path: Path | str, workflow_rows: list[dict]) -> Path:
    target = Path(path)
    if target.suffix.lower() != ".xlsx":
        target = target.with_suffix(".xlsx")
    target.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    for workflow_row in workflow_rows:
        purchase_quantity = int(workflow_row.get("purchase_quantity") or 0)
        if purchase_quantity <= 0:
            continue
        line = workflow_row["line"]
        rows.append({
            "LCSC Part Number": line.product_code,
            "Manufacturer Part Number": line.model,
            "Description": line.description or line.product_type,
            "Quantity": purchase_quantity,
            "Package": line.package,
            "Manufacturer": line.brand,
            "Reference Designator": line.designator,
        })
    temporary = target.with_name(f"{target.stem}.tmp.xlsx")
    try:
        pd.DataFrame(rows, columns=LCSC_EXPORT_COLUMNS).to_excel(
            temporary, index=False, sheet_name="LCSC BOM"
        )
        temporary.replace(target)
    finally:
        if temporary.exists():
            temporary.unlink()
    return target
