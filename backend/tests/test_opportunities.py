API = "/api/v1"


def fit(*items):
    return {"assessments": [{"listing_number": n, "fit_level": level, "reason": "because"} for n, level in items]}


async def test_search_stores_real_listings_with_salary_basis(client, signed_in, fake_llm):
    _, headers = signed_in()
    fake_llm.queue("FitAssessments", fit((0, "ready_now"), (1, "stretch"), (7, "stretch")))
    response = await client.post(f"{API}/opportunities/search", headers=headers, json={"query": "python"})
    assert response.status_code == 200, response.text
    body = response.json()
    titles = [r["title"] for r in body["results"]]
    assert titles == ["Python Developer", "Senior Python Engineer"]  # irrelevant and non-https listings dropped
    jobicy = body["results"][0]
    assert jobicy["compensation_text"] == "90k - 120k USD per year"
    assert jobicy["compensation_basis"] == "employer_provided"
    assert jobicy["canonical_url"].startswith("https://jobicy.com/")
    muse = body["results"][1]
    assert muse["compensation_text"] is None and muse["compensation_basis"] is None
    assert [r["fit_level"] for r in body["results"]] == ["ready_now", "stretch"]
    assert body["fit_assessed"] is True
    assert {a["name"] for a in body["attribution"]} == {"Jobicy", "The Muse"}


async def test_saved_status_survives_new_searches(client, signed_in, fake_llm):
    _, headers = signed_in()
    fake_llm.queue("FitAssessments", fit(), fit())
    first = (await client.post(f"{API}/opportunities/search", headers=headers, json={"query": "python"})).json()
    job_id = first["results"][0]["id"]
    saved = (await client.post(f"{API}/opportunities/{job_id}/save", headers=headers)).json()
    assert saved["status"] == "saved"
    applied = (await client.patch(f"{API}/opportunities/{job_id}/status", headers=headers, json={"status": "applied", "notes": "Sent CV"})).json()
    assert applied["status"] == "applied" and applied["notes"] == "Sent CV"

    again = (await client.post(f"{API}/opportunities/search", headers=headers, json={"query": "python"})).json()
    same = next(r for r in again["results"] if r["id"] == job_id)
    assert same["status"] == "applied" and same["notes"] == "Sent CV"

    tracked = (await client.get(f"{API}/opportunities", headers=headers)).json()
    assert [t["id"] for t in tracked] == [job_id]


async def test_all_providers_failing_is_an_upstream_error(client, signed_in, jobs_mock):
    _, headers = signed_in()
    jobs_mock.fail = True
    response = await client.post(f"{API}/opportunities/search", headers=headers, json={"query": "python", "assess_fit": False})
    assert response.status_code == 502


async def test_fit_failure_still_returns_listings(client, signed_in, fake_llm):
    from app.ai.llm_client import AIProviderError

    _, headers = signed_in()
    fake_llm.queue("FitAssessments", AIProviderError())
    body = (await client.post(f"{API}/opportunities/search", headers=headers, json={"query": "python"})).json()
    assert len(body["results"]) == 2 and body["fit_assessed"] is False
    assert "unavailable" in body["fit_note"]


async def test_salary_uses_only_published_figures(client, signed_in):
    _, headers = signed_in()
    body = (await client.post(f"{API}/opportunities/salary", headers=headers, json={"role": "python"})).json()
    assert body["listings_checked"] == 2
    assert body["groups"] == [{"currency": "USD", "period": "year", "basis": "employer_provided", "sample_size": 1,
                               "low": 105000.0, "median": 105000.0, "high": 105000.0}]
    assert body["evidence"][0]["url"] == "https://jobicy.com/jobs/101-python-developer"


async def test_salary_without_evidence_says_so(client, signed_in):
    _, headers = signed_in()
    body = (await client.post(f"{API}/opportunities/salary", headers=headers, json={"role": "zebra keeper"})).json()
    assert body["groups"] == [] and "no verified salary evidence" in body["note"]


async def test_earning_plan(client, signed_in, fake_llm):
    _, headers = signed_in()
    interest = (await client.post(f"{API}/interests", headers=headers, json={"name": "Illustration", "interest_type": "creative"})).json()
    fake_llm.queue("EarningPlanDraft", {
        "title": "Commissioned portraits", "kind": "side_hustle", "readiness": "Build 5 samples first",
        "offer": "Pet portraits", "who_pays": "Pet owners", "what_you_need": ["Tablet"], "portfolio": "5 pieces",
        "find_customers": ["Local markets"], "test_demand": "Pre-sell 3", "costs_and_pricing": "Compare listings",
        "first_week": ["Make samples", "Post", "Ask friends"], "evaluate_results": "Track enquiries",
        "improve_next": "Raise quality", "cautions": ["Platform fees"],
    })
    response = await client.post(f"{API}/opportunities/plan", headers=headers, json={"interest_id": interest["id"]})
    assert response.status_code == 201
    plan = response.json()
    assert plan["plan"]["generated_by"] == "ai" and plan["interest_id"] == interest["id"]
    assert len((await client.get(f"{API}/opportunities/plans", headers=headers)).json()) == 1
    assert (await client.delete(f"{API}/opportunities/plans/{plan['id']}", headers=headers)).status_code == 204


async def test_opportunities_are_private(client, signed_in, fake_llm):
    _, alice = signed_in("alice@example.com")
    _, bob = signed_in("bob@example.com")
    fake_llm.queue("FitAssessments", fit(), fit())
    alice_job = (await client.post(f"{API}/opportunities/search", headers=alice, json={"query": "python"})).json()["results"][0]
    assert (await client.post(f"{API}/opportunities/{alice_job['id']}/save", headers=bob)).status_code == 404
    bob_results = (await client.post(f"{API}/opportunities/search", headers=bob, json={"query": "python"})).json()["results"]
    assert alice_job["id"] not in {r["id"] for r in bob_results}
