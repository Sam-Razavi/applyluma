from typing import Literal

from pydantic import BaseModel, EmailStr, Field

FeedbackCategory = Literal["bug", "feature", "question", "other"]


class FeedbackRequest(BaseModel):
    category: FeedbackCategory
    subject: str = Field(default="", max_length=200)
    message: str = Field(min_length=10, max_length=5000)


class ContactRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    subject: str = Field(default="", max_length=200)
    message: str = Field(min_length=10, max_length=5000)
    honeypot: str = Field(default="")
    turnstile_token: str = Field(default="", max_length=2048)
