# Shopee × Threads Daily Auto-Post — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a GitHub Actions workflow that fetches a Shopee product daily, generates 2-3 lines of Vietnamese content via Gemini, and posts text + product image to Threads automatically.

**Architecture:** Five Python modules (`product_tracker`, `shopee_client`, `content_generator`, `threads_client`, `token_checker`) wired by `main.py`; a daily GitHub Actions cron job runs `main.py`, then commits the updated `posted.json` back to the repo. No external database — state lives in `data/posted.json`.

**Tech Stack:** Python 3.11+, `google-generativeai`, `requests`, GitHub Actions

**Spec:** `docs/superpowers/specs/2026-10-25-shopee-threads-automation-design.md`

## Global Constraints

- Python 3.11+; no paid APIs
- Gemini model: `gemini-2.0-flash-exp`
- Threads API base URL: `https://graph.threads.net/v1.0`
- Shopee API base URL: `https://partner.shopeemobile.com`
- Shopee signature: HMAC-SHA256 of `"{path}{partner_id}{timestamp}{access_token}"` (bytes, hex digest)
- GitHub Actions cron: `0 1 * * *` (= 08:00 GMT+7)
- All secrets from environment variables (see spec secrets table)
- Shopee token warning threshold: < 7 days remaining
- Threads token warning threshold: < 14 days remaining
- Email via Gmail SMTP on port 587 (TLS)
- `data/posted.json` committed + pushed by the Actions workflow after each successful post
- On Shopee API failure: log error, exit 0 (skip day, no crash)
- On Threads API failure: retry once after 5 seconds, then log and exit 0

## Review Focus

- **All Shopee products already posted:** `product_tracker.select_next()` must reset `posted.json` and return the newest product, not `None` — exercised in Task 1.
- **Threads container not ready:** `threads_client.publish_post()` must poll the container status before publishing (Threads API can return `IN_PROGRESS`) — exercised in Task 4.
- **Gemini returns empty or malformed content:** `content_generator.generate()` must raise `ValueError` on blank output so `main.py` can skip the day — exercised in Task 3.
- **Shopee image URL unreachable by Threads:** `threads_client` passes the raw CDN URL; if Threads rejects it (non-200 on container creation) the error must surface clearly — exercised in Task 4.
- **`SHOPEE_TOKEN_EXPIRY` / `THREADS_TOKEN_EXPIRY` secrets missing or malformed:** `token_checker` must fail gracefully (log warning, skip email) rather than crash — exercised in Task 5.

---

### Task 1: Project scaffold + ProductTracker

**Files:**
- Create: `src/product_tracker.py`
- Create: `data/posted.json`
- Create: `requirements.txt`
- Create: `tests/test_product_tracker.py`

**Interfaces:**
- Produces:
  - `ProductTracker(data_path: str)`
  - `tracker.select_next(items: list[dict]) -> dict` — returns one item `{"item_id": str, "name": str, "image_url": str, "item_url": str, "create_time": int}`; resets cycle if all posted
  - `tracker.mark_posted(item_id: str, threads_post_id: str) -> None`
  - `posted.json` initial structure: `{"posted": [], "last_cycle_reset": null}`

- [ ] **Step 1: Create `data/posted.json` with empty structure**

```json
{"posted": [], "last_cycle_reset": null}
```

- [ ] **Step 2: Create `requirements.txt`**

```
google-generativeai>=0.8.0
requests>=2.31.0
```

- [ ] **Step 3: Write failing tests**

```python
# tests/test_product_tracker.py
import json, os, pytest, tempfile
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
```

- [ ] **Step 4: Run tests to verify they fail**

```bash
pytest tests/test_product_tracker.py -v
```
Expected: `ImportError` or `ModuleNotFoundError`

- [ ] **Step 5: Implement `src/product_tracker.py`**

`__init__` loads `data_path` into `self._data`.
`select_next` filters out posted item_ids, if empty resets `posted` to `[]` and sets `last_cycle_reset` to now ISO, then picks item with max `create_time`.
`mark_posted` appends `{"item_id", "posted_at": now ISO, "threads_post_id"}` and writes file atomically (write temp + rename).

- [ ] **Step 6: Run tests to verify they pass**

```bash
pytest tests/test_product_tracker.py -v
```
Expected: 4 PASSED

- [ ] **Step 7: Commit**

```bash
git add src/product_tracker.py data/posted.json requirements.txt tests/test_product_tracker.py
git commit -m "feat: add ProductTracker with cycle-reset logic"
```

---

### Task 2: ShopeeClient

**Files:**
- Create: `src/shopee_client.py`
- Create: `tests/test_shopee_client.py`

**Interfaces:**
- Consumes: env vars `SHOPEE_PARTNER_ID`, `SHOPEE_PARTNER_KEY`, `SHOPEE_SHOP_ID`, `SHOPEE_ACCESS_TOKEN`
- Produces:
  - `ShopeeClient()` — reads config from env
  - `client.get_active_items() -> list[dict]` — returns list of `{"item_id": str, "name": str, "image_url": str, "item_url": str, "create_time": int}`; raises `ShopeeAPIError` on non-zero `error` field; returns `[]` if no items
  - `ShopeeAPIError(message: str)`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_shopee_client.py
import os, pytest
from unittest.mock import patch, MagicMock
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
        "has_next_page": False
    }
}

ITEM_DETAIL_RESPONSE = {
    "error": "",
    "response": {
        "item_list": [
            {"item_id": 111, "item_name": "Kẹp tóc A", "create_time": 1000, "image": {"image_url_list": ["http://img/111.jpg"]}},
            {"item_id": 222, "item_name": "Cột tóc B", "create_time": 2000, "image": {"image_url_list": ["http://img/222.jpg"]}},
        ]
    }
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_shopee_client.py -v
```

- [ ] **Step 3: Implement `src/shopee_client.py`**

Signature: `HMAC-SHA256` of `f"{path}{partner_id}{timestamp}{access_token}"` encoded as UTF-8, hex digest.
`_post(path, body)` builds URL `https://partner.shopeemobile.com{path}?partner_id=&shop_id=&timestamp=&access_token=&sign=`, POSTs JSON body, returns parsed JSON.
`get_active_items()` calls `/api/v2/item/get_item_list` (status `NORMAL`, page_size=100) then `/api/v2/item/get_item_base_info` for batch item details; builds `item_url` as `https://shopee.vn/product/{shop_id}/{item_id}`.
Handles pagination in `get_item_list` if `has_next_page` is true (keep fetching until false).

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_shopee_client.py -v
```
Expected: 2 PASSED

- [ ] **Step 5: Commit**

```bash
git add src/shopee_client.py tests/test_shopee_client.py
git commit -m "feat: add ShopeeClient with HMAC signing and pagination"
```

---

### Task 3: ContentGenerator

**Files:**
- Create: `src/content_generator.py`
- Create: `tests/test_content_generator.py`

**Interfaces:**
- Consumes: env var `GEMINI_API_KEY`; item dict from `ShopeeClient.get_active_items()`
- Produces:
  - `ContentGenerator()`
  - `generator.generate(item: dict) -> str` — returns 2-3 lines Vietnamese text ending with `item["item_url"]`; raises `ValueError` if Gemini returns empty/blank

- [ ] **Step 1: Write failing tests**

```python
# tests/test_content_generator.py
import os, pytest
from unittest.mock import patch, MagicMock
from src.content_generator import ContentGenerator

ITEM = {"item_id": "111", "name": "Kẹp tóc hoa xinh", "item_url": "https://shopee.vn/product/123/111", "image_url": "http://img/111.jpg", "create_time": 1000}

def test_generate_returns_text_with_link():
    with patch.dict(os.environ, {"GEMINI_API_KEY": "fakekey"}):
        gen = ContentGenerator()
        with patch.object(gen, "_call_gemini", return_value="Kẹp tóc dễ thương cho bé gái.\nThiết kế hoa cực xinh!\n"):
            result = gen.generate(ITEM)
    assert "shopee.vn" in result
    assert "Kẹp tóc" in result

def test_generate_raises_on_empty_response():
    with patch.dict(os.environ, {"GEMINI_API_KEY": "fakekey"}):
        gen = ContentGenerator()
        with patch.object(gen, "_call_gemini", return_value="   "):
            with pytest.raises(ValueError):
                gen.generate(ITEM)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_content_generator.py -v
```

- [ ] **Step 3: Implement `src/content_generator.py`**

`_call_gemini(prompt)` uses `google.generativeai` client with model `gemini-2.0-flash-exp` to generate content; returns `response.text`.
`generate(item)` builds prompt:
```
Viết 2-3 dòng tiếng Việt ngắn gọn, tự nhiên để đăng lên Threads quảng cáo sản phẩm "{item['name']}". 
Shop bán phụ kiện tóc và quà cho con gái (cột tóc, kẹp tóc, dán mái, sticker idol).
Không dùng hashtag. Không emoji quá nhiều. Cuối bài KHÔNG thêm link.
```
Appends `f"\n\n🛒 {item['item_url']}"` to Gemini output. Raises `ValueError` if `_call_gemini` returns blank/whitespace.

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_content_generator.py -v
```
Expected: 2 PASSED

- [ ] **Step 5: Commit**

```bash
git add src/content_generator.py tests/test_content_generator.py
git commit -m "feat: add ContentGenerator with Gemini 2.0 Flash"
```

---

### Task 4: ThreadsClient

**Files:**
- Create: `src/threads_client.py`
- Create: `tests/test_threads_client.py`

**Interfaces:**
- Consumes: env vars `THREADS_ACCESS_TOKEN`, `THREADS_USER_ID`
- Produces:
  - `ThreadsClient()`
  - `client.publish_post(text: str, image_url: str) -> str` — returns `threads_post_id`; polls container until status `FINISHED` (max 10 attempts × 3s); raises `ThreadsAPIError` on failure; retries full flow once on any error

- [ ] **Step 1: Write failing tests**

```python
# tests/test_threads_client.py
import os, pytest
from unittest.mock import patch, call
from src.threads_client import ThreadsClient, ThreadsAPIError

ENV = {"THREADS_ACCESS_TOKEN": "tok", "THREADS_USER_ID": "uid123"}

def test_publish_post_returns_post_id():
    with patch.dict(os.environ, ENV):
        client = ThreadsClient()
        with patch.object(client, "_post") as mock_post, \
             patch.object(client, "_get") as mock_get:
            mock_post.side_effect = [
                {"id": "container_abc"},
                {"id": "post_xyz"},
            ]
            mock_get.return_value = {"status": "FINISHED"}
            result = client.publish_post("Test text", "http://img/1.jpg")
    assert result == "post_xyz"

def test_raises_on_container_error():
    with patch.dict(os.environ, ENV):
        client = ThreadsClient()
        with patch.object(client, "_post", return_value={"error": {"message": "bad token"}}):
            with pytest.raises(ThreadsAPIError):
                client.publish_post("Text", "http://img/1.jpg")

def test_polls_until_finished():
    with patch.dict(os.environ, ENV):
        client = ThreadsClient()
        with patch.object(client, "_post") as mock_post, \
             patch.object(client, "_get") as mock_get, \
             patch("time.sleep"):
            mock_post.side_effect = [{"id": "c1"}, {"id": "p1"}]
            mock_get.side_effect = [{"status": "IN_PROGRESS"}, {"status": "IN_PROGRESS"}, {"status": "FINISHED"}]
            result = client.publish_post("Text", "http://img/1.jpg")
    assert result == "p1"
    assert mock_get.call_count == 3
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_threads_client.py -v
```

- [ ] **Step 3: Implement `src/threads_client.py`**

`_post(path, params)` sends `POST https://graph.threads.net/v1.0{path}` with `access_token` in params; returns JSON.
`_get(path, params)` sends `GET` to same base.
`_create_container(text, image_url)` POSTs to `/{user_id}/threads` with `media_type=IMAGE`, `image_url`, `text`; raises `ThreadsAPIError` if response has `"error"` key or no `"id"`.
`_poll_container(container_id)` GETs `/{container_id}?fields=status,error_message` every 3s up to 10 attempts; raises `ThreadsAPIError` if status is `ERROR` or max attempts exceeded.
`_publish(container_id)` POSTs to `/{user_id}/threads_publish` with `creation_id`; raises `ThreadsAPIError` if no `"id"`.
`publish_post(text, image_url)` calls create → poll → publish; on any `ThreadsAPIError` sleeps 5s and retries the full flow once; propagates error on second failure.

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_threads_client.py -v
```
Expected: 3 PASSED

- [ ] **Step 5: Commit**

```bash
git add src/threads_client.py tests/test_threads_client.py
git commit -m "feat: add ThreadsClient with two-step image post and retry"
```

---

### Task 5: TokenChecker + email alert

**Files:**
- Create: `src/token_checker.py`
- Create: `tests/test_token_checker.py`

**Interfaces:**
- Consumes: env vars `SHOPEE_TOKEN_EXPIRY` (ISO date string), `THREADS_TOKEN_EXPIRY` (ISO date string), `GMAIL_USER`, `GMAIL_APP_PASSWORD`, `ALERT_EMAIL`
- Produces:
  - `TokenChecker()`
  - `checker.check_and_alert() -> list[str]` — returns list of warning messages sent; sends email if any token within threshold; missing/malformed env vars log a warning and are skipped (no raise)

- [ ] **Step 1: Write failing tests**

```python
# tests/test_token_checker.py
import os, pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, MagicMock
from src.token_checker import TokenChecker

def iso(days_from_now):
    return (datetime.now(timezone.utc) + timedelta(days=days_from_now)).isoformat()

def test_no_alert_when_tokens_healthy():
    env = {
        "SHOPEE_TOKEN_EXPIRY": iso(10),
        "THREADS_TOKEN_EXPIRY": iso(20),
        "GMAIL_USER": "a@gmail.com", "GMAIL_APP_PASSWORD": "pw", "ALERT_EMAIL": "b@gmail.com"
    }
    with patch.dict(os.environ, env):
        checker = TokenChecker()
        with patch.object(checker, "_send_email") as mock_send:
            result = checker.check_and_alert()
    assert result == []
    mock_send.assert_not_called()

def test_alert_when_shopee_expiring():
    env = {
        "SHOPEE_TOKEN_EXPIRY": iso(3),
        "THREADS_TOKEN_EXPIRY": iso(20),
        "GMAIL_USER": "a@gmail.com", "GMAIL_APP_PASSWORD": "pw", "ALERT_EMAIL": "b@gmail.com"
    }
    with patch.dict(os.environ, env):
        checker = TokenChecker()
        with patch.object(checker, "_send_email") as mock_send:
            result = checker.check_and_alert()
    assert len(result) == 1
    assert "Shopee" in result[0]
    mock_send.assert_called_once()

def test_skips_missing_expiry_gracefully():
    env = {"GMAIL_USER": "a@gmail.com", "GMAIL_APP_PASSWORD": "pw", "ALERT_EMAIL": "b@gmail.com"}
    with patch.dict(os.environ, env, clear=True):
        checker = TokenChecker()
        result = checker.check_and_alert()
    assert result == []
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_token_checker.py -v
```

- [ ] **Step 3: Implement `src/token_checker.py`**

`check_and_alert()` reads `SHOPEE_TOKEN_EXPIRY` and `THREADS_TOKEN_EXPIRY` from env; parses as ISO datetime; computes days remaining; if days < 7 (Shopee) or < 14 (Threads) appends a warning string and calls `_send_email`; wraps each token check in `try/except` so malformed values only log a warning.
`_send_email(subject, body)` uses `smtplib.SMTP("smtp.gmail.com", 587)` with `starttls()` and `login(GMAIL_USER, GMAIL_APP_PASSWORD)` to send to `ALERT_EMAIL`.

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_token_checker.py -v
```
Expected: 3 PASSED

- [ ] **Step 5: Commit**

```bash
git add src/token_checker.py tests/test_token_checker.py
git commit -m "feat: add TokenChecker with email alert for expiring tokens"
```

---

### Task 6: main.py orchestrator

**Files:**
- Create: `src/main.py`
- Create: `tests/test_main.py`

**Interfaces:**
- Consumes: `ShopeeClient`, `ProductTracker`, `ContentGenerator`, `ThreadsClient`, `TokenChecker`
- Produces: `main()` — top-level entry point; exits 0 always (errors logged, not raised)

- [ ] **Step 1: Write failing tests**

```python
# tests/test_main.py
import pytest
from unittest.mock import patch, MagicMock
from src.main import main

def make_mocks(items=None, post_id="thread_post_1"):
    shopee = MagicMock()
    shopee.get_active_items.return_value = items or [
        {"item_id": "1", "name": "Kẹp tóc", "image_url": "http://img/1.jpg", "item_url": "http://shopee/1", "create_time": 1000}
    ]
    tracker = MagicMock()
    tracker.select_next.return_value = shopee.get_active_items.return_value[0]
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
    from src.shopee_client import ShopeeAPIError
    shopee = MagicMock()
    shopee.get_active_items.side_effect = ShopeeAPIError("API down")
    with patch("src.main.ShopeeClient", return_value=shopee), \
         patch("src.main.ProductTracker"), patch("src.main.ContentGenerator"), \
         patch("src.main.ThreadsClient"), patch("src.main.TokenChecker", return_value=MagicMock(check_and_alert=MagicMock(return_value=[]))):
        main()

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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_main.py -v
```

- [ ] **Step 3: Implement `src/main.py`**

`main()` sequence:
1. `TokenChecker().check_and_alert()` — always runs, errors logged only
2. `ShopeeClient().get_active_items()` — on `ShopeeAPIError` log and return
3. `ProductTracker("data/posted.json").select_next(items)` — if `None` log "no items" and return
4. `ContentGenerator().generate(item)` — on `ValueError` log and return
5. `ThreadsClient().publish_post(content, item["image_url"])` — on `ThreadsAPIError` log and return
6. `tracker.mark_posted(item["item_id"], post_id)`

`if __name__ == "__main__": main()`

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_main.py -v
```
Expected: 3 PASSED

- [ ] **Step 5: Run full test suite**

```bash
pytest tests/ -v
```
Expected: all tests PASSED

- [ ] **Step 6: Commit**

```bash
git add src/main.py tests/test_main.py
git commit -m "feat: add main orchestrator wiring all components"
```

---

### Task 7: GitHub Actions workflow

**Files:**
- Create: `.github/workflows/daily-post.yml`

**Interfaces:**
- Consumes: all GitHub Secrets from spec; `src/main.py` as entry point
- Produces: working cron workflow that runs daily, commits `data/posted.json`

- [ ] **Step 1: Create `.github/workflows/daily-post.yml`**

```yaml
name: Daily Shopee Post

on:
  schedule:
    - cron: '0 1 * * *'
  workflow_dispatch:

jobs:
  post:
    runs-on: ubuntu-latest
    permissions:
      contents: write

    steps:
      - uses: actions/checkout@v4
        with:
          token: ${{ secrets.GITHUB_TOKEN }}

      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Run daily post
        env:
          SHOPEE_PARTNER_ID: ${{ secrets.SHOPEE_PARTNER_ID }}
          SHOPEE_PARTNER_KEY: ${{ secrets.SHOPEE_PARTNER_KEY }}
          SHOPEE_SHOP_ID: ${{ secrets.SHOPEE_SHOP_ID }}
          SHOPEE_ACCESS_TOKEN: ${{ secrets.SHOPEE_ACCESS_TOKEN }}
          SHOPEE_TOKEN_EXPIRY: ${{ secrets.SHOPEE_TOKEN_EXPIRY }}
          THREADS_ACCESS_TOKEN: ${{ secrets.THREADS_ACCESS_TOKEN }}
          THREADS_USER_ID: ${{ secrets.THREADS_USER_ID }}
          THREADS_TOKEN_EXPIRY: ${{ secrets.THREADS_TOKEN_EXPIRY }}
          GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
          GMAIL_USER: ${{ secrets.GMAIL_USER }}
          GMAIL_APP_PASSWORD: ${{ secrets.GMAIL_APP_PASSWORD }}
          ALERT_EMAIL: ${{ secrets.ALERT_EMAIL }}
        run: python -m src.main

      - name: Commit updated posted.json
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add data/posted.json
          git diff --staged --quiet || git commit -m "chore: update posted.json [skip ci]"
          git push
```

- [ ] **Step 2: Initialize git repo and make first commit**

```bash
git init
git add .
git commit -m "feat: initial project structure"
```

- [ ] **Step 3: Create GitHub repo and push**

```bash
gh repo create shopee-automation --private --source=. --push
```

- [ ] **Step 4: Add all GitHub Secrets**

Go to repo → Settings → Secrets and variables → Actions → New repository secret, add each secret from the spec table.

`SHOPEE_TOKEN_EXPIRY` and `THREADS_TOKEN_EXPIRY` format: `2026-11-25T08:00:00+00:00` (ISO 8601).

- [ ] **Step 5: Trigger manual test run**

```bash
gh workflow run daily-post.yml
```

Watch logs:
```bash
gh run watch
```
Expected: workflow completes, `posted.json` gets a new commit.

- [ ] **Step 6: Commit workflow file**

Already committed in Step 2. Verify with:
```bash
git log --oneline -5
```
