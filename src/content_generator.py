import os

from google import genai


class ContentGenerator:
    MODELS = ["gemini-3.6-flash", "gemini-3.8-flash", "gemini-2.5-flash"]

    def __init__(self):
        self._client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

    MAX_TEXT_LENGTH = 490

    def generate(self, item: dict) -> str:
        prompt = (
            f'Viết đúng 30-50 từ tiếng Việt tự nhiên để đăng lên Threads quảng cáo sản phẩm "{item["name"]}".\n'
            "Shop bán phụ kiện tóc và quà cho con gái (cột tóc, kẹp tóc, dán mái, sticker idol).\n"
            "Thêm 1-2 emoji phù hợp xen vào trong câu. Viết 1 đoạn hoàn chỉnh, câu kết phải trọn nghĩa.\n"
            "Cuối bài thêm đúng 3 hashtag: bắt buộc có #viral, kèm 2 hashtag tiếng Việt phù hợp với sản phẩm.\n"
            "KHÔNG dùng **bold**, KHÔNG thêm link, KHÔNG liệt kê nhiều lựa chọn."
        )
        last_error = None
        raw = None
        for model in self.MODELS:
            try:
                raw = self._call_gemini(prompt, model)
                break
            except Exception as e:
                last_error = e
        if raw is None:
            raise ValueError(f"Gemini API error: {last_error}") from last_error
        if not raw or not raw.strip():
            raise ValueError("Gemini returned empty content")
        link = f"\n\n🛒 {item['item_url']}"
        text = raw.strip()
        if len(text) + len(link) > self.MAX_TEXT_LENGTH:
            last_sentence = max(text.rfind("。"), text.rfind("."), text.rfind("!"), text.rfind("?"))
            text = text[: last_sentence + 1] if last_sentence > 0 else text[: self.MAX_TEXT_LENGTH - len(link)]
        return f"{text}{link}"

    def _call_gemini(self, prompt: str, model: str) -> str:
        response = self._client.models.generate_content(model=model, contents=prompt)
        return response.text
