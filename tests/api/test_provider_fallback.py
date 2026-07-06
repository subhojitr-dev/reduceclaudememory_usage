"""Integration tests for the ordered provider/model fallback chain.

Exercises the full path: ModelRouter.resolve_candidates -> MessagesHandler ->
ProviderExecutionService.stream() -> providers/error_mapping classification.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

import pytest
from fastapi.responses import StreamingResponse

from api.handlers import MessagesHandler
from api.models.anthropic import Message, MessagesRequest
from config.settings import Settings
from providers.base import BaseProvider, ProviderConfig
from providers.exceptions import APIError, InvalidRequestError, ProviderError


class ScriptedProvider(BaseProvider):
    """Test double: either raises a scripted exception or yields a minimal SSE stream."""

    def __init__(self, *, fail_with: Exception | None = None) -> None:
        super().__init__(ProviderConfig(api_key="test"))
        self._fail_with = fail_with
        self.call_count = 0

    def preflight_stream(
        self, request: Any, *, thinking_enabled: bool | None = None
    ) -> None:
        return None

    async def cleanup(self) -> None:
        return None

    async def list_model_ids(self) -> frozenset[str]:
        return frozenset({"test-model"})

    async def stream_response(
        self,
        request: Any,
        input_tokens: int = 0,
        *,
        request_id: str | None = None,
        thinking_enabled: bool | None = None,
    ) -> AsyncIterator[str]:
        self.call_count += 1
        if self._fail_with is not None:
            raise self._fail_with
        yield 'event: message_start\ndata: {"type":"message_start"}\n\n'
        yield 'event: message_stop\ndata: {"type":"message_stop"}\n\n'


async def _streaming_body_text(response: StreamingResponse) -> str:
    parts = [
        chunk.decode("utf-8") if isinstance(chunk, bytes) else str(chunk)
        async for chunk in response.body_iterator
    ]
    return "".join(parts)


def _settings(**overrides: Any) -> Settings:
    settings = Settings()
    settings.model = "nvidia_nim/primary-model"
    settings.model_opus = None
    settings.model_sonnet = None
    settings.model_haiku = None
    for key, value in overrides.items():
        setattr(settings, key, value)
    return settings


def _request(model: str = "claude-2.1") -> MessagesRequest:
    return MessagesRequest(
        model=model,
        max_tokens=100,
        messages=[Message(role="user", content="hi")],
    )


@pytest.mark.asyncio
async def test_single_provider_config_is_unchanged() -> None:
    """No fallback configured: behavior matches the pre-fallback implementation."""
    provider = ScriptedProvider()
    settings = _settings()
    handler = MessagesHandler(settings, provider_getter=lambda _: provider)

    response = handler.create(_request())
    assert isinstance(response, StreamingResponse)
    body = await _streaming_body_text(response)

    assert "message_start" in body
    assert provider.call_count == 1


@pytest.mark.asyncio
async def test_single_provider_config_propagates_error_unchanged() -> None:
    """No fallback configured: an upstream failure surfaces exactly as before."""
    provider = ScriptedProvider(fail_with=APIError("boom", status_code=500))
    settings = _settings()
    handler = MessagesHandler(settings, provider_getter=lambda _: provider)

    with pytest.raises(ProviderError) as exc_info:
        response = handler.create(_request())
        assert isinstance(response, StreamingResponse)
        await _streaming_body_text(response)

    assert exc_info.value.status_code == 500
    assert provider.call_count == 1


@pytest.mark.asyncio
async def test_fallback_triggers_on_retryable_error_and_succeeds() -> None:
    """First candidate 5xx's; second candidate succeeds and its output is delivered."""
    failing = ScriptedProvider(fail_with=APIError("unavailable", status_code=503))
    succeeding = ScriptedProvider()
    providers = {"nvidia_nim": failing, "open_router": succeeding}

    settings = _settings(model_fallbacks="open_router/free-model")
    handler = MessagesHandler(
        settings, provider_getter=lambda provider_id: providers[provider_id]
    )

    response = handler.create(_request())
    assert isinstance(response, StreamingResponse)
    body = await _streaming_body_text(response)

    assert "message_start" in body
    assert failing.call_count == 1
    assert succeeding.call_count == 1


@pytest.mark.asyncio
async def test_fallback_does_not_trigger_on_non_retryable_error() -> None:
    """A 400-shaped failure is a client-request problem: no cross-provider retry."""
    failing = ScriptedProvider(fail_with=InvalidRequestError("bad request shape"))
    never_called = ScriptedProvider()
    providers = {"nvidia_nim": failing, "open_router": never_called}

    settings = _settings(model_fallbacks="open_router/free-model")
    handler = MessagesHandler(
        settings, provider_getter=lambda provider_id: providers[provider_id]
    )

    with pytest.raises(ProviderError) as exc_info:
        response = handler.create(_request())
        assert isinstance(response, StreamingResponse)
        await _streaming_body_text(response)

    assert isinstance(exc_info.value, InvalidRequestError)
    assert failing.call_count == 1
    assert never_called.call_count == 0


@pytest.mark.asyncio
async def test_fallback_exhausts_all_candidates_and_raises_clear_final_error() -> None:
    """Every configured candidate fails: a clear, final mapped error surfaces."""
    first = ScriptedProvider(fail_with=APIError("server error", status_code=500))
    second = ScriptedProvider(fail_with=APIError("overloaded", status_code=529))
    providers = {"nvidia_nim": first, "open_router": second}

    settings = _settings(model_fallbacks="open_router/free-model")
    handler = MessagesHandler(
        settings, provider_getter=lambda provider_id: providers[provider_id]
    )

    with pytest.raises(ProviderError) as exc_info:
        response = handler.create(_request())
        assert isinstance(response, StreamingResponse)
        await _streaming_body_text(response)

    # The final surfaced error reflects the LAST candidate attempted.
    assert isinstance(exc_info.value, APIError)
    assert exc_info.value.status_code == 529
    assert first.call_count == 1
    assert second.call_count == 1


@pytest.mark.asyncio
async def test_fallback_chain_of_three_stops_at_first_success() -> None:
    """A middle candidate succeeding stops the chain; the third is never tried."""
    first = ScriptedProvider(fail_with=APIError("server error", status_code=500))
    second = ScriptedProvider()
    third = ScriptedProvider()
    providers = {"nvidia_nim": first, "open_router": second, "ollama": third}

    settings = _settings(
        model_fallbacks="open_router/free-model,ollama/llama3.1",
    )
    handler = MessagesHandler(
        settings, provider_getter=lambda provider_id: providers[provider_id]
    )

    response = handler.create(_request())
    assert isinstance(response, StreamingResponse)
    body = await _streaming_body_text(response)

    assert "message_start" in body
    assert first.call_count == 1
    assert second.call_count == 1
    assert third.call_count == 0
