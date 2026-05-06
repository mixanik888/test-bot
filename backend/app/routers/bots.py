import secrets

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from ..config import get_public_base_url
from ..db import get_db
from ..deps import get_current_org_member, require_manager_or_admin
from ..max_api import max_delete_subscription, max_get_me, max_set_subscription
from ..models import Bot, BotMaxIntegration, BotMessage, OrganizationUser, Plan, Subscription, UsageCounter
from ..schemas import BotCreateRequest, BotMaxTokenRequest, BotMessageResponse, BotResponse, BotTelegramTokenRequest
from ..telegram_api import telegram_delete_webhook, telegram_get_me, telegram_set_webhook

router = APIRouter(prefix="/api/v1/bots", tags=["bots"])


def _telegram_webhook_url(secret: str) -> str:
    return f"{get_public_base_url()}/api/v1/webhooks/telegram/{secret}"


def _max_webhook_url(secret: str) -> str:
    return f"{get_public_base_url()}/api/v1/webhooks/max/{secret}"


def _to_bot_response(bot: Bot) -> BotResponse:
    return BotResponse(
        id=bot.id,
        organization_id=bot.organization_id,
        name=bot.name,
        status=bot.status,
        telegram_bot_username=bot.telegram_bot_username,
        max_bot_username=bot.max_integration.bot_username if bot.max_integration else None,
        webhook_url=_telegram_webhook_url(bot.webhook_secret),
        has_telegram=bool(bot.telegram_bot_token),
        has_max=bool(bot.max_integration and bot.max_integration.access_token),
    )


def _get_plan_and_usage(db: Session, org_id: int) -> tuple[Plan, UsageCounter]:
    sub = db.query(Subscription).filter(Subscription.organization_id == org_id).first()
    if not sub:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subscription not found")
    plan = db.query(Plan).filter(Plan.id == sub.plan_id).first()
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")
    usage = db.query(UsageCounter).filter(UsageCounter.organization_id == org_id).first()
    if not usage:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usage not found")
    return plan, usage


@router.get("", response_model=list[BotResponse])
def list_bots(
    member: OrganizationUser = Depends(get_current_org_member),
    db: Session = Depends(get_db),
):
    bots = db.query(Bot).filter(Bot.organization_id == member.organization_id).all()
    return [_to_bot_response(b) for b in bots]


@router.post("", response_model=BotResponse, status_code=status.HTTP_201_CREATED)
def create_bot(
    payload: BotCreateRequest,
    member: OrganizationUser = Depends(require_manager_or_admin),
    db: Session = Depends(get_db),
):
    if not payload.name.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Name required")

    plan, usage = _get_plan_and_usage(db, member.organization_id)
    n_bots = db.query(Bot).filter(Bot.organization_id == member.organization_id).count()
    if n_bots >= plan.bot_limit:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Достигнут лимит ботов по тарифу",
        )

    bot = Bot(
        organization_id=member.organization_id,
        name=payload.name.strip(),
        status="draft",
        webhook_secret=secrets.token_urlsafe(32),
    )
    db.add(bot)
    db.flush()
    usage.bots_used = db.query(Bot).filter(Bot.organization_id == member.organization_id).count()
    db.commit()
    db.refresh(bot)
    return _to_bot_response(bot)


@router.get("/{bot_id}", response_model=BotResponse)
def get_bot(
    bot_id: int,
    member: OrganizationUser = Depends(get_current_org_member),
    db: Session = Depends(get_db),
):
    bot = (
        db.query(Bot)
        .filter(Bot.id == bot_id, Bot.organization_id == member.organization_id)
        .first()
    )
    if not bot:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bot not found")
    return _to_bot_response(bot)


@router.delete("/{bot_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_bot(
    bot_id: int,
    member: OrganizationUser = Depends(require_manager_or_admin),
    db: Session = Depends(get_db),
):
    bot = (
        db.query(Bot)
        .filter(Bot.id == bot_id, Bot.organization_id == member.organization_id)
        .first()
    )
    if not bot:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bot not found")

    if bot.telegram_bot_token:
        try:
            telegram_delete_webhook(bot.telegram_bot_token)
        except ValueError:
            pass
    if bot.max_integration and bot.max_integration.access_token:
        try:
            max_delete_subscription(bot.max_integration.access_token, _max_webhook_url(bot.webhook_secret))
        except ValueError:
            pass

    org_id = member.organization_id
    db.delete(bot)
    db.flush()
    usage = db.query(UsageCounter).filter(UsageCounter.organization_id == org_id).first()
    if usage:
        usage.bots_used = db.query(Bot).filter(Bot.organization_id == org_id).count()
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{bot_id}/telegram", response_model=BotResponse)
def connect_telegram(
    bot_id: int,
    payload: BotTelegramTokenRequest,
    member: OrganizationUser = Depends(require_manager_or_admin),
    db: Session = Depends(get_db),
):
    bot = (
        db.query(Bot)
        .filter(Bot.id == bot_id, Bot.organization_id == member.organization_id)
        .first()
    )
    if not bot:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bot not found")

    token = payload.token.strip()
    if not token:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Token required")

    try:
        me = telegram_get_me(token)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e

    username = me.get("username")
    wh = _telegram_webhook_url(bot.webhook_secret)
    try:
        telegram_set_webhook(token, wh)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Не удалось настроить webhook (нужен доступный из интернета PUBLIC_BASE_URL): {e}",
        ) from e

    bot.telegram_bot_token = token
    bot.telegram_bot_username = username
    bot.status = "active"
    db.commit()
    db.refresh(bot)
    return _to_bot_response(bot)


@router.post("/{bot_id}/max", response_model=BotResponse)
def connect_max(
    bot_id: int,
    payload: BotMaxTokenRequest,
    member: OrganizationUser = Depends(require_manager_or_admin),
    db: Session = Depends(get_db),
):
    bot = (
        db.query(Bot)
        .filter(Bot.id == bot_id, Bot.organization_id == member.organization_id)
        .first()
    )
    if not bot:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bot not found")

    token = payload.token.strip()
    if not token:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Token required")

    try:
        me = max_get_me(token)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e

    wh = _max_webhook_url(bot.webhook_secret)
    try:
        max_set_subscription(token, wh, bot.webhook_secret)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Не удалось настроить MAX webhook (нужен доступный из интернета PUBLIC_BASE_URL): {e}",
        ) from e

    integration = bot.max_integration
    if not integration:
        integration = BotMaxIntegration(bot_id=bot.id)
        db.add(integration)

    integration.access_token = token
    integration.bot_user_id = me.get("user_id")
    integration.bot_username = me.get("username")
    bot.status = "active"
    db.commit()
    db.refresh(bot)
    return _to_bot_response(bot)


@router.delete("/{bot_id}/max", response_model=BotResponse)
def disconnect_max(
    bot_id: int,
    member: OrganizationUser = Depends(require_manager_or_admin),
    db: Session = Depends(get_db),
):
    bot = (
        db.query(Bot)
        .filter(Bot.id == bot_id, Bot.organization_id == member.organization_id)
        .first()
    )
    if not bot:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bot not found")

    if bot.max_integration and bot.max_integration.access_token:
        try:
            max_delete_subscription(bot.max_integration.access_token, _max_webhook_url(bot.webhook_secret))
        except ValueError:
            pass
        db.delete(bot.max_integration)
        db.flush()

    if not bot.telegram_bot_token:
        bot.status = "draft"
    db.commit()
    db.refresh(bot)
    return _to_bot_response(bot)


@router.delete("/{bot_id}/telegram", response_model=BotResponse)
def disconnect_telegram(
    bot_id: int,
    member: OrganizationUser = Depends(require_manager_or_admin),
    db: Session = Depends(get_db),
):
    bot = (
        db.query(Bot)
        .filter(Bot.id == bot_id, Bot.organization_id == member.organization_id)
        .first()
    )
    if not bot:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bot not found")

    if bot.telegram_bot_token:
        try:
            telegram_delete_webhook(bot.telegram_bot_token)
        except ValueError:
            pass

    bot.telegram_bot_token = None
    bot.telegram_bot_username = None
    if not bot.max_integration:
        bot.status = "draft"
    db.commit()
    db.refresh(bot)
    return _to_bot_response(bot)


@router.get("/{bot_id}/messages", response_model=list[BotMessageResponse])
def list_bot_messages(
    bot_id: int,
    member: OrganizationUser = Depends(get_current_org_member),
    db: Session = Depends(get_db),
):
    bot = (
        db.query(Bot)
        .filter(Bot.id == bot_id, Bot.organization_id == member.organization_id)
        .first()
    )
    if not bot:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bot not found")

    rows = (
        db.query(BotMessage)
        .filter(BotMessage.bot_id == bot_id)
        .order_by(BotMessage.id.desc())
        .limit(50)
        .all()
    )
    rows = list(reversed(rows))
    return [
        BotMessageResponse(
            id=m.id,
            direction=m.direction,
            telegram_chat_id=m.telegram_chat_id,
            text=m.text,
            created_at=m.created_at.isoformat() if m.created_at else None,
        )
        for m in rows
    ]
