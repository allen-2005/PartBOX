# PartBOX Project Table Refinement Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade project component management with stable selection, sortable presentation, quantities, pricing, deletion rollback, and project context actions.

**Architecture:** Keep inventory state in `MainWindow` and project state in `ProjectsPage`, keyed by component IDs rather than view rows. Put all stock-changing deletion logic in transactional `ProjectService` methods; keep display-only sequence, sort glyphs, spin editors, and totals in the UI layer.

**Tech Stack:** Python 3.12, PySide6, SQLite, pytest, pytest-qt, PyInstaller.

## Global Constraints

- Project quantities are integers and never below 1.
- Deleting a project component returns only its persisted `synced_quantity` to stock.
- Any stock return must create both stock movement and project operation records atomically.
- Selection must remain attached to component IDs across sorting and refresh.

---

### Task 1: Project domain rules

**Files:**
- Modify: `src/partbox/database.py`
- Modify: `src/partbox/projects.py`
- Test: `tests/test_projects.py`

**Interfaces:**
- Produces: `ProjectService.remove_components(project_id: int, component_ids: list[int]) -> ProjectSyncResult`
- Produces: `ProjectService.project_total(project_id: int) -> float`

- [ ] Write failing tests for default quantity 1, minimum validation, numeric project total, and atomic synced-quantity return on deletion.
- [ ] Run `python -m pytest tests/test_projects.py -q` and confirm the new assertions fail for the missing behavior.
- [ ] Implement the migration and service methods, preserving exact inventory `product_type` and latest unit price in query results.
- [ ] Run `python -m pytest tests/test_projects.py -q` and confirm all project service tests pass.

### Task 2: Stable inventory selection

**Files:**
- Modify: `src/partbox/ui/main_window.py`
- Test: `tests/test_ui_smoke.py`

**Interfaces:**
- Produces: `MainWindow.checked_component_ids: set[int]`
- Produces: row selection rendering derived from the displayed row's component ID.

- [ ] Write a failing UI test that selects a component, sorts the table, and asserts the same component ID remains selected.
- [ ] Run the focused smoke test and confirm the view-row implementation fails.
- [ ] Replace vertical-header check-state ownership with an ID set and reduce the selector pen to 1 pixel.
- [ ] Run the focused smoke tests and confirm stable selection.

### Task 3: Project table presentation and editing

**Files:**
- Modify: `src/partbox/ui/projects_page.py`
- Test: `tests/test_projects_ui.py`

**Interfaces:**
- Produces: project columns `序号` through `小计`, ID-bound selection, persistent spin editors, and `project_total_label`.

- [ ] Write failing UI tests for headers, sort triangles, continuous sequence numbers, checkbox identity, default spin quantity, totals, and context menu actions.
- [ ] Run `python -m pytest tests/test_projects_ui.py -q` and confirm failures describe missing UI behavior.
- [ ] Implement the project header, quantity delegate/editor, total refresh, selected deletion, and project context menu.
- [ ] Run `python -m pytest tests/test_projects_ui.py -q` and confirm all tests pass.

### Task 4: Integration, packaging, and deployment

**Files:**
- Modify if needed: `tests/test_ui_smoke.py`
- Build output: `dist/PartBOX.exe`
- Deploy output: `C:/Users/lenovo/Desktop/PartBOX/PartBOX.exe`

- [ ] Run `python -m pytest -q` and fix any regression until the suite passes.
- [ ] Launch the application in offscreen smoke mode and verify the main window and project page construct without exceptions.
- [ ] Build with the repository PyInstaller spec or build script.
- [ ] Copy the verified EXE and updated source/manual into the desktop PartBOX folder, update the desktop shortcut if needed, and compare SHA-256 hashes.
