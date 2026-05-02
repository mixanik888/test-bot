from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.auth import hash_password
from app.db import SessionLocal
from app.models import Organization, OrganizationUser, Plan, Subscription, UsageCounter, User


TEST_ORG_NAME = "Test Org"
TEST_USERS = [
    {"email": "admin@example.com", "full_name": "Admin User", "password": "Pass123!", "role": "admin"},
    {"email": "manager@example.com", "full_name": "Manager User", "password": "Manager123!", "role": "manager"},
    {"email": "support@example.com", "full_name": "Support User", "password": "Support123!", "role": "support_agent"},
]


def get_or_create_trial_plan(db):
    plan = db.query(Plan).filter(Plan.code == "trial").first()
    if plan:
        return plan

    plan = Plan(code="trial", name="Trial", bot_limit=3, message_limit=5000, integration_limit=3)
    db.add(plan)
    db.flush()
    return plan


def get_or_create_org(db):
    org = db.query(Organization).filter(Organization.name == TEST_ORG_NAME).first()
    if org:
        return org

    org = Organization(name=TEST_ORG_NAME)
    db.add(org)
    db.flush()
    return org


def ensure_subscription_and_usage(db, org_id, plan_id):
    sub = db.query(Subscription).filter(Subscription.organization_id == org_id).first()
    if not sub:
        db.add(Subscription(organization_id=org_id, plan_id=plan_id))

    usage = db.query(UsageCounter).filter(UsageCounter.organization_id == org_id).first()
    if not usage:
        db.add(UsageCounter(organization_id=org_id, bots_used=0, messages_used=0, integrations_used=0))


def upsert_user(db, org_id, user_data):
    user = db.query(User).filter(User.email == user_data["email"]).first()
    if not user:
        user = User(
            email=user_data["email"],
            full_name=user_data["full_name"],
            password_hash=hash_password(user_data["password"]),
        )
        db.add(user)
        db.flush()
    else:
        user.full_name = user_data["full_name"]
        user.password_hash = hash_password(user_data["password"])

    member = (
        db.query(OrganizationUser)
        .filter(OrganizationUser.organization_id == org_id, OrganizationUser.user_id == user.id)
        .first()
    )
    if not member:
        db.add(OrganizationUser(organization_id=org_id, user_id=user.id, role=user_data["role"]))
    else:
        member.role = user_data["role"]


def seed():
    db = SessionLocal()
    try:
        plan = get_or_create_trial_plan(db)
        org = get_or_create_org(db)
        ensure_subscription_and_usage(db, org.id, plan.id)

        for user_data in TEST_USERS:
            upsert_user(db, org.id, user_data)

        db.commit()
        print("Test users are seeded successfully.")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
