from app.ai.llm_client import AIProviderError

API = "/api/v1"


async def test_plain_reply_is_persisted_with_context(client, signed_in, fake_llm):
    _, headers = signed_in()
    await client.post(f"{API}/interests", headers=headers, json={"name": "Guitar"})
    fake_llm.chat_replies.append("Practice chords for 15 minutes.")
    response = await client.post(f"{API}/chat", headers=headers, json={"message": "What should I do this week?"})
    assert response.status_code == 200, response.text
    conversation = response.json()
    assert [m["role"] for m in conversation["messages"]] == ["user", "assistant"]
    assert conversation["title"] == "What should I do this week?"
    assert conversation["messages"][1]["meta"]["tools_used"] == []
    context_message = fake_llm.calls[0]["messages"][1]["content"]
    assert "Guitar" in context_message and "<user_data>" in context_message

    fake_llm.chat_replies.append("Sure.")
    follow_up = (await client.post(f"{API}/chat", headers=headers, json={"conversation_id": conversation["id"], "message": "Thanks"})).json()
    assert len(follow_up["messages"]) == 4
    history = [m["content"] for m in fake_llm.calls[-1]["messages"][2:]]
    assert history == ["What should I do this week?", "Practice chords for 15 minutes.", "Thanks"]


async def test_tool_results_become_verified_sources(client, signed_in, fake_llm):
    _, headers = signed_in()
    fake_llm.chat_replies.extend([[("search_learning_videos", {"query": "guitar chords"})], "Here are two videos."])
    conversation = (await client.post(f"{API}/chat", headers=headers, json={"message": "Find guitar videos"})).json()
    meta = conversation["messages"][-1]["meta"]
    assert meta["tools_used"] == ["search_learning_videos"]
    assert [s["url"] for s in meta["sources"]] == ["https://www.youtube.com/watch?v=vid_ok_1", "https://www.youtube.com/watch?v=vid_ok_2"]
    tool_message = fake_llm.calls[-1]["messages"][-1]
    assert tool_message["role"] == "tool" and "<tool_result>" in tool_message["content"]


async def test_job_tool_uses_real_listings(client, signed_in, fake_llm):
    _, headers = signed_in()
    fake_llm.chat_replies.extend([[("search_jobs", {"query": "python"})], "Two listings found."])
    conversation = (await client.post(f"{API}/chat", headers=headers, json={"message": "Any python jobs?"})).json()
    sources = conversation["messages"][-1]["meta"]["sources"]
    assert {s["url"] for s in sources} == {"https://jobicy.com/jobs/101-python-developer", "https://www.themuse.com/jobs/acme/senior-python-engineer"}


async def test_proposals_require_user_acceptance(client, signed_in, fake_llm):
    _, headers = signed_in()
    fake_llm.chat_replies.extend([
        [("propose_change", {"change_type": "add_interest", "name": "Songwriting", "interest_type": "creative", "reason": "You mentioned lyrics"}),
         ("propose_change", {"change_type": "update_weekly_hours", "hours": 4, "reason": "Less time"})],
        "I suggested two changes.",
    ])
    conversation = (await client.post(f"{API}/chat", headers=headers, json={"message": "I like writing lyrics and have less time"})).json()
    message = conversation["messages"][-1]
    assert [p["status"] for p in message["meta"]["proposals"]] == ["pending", "pending"]
    assert (await client.get(f"{API}/interests", headers=headers)).json() == []

    accepted = (await client.post(f"{API}/chat/messages/{message['id']}/proposals/0", headers=headers, json={"accept": True})).json()
    assert accepted["meta"]["proposals"][0]["status"] == "accepted"
    assert [i["name"] for i in (await client.get(f"{API}/interests", headers=headers)).json()] == ["Songwriting"]

    dismissed = (await client.post(f"{API}/chat/messages/{message['id']}/proposals/1", headers=headers, json={"accept": False})).json()
    assert dismissed["meta"]["proposals"][1]["status"] == "dismissed"
    assert (await client.get(f"{API}/profile", headers=headers)).json()["available_hours_per_week"] is None
    again = await client.post(f"{API}/chat/messages/{message['id']}/proposals/1", headers=headers, json={"accept": True})
    assert again.status_code == 409


async def test_provider_failure_keeps_message_and_retry(client, signed_in, fake_llm):
    _, headers = signed_in()
    fake_llm.chat_replies.append(AIProviderError())
    failed = await client.post(f"{API}/chat", headers=headers, json={"message": "Help me plan"})
    assert failed.status_code == 502
    conversations = (await client.get(f"{API}/chat/conversations", headers=headers)).json()
    assert conversations[0]["message_count"] == 1
    fake_llm.chat_replies.append("Here's a plan.")
    retried = (await client.post(f"{API}/chat/conversations/{conversations[0]['id']}/retry", headers=headers)).json()
    assert [m["content"] for m in retried["messages"]] == ["Help me plan", "Here's a plan."]


async def test_conversations_are_private_and_deletable(client, signed_in, fake_llm):
    _, alice = signed_in("alice@example.com")
    _, bob = signed_in("bob@example.com")
    fake_llm.chat_replies.append("ok")
    conversation = (await client.post(f"{API}/chat", headers=alice, json={"message": "private"})).json()
    assert (await client.get(f"{API}/chat/conversations/{conversation['id']}", headers=bob)).status_code == 404
    fake_llm.chat_replies.append("ok")
    hijack = await client.post(f"{API}/chat", headers=bob, json={"conversation_id": conversation["id"], "message": "hi"})
    assert hijack.status_code == 404
    assert (await client.delete(f"{API}/chat/conversations/{conversation['id']}", headers=bob)).status_code == 404
    assert (await client.delete(f"{API}/chat/conversations/{conversation['id']}", headers=alice)).status_code == 204
    assert (await client.get(f"{API}/chat/conversations", headers=alice)).json() == []


async def test_chat_without_ai_configuration(client, signed_in, app):
    from tests.fakes import UnconfiguredLLM

    app.state.llm = UnconfiguredLLM()
    _, headers = signed_in()
    response = await client.post(f"{API}/chat", headers=headers, json={"message": "hi"})
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "ai_not_configured"
