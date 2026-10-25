import os

from google import genai


class ContentGenerator:
    MODEL = "gemini-1.5-flash"

    def __init__(self):
        self._client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

    def generate(self, item: dict) -> str:
        prompt = (
            f'Viết 2-3 dòng tiếng Việt ngắn gọn, tự nhiên để đăng lên Threads quảng cáo sản phẩm "{item["name"]}".\n'
            "Shop bán phụ kiện tóc và quà cho con gái (cột tóc, kẹp tóc, dán mái, sticker idol).\n"
            "Không dùng hashtag. Không emoji quá nhiều. Cuối bài KHÔNG thêm link."
        )
        try:
            raw = self._call_gemini(prompt)
        except Exception as e:
            raise ValueError(f"Gemini API error: {e}") from e
        if not raw or not raw.strip():
            raise ValueError("Gemini returned empty content")
        return f"{raw.strip()}\n\n🛒 {item['item_url']}"

    def _call_gemini(self, prompt: str) -> str:
        response = self._client.models.generate_content(model=self.MODEL, contents=prompt)
        return response.text
