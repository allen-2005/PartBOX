# PartBOX Project Configuration Workflow Design

## Goal

Refine the “我的项目” page so that it behaves as a persistent project BOM editor. “保存元件配置” stores the BOM configuration for the selected project, while “导出变更到元件库存” remains the only action that changes actual inventory and creates inventory-operation records.

## Core behavior

### Save project configuration

- Quantity-stepper edits are held as unsaved values on the current project page.
- The project total and each row subtotal update immediately from those visible values.
- “保存元件配置” writes the complete visible quantity mapping to `project_components.quantity` in one transaction.
- Saving never changes `components.current_stock`, never changes `project_components.synced_quantity`, and never creates inventory-movement or project-sync records.
- The save button is enabled only when the visible BOM differs from the last saved project configuration.
- After a successful save, the button remains labelled “保存元件配置” and returns to a disabled, visibly saved state without an interrupting modal.
- Changing projects with unsaved quantities asks whether to save, discard, or cancel the navigation. Closing the page/application uses the same protection.

### Export changes to inventory

- “导出变更到元件库存” operates only from the last saved project configuration.
- If the page has unsaved quantity changes, export is blocked with a clear instruction to save the component configuration first.
- After the configuration is saved, export compares `quantity` with `synced_quantity`, applies only the delta to inventory, updates `synced_quantity`, and records the operation exactly as it does now.
- Repeating export without a new saved change remains idempotent and never deducts inventory twice.

### Imported project components

- Components imported from the inventory page continue to be added to the selected project with a default project quantity of 1.
- Importing components does not deduct inventory.
- The imported component list is part of the project BOM; quantity edits become the saved BOM configuration when the user clicks “保存元件配置”.

## Layout

### Project sidebar

- Remove the page-wide top row containing “＋ 新建项目”, “重命名”, and “删除项目”.
- Keep rename and delete in the project-list context menu; remove the duplicate top buttons.
- Move “＋ 新建项目” to a full-width button pinned to the bottom of the project sidebar.
- Put “我的项目” and the collapse control in the same sidebar header row, with the control directly to the right of the title.
- When expanded, the sidebar is a fixed-width light panel. Project entries are compact rounded cards with a clear selected state, project name on the left, and component count on the right.
- When collapsed, hide the title, list, and new-project button; keep a narrow strip with the expand control so the sidebar can always be reopened.
- Continue persisting expanded/collapsed state through `QSettings`.

### Project action row

- Keep the current project name on the left.
- On the right, show these controls in order: project total, “保存元件配置”, “导出变更到元件库存”.
- Replace “删除选中元件” with “保存元件配置”.
- Use the existing restrained light palette: warm pale yellow for project configuration/save affordances, blue only for selection and primary emphasis, and neutral outline styling for inventory export.

## Data and error handling

- Add one project-service batch method that validates every quantity as an integer greater than or equal to 1 and updates all quantities in a single transaction.
- If any project/component row is missing or invalid, roll back the full save and keep the page dirty so the user can retry.
- Project switching is cancelled if saving fails.
- Existing context-menu project creation, rename, deletion rules, and inventory-sync rules remain unchanged.

## Testing

- Verify quantity edits do not touch the database until “保存元件配置” is clicked.
- Verify saving updates project quantities but not inventory, synced quantities, or operation history.
- Verify export is blocked while configuration is dirty, then changes inventory only after save.
- Verify the save button dirty/saved states and live totals.
- Verify top rename/delete/new buttons are absent, the bottom new-project button is present, and the collapse control is in the sidebar header.
- Verify sidebar state persistence and project-card selected styling.
- Run the complete automated suite, render the project page, inspect the image, build the Windows EXE, smoke-test it, and redeploy the desktop application.
