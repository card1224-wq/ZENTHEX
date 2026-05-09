from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from database.session import get_db
from database.models import User
from auth.router import get_current_user

router = APIRouter(prefix="/api/admin", tags=["admin"])

class AdminState:
    global_kill_switch = False

admin_state = AdminState()

def check_is_admin(user: User):
    # 이메일 하드코딩 제거, DB의 role 컬럼 확인
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized (Requires CEO/Admin role)")

@router.get("/status")
def get_system_status(db: Session = Depends(get_db)):
    # Gather mock system analytics
    total_users = db.query(User).count()
    
    # Normally we would iterate over all running BotStates in a manager.
    # For our MVP backend, we mock it based on total DB users.
    active_finance_bots = max(min(total_users, 1), 0) # Mock to 1 active if user exists
    
    return {
        "status": "success",
        "total_users": total_users,
        "active_finance_bots": active_finance_bots,
        "global_kill_switch": admin_state.global_kill_switch,
        "system_health": "Degraded" if admin_state.global_kill_switch else "OK"
    }

@router.post("/killswitch")
def toggle_killswitch(
    action: dict, # {"enabled": true/false}
    Authorization: str = Header(None), 
    db: Session = Depends(get_db)
):
    if not Authorization:
         raise HTTPException(status_code=401, detail="Missing Token")
    
    token = Authorization.replace("Bearer ", "")
    user = get_current_user(token, db)
    check_is_admin(user)
    
    is_enabled = action.get("enabled", False)
    admin_state.global_kill_switch = is_enabled
    
    if is_enabled:
        print("🚨 [CEO ADMIN] GLOBAL KILL SWITCH ACTIVATED! All Trading Engines halting...")
    else:
         print("✅ [CEO ADMIN] System returned to normal operation.")
         
    return {"status": "success", "kill_switch_active": admin_state.global_kill_switch}
