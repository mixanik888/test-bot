import httpx


BASE_URL = "https://platform-api.max.ru"


def _call(access_token: str, method: str, path: str, *, params: dict | None = None, body: dict | None = None) -> dict:
    url = f"{BASE_URL}{path}"
    headers = {"Authorization": access_token}
    with httpx.Client(timeout=30.0) as client:
        try:
            response = client.request(method, url, headers=headers, params=params, json=body)
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise ValueError("Неверный токен MAX или недоступен MAX API") from e
        except httpx.HTTPError as e:
            raise ValueError("Недоступен MAX API") from e

    data = response.json()
    if isinstance(data, dict) and data.get("success") is False:
        raise ValueError(data.get("message", "MAX API error"))
    return data if isinstance(data, dict) else {}


def max_get_me(access_token: str) -> dict:
    return _call(access_token, "GET", "/me")


def max_set_subscription(access_token: str, url: str, secret: str) -> dict:
    return _call(
        access_token,
        "POST",
        "/subscriptions",
        body={"url": url, "update_types": ["message_created", "bot_started"], "secret": secret},
    )


def max_delete_subscription(access_token: str, url: str) -> dict:
    return _call(access_token, "DELETE", "/subscriptions", params={"url": url})


def max_send_message(access_token: str, chat_id: int, text: str) -> dict:
    return _call(access_token, "POST", "/messages", params={"chat_id": chat_id}, body={"text": text})
