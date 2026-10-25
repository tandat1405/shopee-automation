import os
from unittest.mock import patch

import pytest

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
