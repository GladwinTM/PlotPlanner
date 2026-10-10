import io

import pytest

from app.ai.llm_client import AIProviderError

API = "/api/v1"

RESUME = b"""Jane Doe
Software Engineer at Acme (2020-2024)
Skills: Python, SQL
Portfolio: https://janedoe.dev
"""


def extraction(**overrides):
    return {
        "is_resume": True,
        "summary": "A software engineer resume.",
        "facts": [
            {"kind": "skill", "value": "Python", "detail": None},
            {"kind": "experience", "value": "Software Engineer at Acme (2020-2024)", "detail": "Backend"},
            {"kind": "link", "value": "https://janedoe.dev", "detail": None},
            {"kind": "link", "value": "https://invented.example", "detail": None},
        ],
        **overrides,
    }


async def upload(client, headers, name, data, content_type="application/octet-stream"):
    return await client.post(f"{API}/documents", headers=headers, files={"file": (name, data, content_type)})


async def test_text_resume_creates_unconfirmed_facts(client, signed_in, fake_llm):
    _, headers = signed_in()
    fake_llm.queue("DocumentExtraction", extraction())
    response = await upload(client, headers, "resume.txt", RESUME)
    assert response.status_code == 201, response.text
    document = response.json()
    assert document["processing_status"] == "processed" and document["content_type"] == "text/plain"
    values = [f["value"] for f in document["facts"]]
    assert "https://invented.example" not in values  # links must appear verbatim
    assert len(values) == 3 and not any(f["confirmed"] for f in document["facts"])
    assert "<document>" in fake_llm.calls[0]["messages"][0]["content"]

    # Unconfirmed facts are excluded from AI context until confirmed.
    assert (await client.get(f"{API}/profile/facts?confirmed=true", headers=headers)).json() == []
    fact = document["facts"][0]
    confirmed = (await client.patch(f"{API}/profile/facts/{fact['id']}", headers=headers, json={"confirmed": True})).json()
    assert confirmed["confirmed"] is True


async def test_docx_and_pdf_extraction(client, signed_in, fake_llm):
    import docx
    import pymupdf

    _, headers = signed_in()
    word = docx.Document()
    word.add_paragraph("Experienced illustrator with Procreate skills")
    buffer = io.BytesIO()
    word.save(buffer)
    fake_llm.queue("DocumentExtraction", extraction(facts=[{"kind": "skill", "value": "Procreate", "detail": None}]))
    response = await upload(client, headers, "cv.docx", buffer.getvalue())
    assert response.status_code == 201 and response.json()["processing_status"] == "processed"
    assert "Procreate" in response.json()["text_preview"]

    pdf = pymupdf.open()
    page = pdf.new_page()
    page.insert_text((72, 72), "Certified scrum master")
    fake_llm.queue("DocumentExtraction", extraction(facts=[]))
    response = await upload(client, headers, "cert.pdf", pdf.tobytes())
    assert response.status_code == 201
    assert "Certified scrum master" in response.json()["text_preview"]


@pytest.mark.parametrize("name,data,code", [
    ("resume.exe", b"MZ...", "unsupported_file_type"),
    ("fake.pdf", b"not a pdf", "invalid_file_content"),
    ("fake.docx", b"PK\x03\x04garbage", "invalid_file_content"),
    ("binary.txt", b"abc\x00def", "invalid_file_content"),
    ("empty.txt", b"", "empty_file"),
])
async def test_rejects_invalid_files(client, signed_in, name, data, code):
    _, headers = signed_in()
    response = await upload(client, headers, name, data)
    assert response.status_code == 400
    assert response.json()["error"]["code"] == code
    assert (await client.get(f"{API}/documents", headers=headers)).json() == []


async def test_rejects_oversized_files(client, signed_in, settings):
    _, headers = signed_in()
    data = b"a" * (settings.max_upload_size_mb * 1024 * 1024 + 1)
    response = await upload(client, headers, "big.txt", data)
    assert response.status_code == 413


async def test_ai_failure_keeps_document_with_clear_status(client, signed_in, fake_llm):
    _, headers = signed_in()
    fake_llm.queue("DocumentExtraction", AIProviderError())
    document = (await upload(client, headers, "notes.txt", b"Some notes about painting")).json()
    assert document["processing_status"] == "failed"
    assert "analysis failed" in document["error"]
    assert document["text_length"] > 0


async def test_delete_removes_file_and_unconfirmed_facts(client, signed_in, fake_llm):
    _, headers = signed_in()
    fake_llm.queue("DocumentExtraction", extraction())
    document = (await upload(client, headers, "resume.txt", RESUME)).json()
    keep = document["facts"][0]
    await client.patch(f"{API}/profile/facts/{keep['id']}", headers=headers, json={"confirmed": True})
    assert (await client.delete(f"{API}/documents/{document['id']}", headers=headers)).status_code == 204
    assert (await client.get(f"{API}/documents/{document['id']}", headers=headers)).status_code == 404
    facts = (await client.get(f"{API}/profile/facts", headers=headers)).json()
    assert [f["value"] for f in facts] == [keep["value"]] and facts[0]["document_id"] is None


async def test_documents_are_private(client, signed_in, fake_llm):
    _, alice = signed_in("alice@example.com")
    _, bob = signed_in("bob@example.com")
    fake_llm.queue("DocumentExtraction", extraction())
    document = (await upload(client, alice, "resume.txt", RESUME)).json()
    assert (await client.get(f"{API}/documents/{document['id']}", headers=bob)).status_code == 404
    assert (await client.delete(f"{API}/documents/{document['id']}", headers=bob)).status_code == 404
    assert (await client.patch(f"{API}/profile/facts/{document['facts'][0]['id']}", headers=bob, json={"confirmed": True})).status_code == 404


async def test_chat_document_search_is_scoped(client, signed_in, fake_llm):
    _, alice = signed_in("alice@example.com")
    _, bob = signed_in("bob@example.com")
    fake_llm.queue("DocumentExtraction", extraction())
    await upload(client, alice, "resume.txt", RESUME)
    fake_llm.chat_replies.extend([[("search_my_documents", {"query": "Acme"})], "Found it."])
    await client.post(f"{API}/chat", headers=alice, json={"message": "Where did I work?"})
    assert "Acme" in fake_llm.calls[-1]["messages"][-1]["content"]
    fake_llm.chat_replies.extend([[("search_my_documents", {"query": "Acme"})], "Nothing."])
    await client.post(f"{API}/chat", headers=bob, json={"message": "Where did I work?"})
    assert "Acme" not in fake_llm.calls[-1]["messages"][-1]["content"]
