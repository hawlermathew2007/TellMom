import uuid
from datetime import datetime
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy import Index, String, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from proxy.database.session import Base


class Server(Base):
    __tablename__ = "servers"
    __table_args__ = (Index("ix_server_id", "id"),)

    # Identifiers
    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Unique identifier and public key for the server",
    )

    # Authentication
    username: Mapped[str] = mapped_column(
        String(300),
        unique=True,
        nullable=False,
        comment="Unique username for login and display",
    )
    password_hash: Mapped[str] = mapped_column(
        String(300), nullable=False, comment="Hashed password"
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Time created",
    )
