from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import relationship

from .db import Base


class Organization(Base):
    __tablename__ = "organizations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    users = relationship("OrganizationUser", back_populates="organization")
    bots = relationship("Bot", back_populates="organization")


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    organizations = relationship("OrganizationUser", back_populates="user")


class OrganizationUser(Base):
    __tablename__ = "organization_users"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    role = Column(String(32), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    organization = relationship("Organization", back_populates="users")
    user = relationship("User", back_populates="organizations")


class Plan(Base):
    __tablename__ = "plans"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(64), unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    bot_limit = Column(Integer, nullable=False, default=1)
    message_limit = Column(Integer, nullable=False, default=1000)
    integration_limit = Column(Integer, nullable=False, default=1)


class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    plan_id = Column(Integer, ForeignKey("plans.id"), nullable=False)


class UsageCounter(Base):
    __tablename__ = "usage_counters"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    bots_used = Column(Integer, nullable=False, default=0)
    messages_used = Column(Integer, nullable=False, default=0)
    integrations_used = Column(Integer, nullable=False, default=0)


class Bot(Base):
    __tablename__ = "bots"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    name = Column(String(255), nullable=False)
    status = Column(String(32), nullable=False, default="draft")
    webhook_secret = Column(String(64), unique=True, index=True, nullable=False)
    telegram_bot_token = Column(String(255), nullable=True)
    telegram_bot_username = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    organization = relationship("Organization", back_populates="bots")
    messages = relationship("BotMessage", back_populates="bot", cascade="all, delete-orphan")
    max_integration = relationship(
        "BotMaxIntegration",
        back_populates="bot",
        uselist=False,
        cascade="all, delete-orphan",
    )
    flow_definition = relationship(
        "FlowDefinition",
        back_populates="bot",
        uselist=False,
        cascade="all, delete-orphan",
    )
    dialog_states = relationship("BotDialogState", back_populates="bot", cascade="all, delete-orphan")


class BotMessage(Base):
    __tablename__ = "bot_messages"

    id = Column(Integer, primary_key=True, index=True)
    bot_id = Column(Integer, ForeignKey("bots.id"), nullable=False)
    direction = Column(String(8), nullable=False)
    telegram_chat_id = Column(String(64), nullable=False)
    text = Column(String(4096), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    bot = relationship("Bot", back_populates="messages")


class BotMaxIntegration(Base):
    __tablename__ = "bot_max_integrations"

    id = Column(Integer, primary_key=True, index=True)
    bot_id = Column(Integer, ForeignKey("bots.id"), nullable=False, unique=True)
    access_token = Column(String(255), nullable=False)
    bot_user_id = Column(Integer, nullable=True)
    bot_username = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    bot = relationship("Bot", back_populates="max_integration")


class FlowDefinition(Base):
    __tablename__ = "flow_definitions"

    id = Column(Integer, primary_key=True, index=True)
    bot_id = Column(Integer, ForeignKey("bots.id"), nullable=False, unique=True)
    draft_schema = Column(String, nullable=False, default="[]")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    bot = relationship("Bot", back_populates="flow_definition")
    versions = relationship("FlowVersion", back_populates="flow_definition", cascade="all, delete-orphan")


class FlowVersion(Base):
    __tablename__ = "flow_versions"

    id = Column(Integer, primary_key=True, index=True)
    flow_definition_id = Column(Integer, ForeignKey("flow_definitions.id"), nullable=False)
    version = Column(Integer, nullable=False)
    schema = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    flow_definition = relationship("FlowDefinition", back_populates="versions")


class BotDialogState(Base):
    __tablename__ = "bot_dialog_states"

    id = Column(Integer, primary_key=True, index=True)
    bot_id = Column(Integer, ForeignKey("bots.id"), nullable=False)
    telegram_chat_id = Column(String(64), nullable=False, index=True)
    waiting_trigger_block_id = Column(String(128), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    bot = relationship("Bot", back_populates="dialog_states")
