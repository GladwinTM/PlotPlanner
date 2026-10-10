from sqlalchemy import text

from tests.fakes import course_outline

API = "/api/v1"


async def setup_activity(client, headers, fake_llm):
    interest = (await client.post(f"{API}/interests", headers=headers, json={"name": "Python"})).json()
    fake_llm.queue("CourseOutline", course_outline())
    course_id = (await client.post(f"{API}/courses/generate", headers=headers, json={"interest_id": interest["id"]})).json()["id"]
    course = (await client.post(f"{API}/courses/{course_id}/enroll", headers=headers)).json()
    basics = course["modules"][0]
    for activity in basics["activities"]:
        await client.patch(f"{API}/courses/{course_id}/modules/{basics['id']}/progress", headers=headers,
                           json={"activity_id": activity["id"], "completed": True})
    goal = (await client.post(f"{API}/goals", headers=headers, json={"title": "Practice", "interest_id": interest["id"]})).json()
    await client.post(f"{API}/goals/{goal['id']}/checkins", headers=headers, json={"minutes": 30})
    return interest, course_id, goal


async def test_overview_reflects_records(client, signed_in, fake_llm):
    _, headers = signed_in()
    await setup_activity(client, headers, fake_llm)
    overview = (await client.get(f"{API}/analytics/overview", headers=headers)).json()
    assert overview["active_interests"] == 1
    assert overview["active_courses"] == 1
    assert overview["completed_modules"] == 1 and overview["completed_activities"] == 2
    assert overview["courses"][0]["percent"] == 50
    assert overview["minutes_logged"] == 30
    assert overview["active_goals"] == 1
    assert any(s["kind"] == "plan_goal" for s in overview["suggestions"])
    assert "required modules" in overview["definitions"]["course_percent"]


async def test_activity_series_counts_today(client, signed_in, fake_llm):
    _, headers = signed_in()
    await setup_activity(client, headers, fake_llm)
    body = (await client.get(f"{API}/analytics/activity?days=7", headers=headers)).json()
    assert len(body["series"]) == 8
    today = body["series"][-1]
    assert today["activities_completed"] == 2 and today["checkins"] == 1 and today["minutes_logged"] == 30


async def test_interest_analytics(client, signed_in, fake_llm):
    _, headers = signed_in()
    await setup_activity(client, headers, fake_llm)
    body = (await client.get(f"{API}/analytics/interests", headers=headers)).json()
    assert body["interests"][0]["average_course_percent"] == 50 and body["interests"][0]["goals"] == 1


async def test_analytics_empty_state(client, signed_in):
    _, headers = signed_in()
    overview = (await client.get(f"{API}/analytics/overview", headers=headers)).json()
    assert overview["active_interests"] == 0 and overview["courses"] == [] and overview["suggestions"] == []


async def test_delete_data_removes_only_callers_records(client, signed_in, fake_llm, db_engine):
    alice_id, alice = signed_in("alice@example.com")
    bob_id, bob = signed_in("bob@example.com")
    await setup_activity(client, alice, fake_llm)
    await client.post(f"{API}/interests", headers=bob, json={"name": "Bob keeps this"})
    fake_llm.queue("DocumentExtraction", {"is_resume": False, "summary": "note", "facts": [{"kind": "skill", "value": "Greeting", "detail": None}]})
    uploaded = await client.post(f"{API}/documents", headers=alice, files={"file": ("a.txt", b"hello world", "text/plain")})
    assert uploaded.status_code == 201

    refused = await client.post(f"{API}/account/delete-data", headers=alice, json={"confirm": "yes"})
    assert refused.status_code == 422
    result = (await client.post(f"{API}/account/delete-data", headers=alice, json={"confirm": "DELETE"})).json()
    assert result["deleted"] is True and result["auth_account_deleted"] is False

    with db_engine.connect() as connection:
        for table in ("interests", "goals", "courses", "documents", "profile_facts", "activity_completions", "goal_checkins", "profiles"):
            count = connection.execute(text(f"select count(*) from public.{table} where user_id = :u"), {"u": alice_id}).scalar()
            assert count == 0, table
        assert connection.execute(text("select count(*) from public.interests where user_id = :u"), {"u": bob_id}).scalar() == 1
        assert connection.execute(text("select count(*) from auth.users where id = :u"), {"u": alice_id}).scalar() == 1

    profile = (await client.get(f"{API}/profile", headers=alice)).json()
    assert profile["onboarding_completed"] is False
