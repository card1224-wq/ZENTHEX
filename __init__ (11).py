from fastapi import APIRouter, Depends, HTTPException, Header, status
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
from email.message import EmailMessage

router = APIRouter(prefix="/api/auth", tags=["auth"])
SESSION_TOKENS = {}
DEFAULT_OWNER_EMAILS = set()
DEV_EMAIL_OUTBOX = []
PHONE_VERIFICATION_CODES = {}
PHONE_VERIFIED_NUMBERS = set()
DEV_PHONE_OUTBOX = []

def get_owner_emails():
    configured = os.getenv("ZENTHEX_OWNER_EMAILS", "")
    emails = {email.strip().lower() for email in configured.split(",") if email.strip()}
    return emails or DEFAULT_OWNER_EMAILS

def resolve_role(email: str) -> str:
    return "owner" if email.lower() in get_owner_emails() else "user"

def make_code() -> str:
    return f"{random.randint(100000, 999999)}"

def normalize_phone(phone_number: str) -> str:
    return "".join(ch for ch in (phone_number or "") if ch.isdigit())

def normalize_hint_answer(answer: str) -> str:
    return " ".join((answer or "").strip().lower().split())

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

    if smtp_host and smtp_user and smtp_password:
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

def issue_user_token(user: User):
    access_token = str(uuid.uuid4())
    SESSION_TOKENS[access_token] = user.id
    return {"access_token": access_token, "token_type": "bearer", "user_info": UserResponse.model_validate(user)}

@router.post("/phone/send-code")
def send_phone_verification(req: PhoneCodeRequest):
    phone_number = normalize_phone(req.phone_number)
    if len(phone_number) < 10:
        raise HTTPException(status_code=400, detail="휴대폰 번호를 정확히 입력해주세요.")
    code = make_code()
    PHONE_VERIFICATION_CODES[phone_number] = code
    DEV_PHONE_OUTBOX.append({"phone_number": phone_number, "code": code})
    print(f"[Zenthex SMS:DEV] phone={phone_number} code={code}")
    response = {"status": "success", "message": "휴대폰 인증 코드를 발송했습니다."}
    if os.getenv("ZENTHEX_ENABLE_DEV_OUTBOX", "false").lower() == "true":
        response["dev_code"] = code
    return response

@router.post("/phone/verify")
def verify_phone(req: PhoneVerifyRequest):
    phone_number = normalize_phone(req.phone_number)
    if not phone_number or PHONE_VERIFICATION_CODES.get(phone_number) != req.code.strip():
        raise HTTPException(status_code=400, detail="휴대폰 인증 코드가 올바르지 않습니다.")
    PHONE_VERIFIED_NUMBERS.add(phone_number)
    PHONE_VERIFICATION_CODES.pop(phone_number, None)
    return {"status": "success", "message": "휴대폰 인증이 완료되었습니다."}

@router.post("/signup", response_model=UserResponse)
def signup(user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="이미 가입된 이메일입니다.")

    role = resolve_role(user.email)
    verification_code = make_code()
    hint_answer = normalize_hint_answer(user.password_hint_answer)
    phone_number = normalize_phone(user.phone_number or "")
    if len(user.full_name.strip()) < 2:
        raise HTTPException(status_code=400, detail="이름을 입력해주세요.")
    if len(user.birth_date or "") < 8:
        raise HTTPException(status_code=400, detail="생년월일을 입력해주세요.")
    if len(phone_number) < 10:
        raise HTTPException(status_code=400, detail="휴대폰 번호를 입력해주세요.")
    if role != "owner" and phone_number not in PHONE_VERIFIED_NUMBERS:
        raise HTTPException(status_code=400, detail="휴대폰 인증을 완료해주세요.")
    if len(user.password) < 6:
        raise HTTPException(status_code=400, detail="비밀번호는 6자 이상이어야 합니다.")
    if not user.password_hint_question.strip() or len(hint_answer) < 2:
        raise HTTPException(status_code=400, detail="비밀번호 힌트 질문과 답변을 입력해주세요.")

    new_user = User(
        full_name=user.full_name.strip()[:80],
        email=user.email,
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
        email_verified=role == "owner",
        email_verification_code=None if role == "owner" else verification_code,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    if role != "owner":
        send_account_email(user.email, "Zenthex 이메일 인증 코드", f"인증 코드: {verification_code}")
    PHONE_VERIFIED_NUMBERS.discard(phone_number)
    return new_user

@router.post("/login", response_model=Token)
def login(user: UserLogin, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.email == user.email).first()
    if not db_user or not verify_password(user.password, db_user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="이메일 또는 비밀번호가 올바르지 않습니다.")

    desired_role = resolve_role(db_user.email)
    if db_user.role != desired_role:
        db_user.role = desired_role
        if desired_role == "owner":
            db_user.plan = "ultimate"
            db_user.studio_generations_left = 999999
            db_user.email_verified = True
            db_user.email_verification_code = None
        db.commit()
        db.refresh(db_user)

    return issue_user_token(db_user)

@router.get("/me", response_model=UserResponse)
def me(Authorization: str = Header(None), db: Session = Depends(get_db)):
    if not Authorization:
        raise HTTPException(status_code=401, detail="로그인이 필요합니다.")
    token = Authorization.replace("Bearer ", "")
    return get_current_user(token, db)

@router.post("/email/resend")
def resend_verification(Authorization: str = Header(None), db: Session = Depends(get_db)):
    user = require_current_user(Authorization, db)
    if user.email_verified:
        return {"status": "success", "message": "이미 인증된 이메일입니다."}
    user.email_verification_code = make_code()
    db.commit()
    send_account_email(user.email, "Zenthex 이메일 인증 코드", f"인증 코드: {user.email_verification_code}")
    return {"status": "success", "message": "인증 코드를 발송했습니다."}

@router.post("/email/verify")
def verify_email(req: VerifyEmailRequest, Authorization: str = Header(None), db: Session = Depends(get_db)):
    user = require_current_user(Authorization, db)
    if user.email_verified:
        return {"status": "success", "message": "이미 인증되었습니다."}
    if not user.email_verification_code or user.email_verification_code != req.code:
        raise HTTPException(status_code=400, detail="인증 코드가 올바르지 않습니다.")
    user.email_verified = True
    user.email_verification_code = None
    db.commit()
    return {"status": "success", "message": "이메일 인증이 완료되었습니다."}

@router.post("/find-id")
def find_id(req: EmailRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == req.email).first()
    if user:
        send_account_email(req.email, "Zenthex 아이디 안내", f"가입된 아이디는 이메일 주소 {req.email} 입니다.")
    return {"status": "success", "message": "가입 여부와 아이디 안내를 이메일로 발송했습니다."}

@router.post("/password/request-reset")
def request_password_reset(req: EmailRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == req.email).first()
    if user:
        user.password_reset_code = make_code()
        db.commit()
        hint_text = f"\n비밀번호 힌트 질문: {user.password_hint_question}" if user.password_hint_question else ""
        send_account_email(req.email, "Zenthex 비밀번호 재설정 코드", f"재설정 코드: {user.password_reset_code}{hint_text}")
    return {"status": "success", "message": "비밀번호 재설정 안내를 이메일로 발송했습니다."}

@router.post("/password/question")
def get_password_hint_question(req: EmailRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == req.email).first()
    if not user or not user.password_hint_question:
        raise HTTPException(status_code=404, detail="등록된 비밀번호 힌트 질문을 찾을 수 없습니다.")
    return {"status": "success", "password_hint_question": user.password_hint_question}

@router.post("/password/hint")
def check_password_hint(req: PasswordHintRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == req.email).first()
    if (
        not user
        or not user.password_hint_question
        or not user.password_hint_answer_hash
        or user.password_hint_question.strip() != req.password_hint_question.strip()
        or not verify_password(normalize_hint_answer(req.password_hint_answer), user.password_hint_answer_hash)
    ):
        raise HTTPException(status_code=400, detail="비밀번호 힌트가 일치하지 않습니다.")
    user.password_reset_code = make_code()
    db.commit()
    send_account_email(req.email, "Zenthex 비밀번호 재설정 코드", f"재설정 코드: {user.password_reset_code}")
    return {"status": "success", "message": "힌트가 확인되었습니다. 이메일로 재설정 코드를 발송했습니다."}

@router.post("/password/reset")
def reset_password(req: PasswordResetRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == req.email).first()
    if not user or not user.password_reset_code or user.password_reset_code != req.code:
        raise HTTPException(status_code=400, detail="재설정 코드가 올바르지 않습니다.")
    if len(req.new_password) < 6:
        raise HTTPException(status_code=400, detail="비밀번호는 6자 이상이어야 합니다.")
    user.hashed_password = get_password_hash(req.new_password)
    user.password_reset_code = None
    db.commit()
    return {"status": "success", "message": "비밀번호가 변경되었습니다."}

@router.get("/dev/outbox")
def dev_outbox():
    if os.getenv("ZENTHEX_ENABLE_DEV_OUTBOX", "false").lower() != "true":
        raise HTTPException(status_code=404, detail="Not found")
    return {"messages": DEV_EMAIL_OUTBOX[-20:], "phone_messages": DEV_PHONE_OUTBOX[-20:]}

def require_current_user(Authorization: str, db: Session):
    if not Authorization:
        raise HTTPException(status_code=401, detail="로그인이 필요합니다.")
    token = Authorization.replace("Bearer ", "")
    return get_current_user(token, db)

def get_current_user(token: str, db: Session = Depends(get_db)):
    user_id = SESSION_TOKENS.get(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


