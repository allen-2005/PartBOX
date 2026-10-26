from __future__ import annotations

import os
import sys
import logging
import argparse
from pathlib import Path
from tempfile import TemporaryDirectory

from PySide6.QtCore import QTimer

from partbox.app import build_application
from partbox.importer import parse_statement


def main(output: Path, width: int = 1440, height: int = 820) -> int:
    with TemporaryDirectory() as temp_dir:
        os.environ["PARTBOX_DATA_DIR"] = temp_dir
        app, window, services = build_application([])
        base = Path.home() / "Desktop"
        samples = sorted(
            path for path in base.rglob("*.xls")
            if path.name.endswith("立创商城物料明细对账单.xls")
        )
        if samples:
            preview = services.importer.preview(samples, parser=parse_statement)
            services.importer.commit(preview, {})
        if not services.inventory.list_components():
            now = "2026-08-28 10:00:00"
            seeded = [
                ("C54876731", "排母", "1x2P 间距2.54mm 弯插 盒装", "PM2.54-1x2PWZ", "弯插,P=2.54mm", "SHOU HAN", 10, 0.1680),
                ("C7527659", "USB连接器", "Type-A 母 弯插 托盘", "XUBF-1071D-0201", "弯插", "LX(连欣科技)", 10, 0.8200),
                ("C48996818", "贴片电阻", "厚膜电阻 1.1kΩ ±1% 100mW 编带", "CL0603FN1K1P", "0603", "永龙科技", 50, 0.0153),
                ("C136658", "钽电容", "47uF ±10% 10V 编带", "CA45-B-10V-47uF-K", "CASE-B-3528-19(mm)", "XY(振华新云)", 6, 0.4546),
                ("C908543", "贴片电容(MLCC)", "±0.25pF 8.2pF 50V 编带", "MT18N8R2C500CT", "0603", "Walsin(华新科)", 20, 0.0760),
            ]
            for code, kind, name, model, package, brand, stock, price in seeded:
                services.db.connection.execute(
                    "INSERT INTO components(product_code,product_type,product_name,model,package,brand,current_stock,total_purchased,latest_unit_price,total_spent,created_at,updated_at) "
                    "VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                    (code, kind, name, model, package, brand, stock, stock, price, price * stock, now, now),
                )
            services.db.connection.commit()
        window.refresh()
        window.show()
        window.resize(width, height)
        app.processEvents()
        output.parent.mkdir(parents=True, exist_ok=True)
        window.grab().save(str(output))
        services.db.close()
        logging.shutdown()
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    parser.add_argument("--width", type=int, default=1440)
    parser.add_argument("--height", type=int, default=820)
    args = parser.parse_args()
    raise SystemExit(main(args.output, args.width, args.height))
