"""Add beneficiary_fraud_check.idPicturesStored"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "60b61de718ac"
down_revision = "f6efe8c78450"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("beneficiary_fraud_check", sa.Column("idPicturesStored", sa.Boolean(), nullable=True))


def downgrade():
    op.drop_column("beneficiary_fraud_check", "idPicturesStored")
