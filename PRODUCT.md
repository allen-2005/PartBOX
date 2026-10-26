# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack

Windows desktop application implemented with Python 3.10+ and PySide6. The interface follows a desktop pointer-and-keyboard interaction model even though the product record schema uses the web-like interaction category.

## Users

The primary user is an electronics engineer, maker, or hardware hobbyist managing a personal component inventory and project BOMs during design, procurement, assembly, and restocking.

## Product Purpose

PartBOX helps users maintain an exact local record of electronic components, purchasing history, stock movement, project requirements, comparison candidates, and BOM shortages. Success means the user can confidently know what is available, what a project consumes, and what still needs purchasing without manually reconciling several spreadsheets.

## Positioning

PartBOX joins long-lived personal inventory records with project-specific BOM matching and deduction, preserving exact imported component descriptions while letting the user resolve similar-but-not-identical parts deliberately.

## Operating Context

Users work for long periods on a Windows desktop alongside LCSC/JLCPCB exports, BOM spreadsheets, PCB design tools, component drawers, and purchasing records. The interface is data-dense and frequently navigated with mouse, keyboard, sorting, multi-selection, inline editing, and horizontal tables.

## Capabilities and Constraints

- Import material-detail spreadsheets without normalizing or rewriting source field values.
- Manage stock in/out operations, inventory history, import history, component comparison, project configurations, reference designators, quantities, prices, and line deletion.
- Match a full BOM against exact inventory records, surface similar candidates for user confirmation, calculate shortages for multiple project copies, and export an LCSC-compatible remainder BOM.
- Preserve existing sorting, Shift-range selection, selection identity, inline quantity stepping, reference-designator keyboard navigation, and confirmation flows.
- Remain a local PySide6 desktop application and preserve existing functional behavior unless a separately approved usability correction requires a behavioral change.

## Brand Commitments

- Product name: PartBOX / 小料仓.
- Preserve the approved blue PartBOX and 小料仓 wordmarks stored under `assets/`.
- The default experience is Simplified Chinese.
- The interface should remain light, gentle, comfortable for long sessions, and recognizably technical without becoming visually harsh.

## Evidence on Hand

- Existing functional implementation under `src/partbox/`.
- Existing automated tests under `tests/`.
- Approved wordmark assets under `assets/partbox-wordmark-v1.png` and `assets/partbox-chinese-wordmark-v1.png`.
- Baseline UI renders under `.artifacts/ui-redesign-baseline/`.

## Product Principles

- Preserve exact source data and make user intent explicit.
- Favor scanning speed and predictable interaction over decoration.
- Keep high-density data readable during long work sessions.
- Make destructive, stock-changing, and irreversible actions visibly distinct.
- Improve visual consistency without regressing established workflows.

## Accessibility & Inclusion

Maintain readable Simplified Chinese typography, visible keyboard focus, clear selected and disabled states, sufficient text contrast, and interaction states that do not rely on color alone.
