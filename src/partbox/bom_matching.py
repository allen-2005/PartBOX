from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from enum import Enum

from partbox.bom import BomLine
from partbox.categories import component_category


class MatchKind(Enum):
    EXACT = "exact"
    SIMILAR = "similar"
    UNMATCHED = "unmatched"


@dataclass(frozen=True)
class MatchCandidate:
    component_id: int
    score: int
    differences: tuple[str, ...]
    component: dict


@dataclass(frozen=True)
class MatchResult:
    line: BomLine
    required_quantity: int
    kind: MatchKind
    matched_component_id: int | None
    allocated_quantity: int
    shortage_quantity: int
    candidates: tuple[MatchCandidate, ...] = ()


def _normalized(value: str) -> str:
    text = unicodedata.normalize("NFKC", str(value or "")).upper()
    text = text.replace("Ω", "OHM").replace("Ω", "OHM")
    return re.sub(r"[^0-9A-Z\u4e00-\u9fff]+", "", text)


def _brand(value: str) -> str:
    text = unicodedata.normalize("NFKC", str(value or "")).upper()
    latin = re.findall(r"[A-Z0-9]+", text)
    return "".join(latin) if latin else re.sub(r"[^\u4e00-\u9fff0-9]+", "", text)


def _package(value: str) -> str:
    text = unicodedata.normalize("NFKC", str(value or "")).upper()
    for code in ("01005", "0201", "0402", "0603", "0805", "1206", "1210", "1812", "2010", "2512"):
        if re.search(rf"(?<!\d){code}(?!\d)", text):
            return code
    return re.sub(r"[^0-9A-Z]+", "", text)


def _resistance(text: str) -> float | None:
    normalized = unicodedata.normalize("NFKC", str(text or "")).upper().replace("Ω", "R").replace("OHM", "R")
    embedded = re.search(r"(?<![0-9A-Z])(\d+)([KMR])(\d+)(?![A-Z])", normalized)
    if embedded:
        whole, suffix, fraction = embedded.groups()
        base = float(f"{whole}.{fraction}")
        return base * {"R": 1, "K": 1_000, "M": 1_000_000}[suffix]
    regular = re.search(r"(?<![0-9A-Z])(\d+(?:\.\d+)?)\s*([KMR])(?![WVAHF])", normalized)
    if not regular:
        return None
    number, suffix = regular.groups()
    return float(number) * {"R": 1, "K": 1_000, "M": 1_000_000}[suffix]


def _capacitance(text: str) -> float | None:
    normalized = unicodedata.normalize("NFKC", str(text or "")).upper().replace("Μ", "U").replace("μ", "U")
    match = re.search(r"(?<![0-9A-Z])(\d+(?:\.\d+)?)\s*(PF|NF|UF|MF|F)(?![A-Z])", normalized)
    if not match:
        return None
    number, suffix = match.groups()
    return float(number) * {"PF": 1e-12, "NF": 1e-9, "UF": 1e-6, "MF": 1e-3, "F": 1}[suffix]


def _tolerance(text: str) -> float | None:
    match = re.search(r"(?:±|\+/-)?\s*(\d+(?:\.\d+)?)\s*%", str(text or ""))
    return None if match is None else float(match.group(1))


def _power(text: str) -> float | None:
    normalized = unicodedata.normalize("NFKC", str(text or "")).upper()
    match = re.search(r"(?<![0-9A-Z])(\d+(?:\.\d+)?)\s*(MW|W)(?![A-Z])", normalized)
    if not match:
        return None
    number, suffix = match.groups()
    return float(number) / 1000 if suffix == "MW" else float(number)


def _category(product_type: str, description: str) -> str:
    return component_category({"product_type": product_type, "product_name": description})


def _spec(item, inventory: bool) -> dict:
    description = str(item.get("product_name") or "") if inventory else item.description
    product_type = str(item.get("product_type") or "") if inventory else item.product_type
    model = str(item.get("model") or "") if inventory else item.model
    package = str(item.get("package") or "") if inventory else item.package
    brand = str(item.get("brand") or "") if inventory else item.brand
    text = " ".join((product_type, description, model, package))
    category = _category(product_type, description)
    value = _resistance(text) if category == "电阻" else _capacitance(text) if category == "电容" else None
    return {
        "category": category,
        "value": value,
        "package": _package(package),
        "brand": _brand(brand),
        "tolerance": _tolerance(text),
        "power": _power(text),
        "model": _normalized(model),
    }


def _same_required(left, right) -> bool:
    return left not in (None, "") and right not in (None, "") and left == right


def _semantic_exact(bom: dict, stock: dict) -> bool:
    if bom["category"] != stock["category"]:
        return False
    if bom["category"] in {"电阻", "电容"}:
        if not all(_same_required(bom[key], stock[key]) for key in ("value", "package", "brand")):
            return False
        for key in ("tolerance", "power"):
            if bom[key] is not None or stock[key] is not None:
                if not _same_required(bom[key], stock[key]):
                    return False
        return True
    return all(_same_required(bom[key], stock[key]) for key in ("model", "package", "brand"))


def _candidate(line: BomLine, bom: dict, component: dict, stock: dict) -> MatchCandidate | None:
    same_category = bom["category"] == stock["category"] and bom["category"] != "其他"
    same_value = _same_required(bom["value"], stock["value"])
    same_model = _same_required(bom["model"], stock["model"])
    if not ((same_category and same_value) or same_model):
        return None
    labels = {
        "package": "封装",
        "tolerance": "精度",
        "brand": "品牌",
        "power": "功率",
        "model": "型号",
    }
    differences = []
    score = 0
    for key, label in labels.items():
        left, right = bom[key], stock[key]
        if left == right and left not in (None, ""):
            score += 1
        elif left != right:
            differences.append(f"{label}不同：BOM {line_value(left)}／库存 {line_value(right)}")
    return MatchCandidate(int(component["id"]), score, tuple(differences), component)


def line_value(value) -> str:
    if value in (None, ""):
        return "未注明"
    return f"{value:g}" if isinstance(value, float) else str(value)


def match_bom(lines: list[BomLine], inventory: list[dict], build_quantity: int) -> list[MatchResult]:
    try:
        build_quantity = int(build_quantity)
    except (TypeError, ValueError) as error:
        raise ValueError("项目制作数量必须大于等于 1") from error
    if build_quantity < 1:
        raise ValueError("项目制作数量必须大于等于 1")

    available = [component for component in inventory if int(component.get("current_stock") or 0) > 0]
    remaining_stock = {
        int(component["id"]): int(component.get("current_stock") or 0)
        for component in available
    }
    results = []
    for line in lines:
        required = line.quantity * build_quantity
        bom_spec = _spec(line, inventory=False)
        code = _normalized(line.product_code)
        sku_matches = [
            component for component in available
            if code and _normalized(component.get("product_code") or "") == code
        ]
        exact_matches = sku_matches or [
            component for component in available
            if _semantic_exact(bom_spec, _spec(component, inventory=True))
        ]
        if len(exact_matches) == 1:
            selected = exact_matches[0]
            component_id = int(selected["id"])
            allocated = min(required, remaining_stock[component_id])
            remaining_stock[component_id] -= allocated
            results.append(MatchResult(
                line, required, MatchKind.EXACT, component_id, allocated,
                required - allocated,
            ))
            continue

        candidates = []
        candidate_source = exact_matches if exact_matches else available
        for component in candidate_source:
            candidate = _candidate(line, bom_spec, component, _spec(component, inventory=True))
            if candidate is not None:
                candidates.append(candidate)
        candidates.sort(key=lambda item: (-item.score, item.component_id))
        kind = MatchKind.SIMILAR if candidates else MatchKind.UNMATCHED
        results.append(MatchResult(
            line, required, kind, None, 0, required, tuple(candidates)
        ))
    return results
