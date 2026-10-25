import os
from unittest.mock import patch, MagicMock

import pytest

from src.shopee_client import ShopeeClient, ShopeeAPIError

ENV = {
    "SHOPEE_PARTNER_ID": "12345",
    "SHOPEE_PARTNER_KEY": "testkey",
    "SHOPEE_SHOP_ID": "67890",
    "SHOPEE_ACCESS_TOKEN": "token123",
}

ITEM_LIST_RESPONSE = {
    "error": "",
    "response": {
        "item": [{"item_id": 111}, {"item_id": 222}],
        "has_next_page": False,
    },
}

ITEM_DETAIL_RESPONSE = {
    "error": "",
    "response": {
        "item_list": [
            {
                "item_id": 111,
                "item_name": "Kẹp tóc A",
                "create_time": 1000,
                "image": {"image_url_list": ["http://img/111.jpg"]},
            },
            {
                "item_id": 222,
                "item_name": "Cột tóc B",
                "create_time": 2000,
                "image": {"image_url_list": ["http://img/222.jpg"]},
            },
        ]
    },
}


def test_get_active_items_returns_list():
    with patch.dict(os.environ, ENV):
        client = ShopeeClient()
        with patch.object(client, "_post") as mock_post:
            mock_post.side_effect = [ITEM_LIST_RESPONSE, ITEM_DETAIL_RESPONSE]
            items = client.get_active_items()
    assert len(items) == 2
    assert items[0]["item_id"] == "111"
    assert "image_url" in items[0]
    assert "item_url" in items[0]


def test_raises_on_api_error():
    with patch.dict(os.environ, ENV):
        client = ShopeeClient()
        with patch.object(client, "_post") as mock_post:
            mock_post.return_value = {"error": "error_auth", "message": "invalid token"}
            with pytest.raises(ShopeeAPIError):
                client.get_active_items()
