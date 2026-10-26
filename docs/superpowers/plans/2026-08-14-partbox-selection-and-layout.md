# PartBOX Selection And Layout Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver the four requested PartBOX table-selection and layout refinements in the desktop application.

**Architecture:** Keep selection state keyed by stable database component IDs and add an explicit optional keyboard-modifier argument to both table toggle methods for deterministic tests. Build the project sidebar and inventory action card with existing Qt widgets and persist only the sidebar visibility through the existing `QSettings` instance.

**Tech Stack:** Python 3, PySide6, Qt Designer `.ui`, pytest, pytest-qt, PyInstaller.

## Global Constraints

- Preserve the current database and exact material-statement import behavior.
- Use stable component IDs for selection across sorting.
- Make only the four requested UI/interaction changes.

---

### Task 1: Project table columns and range selection

**Files:**
- Modify: `tests/test_projects_ui.py`
- Modify: `src/partbox/ui/projects_page.py`

**Interfaces:**
- Consumes: `ProjectsPage.toggle_row_checked(row: int)` and project component IDs.
- Produces: `ProjectsPage.toggle_row_checked(row: int, modifiers: Qt.KeyboardModifier | None = None)` and a nine-column table without `序号`.

- [ ] **Step 1: Write failing tests**

Assert that project headers start with `商品编号`, that a normal click followed by Shift-click selects the inclusive displayed range, and that sorting preserves ID-based selection.

- [ ] **Step 2: Run the focused tests and confirm failure**

Run: `pytest -q tests/test_projects_ui.py`

Expected: failures for the old sequence column and missing Shift-range behavior.

- [ ] **Step 3: Implement the minimal behavior**

Remove `sequence` from `PROJECT_COLUMNS`, shift the column constants, delete row-renumbering code, and implement ID-anchored inclusive range selection.

- [ ] **Step 4: Re-run the focused tests**

Run: `pytest -q tests/test_projects_ui.py`

Expected: all project UI tests pass.

### Task 2: Inventory range selection and summary row

**Files:**
- Modify: `tests/test_ui_smoke.py`
- Modify: `src/partbox/ui/main_window.py`
- Modify: `src/partbox/ui/forms/main_window.ui`
- Modify: `src/partbox/ui/theme.py`

**Interfaces:**
- Consumes: inventory component IDs, `statsLayout`, `projectImportButton`.
- Produces: ID-anchored Shift selection and a five-item summary row containing four equal statistic cards plus `projectImportCard`.

- [ ] **Step 1: Write failing tests**

Assert inclusive Shift selection, stable selection after sorting, four equal statistic-card dimensions, and a pale-yellow project-import card on the same layout row.

- [ ] **Step 2: Run the focused tests and confirm failure**

Run: `pytest -q tests/test_ui_smoke.py`

Expected: failures for missing Shift-range selection and old summary layout.

- [ ] **Step 3: Implement the minimal behavior**

Store the inventory anchor by component ID, resolve its current visible row on Shift-click, resize the four Designer cards equally, and add the project-import card directly to `statsLayout`.

- [ ] **Step 4: Re-run the focused tests**

Run: `pytest -q tests/test_ui_smoke.py`

Expected: all main-window UI tests pass.

### Task 3: Collapsible project list

**Files:**
- Modify: `tests/test_projects_ui.py`
- Modify: `src/partbox/ui/projects_page.py`
- Modify: `src/partbox/ui/main_window.py`
- Modify: `src/partbox/ui/theme.py`

**Interfaces:**
- Consumes: the main window's `QSettings` instance.
- Produces: `ProjectsPage.toggle_project_sidebar()` and the `ui/projects_sidebar_visible` setting.

- [ ] **Step 1: Write a failing persistence test**

Create a temporary INI `QSettings`, collapse the project sidebar, recreate the page, and assert that it starts collapsed.

- [ ] **Step 2: Run the focused test and confirm failure**

Run: `pytest -q tests/test_projects_ui.py -k sidebar`

Expected: failure because no project sidebar toggle exists.

- [ ] **Step 3: Implement the collapsible pane**

Replace the adjustable splitter with a fixed-width sidebar frame, add an edge toggle, pass the main window settings into `ProjectsPage`, and persist visibility after each toggle.

- [ ] **Step 4: Re-run focused tests**

Run: `pytest -q tests/test_projects_ui.py`

Expected: all project UI tests pass.

### Task 4: Full verification and desktop delivery

**Files:**
- Modify: `README.md` only if the visible workflow description needs correction.
- Build: `build/dist/PartBOX.exe`
- Deploy: `C:\Users\lenovo\Desktop\PartBOX\PartBOX.exe`

**Interfaces:**
- Consumes: all source and tests from Tasks 1-3.
- Produces: a verified desktop EXE and source copy.

- [ ] **Step 1: Run the complete automated test suite**

Run: `pytest -q`

Expected: zero failures.

- [ ] **Step 2: Render and inspect both principal pages**

Run: `python scripts/render_ui.py` and `python scripts/render_projects.py`.

Expected: no sequence column, aligned summary cards, usable project import card, and collapsible project pane.

- [ ] **Step 3: Build and smoke-test the EXE**

Run: `powershell -ExecutionPolicy Bypass -File scripts/build_windows.ps1`, then `powershell -ExecutionPolicy Bypass -File scripts/smoke_packaged_app.ps1`.

Expected: both commands exit 0.

- [ ] **Step 4: Deploy and verify**

Copy source, instructions, and EXE to `C:\Users\lenovo\Desktop\PartBOX`, verify SHA-256 equality, and verify the desktop shortcut target.
