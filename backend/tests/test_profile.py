import asyncio
import uuid

from sqlalchemy import text

URL = "/api/v1/profile"


def _profile_count(db) -> int:
    return db.execute(text("select count(*) from public.profiles")).scalar_one()


async def test_first_request_creates_profile_for_token_identity(client, db, create_user, auth_headers):
    user_id = create_user("ada@example.com")
    response = await client.get(URL, headers=auth_headers(user_id, email="ada@example.com"))

    assert response.status_code == 200
    body = response.json()
    assert body["user_id"] == str(user_id)
    assert body["display_name"] == "ada"
    assert body["onboarding_completed"] is False
    assert body["location"] is None
    assert _profile_count(db) == 1


async def test_display_name_defaults_from_user_metadata(client, create_user, auth_headers):
    user_id = create_user()
    response = await client.get(URL, headers=auth_headers(user_id, user_metadata={"full_name": "Ada Lovelace"}))
    assert response.json()["display_name"] == "Ada Lovelace"


async def test_repeated_sign_in_does_not_duplicate_profile(client, db, create_user, auth_headers):
    user_id = create_user("ada@example.com")
    first = (await client.get(URL, headers=auth_headers(user_id))).json()
    second = (await client.get(URL, headers=auth_headers(user_id))).json()

    assert first["created_at"] == second["created_at"]
    assert _profile_count(db) == 1


async def test_concurrent_first_requests_create_exactly_one_profile(client, db, create_user, auth_headers):
    user_id = create_user()
    headers = auth_headers(user_id)
    responses = await asyncio.gather(*(client.get(URL, headers=headers) for _ in range(8)))

    assert {response.status_code for response in responses} == {200}
    assert _profile_count(db) == 1


async def test_patch_updates_and_persists(client, create_user, auth_headers):
    user_id = create_user()
    headers = auth_headers(user_id)
    created = (await client.get(URL, headers=headers)).json()

    response = await client.patch(
        URL,
        headers=headers,
        json={
            "display_name": "  Ada  ",
            "location": "London",
            "current_occupation": "Software engineer",
            "education_summary": "BSc Mathematics",
            "experience_summary": "Five years of backend work",
        },
    )

    assert response.status_code == 200
    updated = response.json()
    assert updated["display_name"] == "Ada"
    assert updated["location"] == "London"
    assert updated["updated_at"] > created["updated_at"]
    assert updated["created_at"] == created["created_at"]

    reloaded = (await client.get(URL, headers=headers)).json()
    assert reloaded == updated


async def test_partial_patch_leaves_other_fields_untouched(client, create_user, auth_headers):
    headers = auth_headers(create_user())
    await client.patch(URL, headers=headers, json={"location": "Pune", "current_occupation": "Designer"})

    response = await client.patch(URL, headers=headers, json={"location": "Mumbai"})

    assert response.json()["location"] == "Mumbai"
    assert response.json()["current_occupation"] == "Designer"


async def test_blank_optional_field_clears_it(client, create_user, auth_headers):
    headers = auth_headers(create_user())
    await client.patch(URL, headers=headers, json={"location": "Pune"})

    response = await client.patch(URL, headers=headers, json={"location": "   "})

    assert response.json()["location"] is None


async def test_empty_patch_is_a_noop(client, create_user, auth_headers):
    headers = auth_headers(create_user())
    before = (await client.get(URL, headers=headers)).json()
    response = await client.patch(URL, headers=headers, json={})
    assert response.status_code == 200
    assert response.json() == before


async def test_server_controlled_and_unknown_fields_are_rejected(client, create_user, auth_headers):
    user_id = create_user()
    headers = auth_headers(user_id)
    for forbidden in (
        {"user_id": str(uuid.uuid4())},
        {"onboarding_completed": True},
        {"created_at": "2020-01-01T00:00:00Z"},
        {"is_admin": True},
    ):
        response = await client.patch(URL, headers=headers, json=forbidden)
        assert response.status_code == 422, forbidden
        assert response.json()["error"]["code"] == "validation_error"

    profile = (await client.get(URL, headers=headers)).json()
    assert profile["user_id"] == str(user_id)
    assert profile["onboarding_completed"] is False


async def test_invalid_values_are_rejected_without_echoing_input(client, create_user, auth_headers):
    headers = auth_headers(create_user())
    secret_looking = "x" * 121

    for payload in (
        {"display_name": ""},
        {"display_name": "   "},
        {"display_name": None},
        {"display_name": secret_looking},
        {"location": "y" * 201},
        {"education_summary": "z" * 4001},
        {"display_name": 123},
    ):
        response = await client.patch(URL, headers=headers, json=payload)
        assert response.status_code == 422, payload
        assert secret_looking not in response.text


async def test_users_only_see_and_change_their_own_profile(client, create_user, auth_headers):
    alice, bob = create_user("alice@example.com"), create_user("bob@example.com")
    alice_headers, bob_headers = auth_headers(alice), auth_headers(bob)

    await client.patch(URL, headers=alice_headers, json={"location": "Alice-land"})
    await client.patch(URL, headers=bob_headers, json={"location": "Bob-land"})

    assert (await client.get(URL, headers=alice_headers)).json()["location"] == "Alice-land"
    assert (await client.get(URL, headers=bob_headers)).json()["location"] == "Bob-land"


async def test_identity_cannot_be_overridden_through_query_string(client, create_user, auth_headers):
    alice, bob = create_user(), create_user()
    await client.patch(URL, headers=auth_headers(alice), json={"location": "Alice-land"})

    response = await client.get(URL, params={"user_id": str(alice)}, headers=auth_headers(bob))

    assert response.json()["user_id"] == str(bob)
    assert response.json()["location"] is None


async def test_valid_token_for_deleted_account_is_rejected_and_creates_nothing(client, db, auth_headers):
    ghost = uuid.uuid4()  # signed token, but no such row in auth.users

    response = await client.get(URL, headers=auth_headers(ghost))

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "account_not_found"
    assert _profile_count(db) == 0


async def test_deleting_the_auth_user_removes_the_profile(client, db, create_user, auth_headers):
    user_id = create_user()
    await client.get(URL, headers=auth_headers(user_id))
    assert _profile_count(db) == 1

    db.execute(text("delete from auth.users where id = :id"), {"id": user_id})

    assert _profile_count(db) == 0
