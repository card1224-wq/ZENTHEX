from pydantic import BaseModel, EmailStr

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    birth_date: str | None = None
    phone_number: str | None = None
    password_hint_question: str
    password_hint_answer: str

class PasswordHintRequest(BaseModel):
    email: EmailStr
    password_hint_question: str
    password_hint_answer: str

class PhoneCodeRequest(BaseModel):
    phone_number: str

class PhoneVerifyRequest(BaseModel):
    phone_number: str
    code: str

class UserLogin(BaseModel):
    email: str
    password: str

class EmailRequest(BaseModel):
    email: EmailStr

class VerifyEmailRequest(BaseModel):
    code: str

class PasswordResetRequest(BaseModel):
    email: EmailStr
    code: str
    new_password: str

class UserResponse(BaseModel):
    id: int
    email: str
    plan: str
    role: str
    email_verified: bool
    studio_generations_left: int

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str
    user_info: UserResponse
