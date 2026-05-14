from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from database.session import get_db
from database.models import User
from auth.router import get_current_user
import os

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

def _read_text(path: str) -> str:
    try:
        with open(path, "r", encoding="utf-8") as file:
            return file.read()
    except FileNotFoundError:
        return ""

def _review_item(key: str, title: str, passed: bool, detail: str, level: str = "required"):
    return {
        "key": key,
        "title": title,
        "status": "pass" if passed else "fail",
        "level": level,
        "detail": detail,
    }

@router.get("/review")
def get_launch_review(Authorization: str = Header(None), db: Session = Depends(get_db)):
    user = user_from_header(Authorization, db)
    require_owner_or_admin(user)

    index_html = _read_text("static/index.html")
    login_html = _read_text("static/login.html")
    studio_html = _read_text("static/studio.html")
    finance_html = _read_text("static/finance.html")
    auth_router = _read_text("auth/router.py")
    studio_router = _read_text("studio/router.py")
    billing_router = _read_text("billing/router.py")
    models_py = _read_text("database/models.py")

    owner_emails = os.getenv("ZENTHEX_OWNER_EMAILS", "").strip()
    smtp_ready = all(os.getenv(key) for key in ["ZENTHEX_SMTP_HOST", "ZENTHEX_SMTP_USER", "ZENTHEX_SMTP_PASSWORD"])
    sms_ready = all(os.getenv(key) for key in ["ZENTHEX_SMS_PROVIDER", "ZENTHEX_SMS_ACCESS_KEY", "ZENTHEX_SMS_SECRET_KEY", "ZENTHEX_SMS_FROM"])

    checks = [
        _review_item("homepage_brand", "홈페이지 브랜드 화면", "zenthex-mark.svg" in index_html and "Trading 구조 보기" in index_html, "Zenthex 마크, Studio 체험, Trading 구조 보기 문구 확인"),
        _review_item("no_demo_copy", "데모 문구 제거", "데모" not in index_html + studio_html + finance_html, "공개 화면에 데모 문구가 남아있지 않아야 합니다."),
        _review_item("owner_hidden", "대표계정 문구 비노출", "대표계정" not in login_html and "7foliath" not in login_html, "로그인/회원가입 화면에 대표 계정 안내를 노출하지 않습니다."),
        _review_item("owner_env", "대표 이메일 환경변수", bool(owner_emails), "서버 환경변수 ZENTHEX_OWNER_EMAILS 설정 필요"),
        _review_item("signup_fields", "회원가입 필수 입력", all(text in login_html for text in ["생년월일", "휴대폰 번호", "비밀번호 확인", "비밀번호 힌트 질문"]), "이름, 이메일, 비밀번호 확인, 생년월일, 휴대폰, 힌트 질문/답변 확인"),
        _review_item("phone_verification", "휴대폰 인증 흐름", all(text in auth_router + login_html for text in ["phone/send-code", "phone/verify", "인증코드 발송"]), "휴대폰 인증코드 발송/확인 API와 화면 확인"),
        _review_item("email_recovery", "이메일 인증/비밀번호 재설정", all(text in auth_router for text in ["email/verify", "password/question", "password/hint", "password/reset"]), "이메일 인증, 힌트 질문, 재설정 코드 흐름 확인"),
        _review_item("studio_trial", "Studio 체험 제한", "TRIAL_USAGE_BY_IP" in studio_router and "preview_only" in studio_router and "model_url" in studio_router, "같은 IP 하루 1회, 보기 전용, 구독 후 다운로드 구조 확인"),
        _review_item("trading_gated", "Trading 실거래 잠금", all(text in finance_html for text in ["userCanSeeRealTrade", "real-key-box", "전략 체험 모드"]), "체험판 API 키 숨김, 구독/대표 권한 후 실거래 표시 확인"),
        _review_item("mock_payment_guard", "가짜 결제 보호", "ZENTHEX_ENABLE_MOCK_PAYMENT" in billing_router, "공개 업로드에서 mock 결제가 바로 유료 권한을 열지 않도록 보호"),
        _review_item("db_columns", "DB 컬럼 준비", all(text in models_py for text in ["phone_verified", "password_hint_answer_hash", "email_verified", "studio_generations_left"]), "회원/인증/Studio 사용량 컬럼 확인"),
        _review_item("smtp_ready", "이메일 발송 설정", smtp_ready, "SMTP 환경변수가 채워지면 실제 이메일 발송 가능", "recommended"),
        _review_item("sms_ready", "SMS 발송사 연결", sms_ready, "현재는 개발용 인증 구조입니다. 공개 출시 전 SMS 발송사 연결 필요", "recommended"),
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
    require_owner_or_admin(user)

    is_enabled = action.get("enabled", False)
    admin_state.global_kill_switch = is_enabled
    if is_enabled:
        print("[CEO ADMIN] GLOBAL KILL SWITCH ACTIVATED. All trading engines are halted.")
    else:
        print("[CEO ADMIN] System returned to normal operation.")
    return {"status": "success", "kill_switch_active": admin_state.global_kill_switch}
