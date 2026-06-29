from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, Float, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from config import settings

DATABASE_URL = settings.database_url

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


# ===== PARENT MODEL =====
class Parent(Base):
    __tablename__ = "parents"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    full_name = Column(String)
    phone_number = Column(String, nullable=True)
    hashed_password = Column(String)
    email_verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)


# ===== CHILD MODEL =====
class Child(Base):
    __tablename__ = "children"

    id = Column(Integer, primary_key=True, index=True)
    parent_id = Column(Integer, index=True)
    name = Column(String)
    roblox_username = Column(String, unique=True)
    roblox_user_id = Column(String, unique=True)
    created_at = Column(DateTime, default=datetime.utcnow)


# ===== CONSENT MODEL =====
class Consent(Base):
    __tablename__ = "consents"

    id = Column(Integer, primary_key=True, index=True)
    parent_id = Column(Integer, index=True)
    child_id = Column(Integer, index=True)
    consent_granted = Column(Boolean)
    data_retention_days = Column(Integer, default=30)
    signed_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime)
    notification_method = Column(String)
    high_risk_threshold = Column(Float, default=0.7)


# ===== MESSAGE MODEL =====
class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    child_id = Column(Integer, index=True)
    roblox_user_id = Column(String)
    username = Column(String)
    text = Column(Text)
    risk_score = Column(Float, nullable=True)
    risk_level = Column(String, nullable=True)
    flagged_phrases = Column(String, nullable=True)  # JSON string
    parent_notified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    deleted_at = Column(DateTime, nullable=True)


# ===== ALERT MODEL =====
class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    child_id = Column(Integer, index=True)
    risk_level = Column(String)
    message_preview = Column(Text)
    risk_score = Column(Float)
    triggered_at = Column(DateTime, default=datetime.utcnow)
    acknowledged = Column(Boolean, default=False)
    acknowledged_at = Column(DateTime, nullable=True)


# Create tables
Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
