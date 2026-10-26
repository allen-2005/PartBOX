# PartBOX Qt Designer UI 设计规格

## 目标

让用户直接用 Qt Designer 打开并拖拽修改 PartBOX 主界面，体验接近修改 PPT。保存 `.ui` 后，下次启动 PartBOX 即使用新布局，不需要手工转换 Python 代码。

## 范围

- 将主窗口的顶栏、Logo、搜索区、左侧导航、库存页、分类区、四张统计卡、元件表和右侧摘要面板迁移至 `main_window.ui`。
- 业务逻辑、数据库、订单导入、库存操作、动态分类按钮、辅助页面以及可持久化表头继续由 Python 管理。
- 导入和入库／出库弹窗不在本次迁移范围内。

## 文件与加载规则

- 源码默认界面位于 `src/partbox/ui/forms/main_window.ui`。
- 开发运行时直接加载源码 `.ui`。
- 桌面交付时复制为 `C:\Users\lenovo\Desktop\PartBOX\main_window.ui`，打包后的程序优先加载 EXE 同目录的该文件。
- 外部 `.ui` 缺失或无法加载时，程序读取打包内置副本并记录日志，库存数据库不受影响。

## 控件契约

Python 通过固定 `objectName` 绑定业务控件。用户可修改位置、布局、尺寸、字体、颜色和文案，但不应删除或重命名这些对象：`brandEnglish`、`brandChinese`、`searchInput`、`clearFilterButton`、`importButton`、`navigation`、`pages`、`inventoryPage`、`filterScroll`、`filterBar`、四个统计值标签、`componentTable`、`summaryPanel`、`summaryTitle`、七个摘要值标签、`stockInButton`、`stockOutButton`、`historyButton`。

程序启动时验证契约；外部文件缺少必要控件时自动使用内置界面。

## Designer 入口

- 桌面创建 `编辑 PartBOX 界面.lnk`。
- 快捷方式使用项目环境的 `pyside6-designer.exe` 打开桌面 `main_window.ui`。
- 用户在 Designer 中保存，然后重启 PartBOX 查看效果。

## 验证

- 测试 `.ui` 可被 `QUiLoader` 加载且关键控件齐全。
- 测试 MainWindow 使用 `.ui` 后保留筛选、统计、表格编辑、导航和弹窗入口。
- 测试无效外部 `.ui` 会回退到内置界面。
- 运行全量测试、截图检查、打包及 EXE 启动检查。
