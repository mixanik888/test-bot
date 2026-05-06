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


class BotCreateRequest(BaseModel):
    name: str


class BotTelegramTokenRequest(BaseModel):
    token: str


class BotMaxTokenRequest(BaseModel):
    token: str


class BotResponse(BaseModel):
    id: int
    organization_id: int
    name: str
    status: str
    telegram_bot_username: str | None
    max_bot_username: str | None
    webhook_url: str
    has_telegram: bool
    has_max: bool


class BotMessageResponse(BaseModel):
    id: int
    direction: str
    telegram_chat_id: str
    text: str | None
    created_at: str | None


class FlowTriggerPath(BaseModel):
    id: str
    name: str
    regex: str


class FlowBlock(BaseModel):
    id: str
    type: str
    label: str
    x: int = 80
    y: int = 80
    trigger_paths: list[FlowTriggerPath] | None = None
    condition_regex: str | None = None
    fallback_action_value: str | None = None
    action_type: str | None = None
    action_value: str | None = None


class FlowEdge(BaseModel):
    from_block_id: str
    to_block_id: str
    when: str = "always"


class FlowSchemaSaveRequest(BaseModel):
    blocks: list[FlowBlock]
    edges: list[FlowEdge] = []


class FlowSchemaResponse(BaseModel):
    bot_id: int
    blocks: list[FlowBlock]
    edges: list[FlowEdge]
    is_valid: bool
    errors: list[str]


class FlowVersionResponse(BaseModel):
    id: int
    version: int
    blocks: list[FlowBlock]
    edges: list[FlowEdge]
    created_at: str | None
