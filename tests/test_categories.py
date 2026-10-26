from partbox.categories import available_categories, component_category


def component(product_type: str, product_name: str = "") -> dict:
    return {"product_type": product_type, "product_name": product_name}


def test_resistor_only_inventory_has_no_phantom_categories():
    rows = [component("贴片电阻"), component("插件电阻", "金属膜电阻")]
    assert available_categories(rows) == ["电阻"]


def test_categories_use_priority_and_stable_display_order():
    rows = [
        component("IC/晶体管插座"),
        component("贴片电容(MLCC)"),
        component("三极管（BJT）", "NPN 40V"),
        component("线性稳压器(LDO)", "稳压芯片"),
        component("贴片电阻"),
    ]
    assert component_category(rows[0]) == "连接器"
    assert available_categories(rows) == ["电阻", "电容", "芯片", "三极管", "连接器"]


def test_unknown_component_uses_other_category():
    assert component_category(component("散热板/散热片")) == "其他"


def test_quick_filters_infer_missing_product_type_from_names():
    cases = {
        "厚膜电阻 4.7KΩ ±1% 100mW 编带": "电阻",
        "100nF ±10% 50V 编带": "电容",
        "N沟道增强型场效应管 30V 5.8A 编带": "三极管",
        "40V 3A 编带 SS34": "二极管",
        "0603 红灯 高亮 编带": "LED",
        "47uH ±20% 4.5A 编带": "电感",
    }
    for name, expected in cases.items():
        assert component_category(component("", name)) == expected
