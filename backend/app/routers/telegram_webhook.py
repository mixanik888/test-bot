from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Bot, BotMessage, Plan, Subscription, UsageCounter
from ..telegram_api import telegram_send_message

router = APIRouter(tags=["telegram_webhook"])


@router.post("/api/v1/webhooks/telegram/{webhook_secret}")
async def telegram_webhook(
    webhook_secret: str,
    request: Request,
    db: Session = Depends(get_db),
):
    bot = db.query(Bot).filter(Bot.webhook_secret == webhook_secret).first()
    if not bot or not bot.telegram_bot_token:
        return {"ok": True}

    try:
        data = await request.json()
    except Exception:
        return {"ok": True}

    msg = data.get("message") or {}
    text = msg.get("text")
    chat = msg.get("chat") or {}
    chat_id = chat.get("id")
    if text is None or chat_id is None:
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
        reply = f"Echo: {text}"
        telegram_send_message(bot.telegram_bot_token, int(chat_id), reply)
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
