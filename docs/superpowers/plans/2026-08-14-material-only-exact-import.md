# PartBOX Material-Only Exact Import Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove order-detail importing and guarantee that material-statement descriptive fields are stored and displayed exactly as supplied by the statement.

**Architecture:** Keep `parse_statement()` as the only UI import parser. Separate matching normalization from display-text extraction, then refresh existing component metadata from each accepted material line. Remove the order-detail UI/API surface and update auxiliary scripts and documentation.

**Tech Stack:** Python 3.12, PySide6, pandas/xlrd/openpyxl, SQLite, pytest, PyInstaller.

## Global Constraints

- Only `.xls` and `.xlsx` material detail statements are accepted by the import UI.
- Quick categories may classify rows for filtering but never modify persisted or displayed fields.
- Existing stock, projects, movements, locations, and notes must be preserved.

---

### Task 1: Exact statement text and existing-component repair

**Files:**
- Modify: `tests/test_importer.py`
- Modify: `tests/test_services.py`
- Modify: `src/partbox/importer.py`
- Modify: `src/partbox/services.py`

**Interfaces:**
- Consumes: `parse_statement(path: Path) -> ParsedStatement`, `ImportService.commit(preview, stock_decisions)`
- Produces: exact `OrderLine` descriptive text and existing component metadata refresh

- [ ] Add a parser test using distinct whitespace and full product-type text; assert `brand`, `product_type`, `product_name`, `model`, `package`, and `unit` equal their source cells.
- [ ] Add a service test that starts with a coarse `product_type`, imports an exact material line, and asserts metadata is replaced while stock follows the explicit stock decision.
- [ ] Run both tests and confirm the metadata-refresh test fails before implementation.
- [ ] Add a display-text converter that preserves source strings and use it for the six descriptive fields.
- [ ] Extend the existing-component update statement to write the accepted material line's descriptive fields.
- [ ] Re-run the focused tests and confirm they pass.

### Task 2: Remove order-detail importing

**Files:**
- Modify: `tests/test_importer.py`
- Modify: `tests/test_ui_smoke.py`
- Modify: `tests/test_designer_ui.py`
- Modify: `src/partbox/importer.py`
- Modify: `src/partbox/ui/main_window.py`
- Modify: `src/partbox/ui/ui_loader.py`
- Modify: `src/partbox/ui/forms/main_window.ui`
- Modify: `src/partbox/ui/theme.py`

**Interfaces:**
- Consumes: material statement import only
- Produces: one `materialImportButton` entry and no `parse_order_detail` symbol

- [ ] Change UI tests to require one material import button and assert `orderDetailImportButton` is absent.
- [ ] Run the focused UI test and confirm it fails against the old UI.
- [ ] Remove the order-detail parser and helpers from `importer.py`.
- [ ] Remove the order-detail button, lookup, signal, handler, and stylesheet selector.
- [ ] Run importer and UI tests and confirm they pass.

### Task 3: Update scripts, docs, and deployment

**Files:**
- Modify: `scripts/e2e_upgrade.py`
- Modify: `scripts/render_projects.py`
- Modify: `scripts/render_ui.py`
- Modify: `README.md`
- Modify: `使用说明.txt`

**Interfaces:**
- Consumes: `parse_statement`
- Produces: material-only developer scripts and user guidance

- [ ] Replace order-detail sample discovery in rendering/e2e scripts with material-statement discovery.
- [ ] Remove all current-user guidance that advertises order-detail imports.
- [ ] Run `rg` to ensure runtime code and current docs no longer contain `parse_order_detail`, `orderDetailImportButton`, or `导入订单详情`.
- [ ] Run the full pytest suite.
- [ ] Compare all real material-statement parsed fields against their source cells.
- [ ] Build `PartBOX.exe`, run packaged smoke verification, deploy the EXE, UI, source, tests, and instructions to the desktop PartBOX folder, and verify hashes and shortcut target.
