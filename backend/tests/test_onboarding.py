import pytest

from app.ai.llm_client import AIProviderError
from app.core.exceptions import BadRequestError
from app.services.onboarding_service import OPENER, UNUSABLE_REPLY, validate_inputs
from tests.fakes import course_outline

API = "/api/v1"


def turn(reply="Nice! What else do you enjoy?", *, interests=None, goals=None, skills=None, ready=False, **profile):
    return {
        "reply": reply,
        "profile": {"display_name": None, "location": None, "current_occupation": None, "education_summary": None,
                    "experience_summary": None, "available_hours_per_week": None, "learning_preferences": None,
                    "constraints_summary": None, **profile},
        "interests": interests or [],
        "goals": goals or [],
        "skills": skills or [],
        "ready_to_finish": ready,
    }


def interest(name, parent=None, kind="main", seeks_income=False, interest_type="professional", priority=3):
    return {"name": name, "description": None, "interest_type": interest_type, "node_kind": kind, "category": None,
            "priority": priority, "seeks_income": seeks_income, "parent": parent}


class TestValidateInputs:
    def test_empty_is_rejected(self):
        with pytest.raises(BadRequestError):
            validate_inputs("   ")

    @pytest.mark.parametrize("text", ["I don't know", "idk", "not sure", "No idea really"])
    def test_unsure_answers_are_valid(self, text):
        assert validate_inputs(text).kind == "unsure"

    @pytest.mark.parametrize("text", ["???", "...", "!!!"])
    def test_symbol_only_is_unusable(self, text):
        assert validate_inputs(text).kind == "unusable"

    @pytest.mark.parametrize("text", ["I'm a software engineer", "guitar", "maybe painting and music", "ok"])
    def test_personal_answers_are_preserved(self, text):
        result = validate_inputs(f"  {text} ")
        assert result.kind == "answer" and result.text == text


async def test_start_creates_single_conversation_with_opener(client, signed_in):
    _, headers = signed_in()
    first = (await client.post(f"{API}/onboarding/start", headers=headers)).json()
    second = (await client.post(f"{API}/onboarding/start", headers=headers)).json()
    assert first["conversation_id"] == second["conversation_id"]
    assert [m["content"] for m in second["messages"]] == [OPENER]
    assert second["completed"] is False


async def test_turn_extracts_draft_and_persists_messages(client, signed_in, fake_llm):
    _, headers = signed_in()
    await client.post(f"{API}/onboarding/start", headers=headers)
    fake_llm.queue("OnboardingTurn", turn(
        current_occupation="Software engineer",
        interests=[interest("Software Engineering"), interest("Music Production", interest_type="creative")],
        skills=["Python"],
    ))
    response = await client.post(f"{API}/onboarding/turn", headers=headers, json={"message": "I'm a software engineer who wants to make music"})
    assert response.status_code == 200
    status = response.json()["status"]
    assert [m["role"] for m in status["messages"]] == ["assistant", "user", "assistant"]
    assert status["draft"]["profile"]["current_occupation"] == "Software engineer"
    assert {i["name"] for i in status["draft"]["interests"]} == {"Software Engineering", "Music Production"}

    # Items the model drops are kept; new ones are merged in.
    fake_llm.queue("OnboardingTurn", turn(interests=[interest("Fitness", interest_type="personal")], ready=True))
    status = (await client.post(f"{API}/onboarding/turn", headers=headers, json={"message": "and fitness"})).json()["status"]
    assert {i["name"] for i in status["draft"]["interests"]} == {"Software Engineering", "Music Production", "Fitness"}
    assert status["draft"]["profile"]["current_occupation"] == "Software engineer"
    assert status["ready_to_finish"] is True


async def test_unsure_answer_tells_the_model_to_simplify(client, signed_in, fake_llm):
    _, headers = signed_in()
    fake_llm.queue("OnboardingTurn", turn("What do you enjoy on a free weekend?"))
    response = await client.post(f"{API}/onboarding/turn", headers=headers, json={"message": "I don't know"})
    assert response.json()["assessment"]["kind"] == "unsure"
    assert "simpler" in fake_llm.calls[-1]["messages"][0]["content"]


async def test_unusable_answer_gets_scripted_clarification_without_ai(client, signed_in, fake_llm):
    _, headers = signed_in()
    response = await client.post(f"{API}/onboarding/turn", headers=headers, json={"message": "???"})
    assert response.status_code == 200
    assert response.json()["status"]["messages"][-1]["content"] == UNUSABLE_REPLY
    assert fake_llm.calls == []


async def test_empty_message_is_a_client_error(client, signed_in):
    _, headers = signed_in()
    response = await client.post(f"{API}/onboarding/turn", headers=headers, json={"message": "  "})
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "empty_response"


async def test_provider_failure_preserves_message_and_retry_recovers(client, signed_in, fake_llm):
    _, headers = signed_in()
    fake_llm.queue("OnboardingTurn", AIProviderError())
    failed = await client.post(f"{API}/onboarding/turn", headers=headers, json={"message": "I paint"})
    assert failed.status_code == 502
    assert failed.json()["error"]["code"] == "ai_provider_error"

    status = (await client.get(f"{API}/onboarding/status", headers=headers)).json()
    assert status["messages"][-1]["content"] == "I paint"
    assert status["awaiting_reply"] is True

    blocked = await client.post(f"{API}/onboarding/turn", headers=headers, json={"message": "hello?"})
    assert blocked.status_code == 409

    fake_llm.queue("OnboardingTurn", turn("Lovely. What do you paint?"))
    retried = (await client.post(f"{API}/onboarding/retry", headers=headers)).json()
    assert retried["awaiting_reply"] is False
    assert retried["messages"][-1]["content"] == "Lovely. What do you paint?"


async def test_malformed_ai_output_never_reaches_the_draft(client, signed_in, fake_llm):
    _, headers = signed_in()
    fake_llm.queue("OnboardingTurn", {"reply": "x", "profile": {}, "interests": [{"name": ""}]})
    response = await client.post(f"{API}/onboarding/turn", headers=headers, json={"message": "I like chess"})
    assert response.status_code == 502
    status = (await client.get(f"{API}/onboarding/status", headers=headers)).json()
    assert status["draft"]["interests"] == []


async def test_complete_persists_reviewed_draft_and_starts_pathways(client, signed_in, fake_llm):
    user_id, headers = signed_in()
    draft = {
        "profile": {"current_occupation": "Engineer", "available_hours_per_week": 6},
        "interests": [
            interest("Software Engineering", priority=5),
            interest("AI/ML", parent="Software Engineering", kind="secondary"),
            interest("Guitar", interest_type="creative", priority=4),
        ],
        "goals": [{"title": "Learn guitar", "category": "creative", "target_outcome": "Play a song", "priority": 4, "hours_per_week": 3}],
        "skills": ["Python", "python", "SQL"],
    }
    fake_llm.queue("GraphSuggestions", {"relationships": [
        {"source": "Guitar", "target": "Software Engineering", "relationship_type": "related_to", "reason": "both"},
        {"source": "Unknown", "target": "Guitar", "relationship_type": "related_to", "reason": "ignored"},
    ]})
    fake_llm.queue("CourseOutline", course_outline("Software path"), course_outline("Guitar path"))
    fake_llm.queue("GoalPlan", {"plan_summary": "Practice", "milestones": [
        {"title": "Chords", "description": None, "week_offset": 1}, {"title": "Song", "description": None, "week_offset": 4},
    ]})

    response = await client.post(f"{API}/onboarding/complete", headers=headers, json=draft)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["interests_created"] == 3 and body["goals_created"] == 1
    assert body["relationships_created"] == 2  # part_of from the draft + one valid AI link
    assert len(body["courses_started"]) == 2

    profile = (await client.get(f"{API}/profile", headers=headers)).json()
    assert profile["onboarding_completed"] is True and profile["available_hours_per_week"] == 6
    facts = (await client.get(f"{API}/profile/facts", headers=headers)).json()
    assert sorted(f["value"] for f in facts) == ["Python", "SQL"]
    assert all(f["confirmed"] and f["source"] == "onboarding" for f in facts)

    courses = (await client.get(f"{API}/courses", headers=headers)).json()
    assert {c["status"] for c in courses} == {"ready"}
    goals = (await client.get(f"{API}/goals", headers=headers)).json()
    assert [m["title"] for m in goals[0]["milestones"]] == ["Chords", "Song"]


async def test_complete_requires_some_content(client, signed_in):
    _, headers = signed_in()
    response = await client.post(f"{API}/onboarding/complete", headers=headers, json={"profile": {}, "interests": [], "goals": [], "skills": []})
    assert response.status_code == 400


async def test_draft_edits_are_saved_for_review(client, signed_in):
    _, headers = signed_in()
    draft = {"profile": {"location": "Sydney"}, "interests": [interest("Painting", interest_type="creative")], "goals": [], "skills": []}
    saved = (await client.put(f"{API}/onboarding/draft", headers=headers, json=draft)).json()
    assert saved["draft"]["profile"]["location"] == "Sydney"
    assert saved["draft"]["interests"][0]["name"] == "Painting"


async def test_onboarding_is_private(client, signed_in, fake_llm):
    _, alice = signed_in("alice@example.com")
    _, bob = signed_in("bob@example.com")
    fake_llm.queue("OnboardingTurn", turn())
    await client.post(f"{API}/onboarding/turn", headers=alice, json={"message": "secret hobby"})
    bob_status = (await client.get(f"{API}/onboarding/status", headers=bob)).json()
    assert bob_status["messages"] == [] and bob_status["conversation_id"] is None


async def test_skip_marks_onboarding_complete(client, signed_in):
    _, headers = signed_in()
    assert (await client.post(f"{API}/onboarding/skip", headers=headers)).status_code == 204
    assert (await client.get(f"{API}/profile", headers=headers)).json()["onboarding_completed"] is True


async def test_complete_survives_ai_connection_failure(client, signed_in, fake_llm):
    _, headers = signed_in()
    draft = {"profile": {}, "interests": [interest("Painting", interest_type="creative"), interest("Running", interest_type="personal")],
             "goals": [{"title": "Run 5k", "category": "health", "target_outcome": None, "priority": 3, "hours_per_week": None}], "skills": []}
    fake_llm.queue("GraphSuggestions", AIProviderError())
    fake_llm.queue("CourseOutline", course_outline("A"), course_outline("B"))
    fake_llm.queue("GoalPlan", AIProviderError())
    response = await client.post(f"{API}/onboarding/complete", headers=headers, json=draft)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["interests_created"] == 2 and len(body["courses_started"]) == 2
    assert "could not be suggested" in body["warnings"][0]
    assert (await client.get(f"{API}/profile", headers=headers)).json()["onboarding_completed"] is True
    goals = (await client.get(f"{API}/goals", headers=headers)).json()
    assert goals[0]["milestones"] == []  # plan failure leaves the goal for the user to plan later


async def test_complete_without_ai_still_saves_profile(client, signed_in, app):
    from tests.fakes import UnconfiguredLLM

    app.state.llm = UnconfiguredLLM()
    _, headers = signed_in()
    draft = {"profile": {}, "interests": [interest("Chess", interest_type="personal")], "goals": [], "skills": []}
    body = (await client.post(f"{API}/onboarding/complete", headers=headers, json=draft)).json()
    assert body["interests_created"] == 1 and body["courses_started"] == []
    assert "not configured" in body["warnings"][0]
