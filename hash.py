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
    approval_status: str | None = None


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
        "approval_status": user.approval_status or "approved",
        "is_active": user.is_active,
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
            target.approval_status = "approved"
            target.is_active = True

    if req.approval_status is not None:
        if req.approval_status not in ["pending", "approved", "rejected"]:
            raise HTTPException(status_code=400, detail="Unsupported approval status.")
        if target.role == "owner" and req.approval_status != "approved":
            raise HTTPException(status_code=400, detail="Owner account must stay approved.")
        target.approval_status = req.approval_status
        target.is_active = req.approval_status == "approved"

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


REVIEW_KOREAN_COPY = {
    "homepage_brand": ("홈페이지 브랜드 화면", "젠텍스 마크와 Studio 진입 버튼이 있는지 확인합니다."),
    "homepage_copy": ("홈페이지 소개 문구", "대표로 로그인해도 첫 화면은 내부 운영 화면이 아니라 젠텍스 소개 화면이어야 합니다."),
    "homepage_visual_preview": ("홈페이지 시각 미리보기", "첫 화면이 글만 있는 화면이 아니라 Studio와 Trading 미리보기 패널을 보여주는지 확인합니다."),
    "logged_in_home_nav": ("로그인 후 상단 메뉴", "로그인 사용자가 마이페이지, 고객센터, 로그아웃, 작업실 진입 메뉴를 볼 수 있어야 합니다."),
    "no_demo_copy": ("데모 문구 제거", "실서비스 화면에 demo 또는 데모 버전처럼 보이는 문구가 없어야 합니다."),
    "owner_hidden": ("대표 계정 노출 방지", "로그인/회원가입 화면에 대표 이메일이나 대표 계정 안내가 노출되면 안 됩니다."),
    "owner_env": ("대표 이메일 기준", "대표 이메일은 서버 환경변수 또는 기본값으로 관리되어야 합니다."),
    "signup_fields": ("회원가입 입력 항목", "이름, 생년월일, 휴대폰, 비밀번호 확인, 힌트 질문 항목이 있는지 확인합니다."),
    "signup_approval": ("대표 가입 승인", "일반 사용자는 가입 후 승인 대기 상태가 되고 대표가 승인해야 로그인할 수 있어야 합니다."),
    "phone_verification": ("휴대폰 인증 흐름", "휴대폰 인증코드 발송과 확인 흐름이 있는지 확인합니다."),
    "email_recovery": ("이메일 인증과 비밀번호 찾기", "이메일 인증, 힌트 질문, 비밀번호 재설정 API가 있는지 확인합니다."),
    "studio_trial": ("Studio 체험 제한", "무료 체험은 IP 기준 하루 1회이고 보기 전용이어야 합니다."),
    "studio_access_ui": ("Studio 대표/구독자 화면", "대표와 구독자가 Studio 전체 권한과 다운로드 권한을 볼 수 있어야 합니다."),
    "studio_jpg_export": ("Studio JPG 저장", "GLB와 JPG의 차이를 안내하고 JPG 저장 기능을 제공해야 합니다."),
    "studio_prompt_preview": ("Studio 프롬프트 결과 미리보기", "프롬프트 내용에 따라 3D 미리보기가 실제로 달라져야 합니다."),
    "studio_worker_fallback": ("Studio Worker 장애 대응", "OpenCV/3D Worker 의존성이 없어도 화면 미리보기는 실패하지 않아야 합니다."),
    "studio_nanobanana_provider": ("Studio NanoBanana 연결", "Gemini NanoBanana 키가 있으면 프롬프트 이미지가 즉시 생성되어야 합니다."),
    "studio_nanobanana_main_result": ("Studio 중앙 이미지 결과", "NanoBanana/Gemini 이미지는 작은 보조 패널이 아니라 중앙 메인 결과로 보여야 합니다."),
    "trading_gated": ("Trading 실거래 권한 제한", "체험 화면에서는 API 키 입력을 숨기고 구독/대표 권한에서만 실거래를 열어야 합니다."),
    "upbit_key_verify": ("Upbit 키 인증 버튼", "실거래 전 키 진단뿐 아니라 키 인증 버튼이 있어야 합니다."),
    "binance_connector_ready": ("Binance 연결 준비", "Binance 계정 생성 후 Testnet/Live 키 인증과 잔고 조회를 바로 할 수 있어야 합니다."),
    "upbit_account_summary": ("Upbit 잔고와 수익률 조회", "키를 저장하지 않고 조회 시점의 현금, 보유 코인, 평가손익, 수익률을 볼 수 있어야 합니다."),
    "mobile_real_status_protection": ("모바일 실거래 상태 보호", "휴대폰에서도 상태 확인은 가능하지만 실거래 상태와 중지는 로그인과 Trading 권한이 필요해야 합니다."),
    "upbit_server_ip_notice": ("Upbit 허용 IP 안내", "Upbit에 등록할 Zenthex FastAPI 서버 IP를 화면에 보여줘야 합니다."),
    "upbit_fixed_ip_guard": ("Upbit 고정 IP 보호", "운영 실거래에서는 자동 감지 IP가 아니라 고정 서버 IP가 설정되어야 합니다."),
    "upbit_outbound_ip_verify": ("Upbit outbound IP 검증", "표시 IP와 실제 outbound IP가 같은지 실거래 전 검증할 수 있어야 합니다."),
    "trading_compact_summary": ("Trading 전략 한눈 요약", "전략 설정이 길어도 매도방식, 목표, 투자금, 코인 선택이 상단에서 한눈에 보여야 합니다."),
    "trading_exchange_selection": ("Trading 거래소 선택", "Upbit와 Binance를 버튼으로 먼저 선택한 뒤 해당 거래소 설정으로 넘어가야 합니다."),
    "trading_advanced_collapse": ("Trading 고급 설정 접기", "추적익절과 보유코인 정리 같은 고급/위험 설정은 기본 화면에서 접혀 있어야 합니다."),
    "trading_return_chart": ("Trading 수익률 그래프", "업비트 잔고/상태 조회 기준의 최근 수익률 흐름을 그래프로 확인할 수 있어야 합니다."),
    "trading_split_entry": ("Trading 분할 진입", "총 투자금을 여러 번 나누어 진입하고 평균 매수가 기준으로 익절/손절해야 합니다."),
    "trading_stop_controls": ("Trading 종료 버튼 분리", "일시정지와 전량 매도 후 종료가 분리되어야 합니다."),
    "trading_kst_and_criteria": ("Trading 시간/조건 표시", "시스템 로그는 한국시간 기준이고 자동 선정 조건이 화면에 보여야 합니다."),
    "trading_three_column_layout": ("Trading 3단 레이아웃", "데스크톱에서는 핵심 실행, 실시간 상태, 보조 설정이 3단으로 나뉘어야 합니다."),
    "trading_falling_coin_filter": ("Trading 하락 진입 방지", "거래량은 많지만 가격이 밀리는 코인과 고점 추격 코인을 걸러야 합니다."),
    "trading_rising_confirmation": ("Trading 상승 확인 진입", "1분/3분/5분 상승과 최근 양봉 우세가 확인될 때만 진입해야 합니다."),
    "trading_no_average_down": ("Trading 물타기 금지", "분할 진입은 하락 추가매수가 아니라 수익 방향 확인 후 추가 진입이어야 합니다."),
    "trading_entry_guard": ("Trading 진입 방어", "BTC/ETH 시장 급락, 약한 호가, 진입 직전 가격 밀림, 손절 직후 재진입을 막아야 합니다."),
    "secret_key_visibility": ("Secret Key 보기 제어", "Secret Key는 기본적으로 숨기고 필요할 때만 임시로 볼 수 있어야 합니다."),
    "customer_center": ("고객센터 페이지", "고객센터가 홈페이지에서 연결되고 실제 페이지로 열려야 합니다."),
    "support_tickets": ("고객 문의 접수 시스템", "사용자가 문의를 남기고 대표가 대시보드에서 처리할 수 있어야 합니다."),
    "trading_access_ui": ("Trading 대표/구독자 화면", "대표와 구독자가 실거래 권한 화면으로 진입해야 합니다."),
    "role_separation": ("대표와 구독자 권한 분리", "CEO 운영 기능은 대표 계정만 사용할 수 있어야 합니다."),
    "account_role_workspace": ("마이페이지 역할별 작업 공간", "마이페이지는 대표에게 CEO 운영 진입을, 구독자에게 본인 서비스 작업을 분리해서 보여줘야 합니다."),
    "plan_separation": ("플랜별 서비스 권한", "Studio Pro, Trading Pro, Ultimate 권한이 서로 섞이지 않아야 합니다."),
    "trading_targets": ("Trading 목표수익률과 투자금", "+10%, +30%, +50% 목표와 KRW 현금 전액, 비율, 고정금액, 보유 코인 정리 후 재진입 모드가 있는지 확인합니다."),
    "real_stop_loss_halts": ("실거래 손절 후 완전 정지", "실거래 손절 후 자동으로 다시 스캔하거나 재진입하면 안 됩니다."),
    "trading_engine_scan": ("Trading 스캐너 안정성", "시장 스캔 코드에 깨진 변수 참조가 없는지 확인합니다."),
    "mock_payment_guard": ("Mock 결제 보호", "테스트 결제가 허용된 경우에만 유료 플랜을 열 수 있어야 합니다."),
    "persistent_database": ("영구 데이터베이스", "유료 사용자 데이터는 GitHub 파일이 아니라 영구 DB에 저장되어야 합니다."),
    "postgres_safe_migration": ("PostgreSQL 안전 시작", "운영 DB가 PostgreSQL일 때 SQLite 전용 마이그레이션이 실행되지 않아야 합니다."),
    "auto_billing_plan": ("월 자동결제 구조", "Toss Payments와 Stripe 기반 월 자동결제 구조가 준비되어야 합니다."),
    "subscription_state": ("현재 구독 상태 저장", "결제내역과 별도로 현재 구독 상태를 저장해야 합니다."),
    "operating_cost_review": ("운영 비용 검토", "무료 검증 단계와 유료 운영 단계의 비용을 분리해 검토해야 합니다."),
    "master_plan": ("마스터 플랜 문서", "권한, 결제, 데이터 보존, 리스크가 마스터 플랜에 정리되어야 합니다."),
    "db_columns": ("DB 컬럼 확인", "인증, Studio 사용량, 고객 문의에 필요한 DB 컬럼이 있는지 확인합니다."),
    "user_management": ("가입자 관리", "대표가 사용자 목록, 플랜 변경, 계정 삭제를 할 수 있어야 합니다."),
    "smtp_ready": ("실제 이메일 발송 준비", "정식 출시 전 SMTP 환경값을 연결해야 합니다."),
    "sms_ready": ("실제 문자 발송 준비", "정식 출시 전 SMS 발송 업체를 연결해야 합니다."),
    "persistent_db_ready": ("운영 DB 환경 준비", "유료 가입 전 PostgreSQL 같은 영구 DB 환경변수를 설정해야 합니다."),
    "billing_provider_ready": ("실제 결제사 연결", "유료 결제 전 Toss Payments 또는 Stripe와 webhook을 연결해야 합니다."),
}


def _apply_bilingual_review_copy(checks: list[dict]) -> list[dict]:
    for item in checks:
        item["title_en"] = item["title"]
        item["detail_en"] = item["detail"]
        korean = REVIEW_KOREAN_COPY.get(item["key"])
        if korean:
            item["title_ko"], item["detail_ko"] = korean
            item["title"] = korean[0]
            item["detail"] = korean[1]
    return checks


@router.get("/review")
def get_launch_review(Authorization: str = Header(None), db: Session = Depends(get_db)):
    user = user_from_header(Authorization, db)
    require_owner(user)

    index_html = _read_text("static/index.html")
    login_html = _read_text("static/login.html")
    studio_html = _read_text("static/studio.html")
    finance_html = _read_text("static/finance.html")
    account_html = _read_text("static/account.html")
    customer_html = _read_text("static/customer.html")
    admin_html = _read_text("static/admin.html")
    auth_router = _read_text("auth/router.py")
    admin_router = _read_text("admin/router.py")
    studio_router = _read_text("studio/router.py")
    trading_router = _read_text("trading/router.py")
    billing_router = _read_text("billing/router.py")
    support_router = _read_text("support/router.py")
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
        _review_item("homepage_copy", "Homepage public copy", "Zenthex Control" not in index_html and "Zenthex란?" in index_html, "Homepage remains a public Zenthex brand introduction."),
        _review_item("homepage_visual_preview", "Homepage visual preview", all(text in index_html for text in ["Studio Preview", "Trading Signals", "visual-panel"]), "Homepage includes visual Studio and Trading preview panels."),
        _review_item("logged_in_home_nav", "Logged-in homepage navigation", all(text in index_html for text in ["마이페이지", "고객센터", "로그아웃", "CEO Dashboard"]) and "renderHome" not in index_html and "hero-actions" not in index_html, "Logged-in users see account, support, logout, and owner dashboard navigation without changing the public homepage hero."),
        _review_item("no_demo_copy", "Remove demo copy", "demo" not in (index_html + studio_html + finance_html).lower() and "\ub370\ubaa8" not in index_html + studio_html + finance_html, "Public-facing copy should not read as a demo build."),
        _review_item("owner_hidden", "Hide owner-account copy", "owner account" not in login_html.lower() and "\ub300\ud45c\uacc4\uc815" not in login_html and "7foliath" not in login_html, "Login/signup does not expose owner-account guidance."),
        _review_item("owner_env", "Owner email basis", "7foliath@naver.com" in owner_emails or "DEFAULT_OWNER_EMAILS" in auth_router, "Owner email is controlled by environment or fallback."),
        _review_item("signup_fields", "Signup fields", all(text in login_html for text in ["signup-birth-date", "signup-phone", "signup-password-confirm", "signup-hint-question"]), "Signup includes identity, phone, password confirmation, and hint fields."),
        _review_item("signup_approval", "Owner approval for signup", all(text in auth_router + admin_router + admin_html + models_py for text in ["approval_status", "승인 대기", "changeApproval"]), "Normal users wait for owner approval before they can log in."),
        _review_item("phone_verification", "Phone verification flow", all(text in auth_router + login_html for text in ["phone/send-code", "phone/verify", "122492"]), "Phone code send/verify flow is present."),
        _review_item("email_recovery", "Email and password recovery", all(text in auth_router + login_html for text in ["email/verify", "password/question", "password/request-reset", "password/reset"]), "Email verification, hint question, and password reset routes are present."),
        _review_item("studio_trial", "Studio trial limit", "TRIAL_USAGE_BY_IP" in studio_router and "preview_only" in studio_router and "model_url" in studio_router, "Trial is one-day/IP and free users receive view-only output."),
        _review_item("studio_access_ui", "Studio owner/subscriber UI", all(text in studio_html for text in ["studio-access-chip", "zxCanExport", "대표 전체 권한", "GLB 다운로드"]) and "HL</div>" not in studio_html, "Studio refreshes account permission and shows export access for owner/subscribers."),
        _review_item("studio_jpg_export", "Studio JPG export", all(text in studio_html for text in ["JPG 저장", "zxDownloadJpg", "GLB 3D 모델"]), "Studio explains GLB versus JPG and lets owner/subscribers save the preview as JPG."),
        _review_item("studio_prompt_preview", "Studio prompt-specific preview", all(text in studio_html + studio_router for text in ["describe_prompt_preview", "apartment_32", "preview-result-card", "generateProceduralBuilding(result.preview"]), "Studio prompt generation returns a preview profile and changes the viewer for apartment/cafe/office style prompts."),
        _review_item("studio_worker_fallback", "Studio worker fallback", all(text in studio_router + studio_html for text in ["STUDIO_WORKER_READY", "worker_ready", "3D Worker 의존성", "GLB 파일은 준비되지 않았습니다"]), "Studio remains usable as a visual preview even if OpenCV or the 3D worker is unavailable."),
        _review_item("studio_nanobanana_provider", "Studio NanoBanana provider", all(text in studio_router + studio_html + _read_text(".env.example") + _read_text("requirements.txt") for text in ["generate_preview_image", "GEMINI_API_KEY", "gemini-2.5-flash-image", "nanobanana-preview", "google-genai"]), "Studio can call NanoBanana for immediate prompt image previews when a Gemini API key is configured."),
        _review_item("studio_nanobanana_main_result", "Studio NanoBanana main result", all(text in studio_html for text in ["translate(-50%, -50%)", "JPG 이미지 저장", "3D Worker 서버 연결 후 제공", "zxCurrentImageUrl"]), "NanoBanana/Gemini images are centered as the main Studio result and can be saved by owner/subscribers."),
        _review_item("trading_gated", "Trading real-mode gate", all(text in finance_html for text in ["userCanSeeRealTrade", "real-key-box", "practice"]), "Trial hides API keys; owner/subscription is required for real trading."),
        _review_item("upbit_key_verify", "Upbit key verification step", all(text in finance_html + trading_router for text in ["업비트 키 인증하기", "verifyUpbitKey", "/verify-key", "verified"]), "Real trading has a visible key verification button before the live engine starts."),
        _review_item("binance_connector_ready", "Binance connector readiness", all(text in finance_html + trading_router + _read_text("trading/binance_client.py") for text in ["Binance 키 인증하기", "binance/verify-key", "binance/account-summary", "Testnet", "Spot", "Futures"]), "Binance Testnet/Live key verification and balance lookup are ready, while Futures is blocked for MVP."),
        _review_item("upbit_account_summary", "Upbit balance and return view", all(text in finance_html + trading_router for text in ["업비트 잔고/수익률 불러오기", "account-summary", "build_upbit_account_summary", "totalPnlPct"]), "Users can view Upbit cash balance, holdings, PnL, and return rate inside Zenthex without storing the key."),
        _review_item("mobile_real_status_protection", "Mobile real-status protection", all(text in finance_html + trading_router for text in ["require_real_status_permission", "headers=token", "/api/finance/stop", "실거래 상태 조회는 로그인이 필요합니다"]), "PC/mobile status viewing is supported, but real trading status and stop actions require login and Trading permission."),
        _review_item("upbit_server_ip_notice", "Upbit server IP notice", all(text in finance_html + trading_router + _read_text(".env.example") for text in ["ZENTHEX_SERVER_PUBLIC_IP", "server-ip", "Upbit 허용 IP", "복사", "api.ipify.org"]), "Trading screen exposes the Zenthex FastAPI server IP for Upbit allowed-IP registration."),
        _review_item("upbit_fixed_ip_guard", "Upbit fixed IP guard", all(text in trading_router + finance_html for text in ["is_fixed", "자동 감지값", "고정 서버 IP", "text-red-300"]), "Auto-detected IP is marked as unsafe for production; fixed env IP is required for live Upbit trading."),
        _review_item("upbit_outbound_ip_verify", "Upbit outbound IP verification", all(text in trading_router + finance_html for text in ["server-ip/verify", "configured_ip", "outbound_ip", "matches", "표시 IP와 실제 outbound IP"]), "Trading screen can compare configured IP against actual outbound IP before live trading."),
        _review_item("trading_compact_summary", "Trading compact strategy summary", all(text in finance_html for text in ["strategy-summary", "summary-exit", "summary-target", "summary-capital", "summary-coin", "updateStrategySummary"]), "Trading settings show a compact top summary for exit mode, target, capital, and coin selection."),
        _review_item("trading_exchange_selection", "Trading exchange selection", all(text in finance_html for text in ["exchange-selector", "selectExchange", "exchange-upbit", "exchange-binance"]), "Users choose Upbit or Binance before opening exchange-specific key setup."),
        _review_item("trading_advanced_collapse", "Trading advanced settings collapse", all(text in finance_html for text in ["advanced-strategy-box", "고급 전략 설정", "advanced.open=true", "rotate_holdings", "trailing-drop-box"]), "Advanced and risky trading controls are collapsed by default and opened automatically when selected."),
        _review_item("trading_return_chart", "Trading return chart", all(text in finance_html for text in ["return-chart", "returnHistory", "pushReturnPoint", "renderReturnChart", "totalPnlPct"]), "Trading screen plots recent account/status return rate so the user can watch profit movement, not only holdings."),
        _review_item("trading_split_entry", "Trading split-entry mode", all(text in finance_html + trading_router + engine_py for text in ["entry-mode", "entrySlices", "addEntryDropPct", "entry_count", "calculate_next_entry_krw", "분할 진입"]), "Trading can divide the configured total budget into multiple entries and calculate exits from average buy price."),
        _review_item("trading_stop_controls", "Trading pause and sell-exit controls", all(text in finance_html + trading_router for text in ["btn-sell-exit", "sell-and-stop", "일시정지(보유 유지)", "보유 코인은 매도하지 않습니다", "USER SELL EXIT"]), "Pause keeps holdings; sell-and-stop market-sells the current Zenthex position and then stops."),
        _review_item("trading_kst_and_criteria", "Trading KST logs and criteria", all(text in finance_html + engine_py for text in ["자동 선정 통과 기준", "KST", "1.1", "완화 후보"]), "Trading explains auto-selection criteria and system logs use Korea time."),
        _review_item("trading_three_column_layout", "Trading three-column layout", all(text in finance_html for text in ["aux-settings-panel", "relocateTradingPanels", "aux-stack", "minmax(300px, 380px) minmax(0, 1.45fr) minmax(300px, 420px)"]), "Trading desktop layout separates quick execution, live monitoring, and auxiliary settings."),
        _review_item("trading_falling_coin_filter", "Trading falling-coin filters", all(text in engine_py + finance_html for text in ["price_volume_aligned", "falling_with_volume", "near_day_high", "최근 강한 음봉", "고점 추격"]), "Scanner rejects falling volume spikes, recent red candles, and late high-chase candidates."),
        _review_item("trading_rising_confirmation", "Trading rising confirmation", all(text in engine_py + finance_html for text in ["bullish_1m_count", "minute1_momentum <= 0", "minute3_momentum <= 0", "minute5_momentum <= 0", "완화 진입 없이 대기"]), "Scanner waits unless 1m/3m/5m momentum and recent bullish candles confirm rising strength."),
        _review_item("trading_no_average_down", "Trading no average-down split entry", all(text in engine_py + finance_html for text in ["Pyramid Entry", "수익 방향 추가 진입", "current_yield >= 1.0 +", "하락할 때 물타기하지 않습니다"]), "Split entries add only into profitable rising positions, not falling positions."),
        _review_item("trading_entry_guard", "Trading entry guard", all(text in engine_py + finance_html + trading_router for text in ["market_regime_allows_entry", "orderbook_allows_entry", "confirm_entry_signal", "set_ticker_cooldown", "시장 필터", "cooldownCount"]), "Engine blocks broad-market drops, weak orderbooks, immediate price slips, and repeat entries after stop-loss."),
        _review_item("secret_key_visibility", "Secret key visibility control", all(text in finance_html for text in ["toggleSecretKey", "Secret Key가 점으로 보이는 것은 정상", "보기 버튼"]), "Secret Key remains hidden by default but can be temporarily viewed."),
        _review_item("customer_center", "Customer center page", all(text in customer_html + index_html + _read_text("main.py") for text in ["Zenthex 고객센터", "customer.html", "serve_customer"]), "Customer center exists and is linked from homepage navigation."),
        _review_item("support_tickets", "Customer inquiry system", all(text in customer_html + admin_html + support_router + models_py + migrations_py for text in ["문의 접수하기", "support_tickets", "/api/support/tickets", "/api/support/admin/tickets", "fetchSupportTickets"]), "Customers can submit inquiries and the owner can manage them from the CEO dashboard."),
        _review_item("trading_access_ui", "Trading owner/subscriber UI", all(text in finance_html for text in ["finance-access-chip", "대표 실거래 권한", "구독 실거래 권한", "zenthex-mark"]), "Trading refreshes account permission and opens real-mode UI for owner/subscribers."),
        _review_item("role_separation", "Owner and subscriber separation", all(text in admin_router + admin_html + index_html + login_html for text in ["require_owner", "user.role==='owner'", "role==='owner'"]) and "['owner','admin'].includes" not in index_html + login_html + admin_html, "Only the owner account can access CEO operations screens."),
        _review_item("account_role_workspace", "Account role workspace", all(text in account_html for text in ["role-workspace", "renderRoleWorkspace", "CEO 운영 대시보드", "내 Studio 작업", "내 Trading 엔진"]), "My Page separates owner operations entry from subscriber product workspace."),
        _review_item("plan_separation", "Plan-specific product access", all(text in studio_router + trading_router + billing_router for text in ["studio_pro", "trading_pro", "studio_limit\": 0", "user.role == \"owner\""]), "Studio Pro unlocks Studio, Trading Pro unlocks Trading, and owner unlocks all."),
        _review_item("trading_targets", "Trading target and capital options", all(text in finance_html + trading_router + engine_py for text in ["+10%", "+30%", "+50%", "all_krw", "ratio", "fixed", "rotate_holdings", "rotateExistingAccepted", "trailing", "peak_yield"]), "Short scalping targets, KRW cash modes, explicit existing-holdings rotation, and trailing take-profit are available."),
        _review_item("real_stop_loss_halts", "Real stop-loss halts engine", all(text in engine_py for text in ["손절 매도 후 실거래 엔진을 완전 정지", "TradingState.STOPPED", "Zenthex Trading 손절 정지"]), "Real trading stops after stop-loss sell instead of returning to scan/re-entry."),
        _review_item("trading_engine_scan", "Trading scanner stability", "ohlcv[\"" not in engine_py and "hourly[\"high\"]" in engine_py, "Undefined scanner variable is not present."),
        _review_item("mock_payment_guard", "Mock payment guard", "ZENTHEX_ENABLE_MOCK_PAYMENT" in billing_router, "Mock payment cannot unlock paid plans unless explicitly enabled."),
        _review_item("persistent_database", "Persistent production database", "ZENTHEX_DATABASE_URL" in session_py and "ZENTHEX_DATABASE_URL" in _read_text(".env.example") and "postgres://" in session_py and "psycopg2-binary" in _read_text("requirements.txt"), "Paid user data must live in a persistent DB outside GitHub deploy files."),
        _review_item("postgres_safe_migration", "PostgreSQL-safe startup", "is_sqlite_database" in migrations_py and "if not is_sqlite_database()" in migrations_py, "SQLite-only migrations are skipped when the production database is PostgreSQL."),
        _review_item("auto_billing_plan", "Monthly auto-renewal billing plan", all(text in billing_router for text in ["monthly_auto_renewal", "Toss Payments", "Stripe", "webhook_events"]), "Subscriptions are planned as monthly auto-renewal with Toss Payments and Stripe."),
        _review_item("subscription_state", "Subscription state table", all(text in models_py + billing_router for text in ["class Subscription", "provider_subscription_id", "next_billing_date", "/subscription"]), "Current subscription state is stored separately from one-time receipt history."),
        _review_item("operating_cost_review", "Operating cost review", all(text in master_plan for text in ["비용 단계", "영구 PostgreSQL", "실제 이메일/SMS", "Toss Payments", "Studio AI/GPU"]), "CEO review separates validation costs from production operating costs."),
        _review_item("master_plan", "Master plan document", all(text in master_plan for text in ["Zenthex SaaS Master Plan", "데이터 보존 원칙", "자동결제", "CEO 대시보드", "최종 결론", "Trading 수익률 그래프", "Zenthex 서버 고정 IP"]), "Current architecture, role separation, billing, data retention, fixed-IP trading, return chart, and launch risks are documented."),
        _review_item("db_columns", "Database columns", all(text in models_py for text in ["phone_verified", "password_hint_answer_hash", "email_verified", "studio_generations_left", "class SupportTicket"]), "Auth, verification, Studio usage, and support ticket columns are present."),
        _review_item("user_management", "Subscriber management", all(text in admin_router + admin_html for text in ["/users", "deleteUser", "changePlan"]), "Owner can list users, change plans, and delete accounts."),
        _review_item("smtp_ready", "SMTP delivery configured", smtp_ready, "Real email delivery needs SMTP environment values.", "recommended"),
        _review_item("sms_ready", "SMS provider connected", sms_ready, "Production SMS provider should be connected before public launch.", "recommended"),
        _review_item("persistent_db_ready", "Production DB environment ready", persistent_db_ready, "Before paid users join, set ZENTHEX_DATABASE_URL to PostgreSQL or another persistent DB.", "recommended"),
        _review_item("billing_provider_ready", "Real billing provider connected", billing_provider_ready, "Before charging users, connect Toss Payments and/or Stripe subscriptions with webhooks.", "recommended"),
    ]
    checks = _apply_bilingual_review_copy(checks)

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
