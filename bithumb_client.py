from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from auth.router import get_current_user
from database.models import SupportTicket, User
from database.session import get_db

router = APIRouter(prefix="/api/support", tags=["support"])


class TicketCreateRequest(BaseModel):
    email: str
    category: str
    title: str
    message: str


class TicketUpdateRequest(BaseModel):
    status: str | None = None
    admin_reply: str | None = None


def _optional_user(authorization: str | None, db: Session) -> User | None:
    if not authorization:
        return None
    token = authorization.replace("Bearer ", "")
    try:
        return get_current_user(token, db)
    except HTTPException:
        return None


def _require_owner(authorization: str | None, db: Session) -> User:
    if not authorization:
        raise HTTPException(status_code=401, detail="Login is required.")
    token = authorization.replace("Bearer ", "")
    user = get_current_user(token, db)
    if user.role != "owner":
        raise HTTPException(status_code=403, detail="Owner permission is required.")
    return user


def _serialize_ticket(row: SupportTicket):
    return {
        "id": row.id,
        "user_id": row.user_id,
        "email": row.email,
        "category": row.category,
        "title": row.title,
        "message": row.message,
        "status": row.status,
        "admin_reply": row.admin_reply,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


@router.post("/tickets")
def create_ticket(req: TicketCreateRequest, Authorization: str = Header(None), db: Session = Depends(get_db)):
    title = req.title.strip()
    message = req.message.strip()
    category = req.category.strip() or "general"
    email = req.email.strip().lower()
    if "@" not in email or "." not in email:
        raise HTTPException(status_code=400, detail="Please enter a valid email address.")
    if len(title) < 2:
        raise HTTPException(status_code=400, detail="Please enter an inquiry title.")
    if len(message) < 5:
        raise HTTPException(status_code=400, detail="Please enter inquiry details.")

    user = _optional_user(Authorization, db)
    ticket = SupportTicket(
        user_id=user.id if user else None,
        email=email,
        category=category[:40],
        title=title[:160],
        message=message[:4000],
        status="open",
    )
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    return {"status": "success", "ticket": _serialize_ticket(ticket)}


@router.get("/my-tickets")
def list_my_tickets(Authorization: str = Header(None), db: Session = Depends(get_db)):
    if not Authorization:
        raise HTTPException(status_code=401, detail="Login is required.")
    user = get_current_user(Authorization.replace("Bearer ", ""), db)
    rows = (
        db.query(SupportTicket)
        .filter(func.lower(SupportTicket.email) == user.email.lower())
        .order_by(SupportTicket.id.desc())
        .limit(20)
        .all()
    )
    return {"status": "success", "tickets": [_serialize_ticket(row) for row in rows]}


@router.get("/admin/tickets")
def admin_list_tickets(Authorization: str = Header(None), db: Session = Depends(get_db)):
    _require_owner(Authorization, db)
    rows = db.query(SupportTicket).order_by(SupportTicket.id.desc()).limit(100).all()
    return {"status": "success", "tickets": [_serialize_ticket(row) for row in rows]}


@router.patch("/admin/tickets/{ticket_id}")
def admin_update_ticket(ticket_id: int, req: TicketUpdateRequest, Authorization: str = Header(None), db: Session = Depends(get_db)):
    _require_owner(Authorization, db)
    ticket = db.query(SupportTicket).filter(SupportTicket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Support ticket not found.")
    if req.status is not None:
        if req.status not in ["open", "reviewing", "answered", "closed"]:
            raise HTTPException(status_code=400, detail="Unsupported ticket status.")
        ticket.status = req.status
    if req.admin_reply is not None:
        ticket.admin_reply = req.admin_reply.strip()[:4000]
    ticket.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(ticket)
    return {"status": "success", "ticket": _serialize_ticket(ticket)}
