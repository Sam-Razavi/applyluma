from pydantic import BaseModel, EmailStr, Field


class ContactRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    subject: str = Field(default="", max_length=200)
    message: str = Field(min_length=10, max_length=5000)
    turnstile_token: str
    honeypot: str = Field(default="")
