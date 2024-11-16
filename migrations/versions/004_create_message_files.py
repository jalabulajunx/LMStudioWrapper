"""Create message files association table

Revision ID: 004_message_files
Create Date: 2024-02-14 10:03:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = '004_message_files'
down_revision = '003_uploaded_files'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Create message_files association table
    op.create_table(
        'message_files',
        sa.Column('message_id', sa.Integer(), sa.ForeignKey('chat_messages.id', ondelete='CASCADE')),
        sa.Column('file_id', sa.String(), sa.ForeignKey('uploaded_files.id', ondelete='CASCADE'))
    )
    
    # Add index for performance
    op.create_index('idx_message_files', 'message_files', ['message_id', 'file_id'])
    
    # Add attached_files JSON column to chat_messages
    with op.batch_alter_table('chat_messages') as batch_op:
        batch_op.add_column(sa.Column('attached_files', sa.Text(), nullable=True))

def downgrade() -> None:
    # Drop attached_files column from chat_messages
    with op.batch_alter_table('chat_messages') as batch_op:
        batch_op.drop_column('attached_files')
    
    # Drop index
    op.drop_index('idx_message_files')
    
    # Drop table
    op.drop_table('message_files')