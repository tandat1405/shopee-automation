import csv
import io
import os

import requests


class SheetsError(Exception):
    pass


class SheetsClient:
    def __init__(self):
        self._url = os.environ["GOOGLE_SHEET_CSV_URL"]

    def get_items(self) -> list[dict]:
        try:
            resp = requests.get(self._url, timeout=30)
            resp.raise_for_status()
        except requests.exceptions.RequestException as e:
            raise SheetsError(f"Failed to fetch sheet: {e}") from e

        reader = csv.DictReader(io.StringIO(resp.text))
        items = []
        for row in reader:
            items.append({
                "item_id": row["item_id"].strip(),
                "name": row["name"].strip(),
                "image_url": row["image_url"].strip(),
                "item_url": row["item_url"].strip(),
                "create_time": int(row["create_time"].strip()),
            })

        if not items:
            raise SheetsError("Google Sheet is empty — no products found")

        return items
