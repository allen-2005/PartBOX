# Project Quantity Stepper Fix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make project quantity arrows directly clickable and keep every table row aligned.

**Architecture:** Replace the embedded native spin box with a fixed-height composite widget that owns its mouse events. Keep quantity persistence and total calculations in the existing page methods.

**Tech Stack:** Python 3.10, PySide6, pytest-qt, PyInstaller.

## Global Constraints

- One arrow click changes quantity without preselecting a row.
- Arrow clicks must not select the table row.
- Quantity minimum is 1.
- Stepper height is 32px and table row height is 36px.

---

### Task 1: Direct-click compact stepper

**Files:**
- Modify: `tests/test_projects_ui.py`
- Modify: `src/partbox/ui/projects_page.py`
- Modify: `src/partbox/ui/theme.py`

**Interfaces:**
- Produces: `ProjectQuantityStepper(component_id: int, value: int)` with `value()`, `setValue(int)`, `increase_button`, and `decrease_button`.

- [ ] Write a pytest-qt test that mouse-clicks both buttons with no row selected and asserts quantity, selection count, minimum value, component ID, row height, and widget height.
- [ ] Run the focused test and confirm it fails because the current cell widget is `QSpinBox` and selects a row.
- [ ] Implement the compact stepper and exact table sizing.
- [ ] Run the focused test, all project tests, and the full suite.
- [ ] Render the project page and visually verify column alignment.
- [ ] Rebuild, smoke-test, and deploy the desktop EXE.
