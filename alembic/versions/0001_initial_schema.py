"""Initial schema

Revision ID: 0001
Revises:
Create Date: 2026-03-05
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # users
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("github_id", sa.BigInteger(), unique=True, nullable=False),
        sa.Column("github_username", sa.String(255), nullable=False),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("display_name", sa.String(255), nullable=True),
        sa.Column("timezone", sa.String(64), nullable=False, server_default="UTC"),
        sa.Column("gas", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("streak", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("longest_streak", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_points", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("spendable_points", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("leetcode_username", sa.String(255), nullable=True),
        sa.Column("leetcode_validated", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("active_car_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # oauth_tokens
    op.create_table(
        "oauth_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False),
        sa.Column("provider", sa.String(64), nullable=False),
        sa.Column("access_token_enc", sa.LargeBinary(), nullable=False),
        sa.Column("scope", sa.String(512), nullable=True),
        sa.Column("token_type", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # daily_activity
    op.create_table(
        "daily_activity",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("github_commit_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("lc_easy_accepted", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("lc_medium_accepted", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("lc_hard_accepted", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("lc_total_accepted", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_finalized", sa.Boolean(), nullable=False, server_default="false"),
        sa.UniqueConstraint("user_id", "date", name="uq_daily_activity_user_date"),
    )

    # tracks
    op.create_table(
        "tracks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(128), unique=True, nullable=False),
        sa.Column("description", sa.String(1024), nullable=False, server_default=""),
        sa.Column("length_days", sa.Integer(), nullable=False),
        sa.Column("base_seconds_per_segment", sa.Integer(), nullable=False),
        sa.Column("difficulty", sa.String(32), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
    )

    # perks
    op.create_table(
        "perks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("slug", sa.String(128), unique=True, nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.String(1024), nullable=False),
        sa.Column("effect_type", sa.String(128), nullable=False),
        sa.Column("effect_value", sa.Float(), nullable=False),
    )

    # car_catalog
    op.create_table(
        "car_catalog",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(128), unique=True, nullable=False),
        sa.Column("rarity", sa.String(32), nullable=False),
        sa.Column("description", sa.String(1024), nullable=False, server_default=""),
        sa.Column("base_model", sa.String(255), nullable=False),
        sa.Column("max_upgrade_level", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("perk_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("perks.id"), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
    )

    # runs
    op.create_table(
        "runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("track_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tracks.id"), nullable=False),
        sa.Column("segment_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("last_processed_date", sa.Date(), nullable=True),
        sa.Column("stopwatch_seconds", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("corner_saves", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("weather_penalties_taken", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("ghost_wins", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_complete", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("lootbox_tier", sa.String(32), nullable=True),
        sa.Column("momentum_used", sa.Boolean(), nullable=False, server_default="false"),
    )

    # daily_run_events
    op.create_table(
        "daily_run_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("runs.id"), nullable=False),
        sa.Column("segment_index", sa.Integer(), nullable=False),
        sa.Column("corner_roll", sa.Float(), nullable=True),
        sa.Column("weather_roll", sa.Float(), nullable=True),
        sa.Column("ghost_roll", sa.Float(), nullable=True),
        sa.Column("corner_type", sa.String(64), nullable=True),
        sa.Column("corner_requirement", postgresql.JSONB(), nullable=True),
        sa.Column("corner_time_save_seconds", sa.Integer(), nullable=True),
        sa.Column("weather_type", sa.String(64), nullable=True),
        sa.Column("weather_requirement", postgresql.JSONB(), nullable=True),
        sa.Column("weather_penalty_seconds", sa.Integer(), nullable=True),
        sa.Column("ghost_name", sa.String(128), nullable=True),
        sa.Column("ghost_difficulty", sa.String(32), nullable=True),
        sa.Column("ghost_requirement", postgresql.JSONB(), nullable=True),
        sa.Column("corner_completed", sa.Boolean(), nullable=True),
        sa.Column("weather_survived", sa.Boolean(), nullable=True),
        sa.Column("ghost_won", sa.Boolean(), nullable=True),
        sa.Column("processed", sa.Boolean(), nullable=False, server_default="false"),
        sa.UniqueConstraint("user_id", "date", name="uq_daily_run_events_user_date"),
    )

    # daily_processed_days
    op.create_table(
        "daily_processed_days",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("runs.id"), nullable=True),
        sa.Column("qualified", sa.Boolean(), nullable=False),
        sa.Column("gas_used", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("crashed", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("segment_advanced", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("run_completed", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("stopwatch_delta", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("processed_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", "date", name="uq_daily_processed_days_user_date"),
    )

    # completed_runs
    op.create_table(
        "completed_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("track_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tracks.id"), nullable=False),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("total_seconds", sa.Integer(), nullable=False),
        sa.Column("corner_saves", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("weather_penalties_taken", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("ghost_wins", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("streak_at_completion", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("lootbox_tier", sa.String(32), nullable=False),
        sa.Column("points_awarded", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("gas_awarded", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("pb_set", sa.Boolean(), nullable=False, server_default="false"),
    )

    # personal_bests
    op.create_table(
        "personal_bests",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("track_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tracks.id"), nullable=False),
        sa.Column("best_seconds", sa.Integer(), nullable=False),
        sa.Column("set_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.UniqueConstraint("user_id", "track_id", name="uq_pb_user_track"),
    )

    # lootboxes
    op.create_table(
        "lootboxes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("tier", sa.String(32), nullable=False),
        sa.Column("source_run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("opened", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("car_awarded_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("car_catalog.id"), nullable=True),
        sa.Column("points_awarded", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    # car_ownership
    op.create_table(
        "car_ownership",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("car_catalog_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("car_catalog.id"), nullable=False),
        sa.Column("upgrade_level", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("iconic_unlocked", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("perk_active", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("obtained_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("user_id", "car_catalog_id", name="uq_car_ownership_user_car"),
    )

    # cosmetics
    op.create_table(
        "cosmetics",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("slug", sa.String(128), unique=True, nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("type", sa.String(64), nullable=False),
        sa.Column("rarity", sa.String(32), nullable=False),
        sa.Column("source_description", sa.String(512), nullable=False, server_default=""),
    )

    # cosmetic_inventory
    op.create_table(
        "cosmetic_inventory",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("cosmetic_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("cosmetics.id"), nullable=False),
        sa.Column("obtained_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("user_id", "cosmetic_id", name="uq_cosmetic_inventory_user_cosmetic"),
    )

    # lifetime_stats
    op.create_table(
        "lifetime_stats",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False),
        sa.Column("total_runs_completed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_days_qualified", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_gas_used", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_crashes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_corner_saves", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_weather_survived", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_ghost_wins", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_lootboxes_opened", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_cars_owned", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Indexes
    op.create_index("ix_daily_activity_user_date", "daily_activity", ["user_id", "date"])
    op.create_index("ix_daily_run_events_user_date", "daily_run_events", ["user_id", "date"])
    op.create_index("ix_daily_processed_days_user_date", "daily_processed_days", ["user_id", "date"])
    # Partial unique index: one active run per user at a time
    op.create_index(
        "ix_runs_user_active_unique",
        "runs",
        ["user_id"],
        unique=True,
        postgresql_where=sa.text("is_complete = FALSE"),
    )
    op.create_index("ix_lootboxes_user_opened", "lootboxes", ["user_id", "opened"])


def downgrade() -> None:
    op.drop_table("lifetime_stats")
    op.drop_table("cosmetic_inventory")
    op.drop_table("cosmetics")
    op.drop_table("car_ownership")
    op.drop_table("lootboxes")
    op.drop_table("personal_bests")
    op.drop_table("completed_runs")
    op.drop_table("daily_processed_days")
    op.drop_table("daily_run_events")
    op.drop_table("runs")
    op.drop_table("car_catalog")
    op.drop_table("perks")
    op.drop_table("tracks")
    op.drop_table("daily_activity")
    op.drop_table("oauth_tokens")
    op.drop_table("users")
