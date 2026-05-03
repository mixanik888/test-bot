import httpx


def _call(token: str, method: str, **params) -> dict:
    url = f"https://api.telegram.org/bot{token}/{method}"
    with httpx.Client(timeout=30.0) as client:
        try:
            if params:
                r = client.post(url, json=params)
            else:
                r = client.post(url)
            r.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise ValueError("Неверный токен бота или недоступен Telegram API") from e
        data = r.json()
        if not data.get("ok"):
            raise ValueError(data.get("description", "Telegram API error"))
        return data


def telegram_get_me(token: str) -> dict:
    data = _call(token, "getMe")
    return data.get("result") or {}


def telegram_set_webhook(token: str, url: str) -> dict:
    return _call(token, "setWebhook", url=url)


def telegram_delete_webhook(token: str) -> dict:
    return _call(token, "deleteWebhook")


def telegram_send_message(token: str, chat_id: int, text: str) -> dict:
    return _call(token, "sendMessage", chat_id=chat_id, text=text)
