import enum
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Enum, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.cv import CV
    from app.models.job_description import JobDescription
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
