import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.alert_preferences import UserAlertPreferences
    from app.models.cv import CV
    from app.models.job import JobMatchingScore, SavedJob
    from app.models.job_description import JobDescription
    from app.models.notification import Notification
    from app.models.tailor_job import TailorJob


class UserRole(enum.StrEnum):
    user = "user"
    admin = "admin"
    premium = "premium"


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String, unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String)
    full_name: Mapped[str | None] = mapped_column(String, nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True, server_default="true")
    is_verified: Mapped[bool] = mapped_column(default=False, server_default="false")
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role"),
        default=UserRole.user,
        server_default="user",
    )
    stripe_customer_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    stripe_subscription_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    subscription_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    subscription_ends_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    cvs: Mapped[list["CV"]] = relationship(
        "CV",
        foreign_keys="CV.user_id",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    job_descriptions: Mapped[list["JobDescription"]] = relationship(
        "JobDescription", back_populates="user", cascade="all, delete-orphan"
    )
    tailor_jobs: Mapped[list["TailorJob"]] = relationship(
        "TailorJob", back_populates="user", cascade="all, delete-orphan"
    )
    notifications: Mapped[list["Notification"]] = relationship(
        "Notification", back_populates="user", cascade="all, delete-orphan"
    )
    saved_jobs: Mapped[list["SavedJob"]] = relationship(
        "SavedJob", back_populates="user", cascade="all, delete-orphan"
    )
    matching_scores: Mapped[list["JobMatchingScore"]] = relationship(
        "JobMatchingScore", back_populates="user", cascade="all, delete-orphan"
    )
    alert_preferences: Mapped["UserAlertPreferences | None"] = relationship(
        "UserAlertPreferences",
        back_populates="user",
        cascade="all, delete-orphan",
        uselist=False,
    )
