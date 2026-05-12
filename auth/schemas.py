from pydantic import BaseModel, EmailStr

class UserCreate(BaseModel):
    email: EmailStr
    password: str

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
