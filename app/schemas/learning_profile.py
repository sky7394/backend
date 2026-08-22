# app/schemas/learning_profile.py
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class LearningProfileBase(BaseModel):
    learning_style: str | None = Field(default=None, max_length=50)
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    recommended_pace: str | None = Field(default=None, max_length=20)
    notes: str | None = None


class LearningProfileCreate(LearningProfileBase):
    pass


class LearningProfileUpdate(BaseModel):
    learning_style: str | None = None
    strengths: list[str] | None = None
    weaknesses: list[str] | None = None
    recommended_pace: str | None = None
    notes: str | None = None


class LearningProfileRead(LearningProfileBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    student_id: UUID
    created_at: datetime
    updated_at: datetime
