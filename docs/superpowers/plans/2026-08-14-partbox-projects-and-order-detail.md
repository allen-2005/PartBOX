# PartBOX Projects and Order Detail Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add project-based component allocation with delta stock synchronization, a second LCSC order-detail importer, and the requested compact/collapsible/copyable inventory UI.

**Architecture:** Keep both LCSC formats behind dedicated parser entry points that produce the existing `ParsedStatement` model, so import accounting remains shared. Add focused `ProjectService` tables and methods for transactional delta synchronization. Keep project UI in its own page class and let `MainWindow` coordinate inventory selection, navigation, and the fixed collapsible summary panel.

**Tech Stack:** Python 3.10+, PySide6 6.8, SQLite, pandas/xlrd/openpyxl, pytest/pytest-qt, PyInstaller.

## Global Constraints

- Existing databases must migrate without losing components, purchases, stock movements, settings, or layout preferences.
- Project synchronization uses `current quantity - synced quantity`; positive deltas subtract stock, negative deltas return stock, and zero deltas do nothing.
- Project synchronization is atomic and preserves operation records.
- Both supplied `.xls` order-detail samples must parse.
- The delivered desktop EXE, source, editable UI, guide, and shortcut must be updated together.

---

### Task 1: LCSC order-detail parser

**Files:**
- Modify: `src/partbox/importer.py`
- Modify: `src/partbox/services.py`
- Modify: `tests/test_importer.py`
- Modify: `tests/test_services.py`

**Interfaces:**
- Produces: `parse_order_detail(path: Path) -> ParsedStatement`
- Produces: `ImportService.preview(paths, force=False, parser=parse_statement)`

- [ ] Add tests that parse both supplied samples and assert order number, timestamp, row count, product code, model, package, quantity, unit, price, subtotal, and stable fingerprints.
- [ ] Run `pytest tests/test_importer.py -q` and verify the new tests fail because `parse_order_detail` is absent.
- [ ] Implement label scanning, item-header discovery, unit/currency parsing, empty-template-sheet skipping, and normalized `OrderLine` creation.
- [ ] Add a parser parameter to `ImportService.preview` while preserving the current default.
- [ ] Run importer/service tests and commit.

### Task 2: Project persistence and delta stock service

**Files:**
- Modify: `src/partbox/database.py`
- Create: `src/partbox/projects.py`
- Create: `tests/test_projects.py`
- Modify: `src/partbox/app.py`
- Modify: `src/partbox/ui/main_window.py`

**Interfaces:**
- Produces: `ProjectService.list_projects()`, `create_project(name)`, `rename_project(id, name)`, `delete_project(id)`, `add_components(project_id, component_ids)`, `list_components(project_id)`, `set_quantity(project_id, component_id, quantity)`, `sync(project_id)` and `operation_history(project_id)`.
- Produces: `ProjectSyncResult(operation_id, changed_lines, stock_delta)`.

- [ ] Write tests for database migration, unique/non-empty names, duplicate component add, non-negative quantities, positive delta out, negative delta return, zero-delta no-op, atomic insufficient-stock rollback, and operation history.
- [ ] Run `pytest tests/test_projects.py -q` and verify failure because project tables/service are absent.
- [ ] Add `projects`, `project_components`, `project_operations`, and `project_operation_lines` to idempotent schema initialization.
- [ ] Implement validation and one-transaction synchronization, including linked `stock_movements` rows of types `project_out` and `project_return`.
- [ ] Wire `ProjectService` into the app service container, run tests, and commit.

### Task 3: Main inventory UI polish and selection

**Files:**
- Modify: `src/partbox/ui/forms/main_window.ui`
- Modify: `src/partbox/ui/ui_loader.py`
- Modify: `src/partbox/ui/theme.py`
- Modify: `src/partbox/ui/main_window.py`
- Modify: `src/partbox/ui/inventory_header.py`
- Modify: `tests/test_designer_ui.py`
- Modify: `tests/test_ui_smoke.py`
- Modify: `tests/test_inventory_header.py`

**Interfaces:**
- `MainWindow.selected_component_ids() -> list[int]`
- `MainWindow.toggle_summary_panel()` persists `ui/summary_visible`.

- [ ] Add failing UI tests for equal-width bilingual logo, vertically centered filters, compact statistic order/layout, absence of clear-filter button, two import buttons, fixed collapsible right panel, and leftmost check-state column.
- [ ] Run targeted UI tests and verify expected failures.
- [ ] Update the Designer UI and stylesheet for requested spacing, logo, statistic cards, import buttons, and fixed panel toggle.
- [ ] Extend inventory population and header behavior so the checkbox column remains first and user data columns retain their saved order/hide/sort state.
- [ ] Implement persistent summary collapse and click-to-copy values with a short status/tool-tip confirmation.
- [ ] Run UI tests and commit.

### Task 4: Project page UI

**Files:**
- Create: `src/partbox/ui/projects_page.py`
- Modify: `src/partbox/ui/main_window.py`
- Modify: `src/partbox/ui/theme.py`
- Create: `tests/test_projects_ui.py`
- Modify: `tests/test_ui_smoke.py`

**Interfaces:**
- `ProjectsPage.refresh(project_id: int | None = None)`
- Signal: `ProjectsPage.inventory_changed`
- Slot: `ProjectsPage.add_component_ids(component_ids: list[int])`

- [ ] Add failing tests for “我的项目” navigation, create/rename/delete, yellow table, required columns, editable quantity, importing selected inventory rows, syncing, and visible history.
- [ ] Run targeted tests and verify failures.
- [ ] Implement the focused page with project list/toolbar, component table, quantity editing, sync confirmation, and operation history.
- [ ] Add inventory-page “导入到项目” action enabled only when rows are checked and route selected IDs to the project page.
- [ ] Run project UI tests and commit.

### Task 5: Dual import workflow

**Files:**
- Modify: `src/partbox/ui/main_window.py`
- Modify: `src/partbox/ui/import_dialog.py`
- Modify: `tests/test_dialogs.py`
- Modify: `tests/test_ui_smoke.py`

**Interfaces:**
- `MainWindow.choose_material_files()` uses `parse_statement`.
- `MainWindow.choose_order_detail_files()` uses `parse_order_detail`.
- Shared helper: `MainWindow.import_files(paths, parser, format_name)`.

- [ ] Add failing tests that each button invokes the right parser path and that a wrong format yields a format-specific Chinese error.
- [ ] Run tests and verify expected failures.
- [ ] Split the chooser slots, reuse the current preview/commit dialog, and label the preview with its source format.
- [ ] Verify both sample files preview and import into temporary databases, run tests, and commit.

### Task 6: Regression, visual verification, build and desktop delivery

**Files:**
- Modify: `README.md`
- Modify: `docs/verification.md`
- Modify: `scripts/render_ui.py` if needed
- Build output: `dist/PartBOX.exe`
- Delivery: `C:/Users/lenovo/Desktop/PartBOX/`

- [ ] Run the full pytest suite and fix every regression with a failing regression test first.
- [ ] Render the inventory and project pages at 1440×820; inspect logo edges, filter spacing, statistic alignment, pale-yellow project table, checkbox states, and summary toggle.
- [ ] Exercise a temporary database end to end: import both order-detail files, create a project, add rows, sync out/return, reopen database, and verify persisted state/history.
- [ ] Update the usage guide with both import buttons and project delta behavior.
- [ ] Build the EXE, run startup smoke tests with an empty temporary data directory and the existing desktop database, and compare deployed hashes.
- [ ] Copy code, `main_window.ui`, EXE, assets, and guide into the desktop `PartBOX` folder; verify `PartBOX.lnk` launches the new EXE.
- [ ] Commit the delivery metadata/documentation and record verification evidence.
