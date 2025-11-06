"""add scoring data quality

Revision ID: 20251106_1301
Revises: 20251105_1353_18564497c355
Create Date: 2025-11-06 13:01:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20251106_1301'
down_revision = '18564497c355'
branch_labels = None
depends_on = None


def upgrade():
    # Add data_quality and warnings columns to scores table
    op.add_column('scores', sa.Column('data_quality', sa.JSON(), nullable=True))
    op.add_column('scores', sa.Column('warnings', sa.JSON(), nullable=True))


def downgrade():
    op.drop_column('scores', 'warnings')
    op.drop_column('scores', 'data_quality')
