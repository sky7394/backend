"""create exam tables

Revision ID: 4c9bdf2e71a8
Revises: 85f4bc1fa2fd
Create Date: 2026-07-25

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "4c9bdf2e71a8"
down_revision: str | Sequence[str] | None = "85f4bc1fa2fd"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "exams",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("grade", sa.Integer(), nullable=False),
        sa.Column("subject", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("questions_count", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_exams_grade"), "exams", ["grade"], unique=False)
    op.create_index(op.f("ix_exams_subject"), "exams", ["subject"], unique=False)
    op.create_index(op.f("ix_exams_title"), "exams", ["title"], unique=False)

    op.create_table(
        "questions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("exam_id", sa.Integer(), nullable=False),
        sa.Column("question_text", sa.Text(), nullable=False),
        sa.Column("question_type", sa.String(length=50), nullable=False),
        sa.Column("difficulty", sa.String(length=20), nullable=False),
        sa.Column("grade", sa.Integer(), nullable=False),
        sa.Column("subject", sa.String(length=255), nullable=False),
        sa.Column("topic", sa.String(length=255), nullable=True),
        sa.Column("options", sa.JSON(), nullable=True),
        sa.Column("correct_answer", sa.Text(), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["exam_id"], ["exams.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_questions_difficulty"),
        "questions",
        ["difficulty"],
        unique=False,
    )
    op.create_index(op.f("ix_questions_exam_id"), "questions", ["exam_id"], unique=False)
    op.create_index(op.f("ix_questions_grade"), "questions", ["grade"], unique=False)
    op.create_index(
        op.f("ix_questions_question_type"),
        "questions",
        ["question_type"],
        unique=False,
    )
    op.create_index(op.f("ix_questions_subject"), "questions", ["subject"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_questions_subject"), table_name="questions")
    op.drop_index(op.f("ix_questions_question_type"), table_name="questions")
    op.drop_index(op.f("ix_questions_grade"), table_name="questions")
    op.drop_index(op.f("ix_questions_exam_id"), table_name="questions")
    op.drop_index(op.f("ix_questions_difficulty"), table_name="questions")
    op.drop_table("questions")

    op.drop_index(op.f("ix_exams_title"), table_name="exams")
    op.drop_index(op.f("ix_exams_subject"), table_name="exams")
    op.drop_index(op.f("ix_exams_grade"), table_name="exams")
    op.drop_table("exams")
