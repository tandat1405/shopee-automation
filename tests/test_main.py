from unittest.mock import patch, MagicMock

from src.main import main
from src.shopee_client import ShopeeAPIError
from src.threads_client import ThreadsAPIError


def make_mocks(items=None, post_id="thread_post_1"):
    shopee = MagicMock()
    shopee.get_active_items.return_value = items or [
        {"item_id": "1", "name": "Kẹp tóc", "image_url": "http://img/1.jpg", "item_url": "http://shopee/1", "create_time": 1000}
    ]
    tracker = MagicMock()
    tracker.select_next.return_value = shopee.get_active_items.return_value[0] if (items is None or items) else None
    gen = MagicMock()
    gen.generate.return_value = "Nội dung test\n\n🛒 http://shopee/1"
    threads = MagicMock()
    threads.publish_post.return_value = post_id
    checker = MagicMock()
    checker.check_and_alert.return_value = []
    return shopee, tracker, gen, threads, checker


def test_main_happy_path():
    shopee, tracker, gen, threads, checker = make_mocks()
    with patch("src.main.ShopeeClient", return_value=shopee), \
         patch("src.main.ProductTracker", return_value=tracker), \
         patch("src.main.ContentGenerator", return_value=gen), \
         patch("src.main.ThreadsClient", return_value=threads), \
         patch("src.main.TokenChecker", return_value=checker):
        main()
    threads.publish_post.assert_called_once()
    tracker.mark_posted.assert_called_once_with("1", "thread_post_1")


def test_main_skips_on_shopee_error():
    shopee = MagicMock()
    shopee.get_active_items.side_effect = ShopeeAPIError("API down")
    checker = MagicMock()
    checker.check_and_alert.return_value = []
    with patch("src.main.ShopeeClient", return_value=shopee), \
         patch("src.main.ProductTracker"), \
         patch("src.main.ContentGenerator"), \
         patch("src.main.ThreadsClient") as mock_threads, \
         patch("src.main.TokenChecker", return_value=checker):
        main()
    mock_threads.return_value.publish_post.assert_not_called()


def test_main_skips_on_empty_items():
    shopee, tracker, gen, threads, checker = make_mocks(items=[])
    tracker.select_next.return_value = None
    with patch("src.main.ShopeeClient", return_value=shopee), \
         patch("src.main.ProductTracker", return_value=tracker), \
         patch("src.main.ContentGenerator", return_value=gen), \
         patch("src.main.ThreadsClient", return_value=threads), \
         patch("src.main.TokenChecker", return_value=checker):
        main()
    threads.publish_post.assert_not_called()
