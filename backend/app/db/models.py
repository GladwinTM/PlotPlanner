"""Database models.

``auth.users`` is owned by Supabase Auth. It is declared here only so foreign
keys can reference it; migrations never create or alter it.

Allowed values for constrained text columns live in the ``*_VALUES`` tuples so
the API schemas, the ORM and the migration's CHECK constraints share one list.
"""
from datetime import date, datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    LargeBinary,
    MetaData,
    Numeric,
    SmallInteger,
    String,
    Table,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, deferred, mapped_column, relationship

NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

FACT_KINDS = ("skill", "education", "experience", "project", "certification", "link", "preference", "constraint", "other")
FACT_SOURCES = ("onboarding", "chat", "document", "manual")
CONVERSATION_KINDS = ("onboarding", "chat")
MESSAGE_ROLES = ("user", "assistant")
INTEREST_TYPES = ("professional", "creative", "personal", "educational", "entrepreneurial")
NODE_KINDS = ("main", "secondary", "skill")
INTEREST_SOURCES = ("onboarding", "manual", "chat", "document", "suggestion")
RELATIONSHIP_TYPES = ("part_of", "related_to", "develops_into", "shares_skills_with", "supports", "overlaps_with")
GOAL_CATEGORIES = ("career", "learning", "health", "creative", "personal", "financial", "community", "other")
GOAL_STATUSES = ("active", "paused", "completed", "abandoned")
MILESTONE_SOURCES = ("ai", "manual")
DIFFICULTIES = ("beginner", "intermediate", "advanced")
COURSE_STATUSES = ("generating", "ready", "failed", "archived")
ACTIVITY_KINDS = ("lesson", "exercise", "project", "reflection", "assessment")
RESOURCE_TYPES = ("video", "documentation", "article", "course", "other")
COST_STATUSES = ("free", "freemium", "paid", "unknown")
VERIFICATION_STATUSES = ("verified", "unverified", "unavailable")
ENROLLMENT_STATUSES = ("active", "paused", "completed", "abandoned")
DOCUMENT_STATUSES = ("processing", "processed", "failed")
OPPORTUNITY_TYPES = (
    "full_time", "part_time", "freelance", "contract", "internship", "commission",
    "digital_product", "service_business", "entrepreneurship", "skill_building",
)
OPPORTUNITY_STATUSES = ("found", "saved", "applied", "interviewing", "offer", "rejected", "archived")
COMPENSATION_BASES = ("employer_provided", "provider_estimate")
FIT_LEVELS = ("ready_now", "stretch", "needs_preparation")
EARNING_PLAN_KINDS = ("side_hustle", "freelance", "digital_product", "service_business", "employment")


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


auth_users = Table(
    "users",
    Base.metadata,
    Column("id", PG_UUID(as_uuid=True), primary_key=True),
    schema="auth",
    info={"managed_externally": True},
)


def _user_fk() -> Mapped[UUID]:
    return mapped_column(ForeignKey("auth.users.id", ondelete="CASCADE"), index=True)


def _created() -> Mapped[datetime]:
    return mapped_column(DateTime(timezone=True), server_default=func.now())


def _id() -> Mapped[UUID]:
    return mapped_column(primary_key=True, default=uuid4, server_default=text("gen_random_uuid()"))


class Profile(Base):
    """One application profile per Supabase Auth user (``user_id`` is the key)."""

    __tablename__ = "profiles"

    user_id: Mapped[UUID] = mapped_column(ForeignKey("auth.users.id", ondelete="CASCADE"), primary_key=True)
    display_name: Mapped[str] = mapped_column(String(120), server_default=text("''"))
    location: Mapped[str | None] = mapped_column(String(200))
    current_occupation: Mapped[str | None] = mapped_column(String(200))
    education_summary: Mapped[str | None] = mapped_column(Text)
    experience_summary: Mapped[str | None] = mapped_column(Text)
    available_hours_per_week: Mapped[int | None] = mapped_column(SmallInteger)
    learning_preferences: Mapped[str | None] = mapped_column(String(1000))
    constraints_summary: Mapped[str | None] = mapped_column(String(2000))
    onboarding_completed: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    created_at: Mapped[datetime] = _created()
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ProfileFact(Base):
    """A typed piece of user information with provenance. Unconfirmed facts
    (e.g. extracted from a resume) are suggestions until the user confirms them."""

    __tablename__ = "profile_facts"

    id: Mapped[UUID] = _id()
    user_id: Mapped[UUID] = _user_fk()
    kind: Mapped[str] = mapped_column(String(20))
    value: Mapped[str] = mapped_column(String(500))
    detail: Mapped[str | None] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(20))
    document_id: Mapped[UUID | None] = mapped_column(ForeignKey("documents.id", ondelete="SET NULL"))
    confirmed: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    created_at: Mapped[datetime] = _created()


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[UUID] = _id()
    user_id: Mapped[UUID] = _user_fk()
    kind: Mapped[str] = mapped_column(String(20))
    title: Mapped[str] = mapped_column(String(200), server_default=text("''"))
    # Onboarding keeps its reviewable draft here until the user finalizes it.
    state: Mapped[dict] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    created_at: Mapped[datetime] = _created()
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    messages: Mapped[list["Message"]] = relationship(
        back_populates="conversation", order_by="Message.created_at", cascade="all, delete-orphan", passive_deletes=True
    )


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[UUID] = _id()
    conversation_id: Mapped[UUID] = mapped_column(ForeignKey("conversations.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[UUID] = _user_fk()
    role: Mapped[str] = mapped_column(String(20))
    content: Mapped[str] = mapped_column(Text)
    meta: Mapped[dict] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.clock_timestamp())

    conversation: Mapped[Conversation] = relationship(back_populates="messages")


class Interest(Base):
    __tablename__ = "interests"

    id: Mapped[UUID] = _id()
    user_id: Mapped[UUID] = _user_fk()
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str | None] = mapped_column(Text)
    category: Mapped[str | None] = mapped_column(String(80))
    interest_type: Mapped[str] = mapped_column(String(20))
    node_kind: Mapped[str] = mapped_column(String(20), server_default=text("'secondary'"))
    priority: Mapped[int] = mapped_column(SmallInteger, server_default=text("3"))
    source: Mapped[str] = mapped_column(String(20))
    confidence: Mapped[float | None] = mapped_column(Float)
    seeks_income: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    position_x: Mapped[float | None] = mapped_column(Float)
    position_y: Mapped[float | None] = mapped_column(Float)
    created_at: Mapped[datetime] = _created()
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class InterestRelationship(Base):
    __tablename__ = "interest_relationships"
    __table_args__ = (
        ForeignKeyConstraint(
            ["user_id", "source_interest_id"], ["interests.user_id", "interests.id"], ondelete="CASCADE",
            name="fk_interest_relationships_source_owned",
        ),
        ForeignKeyConstraint(
            ["user_id", "target_interest_id"], ["interests.user_id", "interests.id"], ondelete="CASCADE",
            name="fk_interest_relationships_target_owned",
        ),
    )

    id: Mapped[UUID] = _id()
    user_id: Mapped[UUID] = _user_fk()
    source_interest_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True))
    target_interest_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True))
    relationship_type: Mapped[str] = mapped_column(String(30))
    created_at: Mapped[datetime] = _created()


class Goal(Base):
    __tablename__ = "goals"

    id: Mapped[UUID] = _id()
    user_id: Mapped[UUID] = _user_fk()
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(20))
    target_outcome: Mapped[str | None] = mapped_column(Text)
    priority: Mapped[int] = mapped_column(SmallInteger, server_default=text("3"))
    status: Mapped[str] = mapped_column(String(20), server_default=text("'active'"))
    target_date: Mapped[date | None] = mapped_column(Date)
    hours_per_week: Mapped[int | None] = mapped_column(SmallInteger)
    interest_id: Mapped[UUID | None] = mapped_column(ForeignKey("interests.id", ondelete="SET NULL"))
    plan_summary: Mapped[str | None] = mapped_column(Text)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = _created()
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    milestones: Mapped[list["GoalMilestone"]] = relationship(
        order_by="GoalMilestone.position", cascade="all, delete-orphan", passive_deletes=True
    )
    checkins: Mapped[list["GoalCheckin"]] = relationship(
        order_by="GoalCheckin.created_at.desc()", cascade="all, delete-orphan", passive_deletes=True
    )


class GoalMilestone(Base):
    __tablename__ = "goal_milestones"

    id: Mapped[UUID] = _id()
    goal_id: Mapped[UUID] = mapped_column(ForeignKey("goals.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[UUID] = _user_fk()
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)
    position: Mapped[int] = mapped_column(Integer)
    due_date: Mapped[date | None] = mapped_column(Date)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    source: Mapped[str] = mapped_column(String(10))
    created_at: Mapped[datetime] = _created()


class GoalCheckin(Base):
    __tablename__ = "goal_checkins"

    id: Mapped[UUID] = _id()
    goal_id: Mapped[UUID] = mapped_column(ForeignKey("goals.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[UUID] = _user_fk()
    note: Mapped[str | None] = mapped_column(Text)
    minutes: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = _created()


class Course(Base):
    __tablename__ = "courses"

    id: Mapped[UUID] = _id()
    user_id: Mapped[UUID] = _user_fk()
    interest_id: Mapped[UUID | None] = mapped_column(ForeignKey("interests.id", ondelete="SET NULL"), index=True)
    goal_id: Mapped[UUID | None] = mapped_column(ForeignKey("goals.id", ondelete="SET NULL"))
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)
    objective: Mapped[str | None] = mapped_column(Text)
    difficulty: Mapped[str] = mapped_column(String(20), server_default=text("'beginner'"))
    estimated_hours: Mapped[int | None] = mapped_column(Integer)
    prerequisites: Mapped[str | None] = mapped_column(Text)
    focus: Mapped[str | None] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(20))
    error: Mapped[str | None] = mapped_column(Text)
    version: Mapped[int] = mapped_column(Integer, server_default=text("1"))
    previous_version_id: Mapped[UUID | None] = mapped_column(ForeignKey("courses.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = _created()
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    modules: Mapped[list["CourseModule"]] = relationship(
        order_by="CourseModule.position", cascade="all, delete-orphan", passive_deletes=True
    )


class CourseModule(Base):
    __tablename__ = "course_modules"

    id: Mapped[UUID] = _id()
    course_id: Mapped[UUID] = mapped_column(ForeignKey("courses.id", ondelete="CASCADE"), index=True)
    position: Mapped[int] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)
    learning_objectives: Mapped[str | None] = mapped_column(Text)
    completion_criteria: Mapped[str | None] = mapped_column(Text)
    required: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))
    resource_queries: Mapped[list] = mapped_column(JSONB, server_default=text("'[]'::jsonb"))

    activities: Mapped[list["CourseActivity"]] = relationship(
        order_by="CourseActivity.position", cascade="all, delete-orphan", passive_deletes=True
    )
    resources: Mapped[list["LearningResource"]] = relationship(
        order_by="LearningResource.retrieved_at", cascade="all, delete-orphan", passive_deletes=True
    )


class CourseActivity(Base):
    __tablename__ = "course_activities"

    id: Mapped[UUID] = _id()
    module_id: Mapped[UUID] = mapped_column(ForeignKey("course_modules.id", ondelete="CASCADE"), index=True)
    position: Mapped[int] = mapped_column(Integer)
    kind: Mapped[str] = mapped_column(String(20))
    title: Mapped[str] = mapped_column(String(200))
    instructions: Mapped[str | None] = mapped_column(Text)
    estimated_minutes: Mapped[int | None] = mapped_column(Integer)


class LearningResource(Base):
    __tablename__ = "learning_resources"

    id: Mapped[UUID] = _id()
    module_id: Mapped[UUID] = mapped_column(ForeignKey("course_modules.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(300))
    provider: Mapped[str] = mapped_column(String(80))
    channel: Mapped[str | None] = mapped_column(String(200))
    canonical_url: Mapped[str] = mapped_column(String(500))
    resource_type: Mapped[str] = mapped_column(String(20))
    cost_status: Mapped[str] = mapped_column(String(20))
    duration_seconds: Mapped[int | None] = mapped_column(Integer)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    verification_status: Mapped[str] = mapped_column(String(20))
    external_id: Mapped[str | None] = mapped_column(String(100))


class Enrollment(Base):
    __tablename__ = "enrollments"

    id: Mapped[UUID] = _id()
    user_id: Mapped[UUID] = _user_fk()
    course_id: Mapped[UUID] = mapped_column(ForeignKey("courses.id", ondelete="CASCADE"))
    status: Mapped[str] = mapped_column(String(20), server_default=text("'active'"))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = _created()


class ActivityCompletion(Base):
    """One row per user per completed activity. Kept independently of the
    enrollment so leaving and re-joining a course preserves history."""

    __tablename__ = "activity_completions"

    id: Mapped[UUID] = _id()
    user_id: Mapped[UUID] = _user_fk()
    activity_id: Mapped[UUID] = mapped_column(ForeignKey("course_activities.id", ondelete="CASCADE"), index=True)
    notes: Mapped[str | None] = mapped_column(Text)
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Document(Base):
    """Uploaded files are stored privately in Postgres (bytea) and never served publicly."""

    __tablename__ = "documents"

    id: Mapped[UUID] = _id()
    user_id: Mapped[UUID] = _user_fk()
    filename: Mapped[str] = mapped_column(String(255))
    content_type: Mapped[str] = mapped_column(String(100))
    size_bytes: Mapped[int] = mapped_column(Integer)
    content: Mapped[bytes] = deferred(mapped_column(LargeBinary))
    extracted_text: Mapped[str | None] = deferred(mapped_column(Text))
    processing_status: Mapped[str] = mapped_column(String(20))
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = _created()
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Opportunity(Base):
    """A listing retrieved from a job provider, kept with its source URL and
    retrieval time. ``status='found'`` rows are transient search results."""

    __tablename__ = "opportunities"

    id: Mapped[UUID] = _id()
    user_id: Mapped[UUID] = _user_fk()
    opportunity_type: Mapped[str] = mapped_column(String(30))
    title: Mapped[str] = mapped_column(String(300))
    company: Mapped[str | None] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(40))
    canonical_url: Mapped[str] = mapped_column(String(1000))
    location: Mapped[str | None] = mapped_column(String(300))
    employment_type: Mapped[str | None] = mapped_column(String(80))
    compensation_min: Mapped[float | None] = mapped_column(Numeric(12, 2))
    compensation_max: Mapped[float | None] = mapped_column(Numeric(12, 2))
    currency: Mapped[str | None] = mapped_column(String(10))
    compensation_text: Mapped[str | None] = mapped_column(String(200))
    compensation_basis: Mapped[str | None] = mapped_column(String(30))
    requirements: Mapped[str | None] = mapped_column(Text)
    external_id: Mapped[str] = mapped_column(String(200))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    closing_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    fit_level: Mapped[str | None] = mapped_column(String(30))
    fit_reason: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), server_default=text("'found'"))
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = _created()
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class EarningPlan(Base):
    __tablename__ = "earning_plans"

    id: Mapped[UUID] = _id()
    user_id: Mapped[UUID] = _user_fk()
    interest_id: Mapped[UUID | None] = mapped_column(ForeignKey("interests.id", ondelete="SET NULL"))
    title: Mapped[str] = mapped_column(String(200))
    kind: Mapped[str] = mapped_column(String(30))
    plan: Mapped[dict] = mapped_column(JSONB)
    created_at: Mapped[datetime] = _created()
