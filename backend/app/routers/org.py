from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..auth import hash_password
from ..db import get_db
from ..deps import get_current_org_member, require_admin
from ..models import Organization, OrganizationUser, User
from ..schemas import OrgResponse, InviteRequest, UpdateRoleRequest

router = APIRouter(prefix="/api/v1/org", tags=["organization"])
ALLOWED_ROLES = {"admin", "manager", "support_agent"}


@router.get("", response_model=OrgResponse)
def get_org(member: OrganizationUser = Depends(get_current_org_member), db: Session = Depends(get_db)):
    org = db.query(Organization).filter(Organization.id == member.organization_id).first()
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
    return OrgResponse(id=org.id, name=org.name)


@router.post("/users/invite")
def invite_user(
    payload: InviteRequest,
    admin_member: OrganizationUser = Depends(require_admin),
    db: Session = Depends(get_db),
):
    if payload.role not in ALLOWED_ROLES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid role")

    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User already exists")

    user = User(
        email=payload.email,
        password_hash=hash_password(payload.temp_password),
        full_name=payload.full_name,
    )
    db.add(user)
    db.flush()
    db.add(
        OrganizationUser(
            organization_id=admin_member.organization_id,
            user_id=user.id,
            role=payload.role,
        )
    )
    db.commit()
    return {"status": "invited", "user_id": user.id}


@router.patch("/users/{user_id}/role")
def update_user_role(
    user_id: int,
    payload: UpdateRoleRequest,
    admin_member: OrganizationUser = Depends(require_admin),
    db: Session = Depends(get_db),
):
    if payload.role not in ALLOWED_ROLES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid role")

    target = (
        db.query(OrganizationUser)
        .filter(
            OrganizationUser.organization_id == admin_member.organization_id,
            OrganizationUser.user_id == user_id,
        )
        .first()
    )
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")

    target.role = payload.role
    db.commit()
    return {"status": "updated"}
