from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AppPaths:
    base: Path
    database: Path
    backups: Path
    logs: Path
    exports: Path

    @classmethod
    def for_base(cls, base: Path) -> "AppPaths":
        base = Path(base)
        return cls(
            base=base,
            database=base / "partbox.db",
            backups=base / "backups",
            logs=base / "logs",
            exports=base / "exports",
        )

    @classmethod
    def default(cls) -> "AppPaths":
        override = os.environ.get("PARTBOX_DATA_DIR")
        if override:
            return cls.for_base(Path(override))
        local = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        return cls.for_base(local / "PartBOX")

    def ensure(self) -> None:
        for path in (self.base, self.backups, self.logs, self.exports):
            path.mkdir(parents=True, exist_ok=True)
