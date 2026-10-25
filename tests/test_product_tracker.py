import json
import os
import tempfile

import pytest

from src.product_tracker import ProductTracker

ITEMS = [
    {"item_id": "1", "name": "Kẹp tóc", "image_url": "http://img/1.jpg", "item_url": "http://shopee/1", "create_time": 1000},
    {"item_id": "2", "name": "Cột tóc", "image_url": "http://img/2.jpg", "item_url": "http://shopee/2", "create_time": 2000},
    {"item_id": "3", "name": "Dán mái", "image_url": "http://img/3.jpg", "item_url": "http://shopee/3", "create_time": 3000},
]


def make_tracker(initial=None):
    f = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
    json.dump(initial or {"posted": [], "last_cycle_reset": None}, f)
    f.close()
    return ProductTracker(f.name), f.name


def test_select_newest_unposted():
    tracker, path = make_tracker()
    item = tracker.select_next(ITEMS)
    assert item["item_id"] == "3"
    os.unlink(path)


def test_skip_already_posted():
    tracker, path = make_tracker({"posted": [{"item_id": "3", "posted_at": "2026-10-25T08:00:00+07:00", "threads_post_id": "x"}], "last_cycle_reset": None})
    item = tracker.select_next(ITEMS)
    assert item["item_id"] == "2"
    os.unlink(path)


def test_reset_when_all_posted():
    all_posted = {"posted": [{"item_id": str(i["item_id"]), "posted_at": "", "threads_post_id": "x"} for i in ITEMS], "last_cycle_reset": None}
    tracker, path = make_tracker(all_posted)
    item = tracker.select_next(ITEMS)
    data = json.loads(open(path).read())
    assert data["posted"] == []
    assert data["last_cycle_reset"] is not None
    assert item["item_id"] == "3"
    os.unlink(path)


def test_mark_posted_writes_file():
    tracker, path = make_tracker()
    tracker.select_next(ITEMS)
    tracker.mark_posted("3", "thread_abc")
    data = json.loads(open(path).read())
    assert data["posted"][0]["item_id"] == "3"
    assert data["posted"][0]["threads_post_id"] == "thread_abc"
    os.unlink(path)


def test_returns_none_for_empty_items():
    tracker, path = make_tracker()
    result = tracker.select_next([])
    assert result is None
    os.unlink(path)
