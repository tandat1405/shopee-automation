import os
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from src.token_checker import TokenChecker


def iso(days_from_now):
    return (datetime.now(timezone.utc) + timedelta(days=days_from_now)).isoformat()


def test_no_alert_when_tokens_healthy():
    env = {
        "SHOPEE_TOKEN_EXPIRY": iso(10),
        "THREADS_TOKEN_EXPIRY": iso(20),
        "GMAIL_USER": "a@gmail.com",
        "GMAIL_APP_PASSWORD": "pw",
        "ALERT_EMAIL": "b@gmail.com",
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
        "GMAIL_USER": "a@gmail.com",
        "GMAIL_APP_PASSWORD": "pw",
        "ALERT_EMAIL": "b@gmail.com",
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
