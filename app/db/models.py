from datetime import datetime, timedelta

from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey
from sqlalchemy.orm import relationship

from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    mobile = Column(String(20), unique=True, index=True, nullable=False)
    full_name = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    subscriptions = relationship("Subscription", back_populates="user")
    payments = relationship("Payment", back_populates="user")


class OTPCode(Base):
    __tablename__ = "otp_codes"

    id = Column(Integer, primary_key=True, index=True)
    mobile = Column(String(20), index=True, nullable=False)
    code = Column(String(10), nullable=False)
    is_used = Column(Boolean, default=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    plan_name = Column(String(100), default="monthly")
    is_active = Column(Boolean, default=True)
    starts_at = Column(DateTime, default=datetime.utcnow)
    ends_at = Column(DateTime, default=lambda: datetime.utcnow() + timedelta(days=30))

    user = relationship("User", back_populates="subscriptions")


class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    amount = Column(Integer, nullable=False)
    provider = Column(String(50), default="zarinpal")
    authority = Column(String(255), nullable=True)
    ref_id = Column(String(255), nullable=True)
    status = Column(String(50), default="pending")
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="payments")
