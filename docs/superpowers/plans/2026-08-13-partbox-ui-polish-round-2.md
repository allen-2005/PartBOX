# PartBOX UI Polish Round 2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add continuous table scrolling, simplify navigation and filters, enlarge the search field, refine the Chinese brand label, and make location editable with a high-contrast editor.

**Architecture:** Keep behavior changes local to `MainWindow` and presentation changes in `theme.py`. Preserve existing services and database APIs; `save_cell_edit` already supports generic component updates and will allow `location` through its existing service whitelist.

**Tech Stack:** Python 3.10, PySide6, pytest, pytest-qt, PyInstaller

## Global Constraints

- Keep the existing white, light blue-gray, brand-blue visual system.
- Keep right-panel stock-in and stock-out operations.
- Do not change import, stock movement, or database schemas.
- Deliver updated source and EXE to `C:\Users\lenovo\Desktop\PartBOX`.

---

### Task 1: Navigation, filters, search, and scroll behavior

**Files:**
- Modify: `tests/test_ui_smoke.py`
- Modify: `src/partbox/ui/main_window.py`

**Interfaces:**
- Produces: four navigation entries mapped to four pages, category-only quick filters, a 54-pixel search input, and per-pixel table scrolling

- [ ] Add UI assertions for four navigation labels, four stacked pages, no stock filters, 54-pixel search height, and per-pixel horizontal and vertical scroll modes.
- [ ] Run the focused UI tests and confirm they fail against current behavior.
- [ ] Remove the stock operation navigation entry and placeholder page, then update page refresh indices.
- [ ] Remove `low` and `zero` filter entries and simplify refresh to category plus search only.
- [ ] Set the main table horizontal and vertical scroll modes to `ScrollPerPixel`.
- [ ] Set the search field fixed height to 54 and enlarge the top bar.
- [ ] Run focused UI tests and confirm they pass.

### Task 2: Editable location and brand label

**Files:**
- Modify: `tests/test_ui_smoke.py`
- Modify: `src/partbox/ui/main_window.py`

**Interfaces:**
- Produces: editable keys `{current_stock, location, notes}` and a continuous `小料仓` brand label

- [ ] Change existing table-edit test expectation to include `location`; add brand text and font letter-spacing assertions.
- [ ] Run focused tests and confirm failure against current editable keys and spaced brand text.
- [ ] Add `location` to the editable and save guards.
- [ ] Render the Chinese label as `小料仓`, applying font letter spacing instead of inserted spaces.
- [ ] Run focused tests and confirm pass.

### Task 3: Thick scrollbars and editor contrast

**Files:**
- Modify: `tests/test_ui_smoke.py`
- Modify: `src/partbox/ui/theme.py`

**Interfaces:**
- Produces: 22-pixel scrollbars and high-contrast table cell editing

- [ ] Add stylesheet assertions for 22-pixel scrollbar dimensions, two-pixel editor border, and blue selection background with white selected text.
- [ ] Run focused tests and confirm failure against current stylesheet.
- [ ] Update horizontal and vertical scrollbars to 22 pixels.
- [ ] Add `QTableWidget QLineEdit` rules for white background, two-pixel brand-blue border, dark text, blue selection background, and white selected text.
- [ ] Run focused and full tests.

### Task 4: Visual verification and desktop delivery

**Files:**
- Build: `dist/PartBOX.exe`
- Update: `C:\Users\lenovo\Desktop\PartBOX`

**Interfaces:**
- Produces: reviewed screenshot and verified packaged desktop application

- [ ] Render a 1440-by-820 sample-order screenshot and inspect all requested changes.
- [ ] Render or inspect minimum-width behavior for scrolling and navigation.
- [ ] Request code review and resolve all Critical or Important findings.
- [ ] Run the full test suite and PyInstaller build.
- [ ] Smoke-test the built EXE, update desktop source and EXE, then smoke-test the desktop EXE.
- [ ] Verify shortcut target, EXE hash, Git revision, and clean source status.
