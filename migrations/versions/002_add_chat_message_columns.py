"""Add chat message enhancement columns

Revision ID: 002_chat_message_columns
Create Date: 2024-02-14 10:01:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = '002_chat_message_columns'
down_revision = '001_add_user_logout'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Add new columns to chat_messages
    with op.batch_alter_table('chat_messages') as batch_op:
        batch_op.add_column(sa.Column('token_count', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('generation_time', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('model_used', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('is_complete', sa.Boolean(), server_default='1'))

def downgrade() -> None:
    # Remove columns in reverse order
    with op.batch_alter_table('chat_messages') as batch_op:
        batch_op.drop_column('is_complete')
        batch_op.drop_column('model_used')
        batch_op.drop_column('generation_time')
        batch_op.drop_column('token_count')