# PartBOX Light UI Refresh Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refresh PartBOX with dynamic inventory-backed categories, a restrained light visual system, and direct editing limited to stock and notes.

**Architecture:** Put deterministic category keyword matching in a pure `partbox.categories` module. Let `MainWindow` rebuild quick-filter buttons from current component rows and keep all presentation rules in `theme.py`. Preserve existing database and service APIs.

**Tech Stack:** Python 3.10, PySide6, pytest, pytest-qt, PyInstaller

## Global Constraints

- Use only white, light blue-gray, brand blue, and dark neutral text.
- Show only categories represented by current imported components.
- Keep `全部`, `库存不足`, and `库存为零` available.
- Only `current_stock` and `notes` table cells are editable.
- Do not change order import, stock history, or database schema.

---

### Task 1: Dynamic component categories

**Files:**
- Create: `src/partbox/categories.py`
- Create: `tests/test_categories.py`
- Modify: `src/partbox/ui/main_window.py`

**Interfaces:**
- Produces: `component_category(row: Mapping[str, object]) -> str` and `available_categories(rows: Iterable[Mapping[str, object]]) -> list[str]`
- Consumes: component `product_type` and `product_name`

- [ ] Add tests proving resistor-only rows produce only `电阻`, mixed rows follow priority, and unmatched rows produce `其他`.
- [ ] Run `pytest tests/test_categories.py -q`; expect import failure before module exists.
- [ ] Implement ordered keyword rules and stable display ordering.
- [ ] Rebuild category buttons from all current rows while retaining valid selection.
- [ ] Apply selected category after existing search and stock filtering.
- [ ] Run category and UI tests; expect pass.

### Task 2: Read-only imported fields

**Files:**
- Modify: `tests/test_ui_smoke.py`
- Modify: `src/partbox/ui/main_window.py`

**Interfaces:**
- Produces: editable table cells only for `current_stock` and `notes`

- [ ] Add a UI test that inserts a component and checks every column's `Qt.ItemIsEditable` flag.
- [ ] Run the test; expect failure because several imported fields are currently editable.
- [ ] Restrict the editable set to `{"current_stock", "notes"}` and use a light-blue editable-cell background.
- [ ] Guard `save_cell_edit` so unexpected edits to read-only keys are ignored.
- [ ] Run the UI test; expect pass.

### Task 3: Unified light layout and styling

**Files:**
- Modify: `src/partbox/ui/main_window.py`
- Modify: `src/partbox/ui/theme.py`

**Interfaces:**
- Produces: two-line brand block, expanding search field, equal stat cards, refined sidebars, and 10-pixel rounded scrollbars

- [ ] Replace the single brand label with fixed-width `PartBOX` and `小料仓` labels on a transparent light top bar.
- [ ] Remove the search maximum width and give it the main stretch allocation.
- [ ] Give all stat cards equal stretch and remove trailing empty stretch.
- [ ] Increase navigation and summary widths slightly and assign semantic object names.
- [ ] Replace the stylesheet with the approved light palette, card fills, table states, and scrollbar rules.
- [ ] Run UI tests; expect pass.

### Task 4: Visual and packaged verification

**Files:**
- Build: `dist/PartBOX.exe`
- Update: `C:\Users\lenovo\Desktop\PartBOX\PartBOX.exe`
- Update: desktop source clone

**Interfaces:**
- Consumes: completed source and tests
- Produces: verified desktop executable and source delivery

- [ ] Render `artifacts/partbox-light-ui.png` with sample orders and inspect it visually.
- [ ] Adjust only verified visual defects, rerunning UI tests after changes.
- [ ] Run full pytest suite.
- [ ] Build through `scripts/build.ps1` with process-scoped execution-policy bypass.
- [ ] Run packaged EXE smoke test.
- [ ] Commit source changes, update the desktop clone and EXE, then verify shortcut target and file hash.
