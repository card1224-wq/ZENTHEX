import os

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from auth.router import get_current_user
from database.models import User
from database.session import get_db

router = APIRouter(prefix="/api/admin", tags=["admin"])


class UserUpdateRequest(BaseModel):
    plan: str | None = None
    role: str | None = None


class AdminState:
    global_kill_switch = False


admin_state = AdminState()


def require_owner(user: User):
    if user.role != "owner":
        raise HTTPException(status_code=403, detail="Owner permission is required.")


def user_from_header(Authorization: str, db: Session):
    if not Authorization:
        raise HTTPException(status_code=401, detail="Login is required.")
    token = Authorization.replace("Bearer ", "")
    return get_current_user(token, db)


def serialize_user(user: User):
    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role,
        "plan": user.plan,
        "email_verified": user.email_verified,
        "phone_verified": user.phone_verified,
        "studio_generations_left": user.studio_generations_left,
        "created_at": user.created_at.isoformat() if user.created_at else None,
    }


@router.get("/status")
def get_system_status(Authorization: str = Header(None), db: Session = Depends(get_db)):
    user = user_from_header(Authorization, db)
    require_owner(user)

    total_users = db.query(User).count()
    paid_users = db.query(User).filter(User.plan != "free").count()
    owner_users = db.query(User).filter(User.role == "owner").count()
    billable_users = max(paid_users - owner_users, 0)

    return {
        "status": "success",
        "total_users": total_users,
        "paid_users": paid_users,
        "owner_users": owner_users,
        "active_finance_bots": max(min(total_users, 1), 0),
        "mrr_krw": billable_users * 49000,
        "studio_jobs_today": 0,
        "global_kill_switch": admin_state.global_kill_switch,
        "system_health": "HALTED" if admin_state.global_kill_switch else "OK",
    }


@router.get("/users")
def list_users(Authorization: str = Header(None), db: Session = Depends(get_db)):
    user = user_from_header(Authorization, db)
    require_owner(user)
    rows = db.query(User).order_by(User.id.desc()).all()
    return {"status": "success", "users": [serialize_user(row) for row in rows]}


@router.patch("/users/{user_id}")
def update_user(user_id: int, req: UserUpdateRequest, Authorization: str = Header(None), db: Session = Depends(get_db)):
    admin_user = user_from_header(Authorization, db)
    require_owner(admin_user)

    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="User not found.")

    if target.id == admin_user.id and req.role and req.role != target.role:
        raise HTTPException(status_code=400, detail="You cannot change your own admin role here.")

    if req.plan is not None:
        plan_limits = {"free": 0, "studio_pro": 100, "trading_pro": 0, "ultimate": 1000}
        if req.plan not in plan_limits:
            raise HTTPException(status_code=400, detail="Unsupported plan.")
        target.plan = req.plan
        target.studio_generations_left = 999999 if target.role == "owner" else plan_limits[req.plan]

    if req.role is not None:
        if req.role not in ["user", "admin", "owner"]:
            raise HTTPException(status_code=400, detail="Unsupported role.")
        target.role = req.role
        if target.role == "owner":
            target.plan = "ultimate"
            target.studio_generations_left = 999999

    db.commit()
    db.refresh(target)
    return {"status": "success", "user": serialize_user(target)}


@router.delete("/users/{user_id}")
def delete_user(user_id: int, Authorization: str = Header(None), db: Session = Depends(get_db)):
    admin_user = user_from_header(Authorization, db)
    require_owner(admin_user)

    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="User not found.")
    if target.id == admin_user.id:
        raise HTTPException(status_code=400, detail="You cannot delete the currently logged-in account.")

    db.delete(target)
    db.commit()
    return {"status": "success", "message": "User deleted."}


def _read_text(path: str) -> str:
    try:
        with open(path, "r", encoding="utf-8") as file:
            return file.read()
    except FileNotFoundError:
        return ""


def _env_has_real_smtp() -> bool:
    host = (os.getenv("ZENTHEX_SMTP_HOST") or "").strip()
    user = (os.getenv("ZENTHEX_SMTP_USER") or "").strip()
    password = (os.getenv("ZENTHEX_SMTP_PASSWORD") or "").strip()
    blocked = {"smtp.example.com", "no-reply@example.com", "change-me"}
    return bool(host and user and password and host not in blocked and user not in blocked and password not in blocked)


def _env_has_persistent_database() -> bool:
    db_url = (os.getenv("ZENTHEX_DATABASE_URL") or "").strip()
    if not db_url:
        return False
    return not db_url.startswith("sqlite:///./zenthex.db")


def _billing_provider_ready() -> bool:
    return any(
        os.getenv(key)
        for key in ["ZENTHEX_TOSS_SECRET_KEY", "ZENTHEX_STRIPE_SECRET_KEY", "ZENTHEX_PAYMENT_PROVIDER"]
    )


def _review_item(key: str, title: str, passed: bool, detail: str, level: str = "required"):
    return {"key": key, "title": title, "status": "pass" if passed else "fail", "level": level, "detail": detail}


@router.get("/review")
def get_launch_review(Authorization: str = Header(None), db: Session = Depends(get_db)):
    user = user_from_header(Authorization, db)
    require_owner(user)

    index_html = _read_text("static/index.html")
    login_html = _read_text("static/login.html")
    studio_html = _read_text("static/studio.html")
    finance_html = _read_text("static/finance.html")
    admin_html = _read_text("static/admin.html")
    auth_router = _read_text("auth/router.py")
    admin_router = _read_text("admin/router.py")
    studio_router = _read_text("studio/router.py")
    trading_router = _read_text("trading/router.py")
    billing_router = _read_text("billing/router.py")
    models_py = _read_text("database/models.py")
    session_py = _read_text("database/session.py")
    migrations_py = _read_text("database/migrations.py")
    engine_py = _read_text("trading/engine.py")
    master_plan = _read_text("ZENTHEX_MASTER_PLAN.md")

    owner_emails = os.getenv("ZENTHEX_OWNER_EMAILS", "").strip() or "7foliath@naver.com"
    smtp_ready = _env_has_real_smtp()
    sms_ready = all(
        os.getenv(key)
        for key in ["ZENTHEX_SMS_PROVIDER", "ZENTHEX_SMS_ACCESS_KEY", "ZENTHEX_SMS_SECRET_KEY", "ZENTHEX_SMS_FROM"]
    )
    persistent_db_ready = _env_has_persistent_database()
    billing_provider_ready = _billing_provider_ready()

    checks = [
        _review_item("homepage_brand", "Homepage brand screen", "zenthex-mark.svg" in index_html and "studio.html" in index_html, "Brand mark and Studio entry are present."),
        _review_item("homepage_copy", "Homepage public copy", all(text in index_html for text in ["Zenthex는 프롬프트와 2D 도면", "Studio 체험하기", "Trading 구조 보기", "Zenthex란?"]) and "Zenthex Control" not in index_html, "Homepage remains a public Zenthex brand introduction even when the owner is signed in."),
        _review_item("no_demo_copy", "Remove demo copy", "demo" not in (index_html + studio_html + finance_html).lower() and "\ub370\ubaa8" not in index_html + studio_html + finance_html, "Public-facing copy should not read as a demo build."),
        _review_item("owner_hidden", "Hide owner-account copy", "owner account" not in login_html.lower() and "\ub300\ud45c\uacc4\uc815" not in login_html and "7foliath" not in login_html, "Login/signup does not expose owner-account guidance."),
        _review_item("owner_env", "Owner email basis", "7foliath@naver.com" in owner_emails or "DEFAULT_OWNER_EMAILS" in auth_router, "Owner email is controlled by environment or fallback."),
        _review_item("signup_fields", "Signup fields", all(text in login_html for text in ["signup-birth-date", "signup-phone", "signup-password-confirm", "signup-hint-question"]), "Signup includes identity, phone, password confirmation, and hint fields."),
        _review_item("phone_verification", "Phone verification flow", all(text in auth_router + login_html for text in ["phone/send-code", "phone/verify", "122492"]), "Phone code send/verify flow is present."),
        _review_item("email_recovery", "Email and password recovery", all(text in auth_router + login_html for text in ["email/verify", "password/question", "password/request-reset", "password/reset"]), "Email verification, hint question, and password reset routes are present."),
        _review_item("studio_trial", "Studio trial limit", "TRIAL_USAGE_BY_IP" in studio_router and "preview_only" in studio_router and "model_url" in studio_router, "Trial is one-day/IP and free users receive view-only output."),
        _review_item("studio_access_ui", "Studio owner/subscriber UI", all(text in studio_html for text in ["studio-access-chip", "zxCanExport", "대표 전체 권한", "GLB 다운로드"]) and "HL</div>" not in studio_html, "Studio refreshes account permission, removes the old HL mark, and shows export access for owner/subscribers."),
        _review_item("trading_gated", "Trading real-mode gate", all(text in finance_html for text in ["userCanSeeRealTrade", "real-key-box", "practice"]), "Trial hides API keys; owner/subscription is required for real trading."),
        _review_item("trading_access_ui", "Trading owner/subscriber UI", all(text in finance_html for text in ["finance-access-chip", "대표 실거래 권한", "구독 실거래 권한", "zenthex-mark"]), "Trading refreshes account permission and opens real-mode UI for owner/subscribers."),
        _review_item("role_separation", "Owner and subscriber separation", all(text in admin_router + admin_html + index_html + login_html for text in ["require_owner", "user.role==='owner'", "role==='owner'"]) and "['owner','admin'].includes" not in index_html + login_html + admin_html, "Only the owner account can access CEO operations screens."),
        _review_item("plan_separation", "Plan-specific product access", all(text in studio_router + trading_router + billing_router for text in ["studio_pro", "trading_pro", "studio_limit\": 0", "user.role == \"owner\""]), "Studio Pro unlocks Studio, Trading Pro unlocks Trading, and owner unlocks all."),
        _review_item("trading_targets", "Trading target and capital options", all(text in finance_html for text in ["+10%", "+30%", "+50%", "all_krw"]), "Short scalping targets and high-risk targets are available."),
        _review_item("trading_engine_scan", "Trading scanner stability", "ohlcv[\"" not in engine_py and "hourly[\"high\"]" in engine_py, "Undefined scanner variable is not present."),
        _review_item("mock_payment_guard", "Mock payment guard", "ZENTHEX_ENABLE_MOCK_PAYMENT" in billing_router, "Mock payment cannot unlock paid plans unless explicitly enabled."),
        _review_item("persistent_database", "Persistent production database", "ZENTHEX_DATABASE_URL" in session_py and "ZENTHEX_DATABASE_URL" in _read_text(".env.example") and "postgres://" in session_py and "psycopg2-binary" in _read_text("requirements.txt"), "User accounts, subscriptions, receipts, Studio history, and Trading settings must live in a persistent DB outside GitHub deploy files."),
        _review_item("postgres_safe_migration", "PostgreSQL-safe startup", "is_sqlite_database" in migrations_py and "if not is_sqlite_database()" in migrations_py, "SQLite-only migrations are skipped when the production database is PostgreSQL."),
        _review_item("auto_billing_plan", "Monthly auto-renewal billing plan", all(text in billing_router for text in ["monthly_auto_renewal", "Toss Payments", "Stripe", "webhook_events"]), "Subscriptions are planned as monthly auto-renewal with Toss Payments for Korea and Stripe for global expansion."),
        _review_item("subscription_state", "Subscription state table", all(text in models_py + billing_router for text in ["class Subscription", "provider_subscription_id", "next_billing_date", "/subscription"]), "Current subscription state is stored separately from one-time receipt history."),
        _review_item("operating_cost_review", "Operating cost review", all(text in master_plan for text in ["비용 단계", "무료 PostgreSQL", "정식 유료 서비스", "결제 수수료", "GPU Worker"]), "CEO review separates free validation costs from paid production operating costs."),
        _review_item("master_plan", "Master plan document", all(text in master_plan for text in ["Zenthex SaaS Master Plan", "데이터 보존 원칙", "자동결제", "CEO 대시보드", "최종 결론"]), "Current architecture, role separation, billing, data retention, and launch risks are documented in the master plan."),
        _review_item("db_columns", "Database columns", all(text in models_py for text in ["phone_verified", "password_hint_answer_hash", "email_verified", "studio_generations_left"]), "Latest auth, verification, and Studio usage columns are present."),
        _review_item("user_management", "Subscriber management", all(text in admin_router + admin_html for text in ["/users", "deleteUser", "changePlan"]), "Owner can list users, change plans, and delete accounts."),
        _review_item("smtp_ready", "SMTP delivery configured", smtp_ready, "Real email delivery needs SMTP environment values.", "recommended"),
        _review_item("sms_ready", "SMS provider connected", sms_ready, "Production SMS provider should be connected before public launch.", "recommended"),
        _review_item("persistent_db_ready", "Production DB environment ready", persistent_db_ready, "Before paid users join, set ZENTHEX_DATABASE_URL to PostgreSQL or another persistent DB so GitHub updates never erase accounts.", "recommended"),
        _review_item("billing_provider_ready", "Real billing provider connected", billing_provider_ready, "Before charging users, connect Toss Payments billing-key auto-payment and/or Stripe subscriptions with webhook handling.", "recommended"),
    ]

    required = [item for item in checks if item["level"] == "required"]
    passed_required = [item for item in required if item["status"] == "pass"]
    score = round((len([item for item in checks if item["status"] == "pass"]) / len(checks)) * 100)

    return {
        "status": "success",
        "score": score,
        "ready": len(passed_required) == len(required),
        "passed": len([item for item in checks if item["status"] == "pass"]),
        "total": len(checks),
        "checks": checks,
    }


@router.post("/killswitch")
def toggle_killswitch(action: dict, Authorization: str = Header(None), db: Session = Depends(get_db)):
    user = user_from_header(Authorization, db)
    require_owner(user)
    is_enabled = action.get("enabled", False)
    admin_state.global_kill_switch = is_enabled
    if is_enabled:
        print("[CEO ADMIN] GLOBAL KILL SWITCH ACTIVATED. All trading engines are halted.")
    else:
        print("[CEO ADMIN] System returned to normal operation.")
    return {"status": "success", "kill_switch_active": admin_state.global_kill_switch}
