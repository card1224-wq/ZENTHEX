from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel
from sqlalchemy.orm import Session
from database.session import get_db
from database.models import User
from auth.router import get_current_user

router = APIRouter(prefix="/api/billing", tags=["billing"])

class SubscribeRequest(BaseModel):
    plan_id: str

class CheckoutResponse(BaseModel):
    checkout_url: str
    status: str

PLANS = {
    "free": {"price": 0, "studio_limit": 3, "features": ["Basic AI Prompts"]},
    "studio_pro": {"price": 29000, "studio_limit": 100, "features": ["100x 3D Generations", "NanoBanana Quality"]},
    "trading_pro": {"price": 49000, "studio_limit": 10, "features": ["Auto Crypto Trading", "Risk Manager"]},
    "ultimate": {"price": 99000, "studio_limit": 1000, "features": ["All Features", "Unlimited Priority"]}
}

@router.get("/plans")
def get_plans():
    return {"plans": PLANS}

@router.post("/subscribe", response_model=CheckoutResponse)
def mock_checkout(
    req: SubscribeRequest, 
    Authorization: str = Header(None), 
    db: Session = Depends(get_db)
):
    if not Authorization:
        raise HTTPException(status_code=401, detail="Missing Token")
    
    token = Authorization.replace("Bearer ", "")
    user = get_current_user(token, db)
    
    if req.plan_id not in PLANS:
        raise HTTPException(status_code=400, detail="Invalid plan code")
        
    if PLANS[req.plan_id]["price"] == 0:
        # Auto upgrade to free
        user.plan = "free"
        user.studio_generations_left = PLANS["free"]["studio_limit"]
        db.commit()
        return {"checkout_url": "", "status": "upgraded_to_free"}
        
    # Generate mock checkout URL (Toss Payments / Stripe)
    checkout_url = f"https://mock-toss-payments.zenthex.com/checkout?user={user.id}&plan={req.plan_id}"
    return {"checkout_url": checkout_url, "status": "awaiting_payment"}

@router.post("/webhook/success")
def mock_payment_success(
    req: SubscribeRequest, 
    Authorization: str = Header(None), 
    db: Session = Depends(get_db)
):
    # In a real system, the webhook comes from Stripe/Toss with a payload signature
    # For MVP, we allow the user to manually trigger success using their token
    if not Authorization:
        raise HTTPException(status_code=401, detail="Missing Token")
    
    token = Authorization.replace("Bearer ", "")
    user = get_current_user(token, db)
    
    plan_data = PLANS.get(req.plan_id)
    if not plan_data:
        raise HTTPException(status_code=400, detail="Invalid plan code")
        
    user.plan = req.plan_id
    user.studio_generations_left = plan_data["studio_limit"]
    db.commit()
    
    return {"status": "success", "message": f"Successfully upgraded to {req.plan_id}"}

@router.get("/my_quota")
def check_quota(Authorization: str = Header(None), db: Session = Depends(get_db)):
    if not Authorization:
        raise HTTPException(status_code=401, detail="Missing Token")
    
    token = Authorization.replace("Bearer ", "")
    user = get_current_user(token, db)
    
    return {
        "current_plan": user.plan,
        "studio_generations_left": user.studio_generations_left
    }
