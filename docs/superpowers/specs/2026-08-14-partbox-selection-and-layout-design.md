# PartBOX Selection And Layout Design

## Scope

This revision changes only the inventory and project-page interaction requested in the marked screenshots:

1. Remove the project table's `序号` column.
2. Support Shift + left-click range selection through the row checkboxes on both inventory and project tables.
3. Make the project-list pane collapsible, with its visibility saved between launches.
4. Rebuild the inventory summary row as four equal cards plus a pale-yellow `导入到项目` card aligned on the right.

## Interaction decisions

- A normal checkbox click toggles that component and establishes the range-selection anchor.
- Shift + click selects every currently visible component between the anchor and clicked row, inclusive. The anchor is stored by component ID, so sorting cannot make the range start from the wrong component.
- If the anchor is no longer visible after filtering, Shift + click behaves like a normal click and establishes a new anchor.
- The project-list pane uses a narrow edge button like the inventory detail pane. Collapsed/expanded state is persisted in `QSettings`.
- The four statistic cards remain blue, have identical dimensions, and use the order already present in the application. The project-import action becomes a fifth, pale-yellow card on the same row.

## Non-goals

- No database schema change.
- No changes to order import or exact field preservation.
- No changes to project quantity, price, subtotal, or export behavior.

## Verification

- Automated Qt tests cover removed sequence column, Shift-range selection before and after sorting, project-list visibility persistence, and equal-card layout.
- The full test suite, rendered inventory/project screenshots, packaged EXE smoke test, desktop deployment, hashes, and shortcut target are verified before handoff.
