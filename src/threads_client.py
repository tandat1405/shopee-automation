import os
import time

import requests


class ThreadsAPIError(Exception):
    pass


class ThreadsClient:
    BASE_URL = "https://graph.threads.net/v1.0"
    MAX_POLL_ATTEMPTS = 10
    POLL_INTERVAL = 3
    RETRY_DELAY = 5

    def __init__(self):
        self._access_token = os.environ["THREADS_ACCESS_TOKEN"]
        self._user_id = os.environ["THREADS_USER_ID"]

    def publish_post(self, text: str, image_url: str) -> str:
        try:
            return self._do_publish(text, image_url)
        except ThreadsAPIError:
            time.sleep(self.RETRY_DELAY)
            return self._do_publish(text, image_url)

    def _do_publish(self, text: str, image_url: str) -> str:
        container_id = self._create_container(text, image_url)
        self._poll_container(container_id)
        return self._publish(container_id)

    def _create_container(self, text: str, image_url: str) -> str:
        params = {"text": text}
        if image_url and image_url.strip():
            params["media_type"] = "IMAGE"
            params["image_url"] = image_url
        else:
            params["media_type"] = "TEXT"
        response = self._post(f"/{self._user_id}/threads", params)
        if "error" in response or "id" not in response:
            raise ThreadsAPIError(f"Container creation failed: {response}")
        return response["id"]

    def _poll_container(self, container_id: str) -> None:
        for _ in range(self.MAX_POLL_ATTEMPTS):
            response = self._get(
                f"/{container_id}",
                {"fields": "status,error_message"},
            )
            status = response.get("status")
            if status == "FINISHED":
                return
            if status == "ERROR":
                raise ThreadsAPIError(f"Container error: {response.get('error_message')}")
            time.sleep(self.POLL_INTERVAL)
        raise ThreadsAPIError("Container polling timed out")

    def _publish(self, container_id: str) -> str:
        response = self._post(
            f"/{self._user_id}/threads_publish",
            {"creation_id": container_id},
        )
        if "error" in response or "id" not in response:
            raise ThreadsAPIError(f"Publish failed: {response}")
        return response["id"]

    def _post(self, path: str, params: dict) -> dict:
        merged = {**params, "access_token": self._access_token}
        try:
            resp = requests.post(f"{self.BASE_URL}{path}", params=merged, timeout=30)
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.RequestException as e:
            raise ThreadsAPIError(str(e)) from e

    def _get(self, path: str, params: dict) -> dict:
        merged = {**params, "access_token": self._access_token}
        try:
            resp = requests.get(f"{self.BASE_URL}{path}", params=merged, timeout=30)
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.RequestException as e:
            raise ThreadsAPIError(str(e)) from e
