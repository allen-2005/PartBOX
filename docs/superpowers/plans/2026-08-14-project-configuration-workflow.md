# PartBOX Project Configuration Workflow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn “我的项目” into an explicit BOM configuration editor whose save action never changes inventory, while retaining a separate inventory-export action and applying the approved sidebar layout.

**Architecture:** Add one transactional batch-save operation to `ProjectService`. Keep saved and draft quantity maps in `ProjectsPage`; steppers update only the draft and live totals, “保存元件配置” commits the project map, and inventory export rejects unsaved drafts. Recompose the project sidebar with an integrated header toggle, custom project rows, and a bottom new-project button.

**Tech Stack:** Python 3.10, PySide6, SQLite, pytest, pytest-qt, PyInstaller.

## Global Constraints

- “保存元件配置” may update only `project_components.quantity` and project metadata.
- Only “导出变更到元件库存” may update inventory, `synced_quantity`, or operation history.
- Preserve existing exact material-statement import behavior and project sync idempotence.
- Retain project rename/delete actions in the project-list context menu.
- Keep the existing light blue and pale yellow visual language.

---

### Task 1: Transactional project-configuration save

**Files:**
- Modify: `src/partbox/projects.py`
- Modify: `tests/test_projects.py`

**Interfaces:**
- Consumes: `ProjectService`, `project_components(project_id, component_id, quantity, synced_quantity)`.
- Produces: `ProjectService.save_configuration(project_id: int, quantities: dict[int, int]) -> None`.

- [ ] **Step 1: Write the failing service test**

```python
def test_save_configuration_updates_only_project_quantities(tmp_path):
    service, db, project_id, component_ids = make_project(tmp_path, count=2)
    before_stock = inventory_stock(db, component_ids)
    before_history = service.operation_history(project_id)
    service.save_configuration(project_id, {component_ids[0]: 3, component_ids[1]: 5})
    rows = {row["id"]: row for row in service.list_components(project_id)}
    assert [rows[value]["project_quantity"] for value in component_ids] == [3, 5]
    assert [rows[value]["synced_quantity"] for value in component_ids] == [0, 0]
    assert inventory_stock(db, component_ids) == before_stock
    assert service.operation_history(project_id) == before_history
```

- [ ] **Step 2: Run the test and verify RED**

Run: `$env:PYTHONPATH='src'; .\.venv\Scripts\python.exe -m pytest -q tests\test_projects.py -k save_configuration`

Expected: failure because `save_configuration` does not exist.

- [ ] **Step 3: Implement the batch transaction**

```python
def save_configuration(self, project_id: int, quantities: dict[int, int]) -> None:
    try:
        normalized = {int(component_id): int(quantity) for component_id, quantity in quantities.items()}
    except (TypeError, ValueError) as error:
        raise ProjectError("项目用量必须是大于等于 1 的整数") from error
    if any(quantity < 1 for quantity in normalized.values()):
        raise ProjectError("项目用量必须是大于等于 1 的整数")
    with self.db.transaction() as connection:
        existing = {
            int(row[0]) for row in connection.execute(
                "SELECT component_id FROM project_components WHERE project_id=?", (project_id,)
            )
        }
        if existing != set(normalized):
            raise ProjectError("项目元件配置已变化，请刷新后重试")
        timestamp = now_text()
        for component_id, quantity in normalized.items():
            connection.execute(
                "UPDATE project_components SET quantity=?,updated_at=? WHERE project_id=? AND component_id=?",
                (quantity, timestamp, project_id, component_id),
            )
        connection.execute("UPDATE projects SET updated_at=? WHERE id=?", (timestamp, project_id))
```

- [ ] **Step 4: Run project-service tests and verify GREEN**

Run: `$env:PYTHONPATH='src'; .\.venv\Scripts\python.exe -m pytest -q tests\test_projects.py`

Expected: all project-service tests pass.

- [ ] **Step 5: Commit**

```text
feat(projects): save BOM configuration in one transaction
```

### Task 2: Draft quantities and explicit save workflow

**Files:**
- Modify: `src/partbox/ui/projects_page.py`
- Modify: `src/partbox/ui/main_window.py`
- Modify: `tests/test_projects_ui.py`
- Modify: `tests/test_ui_smoke.py`

**Interfaces:**
- Consumes: `ProjectService.save_configuration`, `ProjectService.sync`.
- Produces: `ProjectsPage.has_unsaved_configuration() -> bool`, `save_configuration() -> bool`, and `confirm_unsaved_configuration() -> bool`.

- [ ] **Step 1: Write failing UI workflow tests**

```python
def test_quantity_edits_are_drafts_until_saved(qtbot, project_page):
    stepper = project_page.component_table.cellWidget(0, QUANTITY_COLUMN)
    stepper.setValue(4)
    assert project_page.has_unsaved_configuration()
    assert project_page.service.list_components(project_page.current_project_id)[0]["project_quantity"] == 1
    assert project_page.save_configuration_button.isEnabled()
    project_page.save_configuration_button.click()
    assert project_page.service.list_components(project_page.current_project_id)[0]["project_quantity"] == 4
    assert not project_page.has_unsaved_configuration()

def test_export_rejects_unsaved_configuration(qtbot, project_page, monkeypatch):
    project_page.component_table.cellWidget(0, QUANTITY_COLUMN).setValue(2)
    warnings = []
    monkeypatch.setattr(QMessageBox, "warning", lambda *args: warnings.append(args[2]))
    project_page.sync_project()
    assert warnings == ["请先保存元件配置，再导出变更到元件库存。"]
```

- [ ] **Step 2: Run focused UI tests and verify RED**

Run: `$env:PYTHONPATH='src'; .\.venv\Scripts\python.exe -m pytest -q tests\test_projects_ui.py -k "draft or export_rejects"`

Expected: failures because quantity changes still save immediately and no save-configuration button exists.

- [ ] **Step 3: Implement saved/draft maps and navigation protection**

```python
self._saved_quantities: dict[int, int] = {}
self._draft_quantities: dict[int, int] = {}

def has_unsaved_configuration(self) -> bool:
    return self._draft_quantities != self._saved_quantities

def save_configuration(self) -> bool:
    if not self.current_project_id or not self.has_unsaved_configuration():
        return True
    self.service.save_configuration(self.current_project_id, self._draft_quantities)
    self._saved_quantities = dict(self._draft_quantities)
    self._update_save_state()
    return True
```

Change the stepper callback to update `_draft_quantities`, row subtotal, and the live total only. Add Save/Discard/Cancel handling before project changes and application close. Block `sync_project()` while drafts are dirty.

- [ ] **Step 4: Run focused and full UI tests**

Run: `$env:PYTHONPATH='src'; .\.venv\Scripts\python.exe -m pytest -q tests\test_projects_ui.py tests\test_ui_smoke.py`

Expected: all project and main-window UI tests pass.

- [ ] **Step 5: Commit**

```text
feat(projects): separate BOM saves from stock export
```

### Task 3: Approved project-sidebar layout

**Files:**
- Modify: `src/partbox/ui/projects_page.py`
- Modify: `src/partbox/ui/theme.py`
- Modify: `tests/test_projects_ui.py`
- Modify: `README.md`
- Modify: `使用说明.md`

**Interfaces:**
- Consumes: `projectSidebar`, `projectList`, context-menu actions, save/export methods.
- Produces: `projectSidebarHeader`, `projectSidebarTitle`, `projectSidebarToggle`, `projectListRow`, `projectCountBadge`, `projectNewButton`, and `projectSaveButton` widgets.

- [ ] **Step 1: Write the failing layout test**

```python
def test_project_sidebar_matches_approved_layout(qtbot, project_page):
    assert project_page.findChild(QPushButton, "projectRenameButton") is None
    assert project_page.findChild(QPushButton, "projectDeleteButton") is None
    assert project_page.new_button.parent() is project_page.project_sidebar
    assert project_page.project_sidebar_toggle.parent() is project_page.project_sidebar
    assert project_page.save_configuration_button.text() == "保存元件配置"
    assert project_page.findChildren(QWidget, "projectListRow")
```

- [ ] **Step 2: Run the layout test and verify RED**

Run: `$env:PYTHONPATH='src'; .\.venv\Scripts\python.exe -m pytest -q tests\test_projects_ui.py -k approved_layout`

Expected: failure because controls still occupy the page-wide title row and list rows are plain text.

- [ ] **Step 3: Recompose the sidebar and action row**

Create an always-available sidebar shell. Put its title and toggle in one header layout, custom project name/count rows in the middle, and the full-width new-project button at the bottom. On collapse, reduce the shell width, hide title/list/new button, and leave the toggle visible. Remove the top rename/delete buttons and replace the former remove button with `projectSaveButton`.

- [ ] **Step 4: Apply restrained styling and update usage docs**

Add selectors for the sidebar shell, selected project cards, count badges, bottom new button, compact integrated toggle, and save button. Update the user documentation to distinguish project-configuration save from inventory export.

- [ ] **Step 5: Run UI tests and render the project page**

Run: `$env:PYTHONPATH='src'; .\.venv\Scripts\python.exe -m pytest -q tests\test_projects_ui.py`

Run: `$env:PYTHONPATH='src'; .\.venv\Scripts\python.exe scripts\render_projects.py artifacts\project-configuration-workflow.png`

Expected: tests pass and the screenshot matches the approved annotated layout.

- [ ] **Step 6: Commit**

```text
style(projects): refine project sidebar and actions
```

### Task 4: Verification and desktop delivery

**Files:**
- Build: `dist/PartBOX.exe`
- Deploy: `C:\Users\lenovo\Desktop\PartBOX\PartBOX.exe`

**Interfaces:**
- Consumes: all completed source and tests.
- Produces: verified desktop source, UI, executable, and shortcut target.

- [ ] **Step 1: Run the complete suite**

Run: `$env:PYTHONPATH='src'; .\.venv\Scripts\python.exe -m pytest -q`

Expected: zero failures.

- [ ] **Step 2: Request independent code review**

Review all commits against `410f4de`, fix every Critical/Important finding, and rerun the full suite.

- [ ] **Step 3: Build and smoke-test**

Run: `powershell.exe -ExecutionPolicy Bypass -File .\scripts\build.ps1`

Run: `powershell.exe -ExecutionPolicy Bypass -File .\scripts\smoke_exe.ps1 -Executable .\dist\PartBOX.exe`

Expected: the build exits 0 and the packaged application remains running long enough to initialize a new database.

- [ ] **Step 4: Deploy and verify hashes**

Copy current source/docs, `dist/main_window.ui`, and `dist/PartBOX.exe` to `C:\Users\lenovo\Desktop\PartBOX`; verify executable and UI SHA-256 equality and confirm `C:\Users\lenovo\Desktop\PartBOX.lnk` still targets the deployed executable.
