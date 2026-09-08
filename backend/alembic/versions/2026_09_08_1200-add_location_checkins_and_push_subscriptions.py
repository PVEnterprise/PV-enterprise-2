"""add location_checkins and push_subscriptions tables

Revision ID: c6d6905a2efa
Revises: b8c9d0e1f2a3
Create Date: 2026-09-08 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'c6d6905a2efa'
down_revision = 'b8c9d0e1f2a3'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'location_checkins',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('slot', sa.String(20), nullable=False),
        sa.Column('recorded_at', sa.DateTime(), nullable=False),
        sa.Column('latitude', sa.Float(), nullable=False),
        sa.Column('longitude', sa.Float(), nullable=False),
        sa.Column('accuracy', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('updated_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.ForeignKeyConstraint(['created_by'], ['users.id']),
        sa.ForeignKeyConstraint(['updated_by'], ['users.id']),
    )
    op.create_index('ix_location_checkins_user_id', 'location_checkins', ['user_id'])
    op.create_index('ix_location_checkins_slot', 'location_checkins', ['slot'])
    op.create_index('ix_location_checkins_recorded_at', 'location_checkins', ['recorded_at'])
    op.create_index('ix_location_checkins_created_by', 'location_checkins', ['created_by'])
    op.create_index('ix_location_checkins_updated_by', 'location_checkins', ['updated_by'])

    op.create_table(
        'push_subscriptions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('endpoint', sa.String(1000), nullable=False),
        sa.Column('p256dh_key', sa.String(255), nullable=False),
        sa.Column('auth_key', sa.String(255), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('updated_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.ForeignKeyConstraint(['created_by'], ['users.id']),
        sa.ForeignKeyConstraint(['updated_by'], ['users.id']),
    )
    op.create_index('ix_push_subscriptions_user_id', 'push_subscriptions', ['user_id'])
    op.create_index('ix_push_subscriptions_endpoint', 'push_subscriptions', ['endpoint'], unique=True)
    op.create_index('ix_push_subscriptions_created_by', 'push_subscriptions', ['created_by'])
    op.create_index('ix_push_subscriptions_updated_by', 'push_subscriptions', ['updated_by'])


def downgrade() -> None:
    op.drop_index('ix_push_subscriptions_updated_by', table_name='push_subscriptions')
    op.drop_index('ix_push_subscriptions_created_by', table_name='push_subscriptions')
    op.drop_index('ix_push_subscriptions_endpoint', table_name='push_subscriptions')
    op.drop_index('ix_push_subscriptions_user_id', table_name='push_subscriptions')
    op.drop_table('push_subscriptions')

    op.drop_index('ix_location_checkins_updated_by', table_name='location_checkins')
    op.drop_index('ix_location_checkins_created_by', table_name='location_checkins')
    op.drop_index('ix_location_checkins_recorded_at', table_name='location_checkins')
    op.drop_index('ix_location_checkins_slot', table_name='location_checkins')
    op.drop_index('ix_location_checkins_user_id', table_name='location_checkins')
    op.drop_table('location_checkins')
