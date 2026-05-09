from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database.session import get_db
from database.models import User
from auth.schemas import UserCreate, UserLogin, Token, UserResponse
from auth.hash import get_password_hash, verify_password
import uuid

router = APIRouter(prefix="/api/auth", tags=["auth"])

# In-memory token store for MVP (so we don't need a strict JWT setup immediately)
# For production, we would use python-jose to encode/decode JWTs.
SESSION_TOKENS = {}

@router.post("/signup", response_model=UserResponse)
def signup(user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    new_user = User(
        email=user.email,
        hashed_password=get_password_hash(user.password)
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@router.post("/login", response_model=Token)
def login(user: UserLogin, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.email == user.email).first()
    if not db_user or not verify_password(user.password, db_user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    
    # Generate mock JWT
    access_token = str(uuid.uuid4())
    SESSION_TOKENS[access_token] = db_user.id
    
    user_info = UserResponse.model_validate(db_user)
    
    return {"access_token": access_token, "token_type": "bearer", "user_info": user_info}

def get_current_user(token: str, db: Session = Depends(get_db)):
    user_id = SESSION_TOKENS.get(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user
