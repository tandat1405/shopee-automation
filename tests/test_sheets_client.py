import os
from unittest.mock import patch, MagicMock

import pytest

from src.sheets_client import SheetsClient, SheetsError

CSV_DATA = "item_id,name,image_url,item_url,create_time\n1,Kẹp tóc hoa,http://img/1.jpg,https://shopee.vn/1,1\n2,Cột tóc pastel,http://img/2.jpg,https://shopee.vn/2,2\n"
ENV = {"GOOGLE_SHEET_CSV_URL": "https://docs.google.com/spreadsheets/d/fake/pub?output=csv"}


def test_get_items_returns_parsed_list():
    with patch.dict(os.environ, ENV):
        client = SheetsClient()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = CSV_DATA
        mock_resp.raise_for_status = MagicMock()
        with patch("requests.get", return_value=mock_resp):
            items = client.get_items()
    assert len(items) == 2
    assert items[0]["item_id"] == "1"
    assert items[0]["name"] == "Kẹp tóc hoa"
    assert items[0]["create_time"] == 1
    assert "image_url" in items[0]
    assert "item_url" in items[0]


def test_raises_on_fetch_error():
    import requests as req
    with patch.dict(os.environ, ENV):
        client = SheetsClient()
        with patch("requests.get", side_effect=req.exceptions.ConnectionError("fail")):
            with pytest.raises(SheetsError):
                client.get_items()


def test_raises_on_empty_sheet():
    with patch.dict(os.environ, ENV):
        client = SheetsClient()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = "item_id,name,image_url,item_url,create_time\n"
        mock_resp.raise_for_status = MagicMock()
        with patch("requests.get", return_value=mock_resp):
            with pytest.raises(SheetsError):
                client.get_items()
