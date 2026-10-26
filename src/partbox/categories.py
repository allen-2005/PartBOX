from __future__ import annotations

from collections.abc import Iterable, Mapping
import re


DISPLAY_ORDER = [
    "电阻", "电容", "芯片", "三极管", "二极管", "连接器",
    "开关", "继电器", "电感", "LED", "传感器", "其他",
]

_MATCH_RULES = [
    ("电阻", ("电阻", "电位器", "排阻")),
    ("电容", ("电容", "MLCC")),
    ("连接器", ("连接器", "连接端子", "接线端子", "插座", "排针", "排母", "端子")),
    ("开关", ("开关", "按键")),
    ("继电器", ("继电器",)),
    ("电感", ("电感", "磁珠")),
    ("LED", ("LED", "发光二极管", "数码管")),
    ("传感器", ("传感器", "感应", "检测器")),
    ("三极管", ("三极管", "BJT", "MOS管", "场效应管", "晶体管")),
    ("二极管", ("二极管", "整流桥", "肖特基", "稳压管")),
    ("芯片", ("芯片", "集成电路", "运算放大器", "稳压器", "逻辑门", "驱动", "计数器", "单片机", "MCU", "ADC", "DAC", "LDO")),
]


def component_category(row: Mapping[str, object]) -> str:
    text = f"{row.get('product_type') or ''} {row.get('product_name') or ''}".upper()
    for category, keywords in _MATCH_RULES:
        if any(keyword.upper() in text for keyword in keywords):
            return category
    if re.search(r"\b\d+(?:\.\d+)?\s*(?:PF|NF|UF|ΜF)\b", text):
        return "电容"
    if re.search(r"\b\d+(?:\.\d+)?\s*(?:NH|UH|ΜH|MH)\b", text):
        return "电感"
    if any(keyword in text for keyword in ("N沟道", "P沟道", "场效应管", "MOSFET")):
        return "三极管"
    if any(keyword in text for keyword in ("SS34", "肖特基", "整流二极管", "稳压二极管")):
        return "二极管"
    if re.search(r"(?:红灯|蓝灯|绿灯|白灯|黄灯|橙灯|紫灯|粉红)", text):
        return "LED"
    return "其他"


def available_categories(rows: Iterable[Mapping[str, object]]) -> list[str]:
    present = {component_category(row) for row in rows}
    return [category for category in DISPLAY_ORDER if category in present]
