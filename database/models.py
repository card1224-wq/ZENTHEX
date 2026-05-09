from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Float, DateTime
from sqlalchemy.sql import func
from .session import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Subscription specific
    plan = Column(String, default="free") # free, studio_pro, trading_pro, ultimate
    role = Column(String, default="user") # user, admin
    
    # Binance Keys
    binance_access_key = Column(String, nullable=True)
    binance_secret_key = Column(String, nullable=True)
    
    # Usage quotas (for simplified billing)
    studio_generations_left = Column(Integer, default=3)
