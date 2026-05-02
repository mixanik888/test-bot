from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..auth import create_access_token, hash_password, verify_password
from ..db import get_db
from ..models import User, Organization, OrganizationUser, Plan, Subscription, UsageCounter
from ..schemas import RegisterRequest, LoginRequest, TokenResponse

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    user = User(
        email=payload.email,
        password_hash=hash_password(payload.password),
        full_name=payload.full_name,
    )
    org = Organization(name=payload.organization_name)
    db.add_all([user, org])
    db.flush()

    db.add(OrganizationUser(organization_id=org.id, user_id=user.id, role="admin"))

    plan = db.query(Plan).filter(Plan.code == "trial").first()
    if not plan:
        plan = Plan(code="trial", name="Trial", bot_limit=1, message_limit=1000, integration_limit=1)
        db.add(plan)
        db.flush()

    db.add(Subscription(organization_id=org.id, plan_id=plan.id))
    db.add(UsageCounter(organization_id=org.id, bots_used=0, messages_used=0, integrations_used=0))
    db.commit()

    return TokenResponse(access_token=create_access_token(str(user.id)))


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    return TokenResponse(access_token=create_access_token(str(user.id)))


@router.post("/oauth/google", response_model=TokenResponse)
def oauth_google():
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="OAuth Google is TODO")


@router.post("/oauth/telegram", response_model=TokenResponse)
def oauth_telegram():
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="OAuth Telegram is TODO")
