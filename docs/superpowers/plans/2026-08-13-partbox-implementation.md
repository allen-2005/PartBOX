# PartBOX Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and package a clear Windows desktop application that imports LCSC order spreadsheets and manages a local electronic-component inventory.

**Architecture:** A PySide6 presentation layer calls focused application services backed by a transactional SQLite repository. Spreadsheet parsing and import planning are pure Python boundaries so format detection, deduplication, component matching, and stock decisions can be tested without the GUI.

**Tech Stack:** Python 3.10+, PySide6, SQLite, pandas, xlrd, openpyxl, pytest, PyInstaller

## Global Constraints

- Product title is `小料仓 PartBOX`; executable is `PartBOX.exe`.
- Delivery directory is `C:\Users\lenovo\Desktop\小料仓PartBOX`.
- The three supplied order files are test inputs only and are never bundled or pre-imported.
- A newly delivered database is empty.
- `.xls` and `.xlsx` LCSC material-detail statements are supported.
- Source order fields remain immutable even if a component is edited.
- The GUI follows the approved dense-table layout with simple left navigation and a right component summary.

---

### Task 1: Project Runtime and Database Foundation

**Files:**
- Create: `pyproject.toml`
- Create: `requirements.txt`
- Create: `src/partbox/__init__.py`
- Create: `src/partbox/paths.py`
- Create: `src/partbox/database.py`
- Test: `tests/test_database.py`

**Interfaces:**
- Produces: `AppPaths.for_base(base: Path) -> AppPaths`; `Database(path: Path)`; `Database.initialize()`; `Database.transaction()`.

- [ ] Write tests proving a new database creates all tables, default settings, and foreign-key enforcement.
- [ ] Run `python -m pytest tests/test_database.py -v` and confirm failure because modules are absent.
- [ ] Add package metadata, dependency pins, application paths, migrations, and transaction helper.
- [ ] Run the test again and confirm pass.
- [ ] Commit with `feat: add PartBOX database foundation`.

### Task 2: LCSC Spreadsheet Parser

**Files:**
- Create: `src/partbox/importer.py`
- Test: `tests/test_importer.py`

**Interfaces:**
- Produces: `parse_statement(path: Path) -> ParsedStatement`; `OrderLine`, `FeeLine`, `ImportIssue`; `file_sha256(path: Path) -> str`.
- `ParsedStatement` exposes `headers`, `order_lines`, `fee_lines`, `issues`, `source_sheet`, and `header_row`.

- [ ] Write failing tests for header discovery, normalized values, fee extraction, missing-header diagnostics, and stable line fingerprints.
- [ ] Run focused tests and confirm expected failures.
- [ ] Implement dataframe-based parsing for `.xls` through `xlrd` and `.xlsx` through `openpyxl`, scanning the first 20 rows for required headers.
- [ ] Run parser unit tests and confirm pass.
- [ ] Add an integration test against each supplied `.xls` that checks parsing succeeds without asserting personal totals.
- [ ] Run all importer tests and commit with `feat: parse LCSC order statements`.

### Task 3: Inventory and Import Services

**Files:**
- Create: `src/partbox/repository.py`
- Create: `src/partbox/services.py`
- Test: `tests/test_services.py`

**Interfaces:**
- Produces: `InventoryService`, `ImportService.preview(paths)`, `ImportService.commit(preview, stock_decisions, force=False)`, `StockService.adjust(...)`, `StockService.reverse(...)`.
- `InventoryService.list_components(search, category, stock_filter)` returns component dictionaries for the table.

- [ ] Write failing tests for SKU-first matching, model-plus-package fallback, file and line dedupe, new-component opening stock, existing-component stock decisions, transaction rollback, stock adjustment, negative-stock guard, and reversal.
- [ ] Run tests and confirm failures are caused by missing services.
- [ ] Implement repository queries and transactional services with immutable purchase rows.
- [ ] Run service tests and full suite; confirm pass.
- [ ] Commit with `feat: add inventory and import services`.

### Task 4: Inventory Dashboard UI

**Files:**
- Create: `src/partbox/ui/__init__.py`
- Create: `src/partbox/ui/theme.py`
- Create: `src/partbox/ui/inventory_page.py`
- Create: `src/partbox/ui/main_window.py`
- Test: `tests/test_ui_smoke.py`

**Interfaces:**
- Produces: `MainWindow(services: ServiceContainer)` and `InventoryPage`.

- [ ] Write an offscreen Qt smoke test asserting title, five navigation items, four stat cards, search field, dense component table, and right summary exist.
- [ ] Run it and confirm failure because UI classes are absent.
- [ ] Implement the approved dark top bar, simple left sidebar, searchable/filterable center table, summary cards, horizontal scrolling, editable cells, and right component summary.
- [ ] Run UI smoke test and full suite; confirm pass.
- [ ] Commit with `feat: build PartBOX inventory dashboard`.

### Task 5: Import Preview and Stock Decisions UI

**Files:**
- Create: `src/partbox/ui/import_dialog.py`
- Modify: `src/partbox/ui/main_window.py`
- Test: `tests/test_import_dialog.py`

**Interfaces:**
- Produces: `ImportDialog` supporting multi-file selection, preview statistics, existing-item stock checkboxes, all-add/all-skip, duplicate warnings, and force confirmation.

- [ ] Write failing Qt tests for preview rendering and stock decision collection.
- [ ] Run focused tests and confirm expected failures.
- [ ] Implement background-safe parsing feedback and atomic commit from the dialog.
- [ ] Run focused and full tests; confirm pass.
- [ ] Commit with `feat: add guided order import`.

### Task 6: Stock, History, Import Records, and Settings Pages

**Files:**
- Create: `src/partbox/ui/stock_dialog.py`
- Create: `src/partbox/ui/history_page.py`
- Create: `src/partbox/ui/imports_page.py`
- Create: `src/partbox/ui/settings_page.py`
- Modify: `src/partbox/ui/main_window.py`
- Test: `tests/test_aux_pages.py`

**Interfaces:**
- Produces: add/remove/calibrate dialogs; searchable stock history; import batch list; backup, restore, export, negative-stock, and reset controls.

- [ ] Write failing smoke and behavior tests for stock changes, reversal, history refresh, backup creation, empty export, and protected reset.
- [ ] Run focused tests and confirm expected failures.
- [ ] Implement the four auxiliary pages and navigation wiring.
- [ ] Run full tests and confirm pass.
- [ ] Commit with `feat: add inventory operations and settings`.

### Task 7: Application Entry Point and Polish

**Files:**
- Create: `src/partbox/app.py`
- Create: `src/partbox/__main__.py`
- Create: `run_partbox.py`
- Create: `assets/partbox.ico`
- Create: `README.md`
- Test: `tests/test_app_startup.py`

**Interfaces:**
- Produces: `python -m partbox`; `run_partbox.py`; logging and user-readable fatal error handling.

- [ ] Write failing startup tests using a temporary application-data directory.
- [ ] Run focused tests and confirm expected failures.
- [ ] Implement startup, logging, icon, empty-state copy, README, and safe shutdown.
- [ ] Run full automated suite and an offscreen startup check.
- [ ] Commit with `feat: finalize PartBOX desktop app`.

### Task 8: Real-Format Verification and Windows Packaging

**Files:**
- Create: `PartBOX.spec`
- Create: `scripts/build.ps1`
- Create: `scripts/smoke_exe.ps1`
- Create: `docs/verification.md`

**Interfaces:**
- Produces: clean `dist/PartBOX/PartBOX.exe` and desktop delivery folder.

- [ ] Run all tests against the project virtual environment.
- [ ] Parse all three supplied statements read-only and record only pass/fail format checks.
- [ ] Launch the application with a fresh temporary data directory, verify the empty dashboard, import one sample into the temporary database, restart, search, and execute an inventory adjustment.
- [ ] Build with PyInstaller using a clean output directory and no sample spreadsheets or database.
- [ ] Run the packaged executable smoke test with a fresh temporary data directory.
- [ ] Copy the packaged application, README, and empty-start instructions into `C:\Users\lenovo\Desktop\小料仓PartBOX`.
- [ ] Inspect the delivery tree to prove no `.xls`, `.xlsx`, personal database, or test file was included.
- [ ] Commit with `build: package PartBOX for Windows`.

