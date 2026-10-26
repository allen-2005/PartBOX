# PartBOX Desktop Delivery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give PartBOX a clean image-only application icon and deliver the complete source, executable, manual, and desktop shortcut under `C:\Users\lenovo\Desktop\PartBOX`.

**Architecture:** Keep the generated transparent PNG as the editable source asset and derive a multi-size Windows ICO from it. Bundle the ICO into the PyInstaller one-file executable and set it on the Qt application at runtime. Copy the clean Git project to the desktop delivery folder, add the built EXE and manual, then create a Windows shortcut pointing to that EXE.

**Tech Stack:** Python 3.10, PySide6, PyInstaller, Pillow (asset conversion only), PowerShell, pytest-qt

## Global Constraints

- The icon contains no text, letters, or numbers.
- The delivery folder is exactly `C:\Users\lenovo\Desktop\PartBOX`.
- The desktop shortcut launches `C:\Users\lenovo\Desktop\PartBOX\PartBOX.exe`.
- User data remains in `%LOCALAPPDATA%\PartBOX`; packaging must not embed personal order data.

---

### Task 1: Icon assets and runtime icon

**Files:**
- Create: `assets/partbox-icon.png`
- Create: `assets/partbox.ico`
- Modify: `src/partbox/app.py`
- Modify: `tests/test_app_startup.py`

**Interfaces:**
- Consumes: `build_application(argv=None)`
- Produces: a non-null `QApplication.windowIcon()` and reusable PNG/ICO assets

- [ ] Add `assert not app.windowIcon().isNull()` to the startup test.
- [ ] Run `pytest tests/test_app_startup.py -q` and confirm it fails because no icon is installed.
- [ ] Add a PyInstaller-safe asset path helper and call `app.setWindowIcon(QIcon(...))`.
- [ ] Run the startup test again and confirm it passes.

### Task 2: Windows executable packaging

**Files:**
- Modify: `PartBOX.spec`
- Build: `dist/PartBOX.exe`

**Interfaces:**
- Consumes: `assets/partbox.ico`
- Produces: a one-file GUI executable with the PartBOX icon embedded

- [ ] Add the ICO to PyInstaller data files and the EXE `icon` setting.
- [ ] Run the complete pytest suite.
- [ ] Build with `scripts/build.ps1`.
- [ ] Run `scripts/smoke_exe.ps1` and confirm the packaged program starts.

### Task 3: Desktop delivery and shortcut

**Files:**
- Create: `C:\Users\lenovo\Desktop\PartBOX\...`
- Create: `C:\Users\lenovo\Desktop\小料仓 PartBOX.lnk`

**Interfaces:**
- Consumes: the clean Git checkout and `dist/PartBOX.exe`
- Produces: a self-contained source-and-binary delivery folder and launch shortcut

- [ ] Clone the current branch locally into the desktop folder.
- [ ] Copy the verified EXE and `README.md` as `使用说明.md`.
- [ ] Create the shortcut with the EXE as both launch target and icon source.
- [ ] Verify required files, shortcut target, EXE version/icon resources, and source cleanliness.
