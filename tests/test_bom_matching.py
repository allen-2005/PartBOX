from partbox.bom import BomLine
from partbox.bom_matching import MatchKind, match_bom


def line(**values) -> BomLine:
    defaults = dict(
        source_row=2,
        source_values={},
        quantity=10,
        designator="R1",
        product_code="",
        product_type="贴片电阻",
        description="100K ±5% 100mW",
        model="",
        package="0603",
        brand="FOJAN",
    )
    defaults.update(values)
    return BomLine(**defaults)


def component(component_id=1, **values) -> dict:
    defaults = dict(
        id=component_id,
        product_code="C100",
        product_type="贴片电阻",
        product_name="厚膜电阻 100kΩ 5% 100mW 编带",
        model="FRC0603J1003TS",
        package="0603",
        brand="FOJAN(富捷)",
        current_stock=20,
    )
    defaults.update(values)
    return defaults


def test_same_lcsc_code_is_exact_and_build_quantity_is_applied():
    result = match_bom(
        [line(product_code="C100", quantity=6)],
        [component(current_stock=10)],
        build_quantity=2,
    )[0]

    assert result.kind is MatchKind.EXACT
    assert result.required_quantity == 12
    assert result.allocated_quantity == 10
    assert result.shortage_quantity == 2
    assert result.matched_component_id == 1


def test_semantically_equal_resistor_text_is_exact():
    result = match_bom([line()], [component()], build_quantity=1)[0]

    assert result.kind is MatchKind.EXACT
    assert result.allocated_quantity == 10
    assert result.shortage_quantity == 0


def test_package_tolerance_and_brand_differences_are_only_candidates():
    inventory = [
        component(1, package="0805"),
        component(2, product_name="100kΩ ±1% 100mW", model="R1", current_stock=8),
        component(3, brand="UNI-ROYAL", model="R2", current_stock=7),
    ]

    result = match_bom([line()], inventory, build_quantity=1)[0]

    assert result.kind is MatchKind.SIMILAR
    assert result.matched_component_id is None
    assert [candidate.component_id for candidate in result.candidates] == [1, 2, 3]
    differences = {candidate.component_id: candidate.differences for candidate in result.candidates}
    assert any("封装" in text for text in differences[1])
    assert any("精度" in text for text in differences[2])
    assert any("品牌" in text for text in differences[3])


def test_zero_stock_component_cannot_satisfy_or_be_a_candidate():
    result = match_bom([line()], [component(current_stock=0)], build_quantity=1)[0]

    assert result.kind is MatchKind.UNMATCHED
    assert result.candidates == ()
    assert result.shortage_quantity == 10


def test_model_package_brand_can_exact_match_non_passive_component():
    bom = line(
        product_type="运算放大器",
        description="双通道运算放大器",
        model="LM358P",
        package="DIP-8",
        brand="TI",
        quantity=1,
    )
    inventory = [component(
        product_type="运算放大器",
        product_name="双通道运算放大器 管装",
        model="lm358p",
        package="DIP8",
        brand="TI(德州仪器)",
        current_stock=1,
    )]

    result = match_bom([bom], inventory, build_quantity=2)[0]

    assert result.kind is MatchKind.EXACT
    assert result.allocated_quantity == 1
    assert result.shortage_quantity == 1


def test_multiple_bom_lines_share_remaining_inventory_without_double_allocation():
    results = match_bom(
        [line(quantity=4, designator="R1"), line(quantity=4, designator="R2")],
        [component(current_stock=6)],
        build_quantity=1,
    )

    assert [result.allocated_quantity for result in results] == [4, 2]
    assert [result.shortage_quantity for result in results] == [0, 2]
