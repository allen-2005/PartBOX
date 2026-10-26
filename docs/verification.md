# PartBOX Verification

Run from the project root:

```powershell
$env:PYTHONPATH='src'
$env:QT_QPA_PLATFORM='offscreen'
.\.venv\Scripts\python.exe -m pytest -q
.\scripts\build.ps1
.\scripts\smoke_exe.ps1 -Executable .\dist\PartBOX.exe
```

The supplied period statements are read-only format samples. Tests never copy them into the application or delivery directory. Packaged startup verification always sets `PARTBOX_DATA_DIR` to a fresh temporary directory. Project verification covers positive/negative delta synchronization, repeated no-op, atomic rollback, operation history, BOM parsing/matching/allocation/export, comparison persistence, and UI workflows.

Visual QA for the new comparison and BOM optimizer pages:

```powershell
$env:PYTHONPATH='src'
$env:QT_QPA_PLATFORM='offscreen'
.\.venv\Scripts\python.exe scripts\render_new_features.py .artifacts\new-features
```

## 2026-08-28 A 风格全界面复核

从仓库根目录执行：

```powershell
python -m pytest -q --tb=short
python scripts/render_ui.py .artifacts/a-style/round2/inventory-1440x820.png --width 1440 --height 820
python scripts/render_ui.py .artifacts/a-style/round2/inventory-1050x650.png --width 1050 --height 650
python scripts/render_projects.py .artifacts/a-style/round2/projects.png
python scripts/render_new_features.py .artifacts/a-style/round2/features
python scripts/render_dialogs.py .artifacts/a-style/round2/dialogs
```

测试结果：exit code 0，132 passed，6 skipped；跳过项仅为本机没有对应格式样例文件。四个渲染脚本均以 exit code 0 完成。

人工复核截图：

- `.impeccable/review/inventory-1440x820.png`（窗口逻辑尺寸 1440×820；系统缩放下按设备像素输出）
- `.impeccable/review/inventory-1050x650.png`（窗口逻辑尺寸 1050×650；系统缩放下按设备像素输出）
- `.impeccable/review/comparison.png`（物料对比）
- `.impeccable/review/projects.png`（我的项目）
- `.impeccable/review/bom.png`（BOM 缺料复核）
- `.impeccable/review/dialogs.png`（库存弹窗）

已检查 Logo 比例与清晰度、顶栏留白、六页背景身份、表头和行对齐、横向滚动、项目数量与位号行高、BOM 补货强调以及弹窗焦点状态。
