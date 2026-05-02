from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import get_current_org_member
from ..models import OrganizationUser, Subscription, Plan, UsageCounter
from ..schemas import PlanResponse, LimitsResponse

router = APIRouter(prefix="/api/v1/billing", tags=["billing"])


@router.get("/plan", response_model=PlanResponse)
def get_plan(member: OrganizationUser = Depends(get_current_org_member), db: Session = Depends(get_db)):
    subscription = (
        db.query(Subscription).filter(Subscription.organization_id == member.organization_id).first()
    )
    if not subscription:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subscription not found")

    plan = db.query(Plan).filter(Plan.id == subscription.plan_id).first()
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")

    return PlanResponse(
        code=plan.code,
        name=plan.name,
        bot_limit=plan.bot_limit,
        message_limit=plan.message_limit,
        integration_limit=plan.integration_limit,
    )


@router.get("/limits", response_model=LimitsResponse)
def get_limits(member: OrganizationUser = Depends(get_current_org_member), db: Session = Depends(get_db)):
    usage = db.query(UsageCounter).filter(UsageCounter.organization_id == member.organization_id).first()
    subscription = (
        db.query(Subscription).filter(Subscription.organization_id == member.organization_id).first()
    )
    if not usage or not subscription:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Billing data not found")

    plan = db.query(Plan).filter(Plan.id == subscription.plan_id).first()
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")

    return LimitsResponse(
        bots_used=usage.bots_used,
        bots_limit=plan.bot_limit,
        messages_used=usage.messages_used,
        messages_limit=plan.message_limit,
        integrations_used=usage.integrations_used,
        integrations_limit=plan.integration_limit,
    )
