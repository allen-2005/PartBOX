from partbox.ui.theme import APP_STYLESHEET, COMMON_COLORS, PAGE_PALETTES


def test_a_style_page_palettes_are_distinct_and_exact():
    assert COMMON_COLORS["accent"] == "#4D78CF"
    assert PAGE_PALETTES == {
        "inventoryPage": {"background": "#EEF5FF", "secondary": "#E3EEFC"},
        "comparisonPage": {"background": "#FFF8E6", "secondary": "#F8EDC8"},
        "projectsPage": {"background": "#EFF9F0", "secondary": "#DFF1E2"},
        "historyPage": {"background": "#F4F1FB", "secondary": "#E9E2F5"},
        "importsPage": {"background": "#FFF3EC", "secondary": "#F8E5D8"},
        "settingsPage": {"background": "#F2F5F7", "secondary": "#E6EBEF"},
    }
    assert len({palette["background"] for palette in PAGE_PALETTES.values()}) == 6


def test_stylesheet_contains_every_page_selector():
    for object_name, palette in PAGE_PALETTES.items():
        assert f"QWidget#{object_name}" in APP_STYLESHEET
        assert palette["background"] in APP_STYLESHEET


def test_a_style_shell_and_table_rules_are_present():
    expected_rules = (
        "QFrame#topBar {\n    background: #FBFCFE;",
        "QListWidget#navigation {\n    background: #F8FAFD;",
        "QWidget#inventoryPage { background: #EEF5FF; }",
        "selection-background-color: #EAF1FD;",
        "QTableWidget QLineEdit {\n    min-height: 0;\n    padding: 2px 5px;\n    background: #FFFFFF;\n    color: #293C51;\n    border: 1px solid #4D78CF;",
    )
    for rule in expected_rules:
        assert rule in APP_STYLESHEET


def test_workspace_specific_surface_rules_are_present():
    expected_rules = (
        "QWidget#comparisonPage { background: #FFF8E6; }",
        "QTableWidget#comparisonTable {\n    background: #FFFCF4;",
        "QWidget#projectsPage { background: #EFF9F0; }",
        'QTableWidget[projectTable="true"] {\n    background: #FCFEFC;',
        "QWidget#historyPage { background: #F4F1FB; }",
        "QWidget#importsPage { background: #FFF3EC; }",
        "QWidget#settingsPage { background: #F2F5F7; }",
    )
    for rule in expected_rules:
        assert rule in APP_STYLESHEET


def test_dialogs_keep_project_and_attention_semantics():
    expected_rules = (
        "QDialog#importDialog, QDialog#stockDialog {\n    background: #F8FAFD;",
        "QDialog#bomOptimizerDialog { background: #EFF9F0; }",
        "QSpinBox#bomExtraPurchase {\n    color: #76530B;\n    background: #FFF5D7;",
        "QToolButton#projectRowDeleteButton:hover {\n    color: #C2414B;",
    )
    for rule in expected_rules:
        assert rule in APP_STYLESHEET
