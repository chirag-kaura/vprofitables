"""Read-only access to validated local analytical Parquet snapshots."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.paths import BASE_DIR

SNAPSHOT_ROOT = Path(BASE_DIR) / "data" / "analytics" / "daily_prices"


def _current_snapshot() -> tuple[dict[str, Any], str] | None:
    """Return the active snapshot manifest and Parquet file glob, if present."""
    pointer = SNAPSHOT_ROOT / "current.json"
    if not pointer.is_file():
        return None
    try:
        current = json.loads(pointer.read_text(encoding="utf-8"))
        snapshot_id = str(current["snapshot_id"])
        if Path(snapshot_id).name != snapshot_id:
            return None
        snapshot_dir = SNAPSHOT_ROOT / snapshot_id
        manifest_path = snapshot_dir / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("snapshot_id") != snapshot_id or manifest.get("dataset") != "daily_prices":
            return None
        files = manifest.get("files") or []
        if not files or any(
            not isinstance(item, dict)
            or Path(str(item.get("file", ""))).name != str(item.get("file", ""))
            or not str(item.get("file", "")).endswith(".parquet")
            or not (snapshot_dir / item["file"]).is_file()
            or (snapshot_dir / item["file"]).stat().st_size != int(item.get("bytes", -1))
            for item in files
        ):
            return None
        glob = str(snapshot_dir / "part-*.parquet")
        return manifest, glob
    except (OSError, ValueError, KeyError, TypeError):
        return None


def snapshot_status(
    required_source_date: str | None = None,
    required_source_updated_at: str | None = None,
) -> dict[str, Any]:
    """Small diagnostic object suitable for API provenance metadata."""
    active = _current_snapshot()
    if active is None:
        return {"available": False, "reason": "missing_or_invalid"}
    manifest, _ = active
    fresh = required_source_date is None or manifest.get("source_latest_trade_date", "") >= required_source_date
    if required_source_updated_at:
        snapshot_updated = manifest.get("source_latest_updated_at") or ""
        fresh = fresh and snapshot_updated >= required_source_updated_at
    return {
        "available": True,
        "fresh": fresh,
        "snapshot_id": manifest.get("snapshot_id"),
        "source_latest_trade_date": manifest.get("source_latest_trade_date"),
        "source_latest_updated_at": manifest.get("source_latest_updated_at"),
        "start_date": manifest.get("start_date"),
        "end_date": manifest.get("end_date"),
        "row_count": manifest.get("row_count"),
    }
