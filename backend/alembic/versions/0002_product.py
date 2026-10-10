"""Product schema: facts, conversations, interest graph, goals, courses,
progress, documents, opportunities and earning plans.

Additive only: existing ``profiles`` rows are preserved (three nullable columns
are added). Every table has RLS enabled with own-row policies for the
``authenticated`` role and no access for ``anon``.

Revision ID: 0002
Revises: 0001
"""
from collections.abc import Sequence

from alembic import op

from app.db import models as m

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _check(column: str, values: tuple[str, ...]) -> str:
    quoted = ", ".join(f"'{v}'" for v in values)
    return f"check ({column} in ({quoted}))"


USER_FK = "user_id uuid not null references auth.users (id) on delete cascade"

TABLES: list[tuple[str, str]] = [
    ("documents", f"""
        id uuid primary key default gen_random_uuid(),
        {USER_FK},
        filename varchar(255) not null,
        content_type varchar(100) not null,
        size_bytes integer not null check (size_bytes >= 0),
        content bytea not null,
        extracted_text text,
        processing_status varchar(20) not null {_check('processing_status', m.DOCUMENT_STATUSES)},
        error text,
        created_at timestamptz not null default now(),
        processed_at timestamptz,
        search_vector tsvector generated always as (to_tsvector('english', coalesce(extracted_text, ''))) stored
    """),
    ("profile_facts", f"""
        id uuid primary key default gen_random_uuid(),
        {USER_FK},
        kind varchar(20) not null {_check('kind', m.FACT_KINDS)},
        value varchar(500) not null check (length(btrim(value)) > 0),
        detail text,
        source varchar(20) not null {_check('source', m.FACT_SOURCES)},
        document_id uuid references public.documents (id) on delete set null,
        confirmed boolean not null default false,
        created_at timestamptz not null default now()
    """),
    ("conversations", f"""
        id uuid primary key default gen_random_uuid(),
        {USER_FK},
        kind varchar(20) not null {_check('kind', m.CONVERSATION_KINDS)},
        title varchar(200) not null default '',
        state jsonb not null default '{{}}'::jsonb,
        created_at timestamptz not null default now(),
        updated_at timestamptz not null default now()
    """),
    ("messages", f"""
        id uuid primary key default gen_random_uuid(),
        conversation_id uuid not null references public.conversations (id) on delete cascade,
        {USER_FK},
        role varchar(20) not null {_check('role', m.MESSAGE_ROLES)},
        content text not null,
        meta jsonb not null default '{{}}'::jsonb,
        created_at timestamptz not null default clock_timestamp()
    """),
    ("interests", f"""
        id uuid primary key default gen_random_uuid(),
        {USER_FK},
        name varchar(120) not null check (length(btrim(name)) > 0),
        description text,
        category varchar(80),
        interest_type varchar(20) not null {_check('interest_type', m.INTEREST_TYPES)},
        node_kind varchar(20) not null default 'secondary' {_check('node_kind', m.NODE_KINDS)},
        priority smallint not null default 3 check (priority between 1 and 5),
        source varchar(20) not null {_check('source', m.INTEREST_SOURCES)},
        confidence double precision check (confidence between 0 and 1),
        seeks_income boolean not null default false,
        position_x double precision,
        position_y double precision,
        created_at timestamptz not null default now(),
        updated_at timestamptz not null default now(),
        constraint uq_interests_user_id_id unique (user_id, id)
    """),
    ("interest_relationships", f"""
        id uuid primary key default gen_random_uuid(),
        {USER_FK},
        source_interest_id uuid not null,
        target_interest_id uuid not null,
        relationship_type varchar(30) not null {_check('relationship_type', m.RELATIONSHIP_TYPES)},
        created_at timestamptz not null default now(),
        constraint fk_interest_relationships_source_owned foreign key (user_id, source_interest_id)
            references public.interests (user_id, id) on delete cascade,
        constraint fk_interest_relationships_target_owned foreign key (user_id, target_interest_id)
            references public.interests (user_id, id) on delete cascade,
        constraint ck_interest_relationships_distinct check (source_interest_id <> target_interest_id)
    """),
    ("goals", f"""
        id uuid primary key default gen_random_uuid(),
        {USER_FK},
        title varchar(200) not null check (length(btrim(title)) > 0),
        description text,
        category varchar(20) not null {_check('category', m.GOAL_CATEGORIES)},
        target_outcome text,
        priority smallint not null default 3 check (priority between 1 and 5),
        status varchar(20) not null default 'active' {_check('status', m.GOAL_STATUSES)},
        target_date date,
        hours_per_week smallint check (hours_per_week between 0 and 168),
        interest_id uuid references public.interests (id) on delete set null,
        plan_summary text,
        completed_at timestamptz,
        created_at timestamptz not null default now(),
        updated_at timestamptz not null default now()
    """),
    ("goal_milestones", f"""
        id uuid primary key default gen_random_uuid(),
        goal_id uuid not null references public.goals (id) on delete cascade,
        {USER_FK},
        title varchar(200) not null,
        description text,
        position integer not null,
        due_date date,
        completed_at timestamptz,
        source varchar(10) not null {_check('source', m.MILESTONE_SOURCES)},
        created_at timestamptz not null default now()
    """),
    ("goal_checkins", f"""
        id uuid primary key default gen_random_uuid(),
        goal_id uuid not null references public.goals (id) on delete cascade,
        {USER_FK},
        note text,
        minutes integer check (minutes between 0 and 1440),
        created_at timestamptz not null default now()
    """),
    ("courses", f"""
        id uuid primary key default gen_random_uuid(),
        {USER_FK},
        interest_id uuid references public.interests (id) on delete set null,
        goal_id uuid references public.goals (id) on delete set null,
        title varchar(200) not null,
        description text,
        objective text,
        difficulty varchar(20) not null default 'beginner' {_check('difficulty', m.DIFFICULTIES)},
        estimated_hours integer check (estimated_hours >= 0),
        prerequisites text,
        focus varchar(500),
        status varchar(20) not null {_check('status', m.COURSE_STATUSES)},
        error text,
        version integer not null default 1,
        previous_version_id uuid references public.courses (id) on delete set null,
        created_at timestamptz not null default now(),
        updated_at timestamptz not null default now()
    """),
    ("course_modules", f"""
        id uuid primary key default gen_random_uuid(),
        course_id uuid not null references public.courses (id) on delete cascade,
        position integer not null,
        title varchar(200) not null,
        description text,
        learning_objectives text,
        completion_criteria text,
        required boolean not null default true,
        resource_queries jsonb not null default '[]'::jsonb
    """),
    ("course_activities", f"""
        id uuid primary key default gen_random_uuid(),
        module_id uuid not null references public.course_modules (id) on delete cascade,
        position integer not null,
        kind varchar(20) not null {_check('kind', m.ACTIVITY_KINDS)},
        title varchar(200) not null,
        instructions text,
        estimated_minutes integer check (estimated_minutes >= 0)
    """),
    ("learning_resources", f"""
        id uuid primary key default gen_random_uuid(),
        module_id uuid not null references public.course_modules (id) on delete cascade,
        title varchar(300) not null,
        provider varchar(80) not null,
        channel varchar(200),
        canonical_url varchar(500) not null check (canonical_url like 'https://%'),
        resource_type varchar(20) not null {_check('resource_type', m.RESOURCE_TYPES)},
        cost_status varchar(20) not null {_check('cost_status', m.COST_STATUSES)},
        duration_seconds integer,
        published_at timestamptz,
        retrieved_at timestamptz not null,
        verification_status varchar(20) not null {_check('verification_status', m.VERIFICATION_STATUSES)},
        external_id varchar(100),
        constraint uq_learning_resources_module_url unique (module_id, canonical_url)
    """),
    ("enrollments", f"""
        id uuid primary key default gen_random_uuid(),
        {USER_FK},
        course_id uuid not null references public.courses (id) on delete cascade,
        status varchar(20) not null default 'active' {_check('status', m.ENROLLMENT_STATUSES)},
        started_at timestamptz not null default now(),
        completed_at timestamptz,
        created_at timestamptz not null default now(),
        constraint uq_enrollments_user_course unique (user_id, course_id)
    """),
    ("activity_completions", f"""
        id uuid primary key default gen_random_uuid(),
        {USER_FK},
        activity_id uuid not null references public.course_activities (id) on delete cascade,
        notes text,
        completed_at timestamptz not null default now(),
        constraint uq_activity_completions_user_activity unique (user_id, activity_id)
    """),
    ("opportunities", f"""
        id uuid primary key default gen_random_uuid(),
        {USER_FK},
        opportunity_type varchar(30) not null {_check('opportunity_type', m.OPPORTUNITY_TYPES)},
        title varchar(300) not null,
        company varchar(200),
        description text,
        source varchar(40) not null,
        canonical_url varchar(1000) not null check (canonical_url like 'https://%'),
        location varchar(300),
        employment_type varchar(80),
        compensation_min numeric(12, 2),
        compensation_max numeric(12, 2),
        currency varchar(10),
        compensation_text varchar(200),
        compensation_basis varchar(30) check (compensation_basis is null or compensation_basis in ('employer_provided', 'provider_estimate')),
        requirements text,
        external_id varchar(200) not null,
        published_at timestamptz,
        closing_at timestamptz,
        retrieved_at timestamptz not null,
        fit_level varchar(30) check (fit_level is null or fit_level in ('ready_now', 'stretch', 'needs_preparation')),
        fit_reason text,
        status varchar(20) not null default 'found' {_check('status', m.OPPORTUNITY_STATUSES)},
        notes text,
        created_at timestamptz not null default now(),
        updated_at timestamptz not null default now(),
        constraint uq_opportunities_user_source_external unique (user_id, source, external_id)
    """),
    ("earning_plans", f"""
        id uuid primary key default gen_random_uuid(),
        {USER_FK},
        interest_id uuid references public.interests (id) on delete set null,
        title varchar(200) not null,
        kind varchar(30) not null {_check('kind', m.EARNING_PLAN_KINDS)},
        plan jsonb not null,
        created_at timestamptz not null default now()
    """),
]

# Child tables without a user_id column are owned through their parent.
PARENT_OWNERSHIP = {
    "course_modules": "exists (select 1 from public.courses c where c.id = course_id and c.user_id = (select auth.uid()))",
    "course_activities": (
        "exists (select 1 from public.course_modules cm join public.courses c on c.id = cm.course_id "
        "where cm.id = module_id and c.user_id = (select auth.uid()))"
    ),
    "learning_resources": (
        "exists (select 1 from public.course_modules cm join public.courses c on c.id = cm.course_id "
        "where cm.id = module_id and c.user_id = (select auth.uid()))"
    ),
}

INDEXES = [
    "create index ix_documents_search_vector on public.documents using gin (search_vector)",
    "create index ix_documents_user_id on public.documents (user_id)",
    "create index ix_profile_facts_user_id on public.profile_facts (user_id)",
    "create index ix_profile_facts_document_id on public.profile_facts (document_id)",
    "create index ix_conversations_user_id on public.conversations (user_id)",
    "create unique index uq_conversations_one_onboarding on public.conversations (user_id) where kind = 'onboarding'",
    "create index ix_messages_conversation_created on public.messages (conversation_id, created_at)",
    "create index ix_messages_user_id on public.messages (user_id)",
    "create index ix_interests_user_id on public.interests (user_id)",
    "create unique index uq_interests_user_lower_name on public.interests (user_id, lower(name))",
    "create index ix_interest_relationships_user_id on public.interest_relationships (user_id)",
    "create index ix_interest_relationships_source on public.interest_relationships (user_id, source_interest_id)",
    "create index ix_interest_relationships_target on public.interest_relationships (user_id, target_interest_id)",
    (
        "create unique index uq_interest_relationships_pair on public.interest_relationships "
        "(user_id, least(source_interest_id, target_interest_id), greatest(source_interest_id, target_interest_id), relationship_type)"
    ),
    "create index ix_goals_user_id on public.goals (user_id)",
    "create index ix_goals_interest_id on public.goals (interest_id)",
    "create index ix_goal_milestones_goal_id on public.goal_milestones (goal_id)",
    "create index ix_goal_milestones_user_id on public.goal_milestones (user_id)",
    "create index ix_goal_checkins_goal_id on public.goal_checkins (goal_id)",
    "create index ix_goal_checkins_user_id on public.goal_checkins (user_id)",
    "create index ix_courses_user_id on public.courses (user_id)",
    "create index ix_courses_interest_id on public.courses (interest_id)",
    "create index ix_courses_goal_id on public.courses (goal_id)",
    "create index ix_courses_previous_version_id on public.courses (previous_version_id)",
    "create index ix_course_modules_course_id on public.course_modules (course_id)",
    "create index ix_course_activities_module_id on public.course_activities (module_id)",
    "create index ix_learning_resources_module_id on public.learning_resources (module_id)",
    "create index ix_enrollments_user_id on public.enrollments (user_id)",
    "create index ix_enrollments_course_id on public.enrollments (course_id)",
    "create index ix_activity_completions_user_id on public.activity_completions (user_id)",
    "create index ix_activity_completions_activity_id on public.activity_completions (activity_id)",
    "create index ix_opportunities_user_status on public.opportunities (user_id, status)",
    "create index ix_earning_plans_user_id on public.earning_plans (user_id)",
    "create index ix_earning_plans_interest_id on public.earning_plans (interest_id)",
]


def _policies(table: str) -> list[str]:
    owned = PARENT_OWNERSHIP.get(table, "(select auth.uid()) = user_id")
    return [
        f"create policy {table}_select_own on public.{table} for select to authenticated using ({owned})",
        f"create policy {table}_insert_own on public.{table} for insert to authenticated with check ({owned})",
        f"create policy {table}_update_own on public.{table} for update to authenticated using ({owned}) with check ({owned})",
        f"create policy {table}_delete_own on public.{table} for delete to authenticated using ({owned})",
    ]


def upgrade() -> None:
    op.execute("alter table public.profiles add column available_hours_per_week smallint check (available_hours_per_week between 0 and 168)")
    op.execute("alter table public.profiles add column learning_preferences varchar(1000)")
    op.execute("alter table public.profiles add column constraints_summary varchar(2000)")

    for table, columns in TABLES:
        op.execute(f"create table public.{table} ({columns})")
        op.execute(f"alter table public.{table} enable row level security")
        op.execute(f"revoke all on table public.{table} from anon")
        for statement in _policies(table):
            op.execute(statement)
    for statement in INDEXES:
        op.execute(statement)


def downgrade() -> None:
    for table, _ in reversed(TABLES):
        op.execute(f"drop table if exists public.{table}")
    op.execute("alter table public.profiles drop column if exists constraints_summary")
    op.execute("alter table public.profiles drop column if exists learning_preferences")
    op.execute("alter table public.profiles drop column if exists available_hours_per_week")
