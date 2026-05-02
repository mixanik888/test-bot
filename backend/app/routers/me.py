from fastapi import APIRouter, Depends

from ..deps import get_current_user, get_current_org_member
from ..models import User, OrganizationUser
from ..schemas import MeResponse, UserResponse

router = APIRouter(prefix="/api/v1", tags=["me"])


@router.get("/me", response_model=MeResponse)
def get_me(
    user: User = Depends(get_current_user),
    member: OrganizationUser = Depends(get_current_org_member),
):
    return MeResponse(
        user=UserResponse(id=user.id, email=user.email, full_name=user.full_name),
        role=member.role,
        organization_id=member.organization_id,
    )
