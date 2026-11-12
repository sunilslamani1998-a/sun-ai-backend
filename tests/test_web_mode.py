from __future__ import annotations

import pytest
from pydantic import SecretStr

import agent
import research
from config import settings


@pytest.mark.asyncio
async def test_web_mode_returns_sources_without_constructing_gemini(monkeypatch):
    monkeypatch.setattr(settings, "assistant_mode", "web")

    async def fake_search(query, max_results=5):
        assert query == "latest Android release"
        assert max_results == 5
        return [{
            "title": "Android release notes",
            "url": "https://example.test/android",
            "content": "The release notes describe recent platform changes.",
            "published_date": None,
        }]

    def unexpected_gemini_client(*args, **kwargs):
        raise AssertionError("Web-only mode must not initialize Gemini.")

    monkeypatch.setattr(research, "search_web", fake_search)
    monkeypatch.setattr(agent, "_get_client", unexpected_gemini_client)

    response = await agent.ask_ai("latest Android release")
    assert "no generative AI model was used" in response
    assert "https://example.test/android" in response


@pytest.mark.asyncio
async def test_web_mode_requires_tavily_key_when_not_configured(monkeypatch):
    monkeypatch.setattr(settings, "assistant_mode", "web")
    monkeypatch.setattr(settings, "tavily_api_key", SecretStr(""))

    with pytest.raises(agent.AgentConfigurationError, match="TAVILY_API_KEY"):
        await agent.ask_ai("weather today")
