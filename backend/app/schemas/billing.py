from pydantic import BaseModel


class CheckoutSessionResponse(BaseModel):
    checkout_url: str


class PortalSessionResponse(BaseModel):
    portal_url: str


class BillingStatusResponse(BaseModel):
    configured: bool
    test_mode: bool
