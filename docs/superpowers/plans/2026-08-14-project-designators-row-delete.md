# Project Designators and Row Delete Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add persistent editable project reference designators and a direct confirmed delete button to every project-component row.

**Architecture:** Extend `project_components` with a migrated `reference_designator` field and save it atomically beside project quantity. Track saved and draft designators in `ProjectsPage`, use a focused item delegate for vertical keyboard navigation, and bind each delete button to its stable component ID so sorting cannot redirect the action.

**Tech Stack:** Python 3.10, SQLite, PySide6, pytest, pytest-qt, PyInstaller.

## Global Constraints

- “保存元件配置” saves project quantities and reference designators only; it never changes inventory or creates operation history.
- A row delete requires confirmation and does not depend on checkbox selection.
- Deleting one row preserves unsaved quantities and designators on every remaining row.
- Existing PartBOX databases migrate automatically without losing project data.

---

### Task 1: Persist project reference designators

**Files:**
- Modify: `src/partbox/database.py`
- Modify: `src/partbox/projects.py`
- Test: `tests/test_projects.py`
- Test: `tests/test_auxiliary.py`

**Interfaces:**
- Consumes: `Database.initialize()`, `ProjectService.list_components(project_id)`.
- Produces: `project_components.reference_designator TEXT NOT NULL DEFAULT ''` and `ProjectService.save_configuration(project_id, quantities, reference_designators=None)`.

- [ ] **Step 1: Write failing migration and atomic-save tests**

```python
def test_database_migrates_project_reference_designator(project_env):
    db, _, _ = project_env
    columns = {row[1] for row in db.connection.execute("PRAGMA table_info(project_components)")}
    assert "reference_designator" in columns

def test_save_configuration_updates_designators_without_inventory(project_env):
    db, service, ids = project_env
    project_id = service.create_project("位号")
    service.add_components(project_id, ids)
    service.save_configuration(project_id, {ids[0]: 2, ids[1]: 3}, {ids[0]: "R1", ids[1]: "R2,R3"})
    rows = {row["id"]: row for row in service.list_components(project_id)}
    assert rows[ids[0]]["reference_designator"] == "R1"
    assert rows[ids[1]]["reference_designator"] == "R2,R3"
    assert db.connection.execute("SELECT COUNT(*) FROM stock_movements").fetchone()[0] == 0
```

- [ ] **Step 2: Run tests and verify RED**

Run: `$env:PYTHONPATH='src'; .\.venv\Scripts\python.exe -m pytest tests/test_projects.py -k "reference_designator or designators" -q`

Expected: FAIL because the column and save argument do not exist.

- [ ] **Step 3: Add schema migration and atomic persistence**

```python
reference_designator TEXT NOT NULL DEFAULT '',

component_columns = {row[1] for row in self.connection.execute("PRAGMA table_info(project_components)")}
if "reference_designator" not in component_columns:
    self.connection.execute(
        "ALTER TABLE project_components ADD COLUMN reference_designator TEXT NOT NULL DEFAULT ''"
    )
```

Update `list_components()` to select `pc.reference_designator`. Extend `save_configuration()` with `reference_designators: dict[int, str] | None = None`, validate that a supplied mapping has the same component IDs as `quantities`, normalize values with `str(value or "").strip()`, and update quantity plus designator inside the existing transaction.

- [ ] **Step 4: Run focused tests and verify GREEN**

Run: `$env:PYTHONPATH='src'; .\.venv\Scripts\python.exe -m pytest tests/test_projects.py tests/test_auxiliary.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```text
feat(projects): persist reference designators
```

### Task 2: Add editable designator draft and keyboard navigation

**Files:**
- Modify: `src/partbox/ui/projects_page.py`
- Modify: `src/partbox/ui/theme.py`
- Test: `tests/test_projects_ui.py`

**Interfaces:**
- Consumes: `ProjectService.save_configuration(project_id, quantities, reference_designators)` and `reference_designator` returned by `list_components()`.
- Produces: `REFERENCE_COLUMN`, `_saved_reference_designators`, `_draft_reference_designators`, and `ReferenceDesignatorDelegate`.

- [ ] **Step 1: Write failing UI draft/save tests**

```python
def test_project_reference_designator_is_editable_and_saved_with_configuration(...):
    item = page.component_table.item(row, REFERENCE_COLUMN)
    assert item.flags() & Qt.ItemIsEditable
    item.setText("R1,R2")
    assert page.save_configuration_button.isEnabled()
    assert service.list_components(project_id)[0]["reference_designator"] == ""
    page.save_configuration_button.click()
    assert service.list_components(project_id)[0]["reference_designator"] == "R1,R2"
```

Add a pytest-qt case that opens the designator editor, presses `Down`, and asserts that the current edited index is the next visible row in `REFERENCE_COLUMN`.

- [ ] **Step 2: Run the new UI tests and verify RED**

Run: `$env:PYTHONPATH='src'; .\.venv\Scripts\python.exe -m pytest tests/test_projects_ui.py -k "designator" -q`

Expected: FAIL because the column, draft state, and delegate do not exist.

- [ ] **Step 3: Implement the editable column and delegate**

Append `("reference_designator", "位号")` before the operation column. Keep all non-designator data read-only, enable `SelectedClicked | EditKeyPressed` edit triggers, and open the editor on the first designator click. Connect `itemChanged` to update `_draft_reference_designators` only for `REFERENCE_COLUMN`, include both draft maps in `has_unsaved_configuration()`, and pass both maps to `save_configuration()`. When the user chooses Discard, restore both saved maps before navigating away.

Implement `ReferenceDesignatorDelegate(QStyledItemDelegate)` so `Up`/`Down` commits the active editor and schedules `setCurrentCell(target_row, REFERENCE_COLUMN)` plus `editItem(...)` for the adjacent visible row.

- [ ] **Step 4: Style and size the designator column**

Set the designator width to 150 px and add a pale yellow editable-cell visual consistent with the project table.

- [ ] **Step 5: Run focused tests and verify GREEN**

Run: `$env:PYTHONPATH='src'; .\.venv\Scripts\python.exe -m pytest tests/test_projects_ui.py -k "designator or project_switch or close" -q`

Expected: PASS.

- [ ] **Step 6: Commit**

```text
feat(projects): edit BOM reference designators
```

### Task 3: Add stable per-row delete actions

**Files:**
- Modify: `src/partbox/ui/projects_page.py`
- Modify: `src/partbox/ui/theme.py`
- Test: `tests/test_projects_ui.py`

**Interfaces:**
- Consumes: `ProjectService.remove_components(project_id, component_ids)`.
- Produces: `ACTION_COLUMN`, `remove_component(component_id)`, and one `projectRowDeleteButton` per visible row.

- [ ] **Step 1: Write failing direct-delete tests**

```python
def test_project_row_delete_button_requires_confirmation(...):
    button = page.component_table.cellWidget(row, ACTION_COLUMN)
    monkeypatch.setattr(QMessageBox, "question", lambda *args, **kwargs: QMessageBox.No)
    button.click()
    assert page.component_table.rowCount() == 2

def test_project_row_delete_preserves_other_drafts_after_sort(...):
    page.component_table.sortItems(ID_COLUMN, Qt.DescendingOrder)
    other_stepper.setValue(4)
    other_designator.setText("R4")
    monkeypatch.setattr(QMessageBox, "question", lambda *args, **kwargs: QMessageBox.Yes)
    target_button.click()
    assert target_id not in {row["id"] for row in service.list_components(project_id)}
    assert page._draft_quantities[other_id] == 4
    assert page._draft_reference_designators[other_id] == "R4"
```

- [ ] **Step 2: Run delete tests and verify RED**

Run: `$env:PYTHONPATH='src'; .\.venv\Scripts\python.exe -m pytest tests/test_projects_ui.py -k "row_delete" -q`

Expected: FAIL because the action column and row buttons do not exist.

- [ ] **Step 3: Implement the operation column**

Append `("_action", "操作")`, create a 30 px `QToolButton` using `QStyle.SP_TrashIcon`, set tooltip and `componentId`, and connect with a stable `component_id` closure. Set the action column to 54 px.

- [ ] **Step 4: Implement confirmed deletion with draft restoration**

`remove_component(component_id)` shows a confirmation containing the product code/name. On Yes, snapshot remaining quantity/designator drafts, call `remove_components`, refresh the project, then reapply remaining draft values through the table widgets so save state and totals are restored. Remove the deleted ID from checkbox selection and the selection anchor.

- [ ] **Step 5: Run delete tests and verify GREEN**

Run: `$env:PYTHONPATH='src'; .\.venv\Scripts\python.exe -m pytest tests/test_projects_ui.py -k "delete" -q`

Expected: PASS.

- [ ] **Step 6: Commit**

```text
feat(projects): add per-row delete action
```

### Task 4: Documentation, regression verification, and desktop delivery

**Files:**
- Modify: `README.md`
- Modify: `使用说明.md`
- Verify: `scripts/render_projects.py`
- Verify: `scripts/build.ps1`
- Verify: `scripts/smoke_exe.ps1`

**Interfaces:**
- Consumes: completed project-page behavior.
- Produces: updated documentation, screenshot, packaged EXE, and desktop deployment.

- [ ] **Step 1: Document位号 and row delete behavior**

State that 位号 is saved by “保存元件配置”, `↑/↓` moves between designator cells, and the trash icon deletes one row after confirmation.

- [ ] **Step 2: Run full automated verification**

Run: `$env:PYTHONPATH='src'; .\.venv\Scripts\python.exe -m pytest -q`

Expected: all tests PASS.

- [ ] **Step 3: Render and inspect the project page**

Run: `$env:PYTHONPATH='src'; .\.venv\Scripts\python.exe scripts\render_projects.py artifacts\project-designators-row-delete.png`

Verify visually that 位号 and trash columns align with 36 px rows, the icon is legible, and the horizontal scrollbar remains usable.

- [ ] **Step 4: Build and smoke-test the EXE**

Run: `powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\build.ps1`

Run: `powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\smoke_exe.ps1 -Executable .\dist\PartBOX.exe`

Expected: build succeeds and packaged executable startup smoke passes.

- [ ] **Step 5: Deploy and verify desktop hashes**

Copy source, `dist\PartBOX.exe`, and `dist\main_window.ui` to `C:\Users\lenovo\Desktop\PartBOX`, preserve the existing user database, refresh `C:\Users\lenovo\Desktop\PartBOX.lnk`, run the desktop EXE smoke test, and verify SHA-256 equality between built and deployed EXEs.

- [ ] **Step 6: Commit documentation**

```text
docs: explain project row editing
```
