import os
from unittest.mock import patch

import pytest

from src.content_generator import ContentGenerator

ITEM = {
    "item_id": "111",
    "name": "Kẹp tóc hoa xinh",
    "item_url": "https://shopee.vn/product/123/111",
    "image_url": "http://img/111.jpg",
    "create_time": 1000,
}


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
