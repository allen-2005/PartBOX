# PartBOX Qt Designer UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 PartBOX 主窗口迁移为可由 Qt Designer 拖拽编辑、保存后运行时直接读取的 `.ui` 文件。

**Architecture:** `main_window.ui` 只负责静态控件树和布局；`MainWindow` 使用 `QUiLoader` 加载并按 `objectName` 绑定业务逻辑。开发版读取源码文件，打包版优先读取 EXE 同目录的外部文件，并以内置文件作为故障回退。

**Tech Stack:** Python 3.10、PySide6、Qt Designer、QUiLoader、PyInstaller、pytest-qt

## Global Constraints

- 不迁移或修改库存数据库。
- 现有主界面视觉和功能保持一致。
- 表头拖动、隐藏和排序持久化保持有效。
- 用户保存桌面 `.ui` 后无需重新打包即可在下次启动生效。

---

### Task 1: UI 资源定位与契约测试

**Files:**
- Create: `tests/test_designer_ui.py`
- Create: `src/partbox/ui/ui_loader.py`

**Interfaces:**
- Produces: `resolve_main_ui_path() -> Path`、`load_main_ui(parent) -> QMainWindow`

- [ ] 写失败测试，要求默认 `.ui` 存在、可加载且包含固定 objectName。
- [ ] 运行 `pytest tests/test_designer_ui.py -q`，确认因加载器或文件不存在而失败。
- [ ] 实现路径选择、契约验证和内置回退。
- [ ] 再次运行测试并确认通过。

### Task 2: 创建 Designer 主窗口并绑定业务逻辑

**Files:**
- Create: `src/partbox/ui/forms/main_window.ui`
- Modify: `src/partbox/ui/main_window.py`
- Modify: `tests/test_ui_smoke.py`

**Interfaces:**
- Consumes: `.ui` 中的固定 objectName。
- Produces: 与现有测试兼容的 MainWindow 属性和信号连接。

- [ ] 扩展 UI 冒烟测试，要求主窗口来自 `.ui` 且关键布局和现有功能不变。
- [ ] 运行定向测试并确认失败。
- [ ] 创建 `.ui` 控件树，删除 Python 中对应的静态布局构建代码，保留动态按钮、辅助页和业务连接。
- [ ] 运行 UI、表头、弹窗和服务测试并确认通过。

### Task 3: 外部编辑、打包与桌面交付

**Files:**
- Modify: `PartBOX.spec`
- Modify: `README.md`
- Modify: `scripts/build.ps1`
- Create: `scripts/open_designer.ps1`

**Interfaces:**
- Produces: EXE 同目录 `main_window.ui` 运行时覆盖、Designer 启动脚本与桌面快捷方式。

- [ ] 添加无效外部文件回退测试并确认失败。
- [ ] 将 `.ui` 加入 PyInstaller datas，完成 EXE 同目录优先加载与回退。
- [ ] 在 README 写明可改属性、不能删除的关键控件及保存后重启规则。
- [ ] 运行全量测试、渲染截图、PyInstaller 构建和打包 EXE 启动测试。
- [ ] 同步桌面代码、`.ui`、说明和 EXE，创建快捷方式并打开 Designer。
