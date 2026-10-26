# PartBOX BOM Optimizer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Import an EDA BOM, multiply by project quantity, match inventory conservatively, let users resolve candidates, export only shortages for LCSC, save a project, and optionally issue matched stock.

**Architecture:** Keep file parsing, semantic matching, workflow state, persistence, export, and Qt presentation in separate modules. The workflow works on immutable source lines plus explicit match decisions; project/stock mutation occurs only after export succeeds and the user confirms.

**Tech Stack:** Python 3.10+, pandas/openpyxl/xlrd, SQLite, PySide6, pytest, pytest-qt

## Global Constraints

- Never modify the source BOM.
- Ask project build quantity before inventory matching; default1, minimum1.
- Automatic matching must be conservative; uncertain rows remain visible.
- Export only the LCSC shopping BOM format.
- Do not implement online pricing or coupon grouping.
- Preserve all existing uncommitted user changes in the desktop worktree.

---

### Task 1: Parse EDA BOMs without losing source values

**Files:**
- Create: `src/partbox/bom.py`
- Create: `tests/test_bom_parser.py`

**Interfaces:**
- Produces: `BomLine`, `ParsedBom`, `parse_bom(path: Path) -> ParsedBom`, `BomError`.

- [ ] Write `.xlsx` and `.csv` fixtures covering Chinese/English aliases, header detection, quantity validation, and untouched source values.
- [ ] Run `python -m pytest tests/test_bom_parser.py -q` and confirm missing-module failure.
- [ ] Implement sheet/header detection and aliases for quantity, designator, LCSC code, type, description/value, model, package, and brand.
- [ ] Reject files without quantity plus one usable identity field; preserve every source column in `BomLine.source_values`.
- [ ] Rerun parser tests.

### Task 2: Implement semantic signatures and conservative matching

**Files:**
- Create: `src/partbox/bom_matching.py`
- Create: `tests/test_bom_matching.py`

**Interfaces:**
- Consumes: `BomLine` and inventory dictionaries.
- Produces: `MatchKind`, `MatchCandidate`, `MatchResult`, `match_bom(lines, inventory, build_quantity)`.

- [ ] Write failing tests for SKU exact match, `100K/100kΩ`, `5%/±5%`, package/brand/tolerance rejection, model+package+brand exact match, similar candidates, zero-stock exclusion, partial stock, and multiplied demand.
- [ ] Implement display-independent normalization, resistance/capacitance/tolerance/power/package extraction, category inference, exact signatures, and difference descriptions.
- [ ] Rank candidates deterministically; never auto-select a candidate with a known key difference.
- [ ] Rerun `python -m pytest tests/test_bom_matching.py -q`.

### Task 3: Persist imported project BOM and match decisions

**Files:**
- Modify: `src/partbox/database.py`
- Modify: `src/partbox/projects.py`
- Create: `tests/test_bom_projects.py`

**Interfaces:**
- Produces: project `build_quantity`; `project_bom_lines`; `ProjectService.create_from_bom(...) -> int`; `ProjectService.issue_bom_allocations(project_id) -> ProjectSyncResult`.

- [ ] Write failing migration/service tests for build quantity, source rows, unmatched rows, selected inventory IDs, allocated quantity, and rollback on stock error.
- [ ] Add additive migrations and tables; do not rewrite existing project rows.
- [ ] Save complete BOM and matched inventory configuration in one transaction.
- [ ] Issue only allocated quantities, reuse stock movement conventions, and update `synced_quantity` without negative stock.
- [ ] Rerun `python -m pytest tests/test_bom_projects.py tests/test_projects.py -q`.

### Task 4: Export LCSC-compatible shortage workbook

**Files:**
- Modify: `src/partbox/bom.py`
- Create: `tests/test_bom_export.py`

**Interfaces:**
- Produces: `export_lcsc_bom(path, workflow_rows) -> Path`.

- [ ] Write failing tests that open the output workbook and assert columns `LCSC Part Number`, `Manufacturer Part Number`, `Description`, `Quantity`, `Package`, `Manufacturer`, `Reference Designator`.
- [ ] Assert fulfilled rows are absent, partial rows contain only shortage, rejected/unmatched rows retain full demand, exhausted optional-restock rows appear only when user quantity is positive.
- [ ] Implement deterministic `.xlsx` export using pandas/openpyxl and atomic replacement.
- [ ] Rerun export tests.

### Task 5: Implement BOM optimizer wizard

**Files:**
- Create: `src/partbox/ui/bom_optimizer.py`
- Modify: `src/partbox/ui/theme.py`
- Create: `tests/test_bom_optimizer_ui.py`

**Interfaces:**
- Consumes: parser, matcher, `ProjectService`.
- Produces: `BomOptimizerDialog`, `project_created = Signal(int)`, `inventory_changed = Signal()`.

- [ ] Write UI tests for build quantity before matching, exact-row highlighting, candidate differences, accept/reject, undo, previous/next, partial shortage, exhausted highlight, editable restock, export cancellation, project saving, and optional issue confirmation.
- [ ] Build stacked pages for setup, matching, and replenishment review.
- [ ] Keep explicit decision history for `undo_last_decision()`; changing build quantity recomputes stock results while preserving compatible selections.
- [ ] Use pale status fills; highlight exhausted rows and their editable zero-default purchase control without a popup.
- [ ] Export first, then create project, then ask stock-issue confirmation; emit signals only after successful mutations.
- [ ] Rerun `python -m pytest tests/test_bom_optimizer_ui.py -q`.

### Task 6: Integrate the wizard into My Projects

**Files:**
- Modify: `src/partbox/ui/projects_page.py`
- Modify: `src/partbox/ui/main_window.py`
- Modify: `tests/test_projects_ui.py`
- Modify: `tests/test_ui_smoke.py`

- [ ] Add a failing test for a sidebar-bottom “导入BOM并计算” action.
- [ ] Add the button next to/below “新建项目” without moving existing project controls.
- [ ] Open `BomOptimizerDialog`, refresh the created project, switch to it, and refresh inventory only when stock changed.
- [ ] Rerun all project/UI tests.

### Task 7: Full verification and packaging

**Files:**
- Modify: `README.md`
- Modify: `使用说明.md`
- Modify: `docs/verification.md`
- Modify: `PartBOX.spec` only if new package data/imports require it.

- [ ] Document comparison and BOM workflow, including offline-only estimated prices and no coupon feature.
- [ ] Run `python -m pytest -q` with `QT_QPA_PLATFORM=offscreen`.
- [ ] Render inventory, comparison, matching, and replenishment states; inspect dimensions, scrolling, fills, and button placement.
- [ ] Run `powershell -ExecutionPolicy Bypass -File scripts/build.ps1` and packaged smoke test.
- [ ] Confirm `C:\Users\lenovo\Desktop\PartBOX\PartBOX.exe` starts and uses the migrated database without data loss.

