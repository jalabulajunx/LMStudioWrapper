"""Create uploaded files table

Revision ID: 003_uploaded_files
Create Date: 2024-02-14 10:02:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = '003_uploaded_files'
down_revision = '002_chat_message_columns'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Create uploaded_files table
    op.create_table(
        'uploaded_files',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('filename', sa.String(), nullable=False),
        sa.Column('content_type', sa.String(), nullable=False),
        sa.Column('size', sa.Integer(), nullable=False),
        sa.Column('file_hash', sa.String(), nullable=False),
        sa.Column('file_data', sa.LargeBinary(), nullable=False),
        sa.Column('uploaded_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('is_active', sa.Boolean(), server_default='1'),
        sa.Column('user_id', sa.String(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('conversation_id', sa.String(), sa.ForeignKey('conversations.id', ondelete='CASCADE'), nullable=False)
    )
    
    # Add indexes for performance
    op.create_index('idx_file_hash', 'uploaded_files', ['file_hash'])
    op.create_index('idx_user_files', 'uploaded_files', ['user_id', 'conversation_id'])

def downgrade() -> None:
    # Drop indexes first
    op.drop_index('idx_file_hash')
    op.drop_index('idx_user_files')
    
    # Drop table
    op.drop_table('uploaded_files')