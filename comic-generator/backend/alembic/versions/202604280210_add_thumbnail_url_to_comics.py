"""Add thumbnail_url column to comics table."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "202604280210"
down_revision: Union[str, None] = "202604261600"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("comics", sa.Column("thumbnail_url", sa.Text(), nullable=True))
    op.execute(
        """
        UPDATE comics AS c
        SET thumbnail_url = page_data.thumbnail_url
        FROM (
            SELECT DISTINCT ON (comic_id)
                comic_id,
                image_urls->-1 AS thumbnail_url
            FROM comic_pages
            WHERE jsonb_array_length(image_urls) > 0
            ORDER BY comic_id, page_number ASC
        ) AS page_data
        WHERE c.id = page_data.comic_id
          AND c.thumbnail_url IS NULL
        """
    )


def downgrade() -> None:
    op.drop_column("comics", "thumbnail_url")
