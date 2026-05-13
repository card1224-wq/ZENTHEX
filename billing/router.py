from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel
from sqlalchemy.orm import Session
from database.session import get_db
from database.models import BillingHistory
from auth.router import get_current_user
import os
import time
import uuid

router = APIRouter(prefix="/api/billing", tags=["billing"])

class SubscribeRequest(BaseModel):
    plan_id: str

class CheckoutResponse(BaseModel):
    checkout_url: str
    status: str

PLANS = {
    "free": {"name": "Free Trial", "price": 0, "studio_limit": 3, "features": ["무료 체험", "저장 제한"]},
    "studio_pro": {"name": "Studio Pro", "price": 49000, "studio_limit": 100, "features": ["3D 생성 100회", "GLB 다운로드", "작업 히스토리"]},
    "trading_pro": {"name": "Trading Pro", "price": 99000, "studio_limit": 10, "features": ["전략 검증", "Signal Guard", "목표 수익률 자동 종료"]},
    "ultimate": {"name": "Zenthex Ultimate", "price": 149000, "studio_limit": 1000, "features": ["Studio + Trading", "우선 처리", "모바일 알림"]},
}

def auth_user(Authorization: str, db: Session):
    if not Authorization:
        raise HTTPException(status_code=401, detail="로그인이 필요합니다.")
    token = Authorization.replace("Bearer ", "")
    return get_current_user(token, db)

def create_billing_history(db: Session, user, plan_id: str, status: str = "paid"):
    plan = PLANS[plan_id]
    item = BillingHistory(
        user_id=user.id,
        plan_id=plan_id,
        plan_name=plan["name"],
        amount_krw=plan["price"],
        status=status,
        payment_method="mock_checkout",
        receipt_no=f"ZX-{time.strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}",
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item

@router.get("/plans")
def get_plans():
    return {"plans": PLANS}

@router.post("/subscribe", response_model=CheckoutResponse)
def mock_checkout(req: SubscribeRequest, Authorization: str = Header(None), db: Session = Depends(get_db)):
    user = auth_user(Authorization, db)

    if user.role == "owner":
        user.plan = "ultimate"
        user.studio_generations_left = 999999
        db.commit()
        return {"checkout_url": "", "status": "owner_unlocked"}

    if req.plan_id not in PLANS:
        raise HTTPException(status_code=400, detail="Invalid plan code")
    if PLANS[req.plan_id]["price"] == 0:
        user.plan = "free"
        user.studio_generations_left = PLANS["free"]["studio_limit"]
        db.commit()
        return {"checkout_url": "", "status": "upgraded_to_free"}

    checkout_url = f"https://mock-toss-payments.zenthex.com/checkout?user={user.id}&plan={req.plan_id}"
    return {"checkout_url": checkout_url, "status": "awaiting_payment"}

@router.post("/webhook/success")
def mock_payment_success(req: SubscribeRequest, Authorization: str = Header(None), db: Session = Depends(get_db)):
    user = auth_user(Authorization, db)
    if user.role != "owner" and os.getenv("ZENTHEX_ENABLE_MOCK_PAYMENT", "false").lower() != "true":
        raise HTTPException(status_code=403, detail="결제 승인 처리는 실제 결제사 연동 후 사용할 수 있습니다.")
    plan_data = PLANS.get(req.plan_id)
    if not plan_data:
        raise HTTPException(status_code=400, detail="Invalid plan code")

    user.plan = req.plan_id
    user.studio_generations_left = plan_data["studio_limit"]
    receipt = create_billing_history(db, user, req.plan_id)
    return {"status": "success", "message": f"Successfully upgraded to {req.plan_id}", "payment_id": receipt.id}

@router.get("/my_quota")
def check_quota(Authorization: str = Header(None), db: Session = Depends(get_db)):
    user = auth_user(Authorization, db)
    if user.role == "owner":
        return {"current_plan": "owner_unlimited", "studio_generations_left": 999999, "billing_required": False}
    return {"current_plan": user.plan, "studio_generations_left": user.studio_generations_left, "billing_required": user.plan == "free"}

@router.get("/history")
def billing_history(Authorization: str = Header(None), db: Session = Depends(get_db)):
    user = auth_user(Authorization, db)
    rows = db.query(BillingHistory).filter(BillingHistory.user_id == user.id).order_by(BillingHistory.id.desc()).all()
    return {"history": [serialize_payment(row) for row in rows]}

@router.get("/receipt/{payment_id}")
def billing_receipt(payment_id: int, Authorization: str = Header(None), db: Session = Depends(get_db)):
    user = auth_user(Authorization, db)
    row = db.query(BillingHistory).filter(BillingHistory.id == payment_id, BillingHistory.user_id == user.id).first()
    if not row:
        raise HTTPException(status_code=404, detail="결제내역을 찾을 수 없습니다.")
    return {"receipt": serialize_payment(row), "company": {"name": "Zenthex", "service": "Zenthex SaaS Platform"}}

def serialize_payment(row: BillingHistory):
    return {
        "id": row.id,
        "plan_id": row.plan_id,
        "plan_name": row.plan_name,
        "amount_krw": row.amount_krw,
        "status": row.status,
        "payment_method": row.payment_method,
        "receipt_no": row.receipt_no,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }
