from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    JSON,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from adapters.base import ChatPlatform
from database.session import Base


class Parent(Base):
    __tablename__ = "parents"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    child_accounts: Mapped[list["ChildAccount"]] = relationship(back_populates="parent")
    alerts: Mapped[list["Alert"]] = relationship(back_populates="parent")


class ChildAccount(Base):
    __tablename__ = "child_accounts"
    __table_args__ = (
        UniqueConstraint("platform", "platform_user_id", name="uq_platform_user"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    parent_id: Mapped[int] = mapped_column(ForeignKey("parents.id", ondelete="CASCADE"))
    platform: Mapped[ChatPlatform] = mapped_column(
        SAEnum(ChatPlatform, values_callable=lambda x: [e.value for e in x])
    )
    platform_user_id: Mapped[str] = mapped_column(String(255), index=True)
    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    parent: Mapped["Parent"] = relationship(back_populates="child_accounts")


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    platform: Mapped[ChatPlatform] = mapped_column(
        SAEnum(ChatPlatform, values_callable=lambda x: [e.value for e in x])
    )
    server_id: Mapped[str] = mapped_column(String(255), index=True)
    sender_platform_user_id: Mapped[str] = mapped_column(String(255), index=True)
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(primary_key=True)
    parent_id: Mapped[int] = mapped_column(ForeignKey("parents.id", ondelete="CASCADE"))
    child_account_id: Mapped[int] = mapped_column(
        ForeignKey("child_accounts.id", ondelete="CASCADE")
    )
    platform: Mapped[ChatPlatform] = mapped_column(
        SAEnum(ChatPlatform, values_callable=lambda x: [e.value for e in x])
    )
    server_id: Mapped[str] = mapped_column(String(255))
    message_preview: Mapped[str] = mapped_column(Text)
    explanation: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    acknowledged: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    parent: Mapped["Parent"] = relationship(back_populates="alerts")
    child_account: Mapped["ChildAccount"] = relationship()


class FlagExplanation(Base):
    __tablename__ = "flag_explanations"
    __table_args__ = (
        UniqueConstraint("platform", "server_id", name="uq_flag_explanation_server"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    platform: Mapped[ChatPlatform] = mapped_column(
        SAEnum(ChatPlatform, values_callable=lambda x: [e.value for e in x])
    )
    server_id: Mapped[str] = mapped_column(String(255), index=True)
    explanation: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
