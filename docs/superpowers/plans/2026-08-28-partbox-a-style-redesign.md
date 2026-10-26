# PartBOX A 风格全界面改造 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 PartBOX 改造成用户确认的 A 风格柔和工作台，并为六个页面分别应用淡蓝、淡黄、浅绿、淡紫灰、淡杏和浅灰蓝识别色，不改变任何业务行为。

**Architecture:** 保留 PySide6、Qt Designer `.ui` 加载机制和现有页面类。`theme.py` 继续作为全应用唯一 QSS 入口，同时新增可测试的公共令牌与页面色板；页面类只负责稳定的 `objectName` 和结构，不在组件内部保留零散颜色。主窗口几何由 `main_window.ui` 与品牌图片配置共同控制。

**Tech Stack:** Python 3.10+、PySide6、Qt Designer `.ui`、pytest、pytest-qt。

## Global Constraints

- 保留所有现有数据库结构、业务规则、字段内容、排序键、选择集合、保存时机和确认流程。
- 保留 `assets/partbox-wordmark-v1.png` 与 `assets/partbox-chinese-wordmark-v1.png`，不得替换为普通字体。
- 元件库存 `#EEF5FF`，物料对比 `#FFF8E6`，我的项目 `#EFF9F0`，库存流水 `#F4F1FB`，导入记录 `#FFF3EC`，设置 `#F2F5F7`。
- 顶栏、导航、字体、间距、圆角、控件状态和品牌蓝交互规则在所有页面保持一致。
- 不引入网络依赖、在线字体、新前端框架或新的图标包。
- 现有工作区包含大量用户修改；每次只暂存当前任务明确列出的文件，不回退其他文件。
- Git 未配置 `user.name`／`user.email` 时，保留改动并报告，禁止编造提交身份。

---

### Task 1: 建立可测试的 A 风格令牌和页面身份

**Files:**
- Modify: `src/partbox/ui/theme.py`
- Modify: `src/partbox/ui/aux_pages.py`
- Create: `tests/test_theme.py`

**Interfaces:**
- Consumes: 现有 `APP_STYLESHEET: str` 导入接口。
- Produces: `COMMON_COLORS: dict[str, str]`、`PAGE_PALETTES: dict[str, dict[str, str]]`，以及六个页面稳定的 `objectName`。

- [ ] **Step 1: 运行当前全量测试建立基线**

Run: `python -m pytest -q`

Expected: exit code 0；所有现有测试通过或仅保留仓库已有的 skip。

- [ ] **Step 2: 写入令牌与页面身份的失败测试**

Create `tests/test_theme.py`:

```python
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
    assert len({p["background"] for p in PAGE_PALETTES.values()}) == 6


def test_stylesheet_contains_every_page_selector():
    for object_name, palette in PAGE_PALETTES.items():
        assert f"QWidget#{object_name}" in APP_STYLESHEET
        assert palette["background"] in APP_STYLESHEET
```

- [ ] **Step 3: 运行测试确认失败**

Run: `python -m pytest tests/test_theme.py -q`

Expected: FAIL，提示无法从 `partbox.ui.theme` 导入 `COMMON_COLORS` 或 `PAGE_PALETTES`。

- [ ] **Step 4: 在主题入口定义公共令牌与六页色板**

Add at the beginning of `src/partbox/ui/theme.py`:

```python
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
```

Keep the existing stylesheet as an ordinary triple-quoted string. Immediately after its existing closing delimiter, append the generated page rules:

```python
APP_STYLESHEET += "\n" + _page_rules()
```

Do not convert the QSS to an f-string because its CSS braces would be interpreted by Python. Keep `APP_STYLESHEET` as a string so existing imports do not change.

- [ ] **Step 5: 给辅助页面和表格添加稳定对象名**

Update constructors in `src/partbox/ui/aux_pages.py`:

```python
class HistoryPage(QWidget):
    def __init__(self, data: DataService, stocks: StockService):
        super().__init__()
        self.setObjectName("historyPage")
        self.data = data
        self.stocks = stocks
        layout = QVBoxLayout(self)
        title = QLabel("库存流水", objectName="pageTitle")
        layout.addWidget(title)
        self.table = QTableWidget(0, 10, objectName="historyTable")


class ImportsPage(QWidget):
    def __init__(self, data: DataService):
        super().__init__()
        self.setObjectName("importsPage")
        self.data = data
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("导入记录", objectName="pageTitle"))
        self.table = QTableWidget(0, 8, objectName="importsTable")
        self.purchase_table = QTableWidget(0, 25, objectName="purchaseDetailsTable")


class SettingsPage(QWidget):
    def __init__(self, data: DataService, default_backup_dir: Path):
        super().__init__()
        self.setObjectName("settingsPage")
        self.data = data
        self.default_backup_dir = Path(default_backup_dir)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("设置与数据安全", objectName="pageTitle"))
```

Keep all existing signals, table headers, refresh calls and button callbacks unchanged.

- [ ] **Step 6: 运行聚焦测试和辅助页测试**

Run: `python -m pytest tests/test_theme.py tests/test_auxiliary.py -q`

Expected: PASS。

- [ ] **Step 7: 提交任务**

```bash
git add src/partbox/ui/theme.py src/partbox/ui/aux_pages.py tests/test_theme.py
git commit -m "style(ui): add page color identities"
```

Expected: commit succeeds；若仅因 Git 身份缺失而失败，立即 `git restore --staged` 撤回本任务暂存并保留工作区修改。

### Task 2: 将主窗口外壳和库存页改造成 A 风格

**Files:**
- Modify: `src/partbox/ui/forms/main_window.ui`
- Modify: `src/partbox/ui/main_window.py`
- Modify: `src/partbox/ui/theme.py`
- Modify: `tests/test_designer_ui.py`
- Modify: `tests/test_ui_smoke.py`

**Interfaces:**
- Consumes: Task 1 的 `COMMON_COLORS`、`PAGE_PALETTES` 和现有 `.ui` 必需对象名。
- Produces: 88px 顶栏、180px 品牌区、48px 搜索框、168px 导航、淡蓝库存工作区，以及平滑清晰的艺术字缩放。

- [ ] **Step 1: 写入主窗口几何和库存页色调的失败测试**

Append to `tests/test_designer_ui.py`:

```python
from PySide6.QtWidgets import QFrame, QLineEdit, QListWidget, QWidget


def test_a_style_shell_geometry(qtbot):
    loaded, _ = load_main_ui()
    qtbot.addWidget(loaded)
    assert loaded.findChild(QFrame, "topBar").minimumHeight() == 88
    assert loaded.findChild(QLineEdit, "searchInput").minimumHeight() == 48
    assert loaded.findChild(QListWidget, "navigation").minimumWidth() == 168
    assert loaded.findChild(QWidget, "inventoryPage").objectName() == "inventoryPage"
```

Append to `tests/test_ui_smoke.py`:

```python
def test_main_window_uses_clear_artwork_geometry(qtbot, tmp_path):
    db = Database(tmp_path / "a-style.db")
    db.initialize()
    services = ServiceContainer(db, InventoryService(db), ImportService(db), StockService(db))
    window = MainWindow(services, QSettings(str(tmp_path / "a-style.ini"), QSettings.IniFormat))
    qtbot.addWidget(window)
    assert window.findChild(QFrame, "topBar").height() == 88
    assert window.findChild(QWidget, "brandBlock").width() == 180
    assert window.findChild(QLabel, "brandEnglish").pixmap() is not None
    assert window.findChild(QLabel, "brandChineseLogo").pixmap() is not None
```

- [ ] **Step 2: 运行测试确认失败**

Run: `python -m pytest tests/test_designer_ui.py::test_a_style_shell_geometry tests/test_ui_smoke.py::test_main_window_uses_clear_artwork_geometry -q`

Expected: FAIL，现有顶栏为 86px／运行时 108px，品牌区为 208px，搜索框为 54px。

- [ ] **Step 3: 调整 Qt Designer 主窗口布局**

In `src/partbox/ui/forms/main_window.ui` set these exact properties while retaining every existing `objectName`:

```xml
<widget class="QFrame" name="topBar">
 <property name="minimumSize"><size><width>0</width><height>88</height></size></property>
 <property name="maximumSize"><size><width>16777215</width><height>88</height></size></property>
 <layout class="QHBoxLayout" name="topBarLayout">
  <property name="spacing"><number>20</number></property>
  <property name="leftMargin"><number>24</number></property>
  <property name="topMargin"><number>12</number></property>
  <property name="rightMargin"><number>20</number></property>
  <property name="bottomMargin"><number>12</number></property>
```

Set `brandBlock` min/max width to 180, `searchInput` min/max height to 48, `inventoryLayout` margins to 16, and `filterRow` spacing to 6. Preserve the 168px navigation, 86px equal statistic cards, 36px table row contract and all existing summary controls.

- [ ] **Step 4: 使用高质量缩放展示艺术字**

Replace the sizing portion of `_configure_brand_artwork` in `src/partbox/ui/main_window.py`:

```python
LOGO_WIDTH = 172


def _set_logo(label: QLabel, source: QPixmap, width: int) -> None:
    scaled = source.scaled(
        width,
        10_000,
        Qt.KeepAspectRatio,
        Qt.SmoothTransformation,
    )
    label.setFixedSize(scaled.size())
    label.setScaledContents(False)
    label.setPixmap(scaled)


# inside _configure_brand_artwork
top_bar.setFixedHeight(88)
top_bar_layout.setSpacing(20)
top_bar_layout.setContentsMargins(24, 12, 20, 12)
brand_block.setFixedWidth(180)
brand_english.clear()
_set_logo(brand_english, english, LOGO_WIDTH)

chinese_layout = brand_chinese.layout()
while chinese_layout.count():
    item = chinese_layout.takeAt(0)
    if item.widget() is not None:
        item.widget().hide()
chinese_label = QLabel(brand_chinese, objectName="brandChineseLogo")
_set_logo(chinese_label, chinese, LOGO_WIDTH)
brand_chinese.setFixedSize(chinese_label.size())
chinese_layout.addWidget(chinese_label)
```

Remove the duplicated `chinese_label = QLabel(brand_chinese)` assignment. Keep `trimmed_logo_pixmap()` and asset lookup behavior unchanged.

- [ ] **Step 5: 重写公共外壳、库存、表格和状态 QSS**

Update the corresponding selectors in `src/partbox/ui/theme.py` to these values:

```css
QMainWindow, QWidget { background: #F6F8FB; color: #293C51; font-family: 'Microsoft YaHei UI'; font-size: 13px; }
QFrame#topBar { background: #FBFCFE; border-bottom: 1px solid #DCE4EE; }
QListWidget#navigation { background: #F8FAFD; border: 0; border-right: 1px solid #DCE4EE; padding: 12px 0; outline: 0; }
QListWidget#navigation::item { min-height: 40px; padding: 2px 12px; margin: 3px 10px; border-radius: 8px; color: #53677F; font-size: 14px; }
QListWidget#navigation::item:selected { color: #315FAE; background: #E7EEFB; font-weight: 600; }
QWidget#inventoryPage { background: #EEF5FF; }
QPushButton { min-height: 34px; padding: 0 12px; border: 1px solid #CED9E6; border-radius: 8px; background: #FFFFFF; color: #293C51; }
QPushButton:hover { border-color: #9CB5D5; background: #F4F7FB; }
QPushButton:focus { border: 1px solid #4D78CF; }
QTableWidget { background: #FFFFFF; alternate-background-color: #FAFBFD; border: 1px solid #D7E1EB; border-radius: 8px; gridline-color: #E5EBF1; selection-background-color: #EAF1FD; selection-color: #293C51; outline: 0; }
QHeaderView::section { background: #EDF2F7; color: #4C6078; padding: 7px 8px; border: 0; border-right: 1px solid #D7E1EB; border-bottom: 1px solid #D3DEE8; font-weight: 600; }
QTableWidget QLineEdit { border: 1px solid #4D78CF; border-radius: 5px; }
```

Set statistic cards to white or `#F8FBFF` with `#D7E1EB` borders; keep `projectImportCard` at `#FFF5D7`. Style `comparisonAddCard` with white background and blue text so yellow remains reserved for importing to a project.

- [ ] **Step 6: 运行主窗口和交互回归测试**

Run: `python -m pytest tests/test_designer_ui.py tests/test_ui_smoke.py tests/test_inventory_header.py -q`

Expected: PASS；排序、Shift 选择、列设置、摘要折叠和项目导入测试全部通过。

- [ ] **Step 7: 提交任务**

```bash
git add src/partbox/ui/forms/main_window.ui src/partbox/ui/main_window.py src/partbox/ui/theme.py tests/test_designer_ui.py tests/test_ui_smoke.py
git commit -m "style(ui): apply A-style inventory shell"
```

### Task 3: 应用六页独立柔和色调并统一项目、对比与辅助页

**Files:**
- Modify: `src/partbox/ui/theme.py`
- Modify: `src/partbox/ui/projects_page.py`
- Modify: `src/partbox/ui/comparison_page.py`
- Modify: `src/partbox/ui/aux_pages.py`
- Modify: `tests/test_projects_ui.py`
- Modify: `tests/test_comparison_ui.py`
- Modify: `tests/test_auxiliary.py`

**Interfaces:**
- Consumes: Task 1 的页面对象名与色板。
- Produces: 比对淡黄、项目浅绿、流水淡紫灰、导入淡杏、设置浅灰蓝，并保持公共控件语法一致。

- [ ] **Step 1: 写入页面身份和局部样式清理测试**

Append to `tests/test_projects_ui.py`:

```python
def test_project_page_exposes_green_workspace_identity(qtbot, tmp_path):
    db = Database(tmp_path / "project-theme.db")
    db.initialize()
    page = ProjectsPage(ProjectService(db))
    qtbot.addWidget(page)
    assert page.objectName() == "projectsPage"
    assert page.component_table.property("projectTable") is True
```

Append to `tests/test_comparison_ui.py`:

```python
def test_comparison_page_exposes_yellow_workspace_identity(qtbot, tmp_path):
    db = Database(tmp_path / "comparison-theme.db")
    db.initialize()
    page = ComparisonPage(ComparisonService(db))
    qtbot.addWidget(page)
    assert page.objectName() == "comparisonPage"
```

Add these imports and this test to `tests/test_auxiliary.py`:

```python
from PySide6.QtWidgets import QLabel

from partbox.ui.aux_pages import HistoryPage, ImportsPage, SettingsPage


def test_auxiliary_pages_expose_distinct_workspace_identities(qtbot, tmp_path):
    db = Database(tmp_path / "aux-theme.db")
    db.initialize()
    data = DataService(db)
    pages = (
        HistoryPage(data, StockService(db)),
        ImportsPage(data),
        SettingsPage(data, tmp_path / "backups"),
    )
    for page in pages:
        qtbot.addWidget(page)
    assert [page.objectName() for page in pages] == [
        "historyPage", "importsPage", "settingsPage"
    ]
    for page in pages:
        title = page.findChild(QLabel, "pageTitle")
        assert title is not None
        assert title.styleSheet() == ""
```

- [ ] **Step 2: 运行聚焦测试确认至少一个失败**

Run: `python -m pytest tests/test_projects_ui.py tests/test_comparison_ui.py tests/test_auxiliary.py -q`

Expected: FAIL until auxiliary page object names and inline title styles are removed.

- [ ] **Step 3: 统一页面布局间距和对象名**

Use these exact margins without changing callbacks:

```python
# comparison_page.py
layout.setContentsMargins(16, 16, 16, 16)
layout.setSpacing(10)

# projects_page.py
root.setContentsMargins(16, 16, 16, 16)
root.setSpacing(10)
right_layout.setContentsMargins(8, 0, 0, 0)

# aux_pages.py, for all three pages
layout.setContentsMargins(16, 16, 16, 16)
layout.setSpacing(10)
```

Remove only inline `title.setStyleSheet(...)` declarations. Preserve project sidebar width/collapse behavior, right-click menu, new-project location, tables and button ordering.

- [ ] **Step 4: 添加页面专属 QSS 规则**

Add or replace these selectors in `src/partbox/ui/theme.py`:

```css
QWidget#comparisonPage { background: #FFF8E6; }
QTableWidget#comparisonTable { background: #FFFCF4; alternate-background-color: #FFFCF4; border-color: #E8DDBD; selection-background-color: #F8EDC8; }
QWidget#comparisonPriceChart { background: #FFFCF4; border: 1px solid #E8DDBD; border-radius: 8px; }
QLabel#comparisonEmpty { color: #6E654E; background: #FFFCF4; border: 1px dashed #D9C99F; border-radius: 8px; padding: 24px; }

QWidget#projectsPage { background: #EFF9F0; }
QFrame#projectSidebar { background: #F8FCF8; border: 1px solid #CFE3D2; border-radius: 10px; }
QListWidget#projectList::item:selected { background: #DFF1E2; border-color: #A8CFAD; }
QTableWidget[projectTable="true"] { background: #FCFEFC; alternate-background-color: #F3FAF4; selection-background-color: #DFF1E2; border-color: #CFE3D2; }
QTableWidget[projectTable="true"] QHeaderView::section { background: #E8F4EA; border-color: #CFE3D2; }
QPushButton#projectSaveButton { color: #285E34; background: #E5F4E7; border-color: #AFCFB4; }

QWidget#historyPage { background: #F4F1FB; }
QTableWidget#historyTable { border-color: #DCD4EA; selection-background-color: #E9E2F5; }
QWidget#importsPage { background: #FFF3EC; }
QTableWidget#importsTable, QTableWidget#purchaseDetailsTable { border-color: #E8D7CB; selection-background-color: #F8E5D8; }
QWidget#settingsPage { background: #F2F5F7; }
```

Keep the blue focus ring on all pages. Keep destructive actions red and project-import actions pale yellow.

- [ ] **Step 5: 运行页面测试**

Run: `python -m pytest tests/test_projects_ui.py tests/test_comparison_ui.py tests/test_auxiliary.py tests/test_theme.py -q`

Expected: PASS。

- [ ] **Step 6: 提交任务**

```bash
git add src/partbox/ui/theme.py src/partbox/ui/projects_page.py src/partbox/ui/comparison_page.py src/partbox/ui/aux_pages.py tests/test_projects_ui.py tests/test_comparison_ui.py tests/test_auxiliary.py
git commit -m "style(ui): differentiate workspace palettes"
```

### Task 4: 统一 BOM、导入和库存弹窗的 A 风格状态

**Files:**
- Modify: `src/partbox/ui/theme.py`
- Modify: `tests/test_theme.py`
- Verify: `src/partbox/ui/bom_optimizer.py`
- Verify: `src/partbox/ui/import_dialog.py`
- Verify: `src/partbox/ui/stock_dialog.py`
- Verify: `tests/test_bom_optimizer_ui.py`
- Verify: `tests/test_dialogs.py`

**Interfaces:**
- Consumes: 公共品牌蓝、项目浅绿和补货淡黄色语义。
- Produces: 与六页一致的弹窗表面、按钮、焦点、禁用和危险状态，不改变向导步骤或库存写入逻辑。

- [ ] **Step 1: 写入弹窗语义色失败测试**

Append to `tests/test_theme.py`:

```python
def test_dialog_styles_keep_project_and_attention_semantics():
    assert "QDialog#bomOptimizerDialog { background: #EFF9F0; }" in APP_STYLESHEET
    assert "QSpinBox#bomExtraPurchase" in APP_STYLESHEET
    assert "background: #FFF5D7" in APP_STYLESHEET
    assert "QDialog#importDialog, QDialog#stockDialog { background: #F8FAFD; }" in APP_STYLESHEET
```

- [ ] **Step 2: 运行测试确认失败**

Run: `python -m pytest tests/test_theme.py::test_dialog_styles_keep_project_and_attention_semantics -q`

Expected: FAIL，因为现有 BOM 对话框背景仍是通用 `#F8FBFF`。

- [ ] **Step 3: 核对现有弹窗对象契约**

Run:

```powershell
rg -n 'setObjectName\("(importDialog|stockDialog|bomOptimizerDialog)"\)' src/partbox/ui/import_dialog.py src/partbox/ui/stock_dialog.py src/partbox/ui/bom_optimizer.py
```

Expected: 三个对象名各出现一次。不要修改现有字段顺序、按钮顺序、布局尺寸或信号连接。

- [ ] **Step 4: 用主题 QSS 统一弹窗状态**

Apply these exact rules in `src/partbox/ui/theme.py`:

```css
QDialog#importDialog, QDialog#stockDialog { background: #F8FAFD; }
QDialog#bomOptimizerDialog { background: #EFF9F0; }
QFrame#bomSetupPage, QFrame#bomCandidatePanel { background: #F8FCF8; border: 1px solid #CFE3D2; border-radius: 10px; }
QLabel#bomMatchSummary, QLabel#bomReviewSummary { color: #315C39; background: #F8FCF8; border: 1px solid #CFE3D2; border-radius: 8px; padding: 10px 12px; }
QSpinBox#bomExtraPurchase { color: #76530B; background: #FFF5D7; border-color: #E5CA7B; font-weight: 600; }
QPushButton#bomRejectCandidatesButton { color: #76530B; background: #FFF5D7; border-color: #E5CA7B; }
QToolButton#projectRowDeleteButton:hover { color: #C2414B; background: #FDECEE; }
```

Keep stock-in blue, stock-out neutral slate, and destructive confirmation red. Focus must remain a 1px blue border.

- [ ] **Step 5: 运行对话框和 BOM 全量测试**

Run: `python -m pytest tests/test_bom_optimizer_ui.py tests/test_dialogs.py tests/test_bom_workflow.py tests/test_bom_matching.py tests/test_bom_export.py -q`

Expected: PASS。

- [ ] **Step 6: 提交任务**

```bash
git add src/partbox/ui/theme.py tests/test_theme.py
git commit -m "style(ui): align workflow dialogs"
```

### Task 5: 全量回归、截图验收和设计记录

**Files:**
- Modify: `docs/verification.md`
- Create: `DESIGN.md`
- Create: `.impeccable/review/inventory-1440x820.png`
- Create: `.impeccable/review/inventory-1050x650.png`
- Create: `.impeccable/review/comparison.png`
- Create: `.impeccable/review/projects.png`
- Create: `.impeccable/review/bom.png`
- Create: `.impeccable/review/dialogs.png`

**Interfaces:**
- Consumes: Tasks 1-4 的最终界面。
- Produces: 可复核的测试证据、六个有效截图和由实际实现提取的 `DESIGN.md`。

- [ ] **Step 1: 运行全量自动化测试**

Run: `python -m pytest -q`

Expected: exit code 0；所有测试通过或仅保留基线已有 skip。

- [ ] **Step 2: 运行现有渲染脚本生成页面证据**

Run:

```powershell
python scripts/render_ui.py
python scripts/render_projects.py
python scripts/render_new_features.py
python scripts/render_dialogs.py
```

Expected: exit code 0；`.artifacts/` 下生成非空 PNG，覆盖库存、项目、对比、BOM 和核心弹窗。

- [ ] **Step 3: 复制并验证最终验收截图**

Create `.impeccable/review/` and copy the relevant rendered PNG files to the exact names listed in this task. Open each image once and verify it contains the named page，不是黑屏、空白或错误页面。截图必须覆盖 1440×820 与 1050×650 两个库存窗口尺寸；若现有脚本缺少尺寸参数，只在脚本中增加 `--width`／`--height` 参数，不改变界面代码。

- [ ] **Step 4: 进行一次集中视觉修复**

Check all screenshots against these exact conditions:

```text
inventory: 淡蓝，Logo 清晰，顶栏留白舒适，四卡等大，表头与行对齐
comparison: 淡黄，差异单元格更深，横向滚动可用
projects: 浅绿，项目列表可折叠，新建项目在底部，数量和位号行高一致
history/imports/settings: 分别淡紫灰、淡杏、浅灰蓝
bom: 浅绿主表面，补货输入淡黄
dialogs: 按钮不换行，焦点可见，危险确认明确
```

Fix all observed material issues in one batch. Do not change business logic while fixing screenshots.

- [ ] **Step 5: 运行第二次确认截图和测试**

Run the four render commands again, replace the review images, then run `python -m pytest -q`.

Expected: valid screenshots and exit code 0。第二轮后停止自行微调。

- [ ] **Step 6: 写入验证记录和实现后的设计系统**

Append to `docs/verification.md` the exact test command, exit code, screenshot paths and checked resolutions. Create `DESIGN.md` from the shipped interface, documenting the six page palettes, common typography, 8-10px radius rule, 36px table rows, 1px focus border, project-yellow and destructive-red semantic boundaries.

- [ ] **Step 7: 提交任务**

```bash
git add DESIGN.md docs/verification.md src/partbox/ui tests
git commit -m "docs(ui): record A-style verification"
```

Do not add `.artifacts/`, generated EXE files, local databases or unrelated dirty files.

## Final verification matrix

- `python -m pytest -q`
- `python scripts/render_ui.py`
- `python scripts/render_projects.py`
- `python scripts/render_new_features.py`
- `python scripts/render_dialogs.py`
- Manual check at 1440×820 and 1050×650
- Confirm exact page backgrounds: `#EEF5FF`, `#FFF8E6`, `#EFF9F0`, `#F4F1FB`, `#FFF3EC`, `#F2F5F7`
- Confirm sorting, Shift range selection, row identity, position editing, quantity steppers, per-row delete confirmation, project save, comparison scrolling and BOM export remain functional
