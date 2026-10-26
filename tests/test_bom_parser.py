import pandas as pd
import pytest

from partbox.bom import BomError, parse_bom


def test_parse_chinese_eda_bom_multiplies_nothing_and_preserves_source_values(tmp_path):
    path = tmp_path / "project-bom.xlsx"
    frame = pd.DataFrame([
        {
            "位号": "R1,R2",
            "商品类型": "贴片电阻",
            "参数": "100kΩ ±5% 100mW",
            "封装": "0603",
            "品牌": "FOJAN(富捷)",
            "立创编号": "C123",
            "数量": 2,
        },
        {
            "位号": "U1",
            "商品类型": "运算放大器",
            "参数": "双通道运放",
            "封装": "DIP-8",
            "品牌": "TI",
            "立创编号": "C456",
            "数量": 1,
        },
    ])
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        pd.DataFrame([["项目BOM"]]).to_excel(writer, index=False, header=False)
        frame.to_excel(writer, index=False, startrow=2)

    parsed = parse_bom(path)

    assert parsed.sheet_name == "Sheet1"
    assert len(parsed.lines) == 2
    resistor = parsed.lines[0]
    assert resistor.quantity == 2
    assert resistor.designator == "R1,R2"
    assert resistor.product_code == "C123"
    assert resistor.product_type == "贴片电阻"
    assert resistor.description == "100kΩ ±5% 100mW"
    assert resistor.package == "0603"
    assert resistor.brand == "FOJAN(富捷)"
    assert resistor.source_values["参数"] == "100kΩ ±5% 100mW"
    assert resistor.source_row == 4


def test_parse_english_csv_aliases(tmp_path):
    path = tmp_path / "eda.csv"
    pd.DataFrame([{
        "Designator": "C1",
        "Comment": "1uF ±10% 16V",
        "Footprint": "0603",
        "LCSC Part #": "C999",
        "Quantity": "3",
        "Manufacturer": "SAMSUNG",
        "Manufacturer Part Number": "CL10A105KO8NNNC",
    }]).to_csv(path, index=False, encoding="utf-8-sig")

    line = parse_bom(path).lines[0]

    assert line.quantity == 3
    assert line.designator == "C1"
    assert line.description == "1uF ±10% 16V"
    assert line.package == "0603"
    assert line.product_code == "C999"
    assert line.model == "CL10A105KO8NNNC"
    assert line.brand == "SAMSUNG"


def test_parse_bom_rejects_missing_quantity_or_invalid_quantity(tmp_path):
    missing = tmp_path / "missing.xlsx"
    pd.DataFrame([{"位号": "R1", "参数": "10k"}]).to_excel(missing, index=False)
    with pytest.raises(BomError, match="数量"):
        parse_bom(missing)

    invalid = tmp_path / "invalid.xlsx"
    pd.DataFrame([{"位号": "R1", "参数": "10k", "数量": 0}]).to_excel(invalid, index=False)
    with pytest.raises(BomError, match="大于等于 1"):
        parse_bom(invalid)

