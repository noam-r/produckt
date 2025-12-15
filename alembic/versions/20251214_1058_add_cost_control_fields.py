"""add cost control fields and user monthly spending table

Revision ID: 20251214_1058_cost_control
Revises: 20251111_force_pwd_change
Create Date: 2025-12-14 10:58:00

"""
from alembic import op
import sqlalchemy as sa
from backend.models.utils import GUID


# revision identifiers, used by Alembic.
revision = '20251214_1058_cost_control'
down_revision = '20251111_force_pwd_change'
branch_labels = None
depends_on = None


def upgrade():
    # Add budget fields to users table
    op.add_column('users', sa.Column('monthly_budget_usd', sa.Numeric(10, 2), nullable=False, server_default='100.00'))
    op.add_column('users', sa.Column('budget_updated_at', sa.DateTime(), nullable=True))
    op.add_column('users', sa.Column('budget_updated_by', GUID, nullable=True))
    
    # Add foreign key constraint for budget_updated_by
    op.create_foreign_key('fk_users_budget_updated_by', 'users', 'users', ['budget_updated_by'], ['id'])
    
    # Add question limit fields to initiatives table
    op.add_column('initiatives', sa.Column('max_questions', sa.Integer(), nullable=False, server_default='50'))
    op.add_column('initiatives', sa.Column('max_questions_updated_at', sa.DateTime(), nullable=True))
    op.add_column('initiatives', sa.Column('max_questions_updated_by', GUID, nullable=True))
    
    # Add foreign key constraint for max_questions_updated_by
    op.create_foreign_key('fk_initiatives_max_questions_updated_by', 'initiatives', 'users', ['max_questions_updated_by'], ['id'])
    
    # Create user_monthly_spending table
    op.create_table('user_monthly_spending',
        sa.Column('id', GUID, nullable=False),
        sa.Column('user_id', GUID, nullable=False),
        sa.Column('year', sa.Integer(), nullable=False),
        sa.Column('month', sa.Integer(), nullable=False),
        sa.Column('total_spent_usd', sa.Numeric(10, 2), nullable=False, server_default='0.00'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('user_id', 'year', 'month', name='uq_user_month')
    )
    
    # Create indexes for performance
    op.create_index('ix_user_monthly_spending_user_month', 'user_monthly_spending', ['user_id', 'year', 'month'])


def downgrade():
    # Drop user_monthly_spending table
    op.drop_index('ix_user_monthly_spending_user_month', table_name='user_monthly_spending')
    op.drop_table('user_monthly_spending')
    
    # Remove question limit fields from initiatives
    op.drop_constraint('fk_initiatives_max_questions_updated_by', 'initiatives', type_='foreignkey')
    op.drop_column('initiatives', 'max_questions_updated_by')
    op.drop_column('initiatives', 'max_questions_updated_at')
    op.drop_column('initiatives', 'max_questions')
    
    # Remove budget fields from users
    op.drop_constraint('fk_users_budget_updated_by', 'users', type_='foreignkey')
    op.drop_column('users', 'budget_updated_by')
    op.drop_column('users', 'budget_updated_at')
    op.drop_column('users', 'monthly_budget_usd')