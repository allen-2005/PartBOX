# PartBOX Dialog and Layout Polish Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Show all importable components in import preview, remove the navigation-content gap, enlarge navigation text, and redesign stock operation dialogs.

**Architecture:** Keep import decisions keyed only by existing purchase-line fingerprints while presenting a unified display model containing new and existing lines. Replace only the outer splitter with a fixed-width navigation layout; retain the inner inventory-summary splitter. Use semantic widget object names and the global stylesheet for consistent dialog styling.

**Tech Stack:** Python 3.10, PySide6, pytest, pytest-qt, PyInstaller

## Global Constraints

- Do not change import commit rules, stock service behavior, or database schema.
- New component purchase lines are always initial stock and are read-only in preview.
- Existing component purchase lines retain user-controlled stock decisions.
- Keep the restrained white and blue-gray visual system.

---

### Task 1: Unified import preview

**Files:**
- Modify: `tests/test_dialogs.py`
- Modify: `src/partbox/ui/import_dialog.py`
- Modify: `src/partbox/ui/theme.py`

**Interfaces:**
- Consumes: `ImportPreview.new_lines` and `ImportPreview.existing_lines`
- Produces: one table containing all importable component lines; `stock_decisions()` still returns existing-line fingerprints only

- [ ] Add tests for new-only and mixed previews, including row labels, read-only new status, existing checkboxes, decisions, and disabled bulk buttons when no existing lines exist.
- [ ] Run focused tests and confirm failure against the existing-only table.
- [ ] Populate the table with new rows followed by existing rows; mark new rows `自动入库` and preserve existing fingerprints only on checkable rows.
- [ ] Restrict bulk actions and decision collection to checkable existing rows.
- [ ] Add compact summary and table status styling through object names.
- [ ] Run focused tests and confirm pass.

### Task 2: Remove layout gap and enlarge navigation

**Files:**
- Modify: `tests/test_ui_smoke.py`
- Modify: `src/partbox/ui/main_window.py`
- Modify: `src/partbox/ui/theme.py`

**Interfaces:**
- Produces: fixed 168-pixel navigation adjacent to an expanding page stack with zero layout gap

- [ ] Add geometry and structure tests asserting the outer area is a horizontal layout rather than a splitter, nav right edge equals pages left edge, and navigation stylesheet uses 15-pixel text.
- [ ] Run focused tests and confirm failure against the outer splitter.
- [ ] Replace the outer `QSplitter` with a zero-spacing `QHBoxLayout` container.
- [ ] Keep the navigation fixed width and page stack expanding.
- [ ] Increase navigation font and row height in the stylesheet.
- [ ] Run focused tests and confirm pass.

### Task 3: Refined stock operation dialog

**Files:**
- Modify: `tests/test_dialogs.py`
- Modify: `src/partbox/ui/stock_dialog.py`
- Modify: `src/partbox/ui/theme.py`

**Interfaces:**
- Consumes: component name, current stock, unit, operation mode
- Produces: semantic title, stock card, unit-suffixed quantity input, notes hint, live change preview, styled confirm button

- [ ] Add UI tests for object names, labels, suffix, placeholder, live preview, and mode-specific confirm text.
- [ ] Run focused tests and confirm failure against the plain form dialog.
- [ ] Build header, current-stock card, form controls, preview card, and action buttons with semantic object names.
- [ ] Preserve `apply_change()` service calls and failure handling.
- [ ] Add scoped dialog styles to the global theme.
- [ ] Run focused and full tests.

### Task 4: Visual review and desktop delivery

**Files:**
- Build: `dist/PartBOX.exe`
- Update: `C:\Users\lenovo\Desktop\PartBOX`

**Interfaces:**
- Produces: reviewed import, main, and stock-dialog screenshots plus verified packaged desktop application

- [ ] Render the main interface and confirm no nav-content gap.
- [ ] Render new-only and mixed import preview dialogs.
- [ ] Render both stock-in and stock-out dialogs.
- [ ] Request code review and resolve all Critical or Important findings.
- [ ] Run full tests, build, and smoke-test both source and desktop EXEs.
- [ ] Verify shortcut, EXE hash, source revision, and clean status.
