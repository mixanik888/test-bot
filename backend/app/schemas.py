from pydantic import BaseModel, EmailStr


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    organization_name: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: int
    email: str
    full_name: str


class MeResponse(BaseModel):
    user: UserResponse
    role: str
    organization_id: int


class OrgResponse(BaseModel):
    id: int
    name: str


class InviteRequest(BaseModel):
    email: EmailStr
    full_name: str
    role: str
    temp_password: str


class UpdateRoleRequest(BaseModel):
    role: str


class PlanResponse(BaseModel):
    code: str
    name: str
    bot_limit: int
    message_limit: int
    integration_limit: int


class LimitsResponse(BaseModel):
    bots_used: int
    bots_limit: int
    messages_used: int
    messages_limit: int
    integrations_used: int
    integrations_limit: int
