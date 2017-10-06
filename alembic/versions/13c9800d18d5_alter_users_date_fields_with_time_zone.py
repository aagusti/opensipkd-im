"""alter users date fields with time zone

Revision ID: 13c9800d18d5
Revises: 
Create Date: 2017-10-07 03:44:28.189216

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '13c9800d18d5'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column('users', 'last_login_date',
        type_=sa.DateTime(timezone=True),
        existing_type=sa.DateTime(timezone=False))
    op.alter_column('users', 'registered_date',
        type_=sa.DateTime(timezone=True),
        existing_type=sa.DateTime(timezone=False))

def downgrade():
    pass
