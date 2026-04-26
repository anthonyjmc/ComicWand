"""Initial schema for users, comics, and comic_pages tables."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "202604261600"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("clerk_id", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("comics_generated_today", sa.Integer(), server_default="0", nullable=False),
        sa.Column("last_comic_date", sa.Date(), nullable=True),
        sa.Column("tier", sa.Enum("free", "pro", name="user_tier"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_clerk_id"), "users", ["clerk_id"], unique=True)
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)

    op.create_table(
        "comics",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("status", sa.Enum("pending", "processing", "completed", "failed", name="comic_status"), nullable=False),
        sa.Column("pages_count", sa.Integer(), nullable=False),
        sa.Column("style", sa.String(length=120), nullable=False),
        sa.Column("reference_image_url", sa.Text(), nullable=True),
        sa.Column("story_prompt", sa.Text(), nullable=False),
        sa.Column("pdf_url", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("generation_cost_usd", sa.Numeric(10, 4), server_default="0", nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_comics_user_id"), "comics", ["user_id"], unique=False)

    op.create_table(
        "comic_pages",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("comic_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=False),
        sa.Column("panel_count", sa.Integer(), nullable=False),
        sa.Column("image_urls", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("dialogue", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("status", sa.Enum("pending", "processing", "completed", "failed", name="page_status"), nullable=False),
        sa.ForeignKeyConstraint(["comic_id"], ["comics.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_comic_pages_comic_id"), "comic_pages", ["comic_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_comic_pages_comic_id"), table_name="comic_pages")
    op.drop_table("comic_pages")
    op.drop_index(op.f("ix_comics_user_id"), table_name="comics")
    op.drop_table("comics")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_index(op.f("ix_users_clerk_id"), table_name="users")
    op.drop_table("users")
    sa.Enum(name="page_status").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="comic_status").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="user_tier").drop(op.get_bind(), checkfirst=True)
