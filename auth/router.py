from fastapi import APIRouter, Depends, HTTPException, Header, Request, status
from sqlalchemy import func
from sqlalchemy.orm import Session
from database.session import get_db
from database.models import User
from auth.schemas import (
    EmailRequest,
    PasswordHintRequest,
    PasswordResetRequest,
    PhoneCodeRequest,
    PhoneVerifyRequest,
    UserCreate,
    UserLogin,
    Token,
    UserResponse,
    VerifyEmailRequest,
)
from auth.hash import get_password_hash, verify_password
import os
import random
import smtplib
import ssl
import uuid
import hmac
import hashlib
import base64
from email.message import EmailMessage

router = APIRouter(prefix="/api/auth", tags=["auth"])
SESSION_TOKENS = {}
DEFAULT_OWNER_EMAILS = {"7foliath@naver.com"}
DEV_EMAIL_OUTBOX = []
PHONE_VERIFICATION_CODES = {}
PHONE_VERIFIED_NUMBERS = set()
DEV_PHONE_OUTBOX = []
TEST_PHONE_CODE = "122492"
TEST_EMAIL_CODE = "122492"

def normalize_email(email: str) -> str:
    return (email or "").strip().lower()

def normalize_phone(phone_number: str) -> str:
    return "".join(ch for ch in (phone_number or "") if ch.isdigit())

def normalize_hint_answer(answer: str) -> str:
    return " ".join((answer or "").strip().lower().split())

def find_user_by_email(db: Session, email: str):
    return db.query(User).filter(func.lower(User.email) == normalize_email(email)).first()

def get_owner_emails():
    configured = os.getenv("ZENTHEX_OWNER_EMAILS", "")
    emails = {normalize_email(email) for email in configured.split(",") if email.strip()}
    return DEFAULT_OWNER_EMAILS | emails

def resolve_role(email: str) -> str:
    return "owner" if normalize_email(email) in get_owner_emails() else "user"

def make_code() -> str:
    return f"{random.randint(100000, 999999)}"

def is_local_request(request: Request) -> bool:
    if not request.client:
        return False
    return request.client.host in {"127.0.0.1", "localhost", "::1"}

def smtp_configured() -> bool:
    host = (os.getenv("ZENTHEX_SMTP_HOST") or "").strip()
    user = (os.getenv("ZENTHEX_SMTP_USER") or "").strip()
    password = (os.getenv("ZENTHEX_SMTP_PASSWORD") or "").strip()
    if not host or not user or not password:
        return False
    blocked_values = {"smtp.example.com", "no-reply@example.com", "change-me"}
    return host not in blocked_values and user not in blocked_values and password not in blocked_values

def send_account_email(to_email: str, subject: str, body: str):
    smtp_host = os.getenv("ZENTHEX_SMTP_HOST")
    smtp_port = int(os.getenv("ZENTHEX_SMTP_PORT", "587"))
    smtp_user = os.getenv("ZENTHEX_SMTP_USER")
    smtp_password = os.getenv("ZENTHEX_SMTP_PASSWORD")
    smtp_from = os.getenv("ZENTHEX_SMTP_FROM", smtp_user or "no-reply@zenthex.com")
    use_ssl = os.getenv("ZENTHEX_SMTP_SSL", "false").lower() == "true"

    message = EmailMessage()
    message["From"] = smtp_from
    message["To"] = to_email
    message["Subject"] = subject
    message.set_content(body)

    if smtp_configured():
        try:
            if use_ssl:
                context = ssl.create_default_context()
                with smtplib.SMTP_SSL(smtp_host, smtp_port, context=context) as server:
                    server.login(smtp_user, smtp_password)
                    server.send_message(message)
            else:
                with smtplib.SMTP(smtp_host, smtp_port) as server:
                    server.starttls(context=ssl.create_default_context())
                    server.login(smtp_user, smtp_password)
                    server.send_message(message)
            print(f"[Zenthex Mail] sent to={to_email} subject={subject}")
            return {"sent": True, "mode": "smtp"}
        except Exception as exc:
            print(f"[Zenthex Mail] SMTP failed: {exc}. Falling back to dev outbox.")

    DEV_EMAIL_OUTBOX.append({"to": to_email, "subject": subject, "body": body})
    print(f"[Zenthex Mail:DEV] to={to_email} subject={subject} body={body}")
    return {"sent": False, "mode": "dev_outbox"}

def token_secret() -> str:
    return os.getenv("ZENTHEX_TOKEN_SECRET", "zenthex-local-dev-token-secret")

def sign_token_payload(payload: str) -> str:
    return hmac.new(token_secret().encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).hexdigest()

def make_signed_token(user_id: int) -> str:
    payload = f"{user_id}:{uuid.uuid4().hex}"
    signature = sign_token_payload(payload)
    raw = f"{payload}:{signature}".encode("utf-8")
    return "zx." + base64.urlsafe_b64encode(raw).decode("utf-8").rstrip("=")

def read_signed_token(token: str):
    if not token or not token.startswith("zx."):
        return None
    encoded = token[3:]
    encoded += "=" * (-len(encoded) % 4)
    try:
        raw = base64.urlsafe_b64decode(encoded.encode("utf-8")).decode("utf-8")
        user_id, nonce, signature = raw.split(":", 2)
    except Exception:
        return None
    payload = f"{user_id}:{nonce}"
    if not hmac.compare_digest(sign_token_payload(payload), signature):
        return None
    try:
        return int(user_id)
    except ValueError:
        return None

def issue_user_token(user: User):
    access_token = make_signed_token(user.id)
    SESSION_TOKENS[access_token] = user.id
    return {"access_token": access_token, "token_type": "bearer", "user_info": UserResponse.model_validate(user)}

def apply_owner_privileges(user: User):
    user.role = "owner"
    user.plan = "ultimate"
    user.studio_generations_left = 999999
    user.approval_status = "approved"
    user.is_active = True

@router.post("/phone/send-code")
def send_phone_verification(req: PhoneCodeRequest, request: Request):
    phone_number = normalize_phone(req.phone_number)
    if len(phone_number) < 10:
        raise HTTPException(status_code=400, detail="Please enter a valid phone number.")
    sms_configured = all(os.getenv(key) for key in [
        "ZENTHEX_SMS_PROVIDER",
        "ZENTHEX_SMS_ACCESS_KEY",
        "ZENTHEX_SMS_SECRET_KEY",
        "ZENTHEX_SMS_FROM",
    ])
    code = make_code() if sms_configured else TEST_PHONE_CODE
    PHONE_VERIFICATION_CODES[phone_number] = code
    DEV_PHONE_OUTBOX.append({"phone_number": phone_number, "code": code})
    response = {"status": "success", "message": "Phone verification code has been sent."}
    if is_local_request(request) or not sms_configured or os.getenv("ZENTHEX_ENABLE_DEV_OUTBOX", "false").lower() == "true":
        response["dev_code"] = code
        response["message"] = "Test phone verification code is available."
    return response

@router.post("/phone/verify")
def verify_phone(req: PhoneVerifyRequest):
    phone_number = normalize_phone(req.phone_number)
    if not phone_number or PHONE_VERIFICATION_CODES.get(phone_number) != req.code.strip():
        raise HTTPException(status_code=400, detail="Invalid phone verification code.")
    PHONE_VERIFIED_NUMBERS.add(phone_number)
    PHONE_VERIFICATION_CODES.pop(phone_number, None)
    return {"status": "success", "message": "Phone verification completed."}

@router.post("/signup", response_model=UserResponse)
def signup(user: UserCreate, db: Session = Depends(get_db)):
    email = normalize_email(user.email)
    if find_user_by_email(db, email):
        raise HTTPException(status_code=400, detail="This email is already registered.")

    role = resolve_role(email)
    verification_code = make_code() if smtp_configured() else TEST_EMAIL_CODE
    hint_answer = normalize_hint_answer(user.password_hint_answer)
    phone_number = normalize_phone(user.phone_number or "")

    if len(user.full_name.strip()) < 2:
        raise HTTPException(status_code=400, detail="Please enter your name.")
    if len(user.birth_date or "") < 8:
        raise HTTPException(status_code=400, detail="Please enter your birth date.")
    if len(phone_number) < 10:
        raise HTTPException(status_code=400, detail="Please enter your phone number.")
    if role != "owner" and phone_number not in PHONE_VERIFIED_NUMBERS:
        raise HTTPException(status_code=400, detail="Please complete phone verification.")
    if len(user.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters.")
    if not user.password_hint_question.strip() or len(hint_answer) < 2:
        raise HTTPException(status_code=400, detail="Please enter a password hint question and answer.")

    new_user = User(
        full_name=user.full_name.strip()[:80],
        email=email,
        hashed_password=get_password_hash(user.password),
        birth_date=(user.birth_date or "").strip()[:20],
        phone_number=phone_number[:30],
        phone_verified=True,
        phone_verification_code=None,
        password_hint_question=user.password_hint_question.strip()[:120],
        password_hint_answer_hash=get_password_hash(hint_answer),
        role=role,
        plan="ultimate" if role == "owner" else "free",
        studio_generations_left=999999 if role == "owner" else 3,
        approval_status="approved" if role == "owner" else "pending",
        is_active=True if role == "owner" else False,
        email_verified=False,
        email_verification_code=verification_code,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    send_account_email(email, "Zenthex email verification code", f"Verification code: {verification_code}")
    PHONE_VERIFIED_NUMBERS.discard(phone_number)
    return new_user

@router.post("/login", response_model=Token)
def login(user: UserLogin, db: Session = Depends(get_db)):
    db_user = find_user_by_email(db, user.email)
    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="가입된 이메일이 없습니다. 배포 후 기존 계정이 사라졌다면 서버 DB가 새로 만들어진 상태일 수 있습니다.",
        )
    if not verify_password(user.password, db_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="비밀번호가 틀렸습니다. 비밀번호 찾기에서 힌트 질문 또는 인증 코드로 재설정하세요.",
        )

    desired_role = resolve_role(db_user.email)
    if desired_role != "owner" and (db_user.approval_status or "approved") != "approved":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="가입 신청은 완료되었지만 대표 승인 대기 중입니다. 승인 후 로그인할 수 있습니다.",
        )
    if desired_role != "owner" and db_user.is_active is False:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="대표 승인 대기 중인 계정입니다. 승인 후 사용할 수 있습니다.",
        )
    if db_user.role != desired_role or desired_role == "owner":
        if desired_role == "owner":
            apply_owner_privileges(db_user)
        else:
            db_user.role = desired_role
        db.commit()
        db.refresh(db_user)

    return issue_user_token(db_user)

@router.get("/me", response_model=UserResponse)
def me(Authorization: str = Header(None), db: Session = Depends(get_db)):
    if not Authorization:
        raise HTTPException(status_code=401, detail="Login required.")
    token = Authorization.replace("Bearer ", "")
    user = get_current_user(token, db)
    if resolve_role(user.email) == "owner" and (user.role != "owner" or user.plan != "ultimate"):
        apply_owner_privileges(user)
        db.commit()
        db.refresh(user)
    return user

@router.post("/email/resend")
def resend_verification(request: Request, Authorization: str = Header(None), db: Session = Depends(get_db)):
    user = require_current_user(Authorization, db)
    if user.email_verified:
        return {"status": "success", "message": "Email is already verified."}
    if resolve_role(user.email) == "owner":
        apply_owner_privileges(user)
    user.email_verification_code = make_code() if smtp_configured() else TEST_EMAIL_CODE
    db.commit()
    send_account_email(user.email, "Zenthex email verification code", f"Verification code: {user.email_verification_code}")
    response = {"status": "success", "message": "Verification code has been sent."}
    if is_local_request(request) or not smtp_configured() or os.getenv("ZENTHEX_ENABLE_DEV_OUTBOX", "false").lower() == "true":
        response["dev_code"] = user.email_verification_code
    return response

@router.post("/email/verify")
def verify_email(req: VerifyEmailRequest, Authorization: str = Header(None), db: Session = Depends(get_db)):
    user = require_current_user(Authorization, db)
    if user.email_verified:
        return {"status": "success", "message": "Email is already verified."}
    if not user.email_verification_code or user.email_verification_code != req.code:
        raise HTTPException(status_code=400, detail="Invalid verification code.")
    if resolve_role(user.email) == "owner":
        apply_owner_privileges(user)
    user.email_verified = True
    user.email_verification_code = None
    db.commit()
    return {"status": "success", "message": "Email verification completed."}

@router.post("/find-id")
def find_id(req: EmailRequest, db: Session = Depends(get_db)):
    user = find_user_by_email(db, req.email)
    if user:
        send_account_email(user.email, "Zenthex ID notice", f"Your Zenthex ID is your email address: {user.email}")
    return {"status": "success", "message": "If an account exists, ID information has been sent by email."}

@router.post("/password/request-reset")
def request_password_reset(req: EmailRequest, request: Request, db: Session = Depends(get_db)):
    user = find_user_by_email(db, req.email)
    dev_code = None
    if user:
        user.password_reset_code = make_code() if smtp_configured() else TEST_EMAIL_CODE
        dev_code = user.password_reset_code
        db.commit()
        hint_text = f"\nPassword hint question: {user.password_hint_question}" if user.password_hint_question else ""
        send_account_email(user.email, "Zenthex password reset code", f"Reset code: {user.password_reset_code}{hint_text}")
    response = {"status": "success", "message": "If an account exists, reset instructions have been sent by email."}
    if dev_code and (is_local_request(request) or not smtp_configured() or os.getenv("ZENTHEX_ENABLE_DEV_OUTBOX", "false").lower() == "true"):
        response["dev_code"] = dev_code
    return response

@router.post("/password/question")
def get_password_hint_question(req: EmailRequest, db: Session = Depends(get_db)):
    user = find_user_by_email(db, req.email)
    if not user:
        raise HTTPException(status_code=404, detail="No account found for this email.")
    if not user.password_hint_question or not user.password_hint_answer_hash:
        return {"status": "success", "password_hint_question": "기존 계정입니다. 이메일 인증 코드로 비밀번호를 재설정하세요.", "reset_without_hint": True}
    return {"status": "success", "password_hint_question": user.password_hint_question, "reset_without_hint": False}

@router.post("/password/hint")
def check_password_hint(req: PasswordHintRequest, db: Session = Depends(get_db)):
    user = find_user_by_email(db, req.email)
    if (
        not user
        or not user.password_hint_question
        or not user.password_hint_answer_hash
        or user.password_hint_question.strip() != req.password_hint_question.strip()
        or not verify_password(normalize_hint_answer(req.password_hint_answer), user.password_hint_answer_hash)
    ):
        raise HTTPException(status_code=400, detail="Password hint does not match.")
    user.password_reset_code = make_code() if smtp_configured() else TEST_EMAIL_CODE
    db.commit()
    send_account_email(user.email, "Zenthex password reset code", f"Reset code: {user.password_reset_code}")
    return {"status": "success", "message": "Hint verified. Reset code has been sent.", "dev_code": user.password_reset_code if not smtp_configured() else None}

@router.post("/password/reset")
def reset_password(req: PasswordResetRequest, db: Session = Depends(get_db)):
    user = find_user_by_email(db, req.email)
    if not user or not user.password_reset_code or user.password_reset_code != req.code:
        raise HTTPException(status_code=400, detail="Invalid reset code.")
    if len(req.new_password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters.")
    user.hashed_password = get_password_hash(req.new_password)
    user.password_reset_code = None
    db.commit()
    return {"status": "success", "message": "Password has been changed."}

@router.get("/dev/outbox")
def dev_outbox():
    if os.getenv("ZENTHEX_ENABLE_DEV_OUTBOX", "false").lower() != "true":
        raise HTTPException(status_code=404, detail="Not found")
    return {"messages": DEV_EMAIL_OUTBOX[-20:], "phone_messages": DEV_PHONE_OUTBOX[-20:]}

def require_current_user(Authorization: str, db: Session):
    if not Authorization:
        raise HTTPException(status_code=401, detail="Login required.")
    token = Authorization.replace("Bearer ", "")
    return get_current_user(token, db)

def get_current_user(token: str, db: Session = Depends(get_db)):
    user_id = SESSION_TOKENS.get(token) or read_signed_token(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=401,
            detail="로그인 토큰은 남아 있지만 서버에 계정 데이터가 없습니다. 배포 과정에서 DB가 초기화됐을 가능성이 큽니다. 다시 로그인하거나 계정을 다시 생성해야 합니다.",
        )
    return user
