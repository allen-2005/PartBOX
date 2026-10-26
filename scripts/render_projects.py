from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

from partbox.app import build_application
from partbox.importer import parse_statement


def render(output: Path) -> int:
    with TemporaryDirectory() as temp_dir:
        os.environ["PARTBOX_DATA_DIR"] = temp_dir
        app, window, services = build_application([])
        statements = sorted(
            path for path in (Path.home() / "Desktop").rglob("*.xls")
            if path.name.endswith("立创商城物料明细对账单.xls")
        )
        preview = services.importer.preview(statements, parser=parse_statement)
        services.importer.commit(preview, {})
        if not services.inventory.list_components():
            now = "2026-08-28 10:00:00"
            samples = [
                ("C2903232", "插件电阻", "金属膜电阻 10kΩ ±1% 250mW", "MF1/4W-10K", "插件,D2.7xL6.2mm", "VO(翔胜)", 20, 0.0320),
                ("C49256800", "直插铝电解电容", "2200uF ±20% 25V 袋装", "ERA25V2200M13X21", "插件,D13xL21mm", "JIERR(捷而瑞)", 8, 0.6240),
                ("C5213", "运算放大器", "双通道运算放大器 管装", "LM358P", "DIP-8", "TI(德州仪器)", 12, 1.1632),
            ]
            for code, kind, name, model, package, brand, stock, price in samples:
                services.db.connection.execute(
                    "INSERT INTO components(product_code,product_type,product_name,model,package,brand,current_stock,total_purchased,latest_unit_price,total_spent,created_at,updated_at) "
                    "VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                    (code, kind, name, model, package, brand, stock, stock, price, price * stock, now, now),
                )
            services.db.connection.commit()
        project_id = services.projects.create_project("开源电源复刻")
        component_ids = [row["id"] for row in services.inventory.list_components()[:8]]
        services.projects.add_components(project_id, component_ids)
        services.projects.save_configuration(
            project_id,
            {component_id: index for index, component_id in enumerate(component_ids, 1)},
            {component_id: f"R{index}" for index, component_id in enumerate(component_ids, 1)},
        )
        window.projects_page.refresh(project_id)
        window.nav_list.setCurrentRow(2)
        window.show(); window.resize(1440, 820); app.processEvents()
        scrollbar = window.projects_page.component_table.horizontalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
        app.processEvents()
        output.parent.mkdir(parents=True, exist_ok=True)
        window.grab().save(str(output))
        services.db.close(); logging.shutdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(render(Path(sys.argv[1])))
