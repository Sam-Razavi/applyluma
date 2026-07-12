import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.core.password_policy import validate_password_strength
from app.models.user import UserRole
from app.services.cv_render import TEMPLATES


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(max_length=128)
    full_name: str | None = Field(default=None, max_length=200)

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        return validate_password_strength(v)


class UserPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    full_name: str | None
    is_active: bool
    is_verified: bool
    role: UserRole
    preferred_template: str | None = None
    stripe_customer_id: str | None = None
    subscription_status: str | None = None
    subscription_ends_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class UserUpdate(BaseModel):
    full_name: str | None = Field(default=None, max_length=200)
    preferred_template: str | None = None

    @field_validator("preferred_template")
    @classmethod
    def template_must_exist(cls, v: str | None) -> str | None:
        if v is not None and v not in TEMPLATES:
            raise ValueError(f"Unknown template '{v}'. Available: {', '.join(sorted(TEMPLATES))}")
        return v


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        return validate_password_strength(v)


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class MagicLinkRequest(BaseModel):
    email: EmailStr


class MagicLinkVerifyRequest(BaseModel):
    token: str


class AuthProvidersResponse(BaseModel):
    google: bool
    linkedin: bool
    github: bool
    magic_link: bool


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(max_length=128)

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        return validate_password_strength(v)
