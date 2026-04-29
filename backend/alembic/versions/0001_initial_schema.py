"""Initial schema: traces, eval_runs, model_configs

Revision ID: 0001
Revises:
Create Date: 2025-01-01 00:00:00
"""
from __future__ import annotations
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "model_configs",
        sa.Column("model_name", sa.String(120), primary_key=True),
        sa.Column("cost_per_input_token", sa.Float, nullable=False, server_default="0.000001"),
        sa.Column("cost_per_output_token", sa.Float, nullable=False, server_default="0.000002"),
        sa.Column("display_name", sa.String(200), nullable=True),
    )

    op.execute(
        sa.text(
            "CREATE TYPE trace_status AS ENUM ('pending', 'evaluating', 'done', 'error')"
        )
    )

    op.create_table(
        "traces",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("model", sa.String(120), nullable=False),
        sa.Column("prompt", sa.Text, nullable=False),
        sa.Column("response", sa.Text, nullable=False),
        sa.Column("context", sa.Text, nullable=True),
        sa.Column("question", sa.Text, nullable=True),
        sa.Column("latency_ms", sa.Float, nullable=False),
        sa.Column("prompt_tokens", sa.Integer, nullable=False, server_default="0"),
        sa.Column("completion_tokens", sa.Integer, nullable=False, server_default="0"),
        sa.Column("cost_usd", sa.Float, nullable=False, server_default="0"),
        sa.Column(
            "status",
            sa.Enum("pending", "evaluating", "done", "error", name="trace_status"),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("extra_metadata", postgresql.JSON, nullable=True),
    )
    op.create_index("ix_traces_created_at", "traces", ["created_at"])
    op.create_index("ix_traces_model", "traces", ["model"])
    op.create_index("ix_traces_status", "traces", ["status"])

    op.create_table(
        "eval_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("trace_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("traces.id"), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("faithfulness", sa.Float, nullable=True),
        sa.Column("answer_relevancy", sa.Float, nullable=True),
        sa.Column("context_recall", sa.Float, nullable=True),
        sa.Column("context_precision", sa.Float, nullable=True),
        sa.Column("error", sa.Text, nullable=True),
    )
    op.create_index("ix_eval_runs_trace_id", "eval_runs", ["trace_id"])

    # Seed default model pricing
    op.execute(
        sa.text(
            """
            INSERT INTO model_configs (model_name, cost_per_input_token, cost_per_output_token, display_name) VALUES
            ('gpt-4o',          0.000005,   0.000015,  'GPT-4o'),
            ('gpt-4o-mini',     0.00000015, 0.0000006, 'GPT-4o Mini'),
            ('gpt-4-turbo',     0.00001,    0.00003,   'GPT-4 Turbo'),
            ('gpt-3.5-turbo',   0.0000005,  0.0000015, 'GPT-3.5 Turbo'),
            ('claude-sonnet-4-6',  0.000003,   0.000015,  'Claude Sonnet 4.6'),
            ('claude-opus-4-7',    0.000015,   0.000075,  'Claude Opus 4.7')
            ON CONFLICT DO NOTHING
            """
        )
    )


def downgrade() -> None:
    op.drop_table("eval_runs")
    op.drop_table("traces")
    op.drop_table("model_configs")
    op.execute(sa.text("DROP TYPE IF EXISTS trace_status"))
