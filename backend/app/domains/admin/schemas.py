from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from app.domains.users.model import UserRole, UserStatus


class AdminOverview(BaseModel):
    users: int
    active_users: int
    tracks: int
    published_tracks: int
    lessons: int
    lesson_completions: int
    issued_certificates: int
    awarded_badges: int


class AdminUserItem(BaseModel):
    id: UUID
    name: str
    email: str
    role: UserRole
    status: UserStatus
    last_login: datetime | None
    completed_lessons: int
    certificates: int


class UpdateUserStatusRequest(BaseModel):
    status: UserStatus


class CreateUserRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    role: UserRole = UserRole.STUDENT


class AdminTrackItem(BaseModel):
    id: UUID
    title: str
    difficulty: str
    estimated_hours: int
    is_active: bool
    lessons: int
    completions: int


class UpdateTrackStatusRequest(BaseModel):
    is_active: bool


class AdminCertificateItem(BaseModel):
    id: UUID
    title: str
    user_name: str
    user_email: str
    issued_at: datetime
    validation_code: str
