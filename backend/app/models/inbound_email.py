import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, SmallInteger, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.application import Application
    from app.models.user import User

# Longest excerpt of the message body kept on disk. Full bodies are never
# persisted: this is user correspondence, and a truncated excerpt is enough to
# debug a bad match without holding the whole message at rest.
SNIPPET_MAX_CHARS = 2000


class InboundEmail(Base, TimestampMixin):
    """A job-related email forwarded into ApplyLuma by a user.

    Rows are written by ``app.tasks.inbound_email`` after the webhook has
    verified the vendor signature and resolved the recipient token to a user.
    """

    __tablename__ = "inbound_emails"
    __table_args__ = (
        # Vendors retry aggressively on any non-2xx or slow response, so the
        # same message arrives more than once as a matter of course.
        UniqueConstraint("user_id", "dedupe_key", name="uq_inbound_emails_user_dedupe"),
        Index("ix_inbound_emails_user_created", "user_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    # Message-ID when the message carried one, otherwise a content hash.
    dedupe_key: Mapped[str] = mapped_column(String(128))
    message_id: Mapped[str | None] = mapped_column(String(512), nullable=True)
    from_address: Mapped[str] = mapped_column(String(320))
    from_domain: Mapped[str] = mapped_column(String(255), index=True)
    subject: Mapped[str | None] = mapped_column(String(512), nullable=True)
    snippet: Mapped[str | None] = mapped_column(Text, nullable=True)
    received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    matched_application_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("applications.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    match_confidence: Mapped[int] = mapped_column(SmallInteger, default=0, server_default="0")
    match_method: Mapped[str] = mapped_column(String(50), default="none", server_default="none")
    # Human-readable explanation of the match decision, shown in the admin view
    # so a wrong or missing match can be diagnosed without the original body.
    match_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    vendor: Mapped[str] = mapped_column(String(32))

    user: Mapped["User"] = relationship("User")
    matched_application: Mapped["Application | None"] = relationship("Application")
