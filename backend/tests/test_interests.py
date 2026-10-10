from tests.fakes import course_outline

API = "/api/v1"


async def create(client, headers, name, **extra):
    response = await client.post(f"{API}/interests", headers=headers, json={"name": name, **extra})
    assert response.status_code == 201, response.text
    return response.json()


async def test_crud_and_validation(client, signed_in):
    _, headers = signed_in()
    music = await create(client, headers, "Music", interest_type="creative", node_kind="main", priority=4)
    assert music["source"] == "manual" and music["priority"] == 4

    duplicate = await client.post(f"{API}/interests", headers=headers, json={"name": "music"})
    assert duplicate.status_code == 409

    invalid = await client.post(f"{API}/interests", headers=headers, json={"name": "X", "priority": 9})
    assert invalid.status_code == 422
    forbidden_field = await client.post(f"{API}/interests", headers=headers, json={"name": "X", "user_id": music["id"]})
    assert forbidden_field.status_code == 422

    updated = (await client.patch(f"{API}/interests/{music['id']}", headers=headers, json={"description": "Producing beats", "seeks_income": True})).json()
    assert updated["description"] == "Producing beats" and updated["seeks_income"] is True

    assert (await client.delete(f"{API}/interests/{music['id']}", headers=headers)).status_code == 204
    assert (await client.get(f"{API}/interests", headers=headers)).json() == []


async def test_create_with_connections(client, signed_in):
    _, headers = signed_in()
    art = await create(client, headers, "Art and Design", node_kind="main")
    software = await create(client, headers, "Software Engineering", node_kind="main")
    uiux = await create(client, headers, "UI/UX", connect_to=[art["id"], software["id"]], relationship_type="shares_skills_with")
    graph = (await client.get(f"{API}/interests/graph", headers=headers)).json()
    assert len(graph["nodes"]) == 3
    edges = {(e["source"], e["target"], e["relationship_type"]) for e in graph["edges"]}
    assert edges == {(uiux["id"], art["id"], "shares_skills_with"), (uiux["id"], software["id"], "shares_skills_with")}


async def test_relationship_rules(client, signed_in):
    _, headers = signed_in()
    _, other = signed_in("other@example.com")
    a = await create(client, headers, "A")
    b = await create(client, headers, "B")
    foreign = await create(client, other, "Foreign")

    self_link = await client.post(f"{API}/interests/relationships", headers=headers, json={"source_interest_id": a["id"], "target_interest_id": a["id"]})
    assert self_link.status_code == 400
    cross_user = await client.post(f"{API}/interests/relationships", headers=headers, json={"source_interest_id": a["id"], "target_interest_id": foreign["id"]})
    assert cross_user.status_code == 404

    created = await client.post(f"{API}/interests/relationships", headers=headers, json={"source_interest_id": a["id"], "target_interest_id": b["id"]})
    assert created.status_code == 201
    reverse_duplicate = await client.post(f"{API}/interests/relationships", headers=headers, json={"source_interest_id": b["id"], "target_interest_id": a["id"]})
    assert reverse_duplicate.status_code == 409
    different_type = await client.post(f"{API}/interests/relationships", headers=headers, json={"source_interest_id": b["id"], "target_interest_id": a["id"], "relationship_type": "supports"})
    assert different_type.status_code == 201

    rel_id = created.json()["id"]
    assert (await client.delete(f"{API}/interests/relationships/{rel_id}", headers=other)).status_code == 404
    assert (await client.delete(f"{API}/interests/relationships/{rel_id}", headers=headers)).status_code == 204


async def test_deleting_interest_keeps_goals_and_courses(client, signed_in, fake_llm):
    _, headers = signed_in()
    guitar = await create(client, headers, "Guitar")
    music = await create(client, headers, "Music", connect_to=[])
    await client.post(f"{API}/interests/relationships", headers=headers, json={"source_interest_id": guitar["id"], "target_interest_id": music["id"], "relationship_type": "part_of"})
    goal = (await client.post(f"{API}/goals", headers=headers, json={"title": "Play a song", "interest_id": guitar["id"]})).json()
    fake_llm.queue("CourseOutline", course_outline())
    course = (await client.post(f"{API}/courses/generate", headers=headers, json={"interest_id": guitar["id"]})).json()

    await client.delete(f"{API}/interests/{guitar['id']}", headers=headers)
    graph = (await client.get(f"{API}/interests/graph", headers=headers)).json()
    assert graph["edges"] == []
    assert (await client.get(f"{API}/goals/{goal['id']}", headers=headers)).json()["interest_id"] is None
    assert (await client.get(f"{API}/courses/{course['id']}", headers=headers)).json()["interest_id"] is None


async def test_graph_metrics_come_from_records(client, signed_in, fake_llm):
    _, headers = signed_in()
    python = await create(client, headers, "Python")
    await client.post(f"{API}/goals", headers=headers, json={"title": "Get a job", "interest_id": python["id"]})
    fake_llm.queue("CourseOutline", course_outline())
    course_id = (await client.post(f"{API}/courses/generate", headers=headers, json={"interest_id": python["id"]})).json()["id"]
    course = (await client.post(f"{API}/courses/{course_id}/enroll", headers=headers)).json()
    project = course["modules"][1]
    await client.patch(f"{API}/courses/{course_id}/modules/{project['id']}/progress", headers=headers,
                       json={"activity_id": project["activities"][0]["id"], "completed": True})
    node = (await client.get(f"{API}/interests/graph", headers=headers)).json()["nodes"][0]
    assert node["course_count"] == 1 and node["goal_count"] == 1
    assert node["course_progress_percent"] == 50 and node["evidence_count"] == 1


async def test_layout_only_updates_own_nodes(client, signed_in):
    _, headers = signed_in()
    _, other = signed_in("other@example.com")
    mine = await create(client, headers, "Mine")
    theirs = await create(client, other, "Theirs")
    response = await client.put(f"{API}/interests/layout", headers=headers, json={"positions": [
        {"id": mine["id"], "x": 10, "y": 20}, {"id": theirs["id"], "x": 1, "y": 1},
    ]})
    assert response.json() == {"updated": 1}
    node = (await client.get(f"{API}/interests/graph", headers=headers)).json()["nodes"][0]
    assert node["position"] == {"x": 10, "y": 20}
    assert (await client.get(f"{API}/interests/graph", headers=other)).json()["nodes"][0]["position"] is None


async def test_suggestions_are_validated_and_not_saved(client, signed_in, fake_llm):
    _, headers = signed_in()
    software = await create(client, headers, "Software")
    await create(client, headers, "Art")
    fake_llm.queue("InterestSuggestions", {
        "suggestions": [
            {"name": "UI/UX", "interest_type": "professional", "node_kind": "secondary", "connects_to": ["Software", "Nope"], "relationship_type": "shares_skills_with", "reason": "bridge"},
            {"name": "software", "interest_type": "professional", "node_kind": "main", "connects_to": [], "relationship_type": "related_to", "reason": "dup"},
        ],
        "connections": [
            {"source": "Software", "target": "Art", "relationship_type": "overlaps_with", "reason": "design"},
            {"source": "Software", "target": "Ghost", "relationship_type": "related_to", "reason": "x"},
        ],
    })
    result = (await client.post(f"{API}/interests/suggestions", headers=headers)).json()
    assert [s["name"] for s in result["interests"]] == ["UI/UX"]
    assert result["interests"][0]["connects_to"] == [software["id"]]
    assert len(result["connections"]) == 1
    assert len((await client.get(f"{API}/interests", headers=headers)).json()) == 2


async def test_requires_authentication(client):
    assert (await client.get(f"{API}/interests")).status_code == 401
