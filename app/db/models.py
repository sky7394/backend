# app/db/models.py
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.learning_profile import LearningProfile  # noqa: F401
from app.models.payment import Payment  # noqa: F401
from app.models.user import Subscription, User  # noqa: F401


class OTPCode(Base):
    __tablename__ = "otp_codes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    mobile: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(10), nullable=False)
    is_used: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(),
        nullable=False,
        server_default=func.now(),
    )


class ExamModel(Base):
    __tablename__ = "exams"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    grade: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    subject: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    questions_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    questions: Mapped[list[QuestionModel]] = relationship(
        back_populates="exam",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="selectin",
        order_by="QuestionModel.id",
    )
    attempts: Mapped[list[ExamAttempt]] = relationship(
        back_populates="exam",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="selectin",
    )
    created_by: Mapped[User | None] = relationship(
        "User",
        foreign_keys=[created_by_user_id],
    )


class QuestionModel(Base):
    __tablename__ = "questions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    exam_id: Mapped[int] = mapped_column(
        ForeignKey("exams.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    question_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    difficulty: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    grade: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    subject: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    topic: Mapped[str | None] = mapped_column(String(255), nullable=True)
    options: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    correct_answer: Mapped[str] = mapped_column(Text, nullable=False)
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    exam: Mapped[ExamModel] = relationship(back_populates="questions")
    attempt_answers: Mapped[list[AttemptAnswer]] = relationship(
        back_populates="question",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class ExamAttempt(Base):
    __tablename__ = "exam_attempts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    exam_id: Mapped[int] = mapped_column(
        ForeignKey("exams.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="in_progress",
        index=True,
    )
    total_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        default=None,
    )
    max_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )
    percentage: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        default=None,
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    submitted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    graded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    exam: Mapped[ExamModel] = relationship(back_populates="attempts")
    student: Mapped[User] = relationship("User", foreign_keys=[student_id])
    answers: Mapped[list[AttemptAnswer]] = relationship(
        back_populates="attempt",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="selectin",
    )


class AttemptAnswer(Base):
    __tablename__ = "attempt_answers"
    __table_args__ = (
        UniqueConstraint(
            "attempt_id",
            "question_id",
            name="uq_attempt_answers_attempt_question",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    attempt_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("exam_attempts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    question_id: Mapped[int] = mapped_column(
        ForeignKey("questions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    submitted_answer: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    grading_status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="pending",
        index=True,
    )
    is_correct: Mapped[bool | None] = mapped_column(
        Boolean,
        nullable=True,
    )
    awarded_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    feedback: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    graded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    attempt: Mapped[ExamAttempt] = relationship(back_populates="answers")
    question: Mapped[QuestionModel] = relationship(back_populates="attempt_answers")
