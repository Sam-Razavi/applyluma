import uuid
from datetime import UTC, datetime
from typing import Any

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.dependencies import get_current_user, get_db
from app.models.user import User, UserRole
from app.schemas.billing import CheckoutSessionResponse, PortalSessionResponse
from app.services import notification_service

router = APIRouter(prefix="/billing", tags=["billing"])


def _require_stripe() -> None:
    if not settings.STRIPE_SECRET_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Stripe is not configured",
        )
    stripe.api_key = settings.STRIPE_SECRET_KEY


def _base_url(request: Request) -> str:
    origin = request.headers.get("origin")
    if origin:
        return origin.rstrip("/")
    return str(request.base_url).rstrip("/")


def _get_attr(value: Any, key: str, default: Any = None) -> Any:
    if isinstance(value, dict):
        return value.get(key, default)
    return getattr(value, key, default)


def _period_end(value: Any) -> datetime | None:
    timestamp = _get_attr(value, "current_period_end")
    if timestamp is None:
        return None
    try:
        return datetime.fromtimestamp(int(timestamp), tz=UTC)
    except (TypeError, ValueError, OSError):
        return None


@router.post("/create-checkout-session", response_model=CheckoutSessionResponse)
def create_checkout_session(
    request: Request,
    current_user: User = Depends(get_current_user),
) -> CheckoutSessionResponse:
    _require_stripe()
    if not settings.STRIPE_PREMIUM_PRICE_ID:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Stripe premium price is not configured",
        )

    base_url = _base_url(request)
    session_kwargs = {
        "mode": "subscription",
        "line_items": [{"price": settings.STRIPE_PREMIUM_PRICE_ID, "quantity": 1}],
        "success_url": f"{base_url}/billing/success",
        "cancel_url": f"{base_url}/billing/cancel",
        "metadata": {"user_id": str(current_user.id)},
    }
    if getattr(current_user, "stripe_customer_id", None):
        session_kwargs["customer"] = current_user.stripe_customer_id
    else:
        session_kwargs["customer_email"] = current_user.email

    session = stripe.checkout.Session.create(
        **session_kwargs,
    )
    checkout_url = _get_attr(session, "url")
    if not checkout_url:
        raise HTTPException(status_code=502, detail="Stripe did not return a checkout URL")
    return CheckoutSessionResponse(checkout_url=checkout_url)


@router.get("/portal", response_model=PortalSessionResponse)
def create_portal_session(
    request: Request,
    current_user: User = Depends(get_current_user),
) -> PortalSessionResponse:
    _require_stripe()
    if not current_user.stripe_customer_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No Stripe customer")

    session = stripe.billing_portal.Session.create(
        customer=current_user.stripe_customer_id,
        return_url=f"{_base_url(request)}/plans",
    )
    portal_url = _get_attr(session, "url")
    if not portal_url:
        raise HTTPException(status_code=502, detail="Stripe did not return a portal URL")
    return PortalSessionResponse(portal_url=portal_url)


@router.post("/webhook")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)) -> dict[str, str]:
    _require_stripe()
    payload = await request.body()
    signature = request.headers.get("stripe-signature", "")

    try:
        event = stripe.Webhook.construct_event(
            payload,
            signature,
            settings.STRIPE_WEBHOOK_SECRET,
        )
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid signature") from exc

    event_type = _get_attr(event, "type")
    event_data = _get_attr(_get_attr(event, "data", {}), "object", {})

    if event_type == "checkout.session.completed":
        _handle_checkout_completed(db, event_data)
    elif event_type == "customer.subscription.deleted":
        _handle_subscription_deleted(db, event_data)

    return {"status": "ok"}


def _handle_checkout_completed(db: Session, session: Any) -> None:
    metadata = _get_attr(session, "metadata", {}) or {}
    user_id = _get_attr(metadata, "user_id")
    if not user_id:
        return

    try:
        user = db.get(User, uuid.UUID(str(user_id)))
    except ValueError:
        return
    if not user:
        return

    user.role = UserRole.premium
    user.stripe_customer_id = _get_attr(session, "customer")
    user.stripe_subscription_id = _get_attr(session, "subscription")
    user.subscription_status = "active"
    user.subscription_ends_at = None
    db.commit()
    try:
        notification_service.create_notification(
            db,
            user_id=user.id,
            type="upgrade_success",
            title="Premium is active",
            body="Your ApplyLuma Premium subscription is now active.",
            related_id=None,
            related_type="billing",
            send_email=True,
            email=user.email,
        )
    except Exception:
        pass


def _handle_subscription_deleted(db: Session, subscription: Any) -> None:
    subscription_id = _get_attr(subscription, "id")
    customer_id = _get_attr(subscription, "customer")
    if subscription_id:
        user = db.query(User).filter(User.stripe_subscription_id == subscription_id).first()
    elif customer_id:
        user = db.query(User).filter(User.stripe_customer_id == customer_id).first()
    else:
        user = None

    if not user:
        return

    user.role = UserRole.user
    user.subscription_status = _get_attr(subscription, "status", "canceled")
    user.subscription_ends_at = _period_end(subscription)
    db.commit()
