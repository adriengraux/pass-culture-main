"""Occasion is the only table to reference things and events

Revision ID: e8c43e6dc0d8
Revises: 11d603462200
Create Date: 2018-07-26 11:52:17.853134

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.

revision = 'e8c43e6dc0d8'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('event_occurence', sa.Column('occasionId', sa.BigInteger(), nullable=True))
    op.create_index(op.f('ix_event_occurence_occasionId'), 'event_occurence', ['occasionId'], unique=False)
    op.create_foreign_key('event_occurence_occasionId_fkey', 'event_occurence', 'occasion', ['occasionId'], ['id'])
    op.add_column('mediation', sa.Column('occasionId', sa.BigInteger(), nullable=True))
    op.create_index(op.f('ix_mediation_occasionId'), 'mediation', ['occasionId'], unique=False)
    op.create_foreign_key('mediation_occasionId_fkey', 'mediation', 'occasion', ['occasionId'], ['id'])
    op.add_column('offer', sa.Column('occasionId', sa.BigInteger(), nullable=True))
    op.create_index(op.f('ix_offer_occasionId'), 'offer', ['occasionId'], unique=False)
    op.create_foreign_key('offer_occasionId_fkey', 'offer', 'occasion', ['occasionId'], ['id'])
    op.add_column('recommendation', sa.Column('occasionId', sa.BigInteger(), nullable=True))
    op.create_index(op.f('ix_recommendation_occasionId'), 'recommendation', ['occasionId'], unique=False)
    op.create_foreign_key('recommendation_occasionId_fkey', 'recommendation', 'occasion', ['occasionId'], ['id'])
    op.alter_column('thing', 'type', existing_type=sa.VARCHAR(length=50), nullable=True)

    op.execute('UPDATE offer of SET "occasionId" = (SELECT oc.id FROM occasion oc WHERE of."thingId" = oc."thingId")')

    op.execute(
        'INSERT INTO Occasion("eventId", "venueId", "dateCreated") '
        'SELECT eo."eventId", eo."venueId", now() '
        'FROM event_occurence eo, offer of '
        'WHERE of."eventOccurenceId" = eo.id '
        'AND NOT EXISTS ( '
        '    SELECT 1 '
        '    FROM Occasion o '
        '    WHERE o."eventId" = eo."eventId" '
        '    AND o."venueId" = eo."venueId"'
        ')'
    )

    op.execute(
        'UPDATE event_occurence eo '
        'SET "occasionId" = ('
        '   SELECT o.id'
        '   FROM occasion o'
        '   WHERE eo."eventId" = o."eventId"'
        '   LIMIT 1'
        ')'
    )

    op.alter_column('event_occurence', 'occasionId', existing_type=sa.BigInteger(), nullable=False)
    op.alter_column('thing', 'type', existing_type=sa.VARCHAR(length=50), nullable=False)

    op.drop_index('ix_event_occurence_eventId', table_name='event_occurence')
    op.drop_index('ix_event_occurence_venueId', table_name='event_occurence')
    op.drop_constraint('event_occurence_eventId_fkey', 'event_occurence', type_='foreignkey')
    op.drop_constraint('event_occurence_venueId_fkey', 'event_occurence', type_='foreignkey')
    op.drop_column('event_occurence', 'venueId')
    op.drop_column('event_occurence', 'eventId')
    op.drop_index('ix_mediation_eventId', table_name='mediation')
    op.drop_index('ix_mediation_thingId', table_name='mediation')
    op.drop_constraint('mediation_offererId_fkey', 'mediation', type_='foreignkey')
    op.drop_constraint('mediation_eventId_fkey', 'mediation', type_='foreignkey')
    op.drop_constraint('mediation_thingId_fkey', 'mediation', type_='foreignkey')
    op.drop_column('mediation', 'eventId')
    op.drop_column('mediation', 'offererId')
    op.drop_column('mediation', 'thingId')
    op.drop_index('ix_offer_offererId', table_name='offer')
    op.drop_index('ix_offer_thingId', table_name='offer')
    op.drop_index('ix_offer_venueId', table_name='offer')
    op.drop_constraint('offer_venueId_fkey', 'offer', type_='foreignkey')
    op.drop_constraint('offer_offererId_fkey', 'offer', type_='foreignkey')
    op.drop_constraint('offer_thingId_fkey', 'offer', type_='foreignkey')
    op.drop_column('offer', 'venueId')
    op.drop_column('offer', 'offererId')
    op.drop_column('offer', 'thingId')
    op.drop_index('ix_recommendation_eventId', table_name='recommendation')
    op.drop_index('ix_recommendation_thingId', table_name='recommendation')
    op.drop_constraint('recommendation_thingId_fkey', 'recommendation', type_='foreignkey')
    op.drop_constraint('recommendation_eventId_fkey', 'recommendation', type_='foreignkey')
    op.drop_column('recommendation', 'eventId')
    op.drop_column('recommendation', 'thingId')

    # ### end Alembic commands ###


def downgrade():
    pass
