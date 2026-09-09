"""migrate embeddings to Gemini 1536

Revision ID: aab1226d1bb8
Revises: 2782ffd2205e
Create Date: 2026-09-07 19:46:43.203435

"""
from typing import Sequence, Union

from alembic import op
import pgvector.sqlalchemy
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'aab1226d1bb8'
down_revision: Union[str, Sequence[str], None] = '2782ffd2205e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Clear incompatible NVIDIA vectors and change to Gemini dimensions."""
    # Gemini vectors are incompatible with NVIDIA vectors.
    # Preserve chunk_text and metadata; only remove old vector values.
    op.execute(
        "UPDATE document_chunks SET embedding = NULL "
        "WHERE embedding IS NOT NULL"
    )

    op.alter_column(
        "document_chunks",
        "embedding",
        existing_type=pgvector.sqlalchemy.vector.VECTOR(dim=2048),
        type_=pgvector.sqlalchemy.vector.VECTOR(dim=1536),
        existing_nullable=True,
    )


def downgrade() -> None:
    """Restore the 2048-dimensional column after clearing vectors."""
    op.execute(
        "UPDATE document_chunks SET embedding = NULL "
        "WHERE embedding IS NOT NULL"
    )

    op.alter_column(
        "document_chunks",
        "embedding",
        existing_type=pgvector.sqlalchemy.vector.VECTOR(dim=1536),
        type_=pgvector.sqlalchemy.vector.VECTOR(dim=2048),
        existing_nullable=True,
    )