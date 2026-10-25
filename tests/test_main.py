from unittest.mock import patch, MagicMock

from src.main import main
from src.sheets_client import SheetsError
from src.threads_client import ThreadsAPIError

ITEM = {"item_id": "1", "name": "Kẹp tóc", "image_url": "http://img/1.jpg", "item_url": "http://shopee/1", "create_time": 1000}


def make_mocks(items=None, post_id="thread_post_1"):
    sheets = MagicMock()
    resolved_items = items if items is not None else [ITEM]
    sheets.get_items.return_value = resolved_items
    tracker = MagicMock()
    tracker.select_next.return_value = resolved_items[0] if resolved_items else None
    gen = MagicMock()
    gen.generate.return_value = "Nội dung test\n\n🛒 http://shopee/1"
    threads = MagicMock()
    threads.publish_post.return_value = post_id
    checker = MagicMock()
    checker.check_and_alert.return_value = []
    return sheets, tracker, gen, threads, checker


def test_main_happy_path():
    sheets, tracker, gen, threads, checker = make_mocks()
    with patch("src.main.SheetsClient", return_value=sheets), \
         patch("src.main.ProductTracker", return_value=tracker), \
         patch("src.main.ContentGenerator", return_value=gen), \
         patch("src.main.ThreadsClient", return_value=threads), \
         patch("src.main.TokenChecker", return_value=checker):
        main()
    threads.publish_post.assert_called_once()
    tracker.mark_posted.assert_called_once_with("1", "thread_post_1")


def test_main_skips_on_sheets_error():
    sheets = MagicMock()
    sheets.get_items.side_effect = SheetsError("fetch failed")
    checker = MagicMock()
    checker.check_and_alert.return_value = []
    with patch("src.main.SheetsClient", return_value=sheets), \
         patch("src.main.ProductTracker"), \
         patch("src.main.ContentGenerator"), \
         patch("src.main.ThreadsClient") as mock_threads, \
         patch("src.main.TokenChecker", return_value=checker):
        main()
    mock_threads.return_value.publish_post.assert_not_called()


def test_main_skips_on_empty_items():
    sheets, tracker, gen, threads, checker = make_mocks(items=[])
    tracker.select_next.return_value = None
    with patch("src.main.SheetsClient", return_value=sheets), \
         patch("src.main.ProductTracker", return_value=tracker), \
         patch("src.main.ContentGenerator", return_value=gen), \
         patch("src.main.ThreadsClient", return_value=threads), \
         patch("src.main.TokenChecker", return_value=checker):
        main()
    threads.publish_post.assert_not_called()
