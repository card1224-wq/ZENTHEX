from sqlalchemy import Boolean, Column, Integer, String, DateTime
from sqlalchemy.sql import func
from .session import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String, nullable=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    birth_date = Column(String, nullable=True)
    phone_number = Column(String, nullable=True)
    phone_verified = Column(Boolean, default=False)
    phone_verification_code = Column(String, nullable=True)
    password_hint_question = Column(String, nullable=True)
    password_hint_answer_hash = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    email_verified = Column(Boolean, default=False)
    email_verification_code = Column(String, nullable=True)
    password_reset_code = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    plan = Column(String, default="free")
    role = Column(String, default="user")

    binance_access_key = Column(String, nullable=True)
    binance_secret_key = Column(String, nullable=True)
    studio_generations_left = Column(Integer, default=3)

class BillingHistory(Base):
    __tablename__ = "billing_history"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    plan_id = Column(String)
    plan_name = Column(String)
    amount_krw = Column(Integer, default=0)
    status = Column(String, default="paid")
    payment_method = Column(String, default="mock_checkout")
    receipt_no = Column(String, unique=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
