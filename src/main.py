import logging
import os

from src.content_generator import ContentGenerator
from src.product_tracker import ProductTracker
from src.sheets_client import SheetsClient, SheetsError
from src.threads_client import ThreadsAPIError, ThreadsClient
from src.token_checker import TokenChecker

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "posted.json")


def main():
    try:
        TokenChecker().check_and_alert()
    except Exception as e:
        logger.error("TokenChecker failed: %s", e)

    try:
        items = SheetsClient().get_items()
    except SheetsError as e:
        logger.error("Google Sheet error, skipping today: %s", e)
        return

    tracker = ProductTracker(DATA_PATH)
    item = tracker.select_next(items)
    if item is None:
        logger.info("No items available, skipping today")
        return

    try:
        content = ContentGenerator().generate(item)
    except ValueError as e:
        logger.error("Content generation failed: %s", e)
        return

    try:
        post_id = ThreadsClient().publish_post(content, item["image_url"])
    except ThreadsAPIError as e:
        logger.error("Threads post failed: %s", e)
        return

    tracker.mark_posted(item["item_id"], post_id)
    logger.info("Posted item %s as Threads post %s", item["item_id"], post_id)


if __name__ == "__main__":
    main()
