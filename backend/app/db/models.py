"""Relational schema. JSON columns hold small, user-owned lists (skills, projects, ...)."""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import JSON, Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


def utcnow() -> datetime:
    return datetime.now(UTC)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(120))
    token_version: Mapped[int] = mapped_column(Integer, default=0)
    refresh_jti: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    profile: Mapped[Profile] = relationship(back_populates="user", uselist=False, cascade="all, delete-orphan")


class Profile(Base):
    __tablename__ = "profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True)
    education: Mapped[str] = mapped_column(String(200), default="")
    college: Mapped[str] = mapped_column(String(200), default="")
    graduation_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    technical_skills: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    soft_skills: Mapped[list[str]] = mapped_column(JSON, default=list)
    projects: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    certifications: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    experience_years: Mapped[float] = mapped_column(Float, default=0.0)
    experience_summary: Mapped[str] = mapped_column(Text, default="")
    career_interests: Mapped[list[str]] = mapped_column(JSON, default=list)
    target_role: Mapped[str | None] = mapped_column(String(60), nullable=True)
    current_location: Mapped[str] = mapped_column(String(120), default="")
    preferred_locations: Mapped[list[str]] = mapped_column(JSON, default=list)
    willing_to_relocate: Mapped[bool] = mapped_column(Boolean, default=False)
    work_mode: Mapped[str] = mapped_column(String(10), default="any")
    expected_salary_lpa: Mapped[float | None] = mapped_column(Float, nullable=True)
    min_salary_lpa: Mapped[float | None] = mapped_column(Float, nullable=True)
    learning_language: Mapped[str] = mapped_column(String(5), default="en")
    app_language: Mapped[str] = mapped_column(String(5), default="en")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    user: Mapped[User] = relationship(back_populates="profile")


class AssessmentAttempt(Base):
    __tablename__ = "assessment_attempts"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    skill: Mapped[str] = mapped_column(String(60), index=True)
    level: Mapped[str] = mapped_column(String(15))
    question_ids: Mapped[list[str]] = mapped_column(JSON)
    answers: Mapped[dict[str, str] | None] = mapped_column(JSON, nullable=True)
    raw_percent: Mapped[float | None] = mapped_column(Float, nullable=True)
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    topic_breakdown: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(primary_key=True)
    company: Mapped[str] = mapped_column(String(120), index=True)
    title: Mapped[str] = mapped_column(String(120), index=True)
    role_id: Mapped[str | None] = mapped_column(String(60), index=True, nullable=True)
    description: Mapped[str] = mapped_column(Text)
    mandatory_skills: Mapped[list[str]] = mapped_column(JSON, default=list)
    preferred_skills: Mapped[list[str]] = mapped_column(JSON, default=list)
    education: Mapped[str] = mapped_column(String(200), default="")
    experience_min_years: Mapped[float] = mapped_column(Float, default=0.0)
    location: Mapped[str] = mapped_column(String(120), index=True)
    work_mode: Mapped[str] = mapped_column(String(10))
    salary_min_lpa: Mapped[float | None] = mapped_column(Float, nullable=True)
    salary_max_lpa: Mapped[float | None] = mapped_column(Float, nullable=True)
    posted_date: Mapped[date] = mapped_column(Date)
    last_verified_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    deadline: Mapped[date | None] = mapped_column(Date, nullable=True)
    apply_url: Mapped[str] = mapped_column(String(500))
    source: Mapped[str] = mapped_column(String(200))
    verification_status: Mapped[str] = mapped_column(String(30), default="Pending Verification")
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Application(Base):
    __tablename__ = "applications"
    __table_args__ = (UniqueConstraint("user_id", "job_id", name="uq_application_user_job"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"))
    status: Mapped[str] = mapped_column(String(15), default="saved")
    notes: Mapped[str] = mapped_column(Text, default="")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    job: Mapped[Job] = relationship()


class RoadmapStep(Base):
    __tablename__ = "roadmap_steps"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    order: Mapped[int] = mapped_column(Integer)
    skill: Mapped[str] = mapped_column(String(60))
    priority: Mapped[str] = mapped_column(String(10))
    reason: Mapped[str] = mapped_column(Text, default="")
    course_id: Mapped[str | None] = mapped_column(String(60), nullable=True)
    estimated_hours: Mapped[int] = mapped_column(Integer, default=10)
    exercise: Mapped[str] = mapped_column(Text, default="")
    project: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(15), default="not_started")
    reassessment_required: Mapped[bool] = mapped_column(Boolean, default=False)
    current_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    target_score: Mapped[int] = mapped_column(Integer, default=65)
    target_role: Mapped[str | None] = mapped_column(String(60), nullable=True)
    roadmap_reason: Mapped[str] = mapped_column(Text, default="")
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AgentRun(Base):
    __tablename__ = "agent_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    trigger: Mapped[str] = mapped_column(String(30))
    llm_mode: Mapped[str] = mapped_column(String(15))
    readiness: Mapped[float | None] = mapped_column(Float, nullable=True)
    result: Mapped[dict[str, Any]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
