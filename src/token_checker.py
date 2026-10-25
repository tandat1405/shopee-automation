import logging
import os
import smtplib
from datetime import datetime, timezone
from email.mime.text import MIMEText

logger = logging.getLogger(__name__)

SHOPEE_WARN_DAYS = 7
THREADS_WARN_DAYS = 14


class TokenChecker:
    def check_and_alert(self) -> list[str]:
        warnings = []
        warnings.extend(self._check_token("Shopee", "SHOPEE_TOKEN_EXPIRY", SHOPEE_WARN_DAYS))
        warnings.extend(self._check_token("Threads", "THREADS_TOKEN_EXPIRY", THREADS_WARN_DAYS))
        if warnings:
            subject = "⚠️ Token sắp hết hạn — Shopee Automation"
            body = "\n".join(warnings) + "\n\nVui lòng refresh token và cập nhật lại GitHub Secrets."
            self._send_email(subject, body)
        return warnings

    def _check_token(self, name: str, env_key: str, threshold_days: int) -> list[str]:
        expiry_str = os.environ.get(env_key)
        if not expiry_str:
            return []
        try:
            expiry = datetime.fromisoformat(expiry_str)
            if expiry.tzinfo is None:
                expiry = expiry.replace(tzinfo=timezone.utc)
            days_left = (expiry - datetime.now(timezone.utc)).days
            if days_left < threshold_days:
                return [f"{name} Access Token còn {days_left} ngày nữa hết hạn (hạn: {expiry_str})."]
        except (ValueError, TypeError) as e:
            logger.warning("Could not parse %s: %s", env_key, e)
        return []

    def _send_email(self, subject: str, body: str) -> None:
        gmail_user = os.environ["GMAIL_USER"]
        gmail_password = os.environ["GMAIL_APP_PASSWORD"]
        alert_email = os.environ["ALERT_EMAIL"]

        msg = MIMEText(body, "plain", "utf-8")
        msg["Subject"] = subject
        msg["From"] = gmail_user
        msg["To"] = alert_email

        with smtplib.SMTP("smtp.gmail.com", 587) as smtp:
            smtp.starttls()
            smtp.login(gmail_user, gmail_password)
            smtp.sendmail(gmail_user, alert_email, msg.as_string())
