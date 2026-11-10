"""The forwarding and unmatched-email queries against a real Postgres.

The endpoint tests use fakes, which never compile SQL. Opt-in, like the other
real-database tests:

    TEST_DATABASE_URL=postgresql://... pytest tests/test_email_forwarding_db.py
"""

from __future__ import annotations

import os
import sys
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

pytestmark = pytest.mark.skipif(
    not os.getenv("TEST_DATABASE_URL"), reason="needs TEST_DATABASE_URL"
)


def test_forwarding_queries_against_real_database() -> None:
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    import app.main  # noqa: F401  (registers every model, so relationships resolve)
    from app.crud import inbound_email as crud_inbound_email
    from app.crud import user as crud_user
    from app.models.application import Application
    from app.models.inbound_email import InboundEmail
    from app.models.user import User

    engine = create_engine(os.environ["TEST_DATABASE_URL"])
    db = sessionmaker(bind=engine)()
    tag = uuid.uuid4().hex[:8]
    now = datetime.now(UTC)
    try:
        user = User(email=f"forwarding-{tag}@example.com", hashed_password=None, google_id=f"g-{tag}")
        db.add(user)
        db.flush()
        application = Application(user_id=user.id, company_name="Acme", job_title="Engineer")
        db.add(application)
        db.flush()

        def email(key: str, **kw: object) -> InboundEmail:
            defaults: dict[str, object] = {
                "user_id": user.id,
                "dedupe_key": f"{tag}-{key}",
                "from_address": "noreply@teamtailor.com",
                "from_domain": "teamtailor.com",
                "vendor": "test",
            }
            defaults.update(kw)
            row = InboundEmail(**defaults)
            db.add(row)
            return row

        rejection = email(
            "rejection", classification="rejection", classification_confidence=90,
            suggested_status="rejected", evidence="Unfortunately...",
        )
        # Too unsure to ask about, matched already, or already decided: hidden.
        email("weak", classification="rejection", classification_confidence=50, suggested_status="rejected")
        email(
            "matched", classification="interview", classification_confidence=90,
            suggested_status="interview", matched_application_id=application.id,
            suggestion_state="pending",
        )
        email(
            "dismissed", classification="offer", classification_confidence=90,
            suggested_status="offer", suggestion_state="dismissed",
        )
        email("newsletter")
        email(
            "gmail", from_address="forwarding-noreply@google.com", from_domain="google.com",
            subject="(#123456789) Gmail Forwarding Confirmation",
        )
        db.commit()

        # Case-insensitive email lookup, and the OAuth-only login hint.
        found = crud_user.get_by_email(db, f"Forwarding-{tag}@Example.COM")
        assert found is not None and found.id == user.id
        assert "Google" in (crud_user.oauth_only_hint(found) or "")

        unmatched = crud_inbound_email.list_unmatched(db, user.id, since=now - timedelta(days=60))
        assert [row.id for row in unmatched] == [rejection.id]
        assert crud_inbound_email.get_unmatched(db, rejection.id, user.id) is not None
        assert crud_inbound_email.get_unmatched(db, rejection.id, uuid.uuid4()) is None

        count, latest = crud_inbound_email.forwarding_stats(db, user.id)
        assert count == 6
        assert latest is not None

        confirmation = crud_inbound_email.latest_from_sender(
            db, user.id, "forwarding-noreply@google.com", now - timedelta(days=7)
        )
        assert confirmation is not None
        assert confirmation.subject == "(#123456789) Gmail Forwarding Confirmation"

        crud_inbound_email.assign_to_application(db, rejection, application.id)
        crud_inbound_email.set_suggestion_state(db, rejection, "accepted")
        assert crud_inbound_email.list_unmatched(db, user.id, since=now - timedelta(days=60)) == []

        rows, total = crud_inbound_email.list_for_user(
            db, user.id, exclude_sender="forwarding-noreply@google.com"
        )
        assert total == 5
        assert all(row.from_address != "forwarding-noreply@google.com" for row, _, _ in rows)
        matched_rows, matched_total = crud_inbound_email.list_for_user(db, user.id, matched=True)
        assert matched_total == 2
        assert {company for _, company, _ in matched_rows} == {"Acme"}

        assert crud_inbound_email.delete_for_user(db, rejection.id, uuid.uuid4()) is False
        assert crud_inbound_email.delete_for_user(db, rejection.id, user.id) is True
        assert crud_inbound_email.forwarding_stats(db, user.id)[0] == 5

        old_token = user.inbox_token
        crud_user.rotate_inbox_token(db, user)
        assert user.inbox_token and user.inbox_token != old_token
    finally:
        db.rollback()
        db.query(User).filter(User.email == f"forwarding-{tag}@example.com").delete()
        db.commit()
        db.close()
