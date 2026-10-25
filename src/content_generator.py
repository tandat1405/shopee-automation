import os

from google import genai


class ContentGenerator:
    MODEL = "gemini-3.6-flash"

    def __init__(self):
        self._client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

    MAX_TEXT_LENGTH = 490

    def generate(self, item: dict) -> str:
        prompt = (
            f'Viết ĐÚNG 2-3 dòng tiếng Việt ngắn gọn, tự nhiên để đăng lên Threads quảng cáo sản phẩm "{item["name"]}".\n'
            "Shop bán phụ kiện tóc và quà cho con gái (cột tóc, kẹp tóc, dán mái, sticker idol).\n"
            "Chỉ viết 1 đoạn duy nhất, KHÔNG liệt kê nhiều lựa chọn, KHÔNG dùng **bold**, KHÔNG hashtag, KHÔNG thêm link."
        )
        try:
            raw = self._call_gemini(prompt)
        except Exception as e:
            raise ValueError(f"Gemini API error: {e}") from e
        if not raw or not raw.strip():
            raise ValueError("Gemini returned empty content")
        link = f"\n\n🛒 {item['item_url']}"
        text = raw.strip()
        if len(text) + len(link) > self.MAX_TEXT_LENGTH:
            text = text[: self.MAX_TEXT_LENGTH - len(link) - 3] + "..."
        return f"{text}{link}"

    def _call_gemini(self, prompt: str) -> str:
        response = self._client.models.generate_content(model=self.MODEL, contents=prompt)
        return response.text
