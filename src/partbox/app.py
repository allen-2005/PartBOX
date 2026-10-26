from __future__ import annotations

import logging
import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtGui import QFont, QFontDatabase, QIcon

from partbox.database import Database
from partbox.paths import AppPaths
from partbox.services import DataService, ImportService, InventoryService, StockService
from partbox.projects import ProjectService
from partbox.ui.main_window import MainWindow, ServiceContainer


def _asset_path(filename: str) -> Path:
    bundle_root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[2]))
    return bundle_root / "assets" / filename


def build_application(argv=None):
    app = QApplication.instance() or QApplication(argv or sys.argv)
    app.setWindowIcon(QIcon(str(_asset_path("partbox.ico"))))
    if sys.platform == "win32":
        windows_dir = Path(__import__("os").environ.get("WINDIR", r"C:\Windows"))
        for filename in ("msyh.ttc", "msyhbd.ttc", "msyhl.ttc"):
            font_path = windows_dir / "Fonts" / filename
            if font_path.exists():
                QFontDatabase.addApplicationFont(str(font_path))
        app.setFont(QFont("Microsoft YaHei UI", 9))
    app.setApplicationName("小料仓 PartBOX")
    app.setOrganizationName("PartBOX")
    paths = AppPaths.default(); paths.ensure()
    logging.basicConfig(filename=paths.logs / "partbox.log", level=logging.INFO, encoding="utf-8", format="%(asctime)s %(levelname)s %(message)s")
    db = Database(paths.database); db.initialize()
    services = ServiceContainer(
        db=db,
        inventory=InventoryService(db),
        importer=ImportService(db, paths.backups),
        stocks=StockService(db),
        data=DataService(db),
        paths=paths,
        projects=ProjectService(db),
    )
    return app, MainWindow(services), services


def main() -> int:
    try:
        app, window, services = build_application()
        app.aboutToQuit.connect(services.db.close)
        window.show()
        return app.exec()
    except Exception as error:
        logging.exception("PartBOX startup failed")
        app = QApplication.instance() or QApplication(sys.argv)
        QMessageBox.critical(None, "PartBOX 启动失败", f"程序无法启动：\n{error}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
