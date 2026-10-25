import hashlib
import hmac
import os
import time

import requests


class ShopeeAPIError(Exception):
    pass


class ShopeeClient:
    BASE_URL = "https://partner.shopeemobile.com"

    def __init__(self):
        self._partner_id = int(os.environ["SHOPEE_PARTNER_ID"])
        self._partner_key = os.environ["SHOPEE_PARTNER_KEY"]
        self._shop_id = int(os.environ["SHOPEE_SHOP_ID"])
        self._access_token = os.environ["SHOPEE_ACCESS_TOKEN"]

    def get_active_items(self) -> list[dict]:
        item_ids = self._fetch_all_item_ids()
        if not item_ids:
            return []
        return self._fetch_item_details(item_ids)

    def _fetch_all_item_ids(self) -> list[int]:
        item_ids = []
        offset = 0
        page_size = 100
        while True:
            response = self._post(
                "/api/v2/item/get_item_list",
                {"offset": offset, "page_size": page_size, "item_status": "NORMAL"},
            )
            if response.get("error"):
                raise ShopeeAPIError(response.get("message", response["error"]))
            data = response.get("response", {})
            for item in data.get("item", []):
                item_ids.append(item["item_id"])
            if not data.get("has_next_page", False):
                break
            offset += page_size
        return item_ids

    def _fetch_item_details(self, item_ids: list[int]) -> list[dict]:
        response = self._post(
            "/api/v2/item/get_item_base_info",
            {"item_id_list": item_ids},
        )
        if response.get("error"):
            raise ShopeeAPIError(response.get("message", response["error"]))
        result = []
        for item in response.get("response", {}).get("item_list", []):
            image_urls = item.get("image", {}).get("image_url_list", [])
            result.append({
                "item_id": str(item["item_id"]),
                "name": item.get("item_name", ""),
                "image_url": image_urls[0] if image_urls else "",
                "item_url": f"https://shopee.vn/product/{self._shop_id}/{item['item_id']}",
                "create_time": item.get("create_time", 0),
            })
        return result

    def _post(self, path: str, body: dict) -> dict:
        timestamp = int(time.time())
        sign = self._sign(path, timestamp)
        params = {
            "partner_id": self._partner_id,
            "shop_id": self._shop_id,
            "timestamp": timestamp,
            "access_token": self._access_token,
            "sign": sign,
        }
        resp = requests.post(
            f"{self.BASE_URL}{path}",
            params=params,
            json=body,
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()

    def _sign(self, path: str, timestamp: int) -> str:
        base_string = f"{path}{self._partner_id}{timestamp}{self._access_token}"
        return hmac.new(
            self._partner_key.encode("utf-8"),
            base_string.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
