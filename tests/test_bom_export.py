import pandas as pd

from partbox.bom import BomLine, export_lcsc_bom


def workflow_row(code: str, purchase_quantity: int, description="100kΩ", quantity=10):
    return {
        "line": BomLine(
            source_row=2,
            source_values={},
            quantity=quantity,
            designator="R1",
            product_code=code,
            product_type="贴片电阻",
            description=description,
            model="R100K",
            package="0603",
            brand="FOJAN",
        ),
        "purchase_quantity": purchase_quantity,
    }


def test_export_lcsc_bom_contains_only_final_purchase_quantities(tmp_path):
    target = tmp_path / "立创商城采购BOM.xlsx"
    rows = [
        workflow_row("C-FULFILLED", 0),
        workflow_row("C-PARTIAL", 6),
        workflow_row("C-UNMATCHED", 2, description="MCU", quantity=1),
        workflow_row("C-RESTOCK", 5),
    ]

    result = export_lcsc_bom(target, rows)

    assert result == target
    exported = pd.read_excel(target, dtype=object)
    assert exported.columns.tolist() == [
        "LCSC Part Number",
        "Manufacturer Part Number",
        "Description",
        "Quantity",
        "Package",
        "Manufacturer",
        "Reference Designator",
    ]
    assert exported["LCSC Part Number"].tolist() == ["C-PARTIAL", "C-UNMATCHED", "C-RESTOCK"]
    assert exported["Quantity"].tolist() == [6, 2, 5]
    assert not list(tmp_path.glob("*.tmp.xlsx"))

