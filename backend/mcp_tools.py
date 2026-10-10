"""A narrow MCP façade over PlotPlanner's domain services.

No database connection belongs here. This is intentional: an MCP host can only
use the same profile and retrieval capabilities that application callers use.
"""
from uuid import UUID

import httpx
from fastmcp import FastMCP
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    profile_service_url: str = "http://localhost:8001"
    knowledge_service_url: str = "http://localhost:8002"
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
mcp = FastMCP("PlotPlanner")


@mcp.tool()
async def get_profile_context(profile_id: UUID) -> dict:
    """Retrieve the explicit interests and goals for one authorized profile."""
    async with httpx.AsyncClient(base_url=settings.profile_service_url, timeout=10) as client:
        response = await client.get(f"/v1/profiles/{profile_id}")
        response.raise_for_status()
        return response.json()


@mcp.tool()
async def search_profile_evidence(profile_id: UUID, query: str, limit: int = 5) -> list[dict]:
    """Find grounded personal evidence. Use it before suggesting a career experiment."""
    async with httpx.AsyncClient(base_url=settings.knowledge_service_url, timeout=20) as client:
        response = await client.post("/v1/search", json={"profile_id": str(profile_id), "query": query, "limit": limit})
        response.raise_for_status()
        return response.json()


if __name__ == "__main__":
    # Deployment places OAuth/user authorization in front of this Streamable HTTP
    # endpoint; the tools remain resource-scoped regardless of the host.
    mcp.run(transport="http", host="0.0.0.0", port=8000)
