from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    church_name: str = Field(min_length=1, max_length=255)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)


class UserResponse(BaseModel):
    id: str
    email: str
    email_verified: bool
    church_id: str
    role: str


class ChurchResponse(BaseModel):
    id: str
    name: str
    slug: str


class RegisterResponse(BaseModel):
    user: UserResponse
    church: ChurchResponse
    message: str


class LoginResponse(BaseModel):
    user: UserResponse


class MeResponse(BaseModel):
    user: UserResponse
    church: ChurchResponse


class VerifyEmailRequest(BaseModel):
    token: str = Field(min_length=1)


class VerifyEmailResponse(BaseModel):
    email_verified: bool


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str = Field(min_length=1)
    new_password: str = Field(min_length=8, max_length=128)


class MessageResponse(BaseModel):
    message: str


class ErrorResponse(BaseModel):
    error: str
