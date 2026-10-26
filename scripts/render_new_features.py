from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

from partbox.app import build_application
from partbox.bom import BomLine, ParsedBom
from partbox.ui.bom_optimizer import BomOptimizerDialog


def render(output_dir: Path) -> int:
    with TemporaryDirectory() as temp_dir:
        os.environ["PARTBOX_DATA_DIR"] = temp_dir
        app, window, services = build_application([])
        now = "2026-08-27 12:00:00"
        samples = [
            ("C25804", "贴片电阻", "100kΩ ±5% 100mW", "0603", "FOJAN(富捷)", 6, 0.0123),
            ("C17414", "贴片电阻", "100kΩ ±1% 100mW", "0805", "UNI-ROYAL", 20, 0.0180),
            ("C1525", "贴片电容", "100nF ±10% 50V", "0603", "SAMSUNG", 30, 0.0250),
        ]
        batch_id = services.db.connection.execute(
            "INSERT INTO import_batches(filename,file_sha256,imported_at) VALUES('render.xlsx','render-sample',?) RETURNING id",
            (now,),
        ).fetchone()[0]
        component_ids = []
        for index, (code, kind, name, package, brand, stock, price) in enumerate(samples, 1):
            component_id = services.db.connection.execute(
                "INSERT INTO components(product_code,product_type,product_name,model,package,brand,current_stock,total_purchased,latest_unit_price,total_spent,created_at,updated_at) "
                "VALUES(?,?,?,?,?,?,?,?,?,?,?,?) RETURNING id",
                (code, kind, name, f"MODEL-{index}", package, brand, stock, stock + 10, price, price * (stock + 10), now, now),
            ).fetchone()[0]
            component_ids.append(int(component_id))
            for month, history_price in (("06", price * 1.25), ("07", price * 0.92), ("08", price)):
                services.db.connection.execute(
                    "INSERT INTO purchase_lines(component_id,batch_id,line_fingerprint,source_sheet,source_row,order_number,order_status,order_time,recipient,customer_part_number,product_code,brand,product_type,product_name,model,package,quantity,unit,unit_price,subtotal,shipping_date,courier,tracking_number,receipt_date,invoice_number,invoice_time,customer_representative,original_order,bom_flag,contract_number) "
                    "VALUES(?,?,?,'物料明细',2,?,'已完成',?,'','','',?,'',?,'',?,10,'个',?,?,'','','','','','','','','','')",
                    (component_id, batch_id, f"history-{component_id}-{month}", f"PO-{month}-{index}", f"2026-{month}-15 10:00:00", brand, name, package, history_price, history_price * 10),
                )
        services.db.connection.commit()
        services.comparison.add_components(component_ids)
        window.comparison_page.refresh()
        window.nav_list.setCurrentRow(1)
        window.show(); window.resize(1500, 900); app.processEvents()
        output_dir.mkdir(parents=True, exist_ok=True)
        window.grab().save(str(output_dir / "comparison.png"))

        parsed = ParsedBom(
            Path("示例控制板_BOM.xlsx"),
            "BOM",
            ["Comment", "Designator", "Footprint", "Quantity"],
            [
                BomLine(2, {}, 6, "R1-R6", "", "贴片电阻", "100K ±5% 100mW", "", "0603", "FOJAN"),
                BomLine(3, {}, 4, "R7-R10", "", "贴片电阻", "100K ±1% 100mW", "", "0603", "FOJAN"),
                BomLine(4, {}, 2, "C1,C2", "", "贴片电容", "1uF ±10% 25V", "", "0603", "SAMSUNG"),
            ],
        )
        dialog = BomOptimizerDialog(services.projects, parsed, window)
        dialog.project_name_edit.setText("示例控制板")
        dialog.next_step()
        dialog.match_table.selectRow(1)
        dialog.show(); dialog.resize(1240, 760); app.processEvents()
        dialog.grab().save(str(output_dir / "bom-matching.png"))
        for row_index, row in enumerate(dialog.workflow.rows):
            if row.unresolved:
                dialog.workflow.reject_candidates(row_index)
        dialog._render_matching()
        dialog.next_step(); app.processEvents()
        dialog.grab().save(str(output_dir / "bom-review.png"))
        services.db.close(); logging.shutdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(render(Path(sys.argv[1])))
