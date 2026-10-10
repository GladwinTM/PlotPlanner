"""profiles

Revision ID: 0001
Revises:
Create Date: 2026-10-11

Creates the application profile, keyed by the Supabase Auth user id, with Row
Level Security. The backend connects with the table owner and enforces
ownership in code; the policies protect the same rows from direct access through
Supabase's Data API using the publishable key.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "profiles",
        sa.Column("user_id", UUID(as_uuid=True), nullable=False),
        sa.Column("display_name", sa.String(120), server_default=sa.text("''"), nullable=False),
        sa.Column("location", sa.String(200), nullable=True),
        sa.Column("current_occupation", sa.String(200), nullable=True),
        sa.Column("education_summary", sa.Text(), nullable=True),
        sa.Column("experience_summary", sa.Text(), nullable=True),
        sa.Column("onboarding_completed", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"], ["auth.users.id"], name="fk_profiles_user_id_users", ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("user_id", name="pk_profiles"),
        schema="public",
    )

    op.execute("alter table public.profiles enable row level security")
    op.execute("revoke all on table public.profiles from anon")
    op.execute(
        """
        create policy profiles_select_own on public.profiles
          for select to authenticated
          using ((select auth.uid()) = user_id)
        """
    )
    op.execute(
        """
        create policy profiles_insert_own on public.profiles
          for insert to authenticated
          with check ((select auth.uid()) = user_id)
        """
    )
    op.execute(
        """
        create policy profiles_update_own on public.profiles
          for update to authenticated
          using ((select auth.uid()) = user_id)
          with check ((select auth.uid()) = user_id)
        """
    )
    op.execute(
        """
        create policy profiles_delete_own on public.profiles
          for delete to authenticated
          using ((select auth.uid()) = user_id)
        """
    )


def downgrade() -> None:
    # Dropping the table deletes profile rows. Run only on disposable databases
    # or after taking a backup.
    op.drop_table("profiles", schema="public")
