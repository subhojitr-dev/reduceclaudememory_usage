"""Tests for the real Anthropic API provider (opt-in passthrough)."""

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, patch

import pytest

from api.models.anthropic import Message, MessagesRequest
from config.constants import ANTHROPIC_DEFAULT_MAX_OUTPUT_TOKENS
from providers.anthropic import AnthropicProvider
from providers.base import ProviderConfig
from providers.defaults import ANTHROPIC_DEFAULT_BASE


@pytest.fixture
def anthropic_config():
    return ProviderConfig(
        api_key="sk-ant-test-key",
        base_url=ANTHROPIC_DEFAULT_BASE,
        rate_limit=10,
        rate_window=60,
        enable_thinking=True,
    )


@pytest.fixture(autouse=True)
def mock_rate_limiter():
    @asynccontextmanager
    async def _slot():
        yield

    with patch(
        "providers.transports.anthropic_messages.transport.GlobalRateLimiter"
    ) as mock:
        instance = mock.get_scoped_instance.return_value

        async def _passthrough(fn, *args, **kwargs):
            return await fn(*args, **kwargs)

        instance.execute_with_retry = AsyncMock(side_effect=_passthrough)
        instance.concurrency_slot.side_effect = _slot
        yield instance


@pytest.fixture
def anthropic_provider(anthropic_config):
    return AnthropicProvider(anthropic_config)


def test_init(anthropic_config):
    with patch("httpx.AsyncClient") as mock_client:
        provider = AnthropicProvider(anthropic_config)
    assert provider._api_key == "sk-ant-test-key"
    assert provider._base_url == ANTHROPIC_DEFAULT_BASE
    assert mock_client.called


def test_request_headers_use_x_api_key_not_bearer(anthropic_provider):
    """Real Anthropic uses x-api-key, unlike every other provider's Bearer scheme."""
    h = anthropic_provider._request_headers()
    assert h["x-api-key"] == "sk-ant-test-key"
    assert "Authorization" not in h
    assert h["anthropic-version"] == "2023-06-01"


def test_model_list_headers_use_x_api_key(anthropic_provider):
    h = anthropic_provider._model_list_headers()
    assert h["x-api-key"] == "sk-ant-test-key"
    assert h["anthropic-version"] == "2023-06-01"


def test_build_request_body_native_passthrough(anthropic_provider):
    request = MessagesRequest(
        model="claude-sonnet-4-5-20260514",
        max_tokens=50,
        messages=[Message(role="user", content="hi")],
    )
    body = anthropic_provider._build_request_body(request)
    assert body["model"] == "claude-sonnet-4-5-20260514"
    assert body["stream"] is True
    assert body["messages"][0]["role"] == "user"


def test_build_request_body_default_max_tokens(anthropic_provider):
    request = MessagesRequest(
        model="m",
        messages=[Message(role="user", content="x")],
    )
    body = anthropic_provider._build_request_body(request)
    assert body["max_tokens"] == ANTHROPIC_DEFAULT_MAX_OUTPUT_TOKENS


@pytest.mark.asyncio
async def test_cleanup_aclose(anthropic_provider):
    anthropic_provider._client = AsyncMock()

    await anthropic_provider.cleanup()

    anthropic_provider._client.aclose.assert_awaited_once()
