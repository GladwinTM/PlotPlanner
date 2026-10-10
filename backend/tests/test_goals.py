API = "/api/v1"


async def test_goal_crud_milestones_checkins(client, signed_in):
    _, headers = signed_in()
    created = await client.post(f"{API}/goals", headers=headers, json={
        "title": "Start running", "category": "health", "priority": 4, "hours_per_week": 3, "target_date": "2027-01-01",
    })
    assert created.status_code == 201
    goal = created.json()
    assert goal["status"] == "active" and goal["progress_percent"] == 0

    goal = (await client.post(f"{API}/goals/{goal['id']}/milestones", headers=headers, json={"title": "Run 1km"})).json()
    goal = (await client.post(f"{API}/goals/{goal['id']}/milestones", headers=headers, json={"title": "Run 5km"})).json()
    first = goal["milestones"][0]
    goal = (await client.patch(f"{API}/goals/{goal['id']}/milestones/{first['id']}", headers=headers, json={"completed": True})).json()
    assert goal["progress_percent"] == 50 and goal["milestones"][0]["completed_at"]

    goal = (await client.post(f"{API}/goals/{goal['id']}/checkins", headers=headers, json={"note": "Felt good", "minutes": 25})).json()
    assert goal["minutes_logged"] == 25
    empty = await client.post(f"{API}/goals/{goal['id']}/checkins", headers=headers, json={})
    assert empty.status_code == 400

    done = (await client.patch(f"{API}/goals/{goal['id']}", headers=headers, json={"status": "completed"})).json()
    assert done["completed_at"]
    reopened = (await client.patch(f"{API}/goals/{goal['id']}", headers=headers, json={"status": "active"})).json()
    assert reopened["completed_at"] is None

    bad = await client.patch(f"{API}/goals/{goal['id']}", headers=headers, json={"status": "nope"})
    assert bad.status_code == 422
    assert (await client.delete(f"{API}/goals/{goal['id']}", headers=headers)).status_code == 204
    assert (await client.get(f"{API}/goals", headers=headers)).json() == []


async def test_plan_keeps_completed_and_manual_milestones(client, signed_in, fake_llm):
    _, headers = signed_in()
    goal = (await client.post(f"{API}/goals", headers=headers, json={"title": "Learn guitar", "category": "creative"})).json()
    fake_llm.queue("GoalPlan", {"plan_summary": "v1", "milestones": [
        {"title": "Chords", "description": None, "week_offset": 1}, {"title": "Rhythm", "description": None, "week_offset": 2},
    ]})
    goal = (await client.post(f"{API}/goals/{goal['id']}/plan", headers=headers)).json()
    assert [m["title"] for m in goal["milestones"]] == ["Chords", "Rhythm"] and goal["plan_summary"] == "v1"
    assert all(m["source"] == "ai" and m["due_date"] for m in goal["milestones"])

    chords = goal["milestones"][0]
    await client.patch(f"{API}/goals/{goal['id']}/milestones/{chords['id']}", headers=headers, json={"completed": True})
    await client.post(f"{API}/goals/{goal['id']}/milestones", headers=headers, json={"title": "My own step"})

    fake_llm.queue("GoalPlan", {"plan_summary": "v2", "milestones": [
        {"title": "Transitions", "description": None, "week_offset": None}, {"title": "Full song", "description": None, "week_offset": 6},
    ]})
    goal = (await client.post(f"{API}/goals/{goal['id']}/plan", headers=headers, json={"adjustment": "Only 1 hour a week"})).json()
    assert [m["title"] for m in goal["milestones"]] == ["Chords", "My own step", "Transitions", "Full song"]
    assert "Only 1 hour a week" in fake_llm.calls[-1]["messages"][0]["content"]


async def test_invalid_plan_changes_nothing(client, signed_in, fake_llm):
    _, headers = signed_in()
    goal = (await client.post(f"{API}/goals", headers=headers, json={"title": "Sleep better", "category": "health"})).json()
    fake_llm.queue("GoalPlan", {"plan_summary": "x", "milestones": []})
    response = await client.post(f"{API}/goals/{goal['id']}/plan", headers=headers)
    assert response.status_code == 502
    assert (await client.get(f"{API}/goals/{goal['id']}", headers=headers)).json()["milestones"] == []


async def test_goals_are_private(client, signed_in):
    _, alice = signed_in("alice@example.com")
    _, bob = signed_in("bob@example.com")
    goal = (await client.post(f"{API}/goals", headers=alice, json={"title": "Secret"})).json()
    assert (await client.get(f"{API}/goals/{goal['id']}", headers=bob)).status_code == 404
    assert (await client.patch(f"{API}/goals/{goal['id']}", headers=bob, json={"title": "x"})).status_code == 404
    assert (await client.delete(f"{API}/goals/{goal['id']}", headers=bob)).status_code == 404
    bob_interest = (await client.post(f"{API}/interests", headers=bob, json={"name": "Bob's"})).json()
    linked = await client.post(f"{API}/goals", headers=alice, json={"title": "Link", "interest_id": bob_interest["id"]})
    assert linked.status_code == 404
