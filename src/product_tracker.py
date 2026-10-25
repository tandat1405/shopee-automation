import json
import os
import tempfile
from datetime import datetime, timezone


class ProductTracker:
    def __init__(self, data_path: str):
        self._data_path = data_path
        with open(data_path, "r", encoding="utf-8") as f:
            self._data = json.load(f)

    def select_next(self, items: list[dict]) -> dict | None:
        if not items:
            return None

        posted_ids = {entry["item_id"] for entry in self._data["posted"]}
        unposted = [item for item in items if item["item_id"] not in posted_ids]

        if not unposted:
            self._data["posted"] = []
            self._data["last_cycle_reset"] = datetime.now(timezone.utc).isoformat()
            self._write()
            unposted = list(items)

        return max(unposted, key=lambda x: x["create_time"])

    def mark_posted(self, item_id: str, threads_post_id: str) -> None:
        self._data["posted"].append({
            "item_id": item_id,
            "posted_at": datetime.now(timezone.utc).isoformat(),
            "threads_post_id": threads_post_id,
        })
        self._write()

    def _write(self) -> None:
        dir_name = os.path.dirname(self._data_path)
        fd, tmp_path = tempfile.mkstemp(dir=dir_name or ".", suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(self._data, f, ensure_ascii=False, indent=2)
            os.replace(tmp_path, self._data_path)
        except Exception:
            os.unlink(tmp_path)
            raise
