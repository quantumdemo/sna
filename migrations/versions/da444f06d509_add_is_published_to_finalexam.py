"""Add is_published to FinalExam

Revision ID: da444f06d509
Revises: fb48a7f7b472
Create Date: 2025-08-21 09:46:11.950051

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'da444f06d509'
down_revision = 'fb48a7f7b472'
branch_labels = None
depends_on = None


def upgrade():
    """
    Add the is_published column to the final_exam table.
    """
    with op.batch_alter_table('final_exam', schema=None) as batch_op:
        batch_op.add_column(sa.Column('is_published', sa.Boolean(), nullable=True, server_default=sa.false()))


def downgrade():
    """
    Remove the is_published column from the final_exam table.
    """
    with op.batch_alter_table('final_exam', schema=None) as batch_op:
        batch_op.drop_column('is_published')
