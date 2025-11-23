"""add force_password_change to users

Revision ID: 20251111_force_pwd_change
Revises: 20251106_1301
Create Date: 2025-11-11 00:00:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20251111_force_pwd_change'
down_revision = '20251106_1301'
branch_labels = None
depends_on = None


def upgrade():
    # Add force_password_change column to users table
    op.add_column('users', sa.Column('force_password_change', sa.Boolean(), nullable=False, server_default='0'))


def downgrade():
    op.drop_column('users', 'force_password_change')
