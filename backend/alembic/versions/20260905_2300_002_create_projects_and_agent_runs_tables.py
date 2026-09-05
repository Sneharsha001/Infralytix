"""create projects and agent_runs tables

Revision ID: 002_projects_and_agent_runs
Revises: 001_auth_tables
Create Date: 2026-09-05 23:00:00.000000+00:00

Hand-written migration matching models: Project, AgentRun.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "002_projects_and_agent_runs"
down_revision: str | None = "001_auth_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ─── Create projects table ────────────────────────────────────────────────
    op.create_table(
        "projects",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("repo_name", sa.String(length=120), nullable=True),
        sa.Column("archive_filename", sa.String(length=255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_projects_id", "projects", ["id"], unique=False)
    op.create_index("ix_projects_user_id", "projects", ["user_id"], unique=False)

    # ─── Create agent_runs table ──────────────────────────────────────────────
    op.create_table(
        "agent_runs",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("project_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column(
            "agent_type",
            sa.String(length=50),
            nullable=False,
            server_default="repository",
        ),
        sa.Column(
            "status",
            sa.Enum("pending", "running", "completed", "failed", name="agent_run_status"),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("output_data", sa.JSON(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_agent_runs_id", "agent_runs", ["id"], unique=False)
    op.create_index("ix_agent_runs_project_id", "agent_runs", ["project_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_agent_runs_project_id", table_name="agent_runs")
    op.drop_index("ix_agent_runs_id", table_name="agent_runs")
    op.drop_table("agent_runs")
    sa.Enum("pending", "running", "completed", "failed", name="agent_run_status").drop(
        op.get_bind(),
        checkfirst=True,
    )

    op.drop_index("ix_projects_user_id", table_name="projects")
    op.drop_index("ix_projects_id", table_name="projects")
    op.drop_table("projects")
