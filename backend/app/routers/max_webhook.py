from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from ..db import get_db
from ..flow_runtime import resolve_action_reply
from ..max_api import max_send_message
from ..models import Bot, BotMaxIntegration, BotMessage, Plan, Subscription, UsageCounter

router = APIRouter(tags=["max_webhook"])


def _parse_int(value: object) -> int | None:
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return None


def _extract_chat_id(update: dict) -> int | None:
    chat_id = _parse_int(update.get("chat_id"))
    if chat_id is not None:
        return chat_id

    chat = update.get("chat") or {}
    chat_chat_id = _parse_int(chat.get("chat_id"))
    if chat_chat_id is not None:
        return chat_chat_id

    message = update.get("message") or {}
    message_chat_id = _parse_int(message.get("chat_id"))
    if message_chat_id is not None:
        return message_chat_id

    recipient = message.get("recipient") or {}
    recipient_chat_id = _parse_int(recipient.get("chat_id"))
    if recipient_chat_id is not None:
        return recipient_chat_id

    return None


def _extract_text(update: dict) -> str | None:
    if isinstance(update.get("text"), str):
        return update.get("text")

    message = update.get("message") or {}
    if isinstance(message.get("text"), str):
        return message.get("text")

    body = message.get("body") or {}
    if isinstance(body.get("text"), str):
        return body.get("text")

    if isinstance(message.get("caption"), str):
        return message.get("caption")

    if isinstance(update.get("payload"), str):
        return update.get("payload")

    return None


@router.post("/api/v1/webhooks/max/{webhook_secret}")
async def max_webhook(
    webhook_secret: str,
    request: Request,
    db: Session = Depends(get_db),
):
    bot = db.query(Bot).filter(Bot.webhook_secret == webhook_secret).first()
    if not bot:
        return {"ok": True}
    integration = db.query(BotMaxIntegration).filter(BotMaxIntegration.bot_id == bot.id).first()
    if not integration or not integration.access_token:
        return {"ok": True}

    header_secret = request.headers.get("X-Max-Bot-Api-Secret")
    if header_secret and header_secret != webhook_secret:
        return {"ok": True}

    try:
        update = await request.json()
    except Exception:
        return {"ok": True}
    if not isinstance(update, dict):
        return {"ok": True}

    chat_id = _extract_chat_id(update)
    text = _extract_text(update)
    if chat_id is None or text is None:
        return {"ok": True}

    sub = db.query(Subscription).filter(Subscription.organization_id == bot.organization_id).first()
    if not sub:
        return {"ok": True}
    plan = db.query(Plan).filter(Plan.id == sub.plan_id).first()
    usage = db.query(UsageCounter).filter(UsageCounter.organization_id == bot.organization_id).first()
    if not plan or not usage:
        return {"ok": True}

    can_echo = usage.messages_used < plan.message_limit
    db.add(
        BotMessage(
            bot_id=bot.id,
            direction="in",
            telegram_chat_id=str(chat_id),
            text=text,
        )
    )
    usage.messages_used += 1
    db.commit()

    if not can_echo:
        return {"ok": True}

    try:
        reply, debug_line = resolve_action_reply(db, bot, text, str(chat_id))
        if not reply:
            reply = f"Echo: {text}"
            debug_line = f"{debug_line}; fallback=echo"

        db.add(
            BotMessage(
                bot_id=bot.id,
                direction="debug",
                telegram_chat_id=str(chat_id),
                text=debug_line,
            )
        )
        db.commit()
        max_send_message(integration.access_token, chat_id, reply)
        db.add(
            BotMessage(
                bot_id=bot.id,
                direction="out",
                telegram_chat_id=str(chat_id),
                text=reply,
            )
        )
        db.commit()
    except ValueError:
        pass

    return {"ok": True}
