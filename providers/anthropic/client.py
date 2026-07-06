"""Real Anthropic API provider (console.anthropic.com) - a native passthrough."""

from __future__ import annotations

from providers.base import ProviderConfig
from providers.defaults import ANTHROPIC_DEFAULT_BASE
from providers.transports.anthropic_messages import AnthropicMessagesTransport

_ANTHROPIC_VERSION = "2023-06-01"


class AnthropicProvider(AnthropicMessagesTransport):
    """Direct passthrough to the real Anthropic Messages API.

    Unlike every other provider in this proxy, this one calls the actual
    Claude API using the caller's own Anthropic billing/credits - it exists
    as an opt-in fallback-of-last-resort, not a default, since the whole
    point of this proxy is normally to avoid spending real Anthropic credits.
    """

    def __init__(self, config: ProviderConfig):
        super().__init__(
            config,
            provider_name="ANTHROPIC",
            default_base_url=ANTHROPIC_DEFAULT_BASE,
        )

    def _request_headers(self) -> dict[str, str]:
        """Real Anthropic uses x-api-key, not the Bearer scheme other providers use."""
        return {
            "Accept": "text/event-stream",
            "x-api-key": self._api_key,
            "Content-Type": "application/json",
            "anthropic-version": _ANTHROPIC_VERSION,
        }

    def _model_list_headers(self) -> dict[str, str]:
        return {
            "x-api-key": self._api_key,
            "anthropic-version": _ANTHROPIC_VERSION,
        }
