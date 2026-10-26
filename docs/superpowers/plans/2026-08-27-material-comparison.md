# PartBOX Material Comparison Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an unlimited, persistent component-comparison page with field highlighting and purchase-price history.

**Architecture:** Add a narrow `ComparisonService` over SQLite, a self-contained `ComparisonPage`, and a dependency-free `PriceHistoryChart`. `MainWindow` only coordinates inventory selection, navigation, and refresh signals.

**Tech Stack:** Python 3.10+, SQLite, PySide6, pytest, pytest-qt

## Global Constraints

- Preserve imported inventory display text exactly.
- No comparison-count limit; use horizontal scrolling.
- Use the current light blue-gray visual system and slightly darker same-hue cells for differences.
- Preserve all existing uncommitted user changes in the desktop worktree.

---

### Task 1: Restore the existing UI baseline

**Files:**
- Modify: `src/partbox/ui/forms/main_window.ui`
- Test: `tests/test_designer_ui.py`

**Interfaces:**
- Consumes: root `main_window.ui` card definition.
- Produces: valid `projectImportCard` and `projectImportButton` objects required by `MainWindow`.

- [ ] Add the missing `projectImportCard` item after the four statistic cards, matching root `main_window.ui`.
- [ ] Run `python -m pytest tests/test_designer_ui.py tests/test_ui_smoke.py -q` and confirm the pre-existing loader failures disappear.

### Task 2: Persist comparison membership and price history

**Files:**
- Modify: `src/partbox/database.py`
- Create: `src/partbox/comparison.py`
- Create: `tests/test_comparison.py`

**Interfaces:**
- Produces: `ComparisonService.add_components(ids) -> int`, `remove_components(ids) -> int`, `clear() -> None`, `list_components() -> list[dict]`, `price_history(ids) -> dict[int, list[dict]]`.

- [ ] Write failing tests for deduplicated insertion, removal, clearing, restart persistence, component ordering, and chronological price history.
- [ ] Run `python -m pytest tests/test_comparison.py -q` and confirm failures reference missing schema/service.
- [ ] Add `comparison_components(component_id INTEGER PRIMARY KEY REFERENCES components(id) ON DELETE CASCADE, added_at TEXT NOT NULL)` to schema and implement `ComparisonService` using parameterized SQL.
- [ ] Run `python -m pytest tests/test_comparison.py -q` and confirm all tests pass.

### Task 3: Build comparison page and chart

**Files:**
- Create: `src/partbox/ui/comparison_page.py`
- Modify: `src/partbox/ui/theme.py`
- Create: `tests/test_comparison_ui.py`

**Interfaces:**
- Consumes: `ComparisonService`.
- Produces: `ComparisonPage.refresh()`, `ComparisonPage.remove_selected()`, `ComparisonPage.clear_all()`, and `changed = Signal()`.

- [ ] Write failing UI tests that assert transposed rows, unlimited columns, horizontal scroll mode, persistent values, darker difference cells, removal, clearing, and plotted history points.
- [ ] Run `python -m pytest tests/test_comparison_ui.py -q` and confirm import/class failures.
- [ ] Implement `ComparisonPage` with `QTableWidget`, `SelectColumns`, `ScrollPerPixel`, pale base fill `#eef5ff`, difference fill `#d8e7ff`, and top actions.
- [ ] Implement `PriceHistoryChart.paintEvent()` with axes, per-component polylines, point markers, legend, empty state, and cached hover tooltips.
- [ ] Add scoped QSS rules and rerun `python -m pytest tests/test_comparison_ui.py -q`.

### Task 4: Integrate inventory selection and navigation

**Files:**
- Modify: `src/partbox/ui/forms/main_window.ui`
- Modify: `main_window.ui`
- Modify: `src/partbox/ui/main_window.py`
- Modify: `src/partbox/ui/ui_loader.py`
- Modify: `tests/test_designer_ui.py`
- Modify: `tests/test_ui_smoke.py`

**Interfaces:**
- Consumes: checked component IDs and `ComparisonPage`.
- Produces: “物料对比” navigation entry and “加入对比” inventory action.

- [ ] Update failing expectations from five to six navigation items and add assertions for `comparisonAddButton` and `ComparisonPage`.
- [ ] Add the new nav item after inventory and a same-size inventory action card/button.
- [ ] Instantiate `ComparisonService` and `ComparisonPage`; update page index routing for projects/history/imports/settings.
- [ ] Add `add_selected_to_comparison()` with a no-selection guard, refresh, navigation, and non-destructive confirmation text.
- [ ] Run `python -m pytest tests/test_comparison.py tests/test_comparison_ui.py tests/test_designer_ui.py tests/test_ui_smoke.py -q`.

### Task 5: Verify material comparison

**Files:**
- Modify: `scripts/render_ui.py` only if fixture navigation needs updating.
- Modify: `docs/verification.md`

- [ ] Run `python -m pytest -q` and record baseline skips separately from failures.
- [ ] Run the offscreen/render script and inspect inventory and comparison screenshots.
- [ ] Record behavior and commands in `docs/verification.md`.

