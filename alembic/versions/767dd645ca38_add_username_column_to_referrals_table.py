"""Add username column to referrals table

Revision ID: 767dd645ca38
Revises: 
Create Date: 2024-08-19 13:33:43.133128

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '767dd645ca38'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.add_column('referrals', sa.Column('username', sa.String(), nullable=True))

def downgrade():
    op.drop_column('referrals', 'username')