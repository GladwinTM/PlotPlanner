from app.ai.llm_client import AIProviderError
from tests.fakes import course_outline

API = "/api/v1"


async def make_interest(client, headers, name="Python"):
    response = await client.post(f"{API}/interests", headers=headers, json={"name": name, "interest_type": "professional"})
    assert response.status_code == 201, response.text
    return response.json()["id"]


async def generate(client, headers, fake_llm, interest_id, outline=None):
    fake_llm.queue("CourseOutline", outline or course_outline())
    response = await client.post(f"{API}/courses/generate", headers=headers, json={"interest_id": interest_id})
    assert response.status_code == 202, response.text
    return response.json()["id"]


async def test_generation_creates_ready_course_with_only_verified_resources(client, signed_in, fake_llm):
    _, headers = signed_in()
    interest_id = await make_interest(client, headers)
    course_id = await generate(client, headers, fake_llm, interest_id)

    course = (await client.get(f"{API}/courses/{course_id}", headers=headers)).json()
    assert course["status"] == "ready" and course["title"] == "Python Foundations"
    assert [m["title"] for m in course["modules"]] == ["Basics", "Project", "Earning path"]
    basics = course["modules"][0]
    videos = [r for r in basics["resources"] if r["resource_type"] == "video"]
    # Private and short videos are dropped; only videos.list-confirmed ones remain.
    assert [v["canonical_url"] for v in videos] == ["https://www.youtube.com/watch?v=vid_ok_1", "https://www.youtube.com/watch?v=vid_ok_2"]
    assert videos[0]["title"] == "Intro & Basics" and videos[0]["cost_status"] == "free"
    assert all(v["verification_status"] == "verified" and v["retrieved_at"] for v in videos)
    docs = [r for r in basics["resources"] if r["resource_type"] == "documentation"]
    assert [d["canonical_url"] for d in docs] == ["https://docs.python.org/3/tutorial/"]  # unreachable link discarded
    assert docs[0]["cost_status"] == "unknown"
    assert course["interest_name"] == "Python"


async def test_generation_failure_is_recorded(client, signed_in, fake_llm):
    _, headers = signed_in()
    interest_id = await make_interest(client, headers)
    fake_llm.queue("CourseOutline", AIProviderError())
    response = await client.post(f"{API}/courses/generate", headers=headers, json={"interest_id": interest_id})
    course = (await client.get(f"{API}/courses/{response.json()['id']}", headers=headers)).json()
    assert course["status"] == "failed"
    assert "AI provider" in course["error"]
    assert course["modules"] == []


async def test_youtube_quota_does_not_block_the_course(client, signed_in, fake_llm, youtube_mock):
    _, headers = signed_in()
    youtube_mock.fail_with = 403
    interest_id = await make_interest(client, headers)
    course_id = await generate(client, headers, fake_llm, interest_id)
    course = (await client.get(f"{API}/courses/{course_id}", headers=headers)).json()
    assert course["status"] == "ready"
    assert "quota" in course["error"]
    assert not [r for m in course["modules"] for r in m["resources"] if r["resource_type"] == "video"]


async def test_generate_requires_a_target(client, signed_in):
    _, headers = signed_in()
    response = await client.post(f"{API}/courses/generate", headers=headers, json={})
    assert response.status_code == 400


async def test_progress_lifecycle(client, signed_in, fake_llm):
    _, headers = signed_in()
    course_id = await generate(client, headers, fake_llm, await make_interest(client, headers))
    course = (await client.get(f"{API}/courses/{course_id}", headers=headers)).json()
    basics, project, optional = course["modules"]

    not_enrolled = await client.patch(
        f"{API}/courses/{course_id}/modules/{basics['id']}/progress", headers=headers,
        json={"activity_id": basics["activities"][0]["id"], "completed": True},
    )
    assert not_enrolled.status_code == 409

    course = (await client.post(f"{API}/courses/{course_id}/enroll", headers=headers)).json()
    assert course["enrollment"]["status"] == "active"
    assert course["progress"]["percent"] == 0
    assert course["next_activity"]["activity_title"] == "Variables"

    async def mark(module, index, completed=True, notes=None):
        response = await client.patch(
            f"{API}/courses/{course_id}/modules/{module['id']}/progress", headers=headers,
            json={"activity_id": module["activities"][index]["id"], "completed": completed, "notes": notes},
        )
        assert response.status_code == 200, response.text
        return response.json()

    course = await mark(basics, 0)
    assert course["progress"]["percent"] == 0  # module not complete until all activities are
    course = await mark(basics, 1)
    assert course["progress"]["percent"] == 50 and course["modules"][0]["completed"] is True
    course = await mark(project, 0, notes="https://github.com/me/cli")
    # Optional module does not hold back completion.
    assert course["progress"]["percent"] == 100
    assert course["enrollment"]["status"] == "completed"
    assert course["modules"][1]["activities"][0]["notes"] == "https://github.com/me/cli"

    course = await mark(project, 0, completed=False)
    assert course["progress"]["percent"] == 50 and course["enrollment"]["status"] == "active"

    paused = (await client.patch(f"{API}/courses/{course_id}/enrollment", headers=headers, json={"status": "paused"})).json()
    assert paused["enrollment"]["status"] == "paused"
    blocked = await client.patch(
        f"{API}/courses/{course_id}/modules/{project['id']}/progress", headers=headers,
        json={"activity_id": project["activities"][0]["id"], "completed": True},
    )
    assert blocked.status_code == 409

    # Leaving keeps completion records; re-enrolling resumes.
    assert (await client.delete(f"{API}/courses/{course_id}/enrollment", headers=headers)).status_code == 204
    course = (await client.post(f"{API}/courses/{course_id}/enroll", headers=headers)).json()
    assert course["progress"]["completed_activities"] == 2


async def test_activity_must_belong_to_module(client, signed_in, fake_llm):
    _, headers = signed_in()
    course_id = await generate(client, headers, fake_llm, await make_interest(client, headers))
    course = (await client.post(f"{API}/courses/{course_id}/enroll", headers=headers)).json()
    basics, project, _ = course["modules"]
    response = await client.patch(
        f"{API}/courses/{course_id}/modules/{basics['id']}/progress", headers=headers,
        json={"activity_id": project["activities"][0]["id"], "completed": True},
    )
    assert response.status_code == 404


async def test_regeneration_archives_old_version_and_keeps_history(client, signed_in, fake_llm):
    _, headers = signed_in()
    course_id = await generate(client, headers, fake_llm, await make_interest(client, headers))
    course = (await client.post(f"{API}/courses/{course_id}/enroll", headers=headers)).json()
    first = course["modules"][0]
    await client.patch(f"{API}/courses/{course_id}/modules/{first['id']}/progress", headers=headers,
                       json={"activity_id": first["activities"][0]["id"], "completed": True})

    fake_llm.queue("CourseOutline", course_outline("Python v2", optional_module=False))
    new = (await client.post(f"{API}/courses/{course_id}/regenerate", headers=headers, json={"focus": "web APIs"})).json()
    assert new["version"] == 2 and new["previous_version_id"] == course_id

    listed = (await client.get(f"{API}/courses", headers=headers)).json()
    assert [c["title"] for c in listed] == ["Python v2"]
    assert listed[0]["enrollment"]["status"] == "active"
    old = (await client.get(f"{API}/courses/{course_id}", headers=headers)).json()
    assert old["status"] == "archived" and old["progress"]["completed_activities"] == 1


async def test_failed_regeneration_keeps_current_version(client, signed_in, fake_llm):
    _, headers = signed_in()
    course_id = await generate(client, headers, fake_llm, await make_interest(client, headers))
    fake_llm.queue("CourseOutline", AIProviderError())
    await client.post(f"{API}/courses/{course_id}/regenerate", headers=headers)
    old = (await client.get(f"{API}/courses/{course_id}", headers=headers)).json()
    assert old["status"] == "ready"


async def test_refresh_marks_removed_videos_unavailable(client, signed_in, fake_llm, youtube_mock):
    _, headers = signed_in()
    course_id = await generate(client, headers, fake_llm, await make_interest(client, headers))
    module_id = (await client.get(f"{API}/courses/{course_id}", headers=headers)).json()["modules"][0]["id"]
    del youtube_mock.available["vid_ok_2"]
    youtube_mock.search_ids = ["vid_new"]
    youtube_mock.available["vid_new"] = youtube_mock.available["vid_ok_1"] | {"id": "vid_new"}
    course = (await client.post(f"{API}/courses/{course_id}/modules/{module_id}/resources/refresh", headers=headers)).json()
    statuses = {r["canonical_url"].split("=")[-1]: r["verification_status"] for r in course["modules"][0]["resources"] if r["resource_type"] == "video"}
    assert statuses == {"vid_ok_1": "verified", "vid_ok_2": "unavailable", "vid_new": "verified"}


async def test_courses_are_private(client, signed_in, fake_llm):
    _, alice = signed_in("alice@example.com")
    _, bob = signed_in("bob@example.com")
    course_id = await generate(client, alice, fake_llm, await make_interest(client, alice))
    assert (await client.get(f"{API}/courses/{course_id}", headers=bob)).status_code == 404
    assert (await client.post(f"{API}/courses/{course_id}/enroll", headers=bob)).status_code == 404
    assert (await client.get(f"{API}/courses", headers=bob)).json() == []
    other_interest = await make_interest(client, bob, "Bob topic")
    response = await client.post(f"{API}/courses/generate", headers=alice, json={"interest_id": other_interest})
    assert response.status_code == 404


async def test_archive_hides_course(client, signed_in, fake_llm):
    _, headers = signed_in()
    course_id = await generate(client, headers, fake_llm, await make_interest(client, headers))
    assert (await client.delete(f"{API}/courses/{course_id}", headers=headers)).status_code == 204
    assert (await client.get(f"{API}/courses", headers=headers)).json() == []
    archived = (await client.get(f"{API}/courses?include_archived=true", headers=headers)).json()
    assert archived[0]["status"] == "archived"
