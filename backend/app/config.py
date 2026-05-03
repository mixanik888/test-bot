import os


def get_public_base_url() -> str:
    """Публичный URL API (без завершающего /). Нужен для setWebhook Telegram."""
    return os.environ.get("PUBLIC_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
