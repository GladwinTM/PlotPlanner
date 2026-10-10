"""The MCP endpoint is protected by the same Supabase token verification as the API."""
from httpx import ASGITransport, AsyncClient

INIT = {
    "jsonrpc": "2.0", "id": 1, "method": "initialize",
    "params": {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "test", "version": "1"}},
}
HEADERS = {"Accept": "application/json, text/event-stream", "Content-Type": "application/json"}


async def test_mcp_requires_valid_token(app, make_token, signed_in):
    user_id, _ = signed_in()
    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://localhost") as client:
            anonymous = await client.post("/mcp/", json=INIT, headers=HEADERS)
            assert anonymous.status_code == 401

            forged = await client.post("/mcp/", json=INIT, headers={**HEADERS, "Authorization": "Bearer not-a-jwt"})
            assert forged.status_code == 401

            valid = await client.post("/mcp/", json=INIT, headers={**HEADERS, "Authorization": f"Bearer {make_token(user_id)}"})
            assert valid.status_code == 200
            assert "PlotPlanner" in valid.text


async def test_mcp_tools_are_registered(app):
    from app.mcp_server import build_mcp

    names = {tool.name for tool in await build_mcp(app.state).list_tools()}
    assert names == {"search_learning_resources", "search_jobs", "get_course_details"}
