# Design: Shopee × Threads Daily Auto-Post

**Date:** 2026-10-25

## Intent

Tự động đăng 1 bài lên Threads mỗi ngày, nội dung 2-3 dòng tiếng Việt do AI sinh ra, kèm link sản phẩm Shopee. Shop bán phụ kiện tóc và quà tặng cho con gái (cột tóc, kẹp tóc, dán mái, sticker idol). Không cần thao tác thủ công hàng ngày.

## Goals

- Đăng 1 bài/ngày lên Threads tự động, không cần can thiệp thủ công
- Nội dung tự nhiên, ngắn gọn, phù hợp sản phẩm đang quảng cáo
- Ưu tiên sản phẩm mới hoặc chưa được đăng trước
- Khi hết sản phẩm mới thì xoay vòng lại từ đầu
- Chi phí vận hành = $0 (dùng free tier)

## Non-goals

- Không đăng nhiều hơn 1 lần/ngày
- Không tự động reply comment hay tương tác
- Không tự động tạo ảnh (dùng ảnh sẵn có từ Shopee CDN)
- Không quản lý nhiều shop hay nhiều tài khoản Threads

## Anti-goals

- Không dùng tool trả phí cho tác vụ AI (dùng Gemini free)
- Không cần dashboard hay giao diện quản lý
- Không lưu dữ liệu lên database bên ngoài

## Constraints

- Chạy trên GitHub Actions (free tier: 2000 phút/tháng — đủ dùng)
- Shopee Open Platform API: user đã có access, cần Partner ID, Partner Key, Shop ID, Access Token
- Threads API: Meta's official API, cần App ID + Access Token
- AI: Google Gemini 2.0 Flash API (miễn phí, 1500 req/ngày)
- Ngôn ngữ: Python 3.11+

## Architecture

### Components

```
GitHub Actions (cron: 0 1 * * *)   ← chạy 8h sáng GMT+7 mỗi ngày
         │
         ▼
  main.py (orchestrator)
    ├── shopee_client.py     ← Shopee Open Platform API
    ├── content_generator.py ← Google Gemini API
    ├── threads_client.py    ← Threads API
    └── product_tracker.py  ← đọc/ghi posted.json
```

### Data flow

1. `shopee_client.py` → gọi Shopee API lấy danh sách sản phẩm đang active
2. `product_tracker.py` → đọc `posted.json` trong repo, tìm sản phẩm chưa đăng (ưu tiên mới nhất theo `create_time`)
3. `content_generator.py` → gọi Gemini 2.0 Flash sinh 2-3 dòng text tiếng Việt cho sản phẩm đó, kèm link Shopee
4. `threads_client.py` → đăng bài lên Threads (text + ảnh sản phẩm từ Shopee CDN, dùng two-step container-then-publish flow của Threads API)
5. `product_tracker.py` → cập nhật `posted.json`, commit + push lên repo

### Product selection logic

- Lấy toàn bộ sản phẩm active từ Shopee
- Loại bỏ những sản phẩm đã có trong `posted.json`
- Nếu còn sản phẩm chưa đăng: chọn sản phẩm mới nhất (`create_time` cao nhất)
- Nếu tất cả đã đăng: reset `posted.json`, bắt đầu lại từ đầu

### posted.json structure

```json
{
  "posted": [
    {
      "item_id": "123456",
      "posted_at": "2026-10-25T08:00:00+07:00",
      "threads_post_id": "abc123"
    }
  ],
  "last_cycle_reset": "2026-10-25T08:00:00+07:00"
}
```

### GitHub Secrets required

| Secret name | Value |
|---|---|
| `SHOPEE_PARTNER_ID` | Partner ID từ Shopee Open Platform |
| `SHOPEE_PARTNER_KEY` | Partner Key |
| `SHOPEE_SHOP_ID` | Shop ID |
| `SHOPEE_ACCESS_TOKEN` | Access Token (có expiry — cần refresh thủ công hoặc auto) |
| `SHOPEE_REFRESH_TOKEN` | Refresh Token để auto-renew access token |
| `GEMINI_API_KEY` | Google AI Studio API key |
| `SHOPEE_REFRESH_TOKEN` | Refresh Token để tính expiry còn lại |
| `THREADS_ACCESS_TOKEN` | Threads long-lived access token |
| `THREADS_USER_ID` | Threads user ID |
| `THREADS_TOKEN_EXPIRY` | ISO date token hết hạn (để tính cảnh báo) |
| `GMAIL_USER` | Gmail address dùng để gửi cảnh báo |
| `GMAIL_APP_PASSWORD` | Gmail App Password (không phải mật khẩu chính) |
| `ALERT_EMAIL` | Địa chỉ email nhận cảnh báo |

### Token expiry warnings

Cả hai token đều cần refresh thủ công, hệ thống sẽ gửi email cảnh báo sớm:

- **Shopee Access Token** (~30 ngày): cảnh báo khi còn < 7 ngày
- **Threads Long-lived Token** (~60 ngày): cảnh báo khi còn < 14 ngày

Email gửi qua **GitHub Actions + `actions/send-mail`** (dùng Gmail SMTP). Thêm 2 secrets: `GMAIL_USER`, `GMAIL_APP_PASSWORD`, `ALERT_EMAIL` (địa chỉ nhận cảnh báo).

Refresh token thực hiện thủ công bởi user, sau đó cập nhật lại GitHub Secrets.

## File structure

```
shopee-automation/
├── .github/
│   └── workflows/
│       └── daily-post.yml
├── src/
│   ├── main.py
│   ├── shopee_client.py
│   ├── content_generator.py
│   ├── threads_client.py
│   └── product_tracker.py
├── data/
│   └── posted.json
├── requirements.txt
└── README.md
```

## Decisions made by builder

- Giờ chạy: 8:00 sáng giờ Việt Nam (UTC+7) = `0 1 * * *` UTC
- Gemini model: `gemini-2.0-flash-exp` (miễn phí, đủ mạnh)
- Token refresh: tự động via GitHub API, không cần thủ công
- Nếu Shopee API fail: skip ngày đó, log error, không crash
- Nếu Threads API fail: retry 1 lần, sau đó skip và log
