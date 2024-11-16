"""Add user logout timestamp

Revision ID: 001_add_user_logout
Create Date: 2024-02-14 10:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = '001_add_user_logout'
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Add last_logout to users table
    with op.batch_alter_table('users') as batch_op:
        batch_op.add_column(sa.Column('last_logout', sa.DateTime(timezone=True), nullable=True))
    
    # Add index for performance
    op.create_index('idx_user_logout', 'users', ['last_logout'])

def downgrade() -> None:
    # Remove index first
    op.drop_index('idx_user_logout')
    
    # Remove column
    with op.batch_alter_table('users') as batch_op:
        batch_op.drop_column('last_logout')