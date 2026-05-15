import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, SmallInteger, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.application_contact import ApplicationContact
    from app.models.application_event import ApplicationEvent
    from app.models.cv import CV
    from app.models.job_description import JobDescription
    from app.models.user import User


class Application(Base, TimestampMixin):
    __tablename__ = "applications"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    job_description_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("job_descriptions.id", ondelete="SET NULL"),
        nullable=True,
    )
    cv_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cvs.id", ondelete="SET NULL"), nullable=True
    )
    company_name: Mapped[str] = mapped_column(String(255))
    job_title: Mapped[str] = mapped_column(String(255))
    job_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="wishlist", server_default="wishlist")
    applied_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    source: Mapped[str | None] = mapped_column(String(100), nullable=True)
    salary_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    salary_max: Mapped[int | None] = mapped_column(Integer, nullable=True)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    remote_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    priority: Mapped[int] = mapped_column(SmallInteger, default=1, server_default="1")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    user: Mapped["User"] = relationship("User")
    cv: Mapped["CV | None"] = relationship("CV")
    job_description: Mapped["JobDescription | None"] = relationship("JobDescription")
    events: Mapped[list["ApplicationEvent"]] = relationship(
        "ApplicationEvent",
        back_populates="application",
        cascade="all, delete-orphan",
        order_by="ApplicationEvent.event_date.desc()",
    )
    contacts: Mapped[list["ApplicationContact"]] = relationship(
        "ApplicationContact",
        back_populates="application",
        cascade="all, delete-orphan",
        order_by="ApplicationContact.created_at.desc()",
    )
