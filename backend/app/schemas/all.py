"""Pydantic schemas for authentication, profile, assessments, jobs, courses, roadmap, and mentor."""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field, HttpUrl, field_validator

LangCode = Literal["en", "ta", "hi", "te", "kn", "ml", "bn", "mr"]
SkillLevel = Literal["beginner", "intermediate", "advanced"]
WorkMode = Literal["remote", "hybrid", "onsite", "any"]
AppStatus = Literal["saved", "applied", "interviewing", "offer", "rejected"]
StepStatus = Literal["not_started", "in_progress", "completed"]


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=2, max_length=120)

    @field_validator("password")
    @classmethod
    def _password_strength(cls, v: str) -> str:
        if not any(c.isalpha() for c in v) or not any(c.isdigit() for c in v):
            raise ValueError("Password must include at least one letter and one digit.")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class UserOut(BaseModel):
    id: int
    email: EmailStr
    full_name: str
    created_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"  # noqa: S105
    user: UserOut


class TechnicalSkillIn(BaseModel):
    name: str = Field(min_length=1, max_length=60)
    self_level: SkillLevel = "beginner"


class ProjectIn(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=600)
    skills: list[str] = Field(default_factory=list, max_length=12)


class CertificationIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    issuer: str = Field(default="", max_length=120)
    year: int | None = Field(default=None, ge=1990, le=2035)


class ProfileUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=120)
    education: str | None = Field(default=None, max_length=200)
    college: str | None = Field(default=None, max_length=200)
    graduation_year: int | None = Field(default=None, ge=1990, le=2035)
    technical_skills: list[TechnicalSkillIn] | None = Field(default=None, max_length=30)
    soft_skills: list[str] | None = Field(default=None, max_length=20)
    projects: list[ProjectIn] | None = Field(default=None, max_length=15)
    certifications: list[CertificationIn] | None = Field(default=None, max_length=15)
    experience_years: float | None = Field(default=None, ge=0, le=50)
    experience_summary: str | None = Field(default=None, max_length=1000)
    career_interests: list[str] | None = Field(default=None, max_length=10)
    target_role: str | None = Field(default=None, max_length=60)
    current_location: str | None = Field(default=None, max_length=120)
    preferred_locations: list[str] | None = Field(default=None, max_length=10)
    willing_to_relocate: bool | None = None
    work_mode: WorkMode | None = None
    expected_salary_lpa: float | None = Field(default=None, ge=0, le=200)
    min_salary_lpa: float | None = Field(default=None, ge=0, le=200)
    learning_language: LangCode | None = None
    app_language: LangCode | None = None


class AssessmentStartRequest(BaseModel):
    skill: str = Field(min_length=1, max_length=60)
    level: SkillLevel = "beginner"


class AssessmentSubmitRequest(BaseModel):
    answers: dict[str, str] = Field(default_factory=dict)


class OrchestratorRunRequest(BaseModel):
    trigger: Literal[
        "manual",
        "profile_updated",
        "assessment_completed",
        "goal_changed",
        "learning_completed",
        "job_added",
    ] = "manual"


class TargetCareerRequest(BaseModel):
    role_id: str = Field(min_length=1, max_length=60)


class ExtractJobRequest(BaseModel):
    description: str = Field(min_length=10, max_length=5000)


class JobCreateRequest(BaseModel):
    company: str = Field(min_length=2, max_length=120)
    title: str = Field(min_length=2, max_length=120)
    description: str = Field(min_length=50, max_length=5000)
    mandatory_skills: list[str] | None = Field(default=None, max_length=25)
    preferred_skills: list[str] | None = Field(default=None, max_length=25)
    location: str = Field(min_length=2, max_length=120)
    work_mode: Literal["remote", "hybrid", "onsite"]
    salary_min_lpa: float | None = Field(default=None, ge=0, le=200)
    salary_max_lpa: float | None = Field(default=None, ge=0, le=200)
    experience_min_years: float = Field(default=0.0, ge=0, le=40)
    education: str = Field(default="", max_length=200)
    posted_date: date
    deadline: date | None = None
    apply_url: HttpUrl
    source: str = Field(min_length=2, max_length=200)

    @field_validator("apply_url")
    @classmethod
    def _https_only(cls, v: HttpUrl) -> HttpUrl:
        if v.scheme != "https":
            raise ValueError("apply_url must use https://")
        return v

    @field_validator("salary_max_lpa")
    @classmethod
    def _salary_order(cls, v: float | None, info) -> float | None:
        s_min = info.data.get("salary_min_lpa")
        if v is not None and s_min is not None and v < s_min:
            raise ValueError("salary_max_lpa must be greater than or equal to salary_min_lpa")
        return v


class ApplicationCreateRequest(BaseModel):
    job_id: int
    status: AppStatus = "saved"


class ApplicationUpdateRequest(BaseModel):
    status: AppStatus | None = None
    notes: str | None = Field(default=None, max_length=1000)


class RoadmapStepUpdateRequest(BaseModel):
    status: StepStatus


class MentorChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=1000)
    language: LangCode = "en"
