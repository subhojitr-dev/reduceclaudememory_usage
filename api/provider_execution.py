"""Shared provider execution primitive for API product handlers."""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator, Callable
from typing import Any

from loguru import logger

from config.settings import Settings
from core.anthropic import get_token_count
from core.trace import api_messages_request_snapshot, trace_event, traced_async_stream
from providers.base import BaseProvider
from providers.error_mapping import is_retryable_via_different_provider, map_error

from .model_router import ResolvedModel, RoutedMessagesRequest

TokenCounter = Callable[[list[Any], str | list[Any] | None, list[Any] | None], int]
ProviderGetter = Callable[[str], BaseProvider]


class ProviderExecutionService:
    """Resolve a provider and execute one routed Anthropic Messages stream."""

    def __init__(
        self,
        settings: Settings,
        provider_getter: ProviderGetter,
        *,
        token_counter: TokenCounter = get_token_count,
    ) -> None:
        self._settings = settings
        self._provider_getter = provider_getter
        self._token_counter = token_counter

    def stream(
        self,
        routed: RoutedMessagesRequest,
        *,
        wire_api: str,
        raw_log_label: str,
        raw_log_payload: Any,
    ) -> AsyncIterator[str]:
        candidates = routed.candidates or (routed.resolved,)
        complete_event, interrupted_event = self._trace_events(wire_api)

        if len(candidates) == 1:
            # Single-provider config: unchanged behavior, pure passthrough
            # streaming (no buffering, no added latency).
            _, agen, request_id = self._prepare_attempt(
                routed,
                candidates[0],
                wire_api=wire_api,
                raw_log_label=raw_log_label,
                raw_log_payload=raw_log_payload,
            )
            return traced_async_stream(
                agen,
                stage="egress",
                source="api",
                complete_event=complete_event,
                interrupted_event=interrupted_event,
                chunk_event=None,
                extra={
                    "request_id": request_id,
                    "provider_id": candidates[0].provider_id,
                    "gateway_model": routed.request.model,
                },
            )

        return traced_async_stream(
            self._stream_with_fallback(
                routed,
                candidates,
                wire_api=wire_api,
                raw_log_label=raw_log_label,
                raw_log_payload=raw_log_payload,
            ),
            stage="egress",
            source="api",
            complete_event=complete_event,
            interrupted_event=interrupted_event,
            chunk_event=None,
            extra={
                "gateway_model": routed.request.model,
                "candidate_count": len(candidates),
            },
        )

    @staticmethod
    def _trace_events(wire_api: str) -> tuple[str, str]:
        if wire_api == "responses":
            return "api.responses.stream_completed", "api.responses.stream_interrupted"
        return "api.response.stream_completed", "api.response.stream_interrupted"

    def _prepare_attempt(
        self,
        routed: RoutedMessagesRequest,
        candidate: ResolvedModel,
        *,
        wire_api: str,
        raw_log_label: str,
        raw_log_payload: Any,
    ) -> tuple[BaseProvider, AsyncIterator[str], str]:
        """Resolve the provider for one candidate and build its stream.

        Raises the provider's own exception (unmapped) on preflight failure,
        same as before this feature existed for the single-candidate path.
        """
        provider = self._provider_getter(candidate.provider_id)
        provider.preflight_stream(
            routed.request,
            thinking_enabled=candidate.thinking_enabled,
        )

        route_trace: dict[str, Any] = {
            "stage": "routing",
            "event": "api.route.resolved",
            "source": "api",
            "provider_id": candidate.provider_id,
            "provider_model": candidate.provider_model,
            "provider_model_ref": candidate.provider_model_ref,
            "gateway_model": routed.request.model,
            "thinking_enabled": candidate.thinking_enabled,
        }
        if wire_api == "responses":
            route_trace["wire_api"] = "responses"
        trace_event(**route_trace)

        request_id = f"req_{uuid.uuid4().hex[:12]}"
        trace_event(
            stage="ingress",
            event=(
                "api.responses.request.received"
                if wire_api == "responses"
                else "api.request.received"
            ),
            source="api",
            message_count=len(routed.request.messages),
            snapshot=api_messages_request_snapshot(routed.request),
            request_id=request_id,
        )

        if self._settings.log_raw_api_payloads:
            logger.debug(f"{raw_log_label} [{{}}]: {{}}", request_id, raw_log_payload)

        input_tokens = self._token_counter(
            routed.request.messages,
            routed.request.system,
            routed.request.tools,
        )
        agen = provider.stream_response(
            routed.request,
            input_tokens=input_tokens,
            request_id=request_id,
            thinking_enabled=candidate.thinking_enabled,
        )
        return provider, agen, request_id

    async def _stream_with_fallback(
        self,
        routed: RoutedMessagesRequest,
        candidates: tuple[ResolvedModel, ...],
        *,
        wire_api: str,
        raw_log_label: str,
        raw_log_payload: Any,
    ) -> AsyncIterator[str]:
        """Attempt each candidate in order, falling back on retryable errors.

        Each candidate's response is fully buffered before anything is
        forwarded to the caller. This trades away time-to-first-byte (only
        when a fallback chain is actually configured) for the correctness
        guarantee that a client never observes a partial/duplicate stream
        (e.g. two `message_start` events) from a failed then retried attempt.
        """
        last_count = len(candidates)
        for index, candidate in enumerate(candidates):
            is_last = index == last_count - 1
            try:
                _, agen, request_id = self._prepare_attempt(
                    routed,
                    candidate,
                    wire_api=wire_api,
                    raw_log_label=raw_log_label,
                    raw_log_payload=raw_log_payload,
                )
                buffered = [chunk async for chunk in agen]
            except Exception as error:
                mapped = map_error(error)
                trace_event(
                    stage="provider",
                    event="provider.fallback.attempt_failed",
                    source="api",
                    provider_id=candidate.provider_id,
                    provider_model=candidate.provider_model,
                    attempt=index + 1,
                    total_candidates=last_count,
                    exc_type=type(mapped).__name__,
                    status_code=getattr(mapped, "status_code", None),
                )
                retryable = is_retryable_via_different_provider(mapped)
                if retryable and not is_last:
                    continue
                if retryable:
                    trace_event(
                        stage="provider",
                        event="provider.fallback.exhausted",
                        source="api",
                        total_candidates=last_count,
                        exc_type=type(mapped).__name__,
                    )
                raise mapped from error
            trace_event(
                stage="provider",
                event="provider.fallback.succeeded",
                source="api",
                provider_id=candidate.provider_id,
                provider_model=candidate.provider_model,
                attempt=index + 1,
                total_candidates=last_count,
                request_id=request_id,
            )
            for chunk in buffered:
                yield chunk
            return
