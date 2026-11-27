from sqlalchemy import Boolean, Column, Integer, String, DateTime, Float
from sqlalchemy.sql import func
from sqlalchemy import Date, BigInteger
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
    approval_status = Column(String, default="approved")
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

class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, unique=True, index=True)
    plan_id = Column(String, default="free")
    status = Column(String, default="inactive")
    provider = Column(String, nullable=True)
    provider_customer_id = Column(String, nullable=True)
    provider_subscription_id = Column(String, nullable=True)
    next_billing_date = Column(String, nullable=True)
    cancel_at_period_end = Column(Boolean, default=False)
    last_payment_status = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class SupportTicket(Base):
    __tablename__ = "support_tickets"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=True, index=True)
    email = Column(String, index=True)
    category = Column(String, default="general")
    title = Column(String)
    message = Column(String)
    status = Column(String, default="open")
    admin_reply = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=True)

class TradeRecord(Base):
    """One closed Zenthex Trading position (buy -> sell), stored with fees already deducted."""
    __tablename__ = "trade_records"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=True, index=True)
    mode = Column(String, default="practice", index=True)  # practice / real / bithumb_real
    exchange = Column(String, default="upbit")
    ticker = Column(String)
    entry_cost_krw = Column(Float, default=0.0)   # KRW paid including buy fee
    exit_value_krw = Column(Float, default=0.0)   # KRW received after sell fee
    pnl_krw = Column(Float, default=0.0)
    pnl_pct = Column(Float, default=0.0)          # fraction, e.g. 0.004 = +0.4%
    peak_pct = Column(Float, default=0.0)
    reason = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class HouseholdSettings(Base):
    __tablename__ = 'household_settings'
    user_id = Column(Integer, primary_key=True)
    as_of = Column(Date, nullable=False)
    cash_krw = Column(BigInteger, nullable=False)
    reserve_krw = Column(BigInteger, nullable=True)


class HouseholdEntry(Base):
    __tablename__ = 'household_entries'
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)
    activity = Column(String(24), nullable=False, default='household')
    kind = Column(String(24), nullable=False)
    category = Column(String(40), nullable=False)
    description = Column(String(160), nullable=False)
    method = Column(String(40), nullable=False, default='계좌')
    amount_krw = Column(BigInteger, nullable=True)
    status = Column(String(16), nullable=False, default='planned')
    confirmed = Column(Boolean, nullable=False, default=True)
    deleted = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
