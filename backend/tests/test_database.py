"""Schema, migration and Row Level Security checks against the real migration."""
import uuid

import pytest
from alembic import command
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from tests.conftest import alembic_config


def _scalar(db, sql: str, **params):
    return db.execute(text(sql), params).scalar_one()


def test_profiles_table_has_rls_enabled(db):
    assert _scalar(db, "select relrowsecurity from pg_class where oid = 'public.profiles'::regclass") is True


def test_alembic_bookkeeping_is_not_in_the_public_schema(db):
    in_public = _scalar(db, "select count(*) from pg_tables where schemaname = 'public' and tablename = 'alembic_version'")
    private = _scalar(db, "select count(*) from pg_tables where schemaname = 'app_private' and tablename = 'alembic_version'")
    assert (in_public, private) == (0, 1)


def test_user_id_must_reference_an_auth_user(db):
    with pytest.raises(DBAPIError):
        db.execute(text("insert into public.profiles (user_id) values (:id)"), {"id": uuid.uuid4()})


def _seed_two_profiles(db, create_user):
    alice, bob = create_user("a@example.com"), create_user("b@example.com")
    for user_id, name in ((alice, "alice"), (bob, "bob")):
        db.execute(text("insert into public.profiles (user_id, display_name) values (:id, :n)"), {"id": user_id, "n": name})
    return alice, bob


def _as_authenticated(db, user_id):
    tx = db.begin()
    db.execute(text("set local role authenticated"))
    db.execute(text("select set_config('request.jwt.claim.sub', :sub, true)"), {"sub": str(user_id)})
    return tx


def test_rls_limits_data_api_reads_to_own_row(db_engine, create_user):
    with db_engine.connect() as admin:
        alice, bob = _seed_two_profiles(admin, create_user)
    with db_engine.connect().execution_options(isolation_level="READ COMMITTED") as db:
        with _as_authenticated(db, alice):
            names = db.execute(text("select display_name from public.profiles")).scalars().all()
    assert names == ["alice"]


def test_rls_blocks_updating_and_deleting_another_users_row(db_engine, create_user):
    with db_engine.connect() as admin:
        alice, bob = _seed_two_profiles(admin, create_user)
    with db_engine.connect().execution_options(isolation_level="READ COMMITTED") as db:
        with _as_authenticated(db, alice):
            updated = db.execute(text("update public.profiles set display_name = 'hacked' where user_id = :id"), {"id": bob})
            deleted = db.execute(text("delete from public.profiles where user_id = :id"), {"id": bob})
            assert (updated.rowcount, deleted.rowcount) == (0, 0)
    with db_engine.connect() as admin:
        assert _scalar(admin, "select display_name from public.profiles where user_id = :id", id=bob) == "bob"


def test_rls_blocks_inserting_a_profile_for_someone_else(db_engine, create_user):
    alice, bob = create_user(), create_user()
    with db_engine.connect().execution_options(isolation_level="READ COMMITTED") as db:
        with pytest.raises(DBAPIError):
            with _as_authenticated(db, alice):
                db.execute(text("insert into public.profiles (user_id) values (:id)"), {"id": bob})


def test_rls_blocks_reassigning_a_row_to_another_user(db_engine, create_user):
    with db_engine.connect() as admin:
        alice, bob = _seed_two_profiles(admin, create_user)
    carol = create_user()
    with db_engine.connect().execution_options(isolation_level="READ COMMITTED") as db:
        with pytest.raises(DBAPIError):
            with _as_authenticated(db, alice):
                db.execute(text("update public.profiles set user_id = :c where user_id = :a"), {"c": carol, "a": alice})


def test_anonymous_role_has_no_access(db_engine):
    with db_engine.connect().execution_options(isolation_level="READ COMMITTED") as db:
        with pytest.raises(DBAPIError):
            with db.begin():
                db.execute(text("set local role anon"))
                db.execute(text("select * from public.profiles"))


def test_migration_downgrade_and_upgrade_roundtrip(db_engine):
    command.downgrade(alembic_config(), "base")
    assert _scalar(db_engine.connect(), "select to_regclass('public.profiles') is null")
    command.upgrade(alembic_config(), "head")
    assert _scalar(db_engine.connect(), "select to_regclass('public.profiles') is not null")


def test_every_public_table_has_rls_and_no_anon_access(db):
    tables = db.execute(text("select tablename from pg_tables where schemaname = 'public'")).scalars().all()
    assert len(tables) >= 18
    for table in tables:
        assert _scalar(db, "select relrowsecurity from pg_class where oid = cast(:t as regclass)", t=f"public.{table}") is True, table
        assert _scalar(db, "select count(*) from pg_policies where schemaname = 'public' and tablename = :t", t=table) == 4, table
        assert _scalar(db, "select has_table_privilege('anon', cast(:t as regclass), 'select')", t=f"public.{table}") is False, table


def test_rls_scopes_child_tables_through_their_parent(db_engine, create_user):
    with db_engine.connect() as admin:
        alice, bob = create_user("a@example.com"), create_user("b@example.com")
        course_id = admin.execute(text(
            "insert into public.courses (user_id, title, status) values (:u, 'Bob course', 'ready') returning id"
        ), {"u": bob}).scalar_one()
        admin.execute(text("insert into public.course_modules (course_id, position, title) values (:c, 0, 'M')"), {"c": course_id})
        admin.execute(text("insert into public.interests (user_id, name, interest_type, source) values (:u, 'Bob interest', 'personal', 'manual')"), {"u": bob})
    with db_engine.connect().execution_options(isolation_level="READ COMMITTED") as db:
        with _as_authenticated(db, alice):
            assert db.execute(text("select count(*) from public.course_modules")).scalar_one() == 0
            assert db.execute(text("select count(*) from public.interests")).scalar_one() == 0
        with _as_authenticated(db, bob):
            assert db.execute(text("select count(*) from public.course_modules")).scalar_one() == 1


def test_relationships_cannot_join_interests_of_different_users(db_engine, create_user):
    with db_engine.connect() as admin:
        alice, bob = create_user("a@example.com"), create_user("b@example.com")
        mine = admin.execute(text("insert into public.interests (user_id, name, interest_type, source) values (:u, 'Mine', 'personal', 'manual') returning id"), {"u": alice}).scalar_one()
        theirs = admin.execute(text("insert into public.interests (user_id, name, interest_type, source) values (:u, 'Theirs', 'personal', 'manual') returning id"), {"u": bob}).scalar_one()
        with pytest.raises(DBAPIError):
            admin.execute(text(
                "insert into public.interest_relationships (user_id, source_interest_id, target_interest_id, relationship_type) "
                "values (:u, :a, :b, 'related_to')"
            ), {"u": alice, "a": mine, "b": theirs})
