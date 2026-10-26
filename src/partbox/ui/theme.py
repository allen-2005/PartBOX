COMMON_COLORS = {
    "app_background": "#F6F8FB",
    "topbar": "#FBFCFE",
    "sidebar": "#F8FAFD",
    "surface": "#FFFFFF",
    "muted_surface": "#EDF2F7",
    "title": "#193857",
    "text": "#293C51",
    "muted_text": "#718197",
    "border": "#D7E1EB",
    "border_soft": "#DCE4EE",
    "accent": "#4D78CF",
    "accent_soft": "#E7EEFB",
    "danger": "#C2414B",
    "project_action": "#FFF5D7",
    "project_action_text": "#76530B",
    "project_action_border": "#E5CA7B",
}

PAGE_PALETTES = {
    "inventoryPage": {"background": "#EEF5FF", "secondary": "#E3EEFC"},
    "comparisonPage": {"background": "#FFF8E6", "secondary": "#F8EDC8"},
    "projectsPage": {"background": "#EFF9F0", "secondary": "#DFF1E2"},
    "historyPage": {"background": "#F4F1FB", "secondary": "#E9E2F5"},
    "importsPage": {"background": "#FFF3EC", "secondary": "#F8E5D8"},
    "settingsPage": {"background": "#F2F5F7", "secondary": "#E6EBEF"},
}


def _page_rules() -> str:
    return "\n".join(
        f"QWidget#{name} {{ background: {colors['background']}; }}"
        for name, colors in PAGE_PALETTES.items()
    )


APP_STYLESHEET = """
QMainWindow, QWidget {
    background: #f8fbff;
    color: #172033;
    font-family: 'Microsoft YaHei UI';
    font-size: 13px;
}
QFrame#topBar {
    background: #f8fbff;
    border-bottom: 1px solid #dbe5f1;
}
QWidget#brandBlock { background: transparent; }
QLabel#brandEnglish {
    color: #2563eb;
    background: transparent;
    font-size: 25px;
    font-weight: 800;
}
QLabel#brandChinese,
QLabel#brandChineseFirst,
QLabel#brandChineseMiddle,
QLabel#brandChineseLast {
    color: #4f7fd9;
    background: transparent;
    font-size: 13px;
    font-weight: 600;
}
QPushButton {
    min-height: 34px;
    padding: 0 14px;
    border: 1px solid #cbd8e8;
    border-radius: 8px;
    background: #ffffff;
    color: #24324a;
}
QPushButton:hover { border-color: #87a9e8; background: #f1f6ff; }
QPushButton:pressed { background: #e8f0ff; }
QPushButton#primary, QPushButton#materialImportButton, QPushButton#stockInButton {
    color: #ffffff;
    background: #2563eb;
    border-color: #2563eb;
    font-weight: 600;
}
QPushButton#primary:hover, QPushButton#materialImportButton:hover, QPushButton#stockInButton:hover { background: #1f57d6; border-color: #1f57d6; }
QPushButton#filterButton { min-height: 34px; padding: 0 16px; }
QPushButton#filterButton:checked {
    color: #1d5bd7;
    background: #eaf2ff;
    border-color: #94b5ef;
    font-weight: 600;
}
QLineEdit, QSpinBox, QComboBox {
    min-height: 36px;
    border: 1px solid #c8d5e6;
    border-radius: 8px;
    background: #ffffff;
    padding: 0 11px;
    selection-background-color: #cfe0ff;
}
QLineEdit:focus, QSpinBox:focus, QComboBox:focus { border-color: #6e98e5; }
QTableWidget QLineEdit {
    min-height: 0;
    padding: 2px 5px;
    background: #ffffff;
    color: #172033;
    border: 2px solid #2563eb;
    border-radius: 5px;
    selection-background-color: #2563eb;
    selection-color: #ffffff;
}
QListWidget#navigation {
    background: #f1f6fc;
    border: 0;
    border-right: 1px solid #dbe5f1;
    padding: 10px 0;
    outline: 0;
}
QListWidget#navigation::item {
    min-height: 44px;
    padding: 4px 14px;
    margin: 3px 10px;
    border-radius: 8px;
    color: #43516a;
    font-size: 16px;
}
QListWidget#navigation::item:hover { background: #eaf1fa; }
QListWidget#navigation::item:selected {
    color: #1f5fd8;
    background: #dfeaff;
    font-weight: 700;
}
QWidget#filterBar { background: transparent; }
QScrollArea#filterScroll { background: transparent; border: 0; }
QScrollArea#filterScroll > QWidget > QWidget { background: transparent; border: 0; }
QFrame#statCard, QFrame#statKindsCard, QFrame#statStockCard, QFrame#statSpentCard, QFrame#statOrdersCard {
    background: #eef4fc;
    border: 1px solid #d5e1ef;
    border-radius: 10px;
}
QFrame#projectImportCard {
    background: #fff4cf;
    border: 1px solid #ead493;
    border-radius: 10px;
}
QPushButton#projectImportButton {
    color: #7c5a08; background: transparent; border: 0;
    font-size: 16px; font-weight: 700; min-height: 48px;
}
QPushButton#projectImportButton:hover { background: #ffedb0; border-radius: 7px; }
QPushButton#projectImportButton:disabled { color: #b9a97d; background: transparent; }
QFrame#summaryPanel {
    background: #f2f6fc;
    border: 1px solid #d5e1ef;
    border-radius: 10px;
}
QPushButton#summaryToggleButton {
    min-width: 24px; max-width: 24px; padding: 0;
    border-radius: 8px; color: #2563eb; font-size: 20px;
    background: #edf3fb;
}
QFrame#projectSidebar {
    background: #f8fbff;
    border: 1px solid #d5e1ef;
    border-radius: 10px;
}
QLabel#projectSidebarTitle {
    color: #172b4d; font-size: 21px; font-weight: 750;
}
QPushButton#projectSidebarToggle {
    min-width: 28px; max-width: 28px; min-height: 28px; max-height: 28px; padding: 0;
    border: 1px solid #cfdbeb; border-radius: 7px;
    color: #2563eb; font-size: 18px; background: #edf3fb;
}
QPushButton#projectSidebarToggle:hover { background: #dfeaff; border-color: #aebfda; }
QListWidget#projectList {
    background: transparent; border: 0; outline: 0; padding: 2px;
}
QListWidget#projectList::item {
    background: #ffffff; border: 1px solid #e0e8f2; border-radius: 8px;
    margin: 3px 1px;
}
QListWidget#projectList::item:hover { background: #f1f6fd; border-color: #c8d7ea; }
QListWidget#projectList::item:selected { background: #e4efff; border-color: #8db4f6; }
QWidget#projectListRow { background: transparent; border: 0; }
QLabel#projectListName { color: #243b5a; font-size: 15px; font-weight: 600; }
QLabel#projectCountBadge {
    min-width: 24px; max-height: 24px; padding: 2px 6px;
    color: #1f5fd8; background: #eaf2ff; border: 1px solid #cbdcf7;
    border-radius: 10px; font-size: 13px; font-weight: 700;
}
QPushButton#projectNewButton {
    color: #1f5fd8; background: #eef4ff; border: 1px solid #b9cff1;
    border-radius: 8px; min-height: 42px; font-size: 15px; font-weight: 700;
}
QPushButton#projectNewButton:hover { background: #dfeaff; border-color: #8fb2ea; }
QPushButton#projectBomButton {
    color: #7c5a08; background: #fff4cf; border: 1px solid #dfc36d;
    border-radius: 8px; min-height: 42px; font-size: 14px; font-weight: 700;
}
QPushButton#projectBomButton:hover { background: #ffedb0; border-color: #cda943; }
QWidget#projectsPage { background: #fffdf5; }
QLabel#pageTitle { color: #172b4d; font-size: 21px; font-weight: 750; }
QLabel#projectTitle, QLabel#sectionTitle { color: #3f3a2c; font-size: 16px; font-weight: 700; }
QLabel#projectTotal {
    color: #7c5a08; background: #fff4cf; border: 1px solid #ead493;
    border-radius: 8px; padding: 7px 12px; font-size: 16px; font-weight: 750;
}
QPushButton#projectSaveButton {
    color: #7c5a08; background: #fff4cf; border: 1px solid #dfc36d;
    border-radius: 8px; min-height: 36px; padding: 7px 14px; font-weight: 700;
}
QPushButton#projectSaveButton:hover { background: #ffedb0; border-color: #cda943; }
QPushButton#projectSaveButton:disabled {
    color: #a69770; background: #faf3de; border-color: #e5d9b4;
}
QTableWidget[projectTable="true"] {
    background: #fffdf6; alternate-background-color: #fff8df;
    selection-background-color: #ffedb0; border-color: #eadcad;
}
QTableWidget[projectTable="true"] QHeaderView::section { background: #f9edc9; border-color: #e6d6a5; }
QTableWidget[projectTable="true"] QLineEdit {
    color: #172033; background: #fffdf4; border: 1px solid #d5a82f;
    border-radius: 4px; padding: 2px 5px; selection-background-color: #2563eb;
}
QToolButton#projectRowDeleteButton {
    background: transparent; border: 0; border-radius: 5px; padding: 5px;
}
QToolButton#projectRowDeleteButton:hover { background: #fee2e2; }
QToolButton#projectRowDeleteButton:pressed { background: #fecaca; }
QWidget#projectQuantityStepper {
    background: #fffaf0; border: 1px solid #dcc98d; border-radius: 5px;
}
QLabel#projectQuantityValue {
    background: transparent; color: #172033; border: 0; font-size: 14px;
}
QToolButton#projectQuantityIncrease, QToolButton#projectQuantityDecrease {
    background: transparent; color: #26364f; border: 0; border-left: 1px solid #d8c58a;
    border-radius: 0; padding: 0; margin: 0; font-size: 10px;
}
QToolButton#projectQuantityIncrease:hover, QToolButton#projectQuantityDecrease:hover {
    color: #1f5fd8; background: #fff0bd;
}
QToolButton#projectQuantityIncrease:pressed, QToolButton#projectQuantityDecrease:pressed {
    background: #ffe69b;
}
QToolButton#projectQuantityDecrease:disabled {
    color: #bcc3ce; background: transparent;
}
QWidget#comparisonPage { background: #eef5ff; }
QLabel#comparisonTitle { color: #17345e; font-size: 22px; font-weight: 750; }
QLabel#comparisonChartTitle { color: #294b7d; font-size: 16px; font-weight: 700; }
QLabel#comparisonEmpty {
    color: #60738d; background: #eef5ff; border: 1px dashed #b9cbe2;
    border-radius: 10px; padding: 28px;
}
QTableWidget#comparisonTable {
    background: #eef5ff; alternate-background-color: #eef5ff;
    border-color: #c8d9ed;
}
QTableWidget#comparisonTable QHeaderView::section { background: #e3eefb; }
QWidget#comparisonPriceChart { background: #eef5ff; border: 1px solid #c8d9ed; border-radius: 9px; }
QDialog#importDialog, QDialog#stockDialog, QDialog#bomOptimizerDialog { background: #f8fbff; }
QLabel#bomOptimizerHeading { color: #17345e; font-size: 22px; font-weight: 750; }
QLabel#bomOptimizerStep {
    color: #1f5fd8; background: #e7f0ff; border: 1px solid #bfd3f3;
    border-radius: 12px; padding: 7px 12px; font-weight: 700;
}
QFrame#bomSetupPage, QFrame#bomCandidatePanel {
    background: #eef5ff; border: 1px solid #cfdeef; border-radius: 10px;
}
QLabel#bomHint { color: #60738d; }
QLabel#bomPanelTitle { color: #17345e; font-size: 16px; font-weight: 700; }
QLabel#bomMatchSummary, QLabel#bomReviewSummary {
    color: #294b7d; background: #eef5ff; border: 1px solid #cfdeef;
    border-radius: 8px; padding: 10px 12px; font-weight: 650;
}
QPushButton#bomAcceptCandidateButton, QPushButton#bomNextButton, QPushButton#bomExportButton {
    color: #ffffff; background: #2563eb; border-color: #2563eb; font-weight: 700;
}
QPushButton#bomRejectCandidatesButton {
    color: #8a5b05; background: #fff4cf; border-color: #dfc36d; font-weight: 700;
}
QSpinBox#bomExtraPurchase {
    background: #fff4cf; border-color: #dfc36d; color: #7c5a08; font-weight: 700;
}
QLabel#dialogHeading { color: #152b4d; font-size: 21px; font-weight: 750; }
QLabel#importSummary, QLabel#importHint { color: #53627a; }
QFrame#importStats { background: transparent; }
QFrame#importStatCard {
    background: #eef4fc;
    border: 1px solid #d5e1ef;
    border-radius: 9px;
}
QLabel#importStatValue { color: #17345e; font-size: 20px; font-weight: 750; }
QTableWidget#importPreviewTable { border-radius: 9px; }
QLabel#stockDialogTitle {
    min-width: 48px;
    padding: 5px 10px;
    color: #ffffff;
    background: #2563eb;
    border-radius: 7px;
    font-weight: 700;
}
QLabel#stockDialogTitle[mode="out"] { background: #5c7191; }
QLabel#stockComponentName { color: #172b4d; font-size: 18px; font-weight: 700; }
QFrame#stockInfoCard, QFrame#stockPreviewCard {
    background: #eef4fc;
    border: 1px solid #d3e0ef;
    border-radius: 10px;
}
QLabel#currentStockValue { color: #2563eb; font-size: 22px; font-weight: 750; }
QLabel#stockPreviewValue { color: #17345e; font-size: 20px; font-weight: 700; }
QLabel#fieldLabel { color: #4d5d76; font-weight: 600; }
QSpinBox#stockQuantity { font-size: 17px; font-weight: 600; }
QLabel#statValue, QLabel#statKindsValue, QLabel#statStockValue, QLabel#statSpentValue, QLabel#statOrdersValue {
    background: transparent;
    color: #13294b;
    font-size: 25px;
    font-weight: 750;
}
QLabel { background: transparent; }
QLabel#muted,
QLabel#statKindsLabel, QLabel#statStockLabel, QLabel#statSpentLabel, QLabel#statOrdersLabel,
QLabel#summaryProductCodeLabel, QLabel#summaryProductTypeLabel, QLabel#summaryPackageLabel,
QLabel#summaryBrandLabel, QLabel#summaryCurrentStockLabel, QLabel#summaryLatestOrderTimeLabel,
QLabel#summaryLocationLabel { background: transparent; color: #66758d; }
QLabel#statKindsLabel, QLabel#statStockLabel, QLabel#statSpentLabel, QLabel#statOrdersLabel {
    color: #294b7d; font-size: 15px; font-weight: 700;
}
QTableWidget {
    background: #ffffff;
    alternate-background-color: #f7f9fc;
    border: 1px solid #d6e0ec;
    border-radius: 9px;
    gridline-color: #e3eaf2;
    selection-background-color: #dfeaff;
    selection-color: #172033;
    outline: 0;
}
QTableWidget::item { padding: 4px; }
QHeaderView::section {
    background: #eaf0f7;
    color: #34435b;
    padding: 8px;
    border: 0;
    border-right: 1px solid #d4deea;
    border-bottom: 1px solid #cbd7e5;
    font-weight: 600;
}
QHeaderView::up-arrow, QHeaderView::down-arrow { image: none; width: 0; height: 0; }
QHeaderView::indicator {
    width: 17px; height: 17px; border: 2px solid #4d88ed;
    border-radius: 4px; background: #ffffff;
}
QHeaderView::indicator:checked { background: #2563eb; border-color: #2563eb; }
QSplitter::handle { background: #e3eaf3; }
QSplitter::handle:horizontal { width: 5px; }
QSplitter::handle:vertical { height: 5px; }
QSplitter::handle:hover { background: #b9cbe2; }
QScrollBar:vertical {
    background: #edf2f7;
    width: 22px;
    margin: 1px;
    border: 0;
    border-radius: 10px;
}
QScrollBar::handle:vertical {
    background: #aabbd0;
    min-height: 34px;
    border-radius: 10px;
    margin: 2px;
}
QScrollBar::handle:vertical:hover { background: #829ab7; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }
QScrollBar:horizontal {
    background: #edf2f7;
    height: 22px;
    margin: 1px;
    border: 0;
    border-radius: 10px;
}
QScrollBar::handle:horizontal {
    background: #aabbd0;
    min-width: 34px;
    border-radius: 10px;
    margin: 2px;
}
QScrollBar::handle:horizontal:hover { background: #829ab7; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal { background: transparent; }
QTabWidget::pane { border: 0; }
"""

APP_STYLESHEET += "\n" + _page_rules()

APP_STYLESHEET += """
QMainWindow, QWidget {
    background: #F6F8FB;
    color: #293C51;
    font-family: 'Microsoft YaHei UI';
    font-size: 13px;
}
QFrame#topBar {
    background: #FBFCFE;
    border-bottom: 1px solid #DCE4EE;
}
QWidget#brandBlock, QLabel#brandEnglish, QWidget#brandChinese, QLabel#brandChineseLogo {
    background: transparent;
}
QListWidget#navigation {
    background: #F8FAFD;
    border: 0;
    border-right: 1px solid #DCE4EE;
    padding: 12px 0;
    outline: 0;
}
QListWidget#navigation::item {
    min-height: 40px;
    padding: 2px 12px;
    margin: 3px 10px;
    border-radius: 8px;
    color: #53677F;
    font-size: 14px;
}
QListWidget#navigation::item:hover { background: #EEF3F9; }
QListWidget#navigation::item:selected {
    color: #315FAE;
    background: #E7EEFB;
    font-weight: 600;
}
QPushButton {
    min-height: 34px;
    padding: 0 12px;
    border: 1px solid #CED9E6;
    border-radius: 8px;
    background: #FFFFFF;
    color: #293C51;
}
QPushButton:hover { border-color: #9CB5D5; background: #F4F7FB; }
QPushButton:pressed { border-color: #7F9FC8; background: #EAF0F8; }
QPushButton:focus { border: 1px solid #4D78CF; }
QPushButton:disabled { color: #9AA8B8; background: #F3F5F8; border-color: #E1E6EC; }
QPushButton#primary, QPushButton#materialImportButton, QPushButton#stockInButton {
    color: #FFFFFF;
    background: #4D78CF;
    border-color: #4D78CF;
    font-weight: 600;
}
QPushButton#primary:hover, QPushButton#materialImportButton:hover, QPushButton#stockInButton:hover {
    background: #426AB8;
    border-color: #426AB8;
}
QLineEdit, QSpinBox, QComboBox {
    min-height: 36px;
    border: 1px solid #CED9E6;
    border-radius: 8px;
    background: #FFFFFF;
    color: #293C51;
    padding: 0 11px;
    selection-background-color: #CFE0FF;
}
QLineEdit:focus, QSpinBox:focus, QComboBox:focus { border: 1px solid #4D78CF; }
QWidget#inventoryPage { background: #EEF5FF; }
QWidget#filterBar, QScrollArea#filterScroll, QScrollArea#filterScroll > QWidget > QWidget {
    background: transparent;
    border: 0;
}
QPushButton#filterButton { min-height: 32px; padding: 0 12px; }
QPushButton#filterButton:checked {
    color: #315FAE;
    background: #E7EEFB;
    border-color: #B9CBED;
    font-weight: 600;
}
QFrame#statCard, QFrame#statKindsCard, QFrame#statStockCard,
QFrame#statSpentCard, QFrame#statOrdersCard {
    background: #F8FBFF;
    border: 1px solid #D7E1EB;
    border-radius: 10px;
}
QFrame#projectImportCard {
    background: #FFF5D7;
    border: 1px solid #E5CA7B;
    border-radius: 10px;
}
QPushButton#projectImportButton {
    color: #76530B;
    background: transparent;
    border: 0;
    font-size: 15px;
    font-weight: 700;
}
QWidget#comparisonAddCard {
    background: #FFFFFF;
    border: 1px solid #D7E1EB;
    border-radius: 10px;
}
QPushButton#comparisonAddButton {
    color: #315FAE;
    background: transparent;
    border: 0;
    font-weight: 700;
}
QFrame#summaryPanel {
    background: #F8FBFF;
    border: 1px solid #D7E1EB;
    border-radius: 10px;
}
QTableWidget {
    background: #FFFFFF;
    alternate-background-color: #FAFBFD;
    border: 1px solid #D7E1EB;
    border-radius: 8px;
    gridline-color: #E5EBF1;
    selection-background-color: #EAF1FD;
    selection-color: #293C51;
    outline: 0;
}
QTableWidget::item { padding: 4px 7px; }
QHeaderView::section {
    background: #EDF2F7;
    color: #4C6078;
    padding: 7px 8px;
    border: 0;
    border-right: 1px solid #D7E1EB;
    border-bottom: 1px solid #D3DEE8;
    font-weight: 600;
}
QTableWidget QLineEdit {
    min-height: 0;
    padding: 2px 5px;
    background: #FFFFFF;
    color: #293C51;
    border: 1px solid #4D78CF;
    border-radius: 5px;
    selection-background-color: #4D78CF;
    selection-color: #FFFFFF;
}
QScrollBar:vertical, QScrollBar:horizontal { background: #EDF2F7; border: 0; }
QScrollBar::handle:vertical, QScrollBar::handle:horizontal { background: #AABBD0; border-radius: 6px; }
QScrollBar::handle:vertical:hover, QScrollBar::handle:horizontal:hover { background: #829AB7; }

QWidget#comparisonPage { background: #FFF8E6; }
QTableWidget#comparisonTable {
    background: #FFFCF4;
    alternate-background-color: #FFFCF4;
    border-color: #E8DDBD;
    selection-background-color: #F8EDC8;
}
QWidget#comparisonPriceChart {
    background: #FFFCF4;
    border: 1px solid #E8DDBD;
    border-radius: 8px;
}
QLabel#comparisonEmpty {
    color: #6E654E;
    background: #FFFCF4;
    border: 1px dashed #D9C99F;
    border-radius: 8px;
    padding: 24px;
}

QWidget#projectsPage { background: #EFF9F0; }
QFrame#projectSidebar {
    background: #F8FCF8;
    border: 1px solid #CFE3D2;
    border-radius: 10px;
}
QListWidget#projectList {
    background: transparent;
    border: 0;
    outline: 0;
}
QListWidget#projectList::item {
    min-height: 34px;
    margin: 2px 0;
    padding: 0 9px;
    border: 1px solid transparent;
    border-radius: 7px;
}
QListWidget#projectList::item:hover { background: #EFF7F0; }
QListWidget#projectList::item:selected {
    color: #285E34;
    background: #DFF1E2;
    border-color: #A8CFAD;
    font-weight: 600;
}
QTableWidget[projectTable="true"] {
    background: #FCFEFC;
    alternate-background-color: #F3FAF4;
    selection-background-color: #DFF1E2;
    border-color: #CFE3D2;
}
QTableWidget[projectTable="true"] QHeaderView::section {
    background: #E8F4EA;
    border-color: #CFE3D2;
}
QPushButton#projectSaveButton {
    color: #285E34;
    background: #E5F4E7;
    border-color: #AFCFB4;
    font-weight: 600;
}

QWidget#historyPage { background: #F4F1FB; }
QTableWidget#historyTable {
    border-color: #DCD4EA;
    selection-background-color: #E9E2F5;
}
QWidget#importsPage { background: #FFF3EC; }
QTableWidget#importsTable, QTableWidget#purchaseDetailsTable {
    border-color: #E8D7CB;
    selection-background-color: #F8E5D8;
}
QWidget#settingsPage { background: #F2F5F7; }

QDialog#importDialog, QDialog#stockDialog {
    background: #F8FAFD;
}
QDialog#bomOptimizerDialog { background: #EFF9F0; }
QFrame#bomSetupPage, QFrame#bomCandidatePanel {
    background: #F8FCF8;
    border: 1px solid #CFE3D2;
    border-radius: 10px;
}
QLabel#bomMatchSummary, QLabel#bomReviewSummary {
    color: #315C39;
    background: #F8FCF8;
    border: 1px solid #CFE3D2;
    border-radius: 8px;
    padding: 10px 12px;
}
QPushButton#bomRejectCandidatesButton {
    color: #76530B;
    background: #FFF5D7;
    border-color: #E5CA7B;
}
QSpinBox#bomExtraPurchase {
    color: #76530B;
    background: #FFF5D7;
    border-color: #E5CA7B;
    font-weight: 600;
}
QToolButton#projectRowDeleteButton:hover {
    color: #C2414B;
    background: #FDECEE;
}
"""
