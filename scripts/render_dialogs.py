from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

from partbox.app import build_application
from partbox.ui.import_dialog import ImportDialog
from partbox.ui.stock_dialog import StockDialog


def render(output_dir: Path) -> int:
    with TemporaryDirectory() as temp_dir:
        os.environ["PARTBOX_DATA_DIR"] = temp_dir
        app, window, services = build_application([])
        samples = sorted(
            path
            for path in (Path.home() / "Desktop").rglob("*.xls")
            if path.name.startswith(
                (
                    "(20251015-20251215)",
                    "(20260506-20260806)",
                    "(20260701-20260806)",
                )
            )
        )
        preview = services.importer.preview(samples)
        output_dir.mkdir(parents=True, exist_ok=True)

        import_dialog = ImportDialog(services.importer, window)
        import_dialog.set_preview(preview)
        import_dialog.show()
        app.processEvents()
        import_dialog.grab().save(str(output_dir / "import-preview.png"))
        import_dialog.close()

        services.importer.commit(preview, {})
        components = services.inventory.list_components()
        if not components:
            now = "2026-08-28 10:00:00"
            services.db.connection.execute(
                "INSERT INTO components(product_code,product_type,product_name,model,package,brand,current_stock,total_purchased,latest_unit_price,total_spent,created_at,updated_at) "
                "VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                ("C25804", "贴片电阻", "100kΩ ±5% 100mW", "RC0603FR-07100KL", "0603", "FOJAN(富捷)", 6, 16, 0.0123, 0.1968, now, now),
            )
            services.db.connection.commit()
            components = services.inventory.list_components()
        component = components[0]
        for mode in ("in", "out"):
            stock_dialog = StockDialog(
                services.stocks,
                component["id"],
                component["model"] or component["product_name"],
                component["current_stock"],
                component["unit"],
                mode,
                window,
            )
            stock_dialog.show()
            app.processEvents()
            stock_dialog.grab().save(str(output_dir / f"stock-{mode}.png"))
            stock_dialog.close()

        services.db.close()
        logging.shutdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(render(Path(sys.argv[1])))
