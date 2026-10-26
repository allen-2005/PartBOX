from partbox.bom import BomLine
from partbox.bom_matching import MatchKind
from partbox.bom_workflow import BomWorkflow


def line(source_row=2, **values) -> BomLine:
    defaults = dict(
        source_row=source_row,
        source_values={},
        quantity=4,
        designator=f"R{source_row}",
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
        current_stock=6,
    )
    defaults.update(values)
    return defaults


def test_build_quantity_is_applied_before_inventory_allocation():
    workflow = BomWorkflow([line(quantity=3)], [component(current_stock=4)], 2)

    row = workflow.rows[0]
    assert row.required_quantity == 6
    assert row.allocated_quantity == 4
    assert row.shortage_quantity == 2
    assert row.purchase_quantity == 2


def test_similar_candidate_can_be_selected_and_action_undone():
    workflow = BomWorkflow(
        [line()],
        [component(package="0805", current_stock=3)],
        1,
    )
    assert workflow.rows[0].match_kind is MatchKind.SIMILAR
    assert workflow.unresolved_count == 1

    workflow.choose_candidate(0, 1)
    assert workflow.rows[0].matched_component_id == 1
    assert workflow.rows[0].allocated_quantity == 3
    assert workflow.rows[0].shortage_quantity == 1
    assert workflow.unresolved_count == 0

    assert workflow.undo() is True
    assert workflow.rows[0].matched_component_id is None
    assert workflow.unresolved_count == 1


def test_rejecting_all_candidates_marks_line_unmatched():
    workflow = BomWorkflow([line()], [component(package="0805")], 1)

    workflow.reject_candidates(0)

    assert workflow.rows[0].rejected is True
    assert workflow.rows[0].matched_component_id is None
    assert workflow.rows[0].purchase_quantity == 4
    assert workflow.unresolved_count == 0


def test_shared_inventory_is_reallocated_after_manual_choice():
    workflow = BomWorkflow(
        [line(2), line(3)],
        [component(package="0805", current_stock=6)],
        1,
    )

    workflow.choose_candidate(0, 1)
    workflow.choose_candidate(1, 1)

    assert [row.allocated_quantity for row in workflow.rows] == [4, 2]
    assert [row.shortage_quantity for row in workflow.rows] == [0, 2]


def test_only_the_row_that_consumes_the_last_available_unit_is_marked_exhausted():
    workflow = BomWorkflow(
        [line(2, quantity=4), line(3, quantity=2)],
        [component(current_stock=6)],
        1,
    )

    assert [row.exhausts_stock for row in workflow.rows] == [False, True]


def test_exact_stock_exhaustion_is_reported_even_without_shortage():
    workflow = BomWorkflow([line(quantity=6)], [component(current_stock=6)], 1)

    assert workflow.shortage_rows == []
    assert workflow.exhausted_rows == [workflow.rows[0]]
    assert workflow.rows[0].extra_purchase_quantity == 0
    assert workflow.rows[0].purchase_quantity == 0


def test_extra_purchase_defaults_to_zero_and_is_added_to_shortage():
    workflow = BomWorkflow([line(quantity=8)], [component(current_stock=6)], 1)

    workflow.set_extra_purchase(0, 5)

    assert workflow.rows[0].shortage_quantity == 2
    assert workflow.rows[0].extra_purchase_quantity == 5
    assert workflow.rows[0].purchase_quantity == 7
    assert workflow.export_rows()[0]["purchase_quantity"] == 7


def test_negative_extra_purchase_is_rejected():
    workflow = BomWorkflow([line()], [], 1)

    try:
        workflow.set_extra_purchase(0, -1)
    except ValueError as error:
        assert "大于等于 0" in str(error)
    else:
        raise AssertionError("negative extra purchase was accepted")
