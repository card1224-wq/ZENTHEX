from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from database.session import get_db
from database.models import User
from auth.router import get_current_user

router = APIRouter(prefix="/api/admin", tags=["admin"])

class AdminState:
    global_kill_switch = False

admin_state = AdminState()

def require_owner_or_admin(user: User):
    if user.role not in ["owner", "admin"]:
        raise HTTPException(status_code=403, detail="대표 또는 관리자 권한이 필요합니다.")

def user_from_header(Authorization: str, db: Session):
    if not Authorization:
        raise HTTPException(status_code=401, detail="로그인이 필요합니다.")
    token = Authorization.replace("Bearer ", "")
    return get_current_user(token, db)

@router.get("/status")
def get_system_status(Authorization: str = Header(None), db: Session = Depends(get_db)):
    user = user_from_header(Authorization, db)
    require_owner_or_admin(user)

    total_users = db.query(User).count()
    paid_users = db.query(User).filter(User.plan != "free").count()
    owner_users = db.query(User).filter(User.role == "owner").count()
    active_finance_bots = max(min(total_users, 1), 0)

    return {
        "status": "success",
        "total_users": total_users,
        "paid_users": paid_users,
        "owner_users": owner_users,
        "active_finance_bots": active_finance_bots,
        "mrr_krw": max(paid_users - owner_users, 0) * 49000,
        "studio_jobs_today": 0,
        "global_kill_switch": admin_state.global_kill_switch,
        "system_health": "HALTED" if admin_state.global_kill_switch else "OK",
    }

@router.post("/killswitch")
def toggle_killswitch(action: dict, Authorization: str = Header(None), db: Session = Depends(get_db)):
    user = user_from_header(Authorization, db)
    require_owner_or_admin(user)

    is_enabled = action.get("enabled", False)
    admin_state.global_kill_switch = is_enabled
    if is_enabled:
        print("[CEO ADMIN] GLOBAL KILL SWITCH ACTIVATED. All trading engines are halted.")
    else:
        print("[CEO ADMIN] System returned to normal operation.")
    return {"status": "success", "kill_switch_active": admin_state.global_kill_switch}
