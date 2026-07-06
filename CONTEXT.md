# CONTEXT — Managing Claude Usage

Read this first at the start of any session touching this project. This directory (`C:\Users\subho\reduceclaudememory_usage`) is the home base for everything related to reducing/managing Claude Code token usage — it hosts the `free-claude-code` proxy source, and this doc tracks the broader strategy (MCP trimming, PrintingPress) even though those tools live elsewhere on the machine.

## Why this project exists

Claude usage (5-hour reset window) started depleting much faster than before. Root cause identified: many MCP servers connected simultaneously across concurrent Claude Code projects (Gmail, Figma, Canva, TradingView, Calendar, computer-use, Chrome, etc.) — each connected MCP server loads its full tool schema into context on every turn, whether used or not. Three complementary strategies are in progress:

## Strategy 1 — free-claude-code proxy (this repo's code)

**What it is:** a local proxy (`fcc-server`) that impersonates Anthropic's API. Running `fcc-claude` instead of `claude` points Claude Code at the proxy, which forwards requests to a configured alternate provider (DeepSeek, NVIDIA NIM, OpenRouter, Gemini, local Ollama, etc.) instead of real Claude. It's a full swap per session, not a smart hybrid router — no automatic fallback based on availability. See [Interpret.md](Interpret.md) for the full layman's explainer.

**Status:** repo cloned only (see [SETUP.md](SETUP.md)). `uv` 0.11.7 and Python 3.14.3 already present. **Not yet installed/configured** — no `fcc-server` run, no `~/.fcc/.env`, no provider API key chosen or entered.

**Plan when picked back up:**
1. Get a free API key (recommended: DeepSeek or Kimi K2 — closest coding quality to Claude among free/cheap options).
2. Either run the official installer (`scripts/install.ps1`) or create `~/.fcc/.env` directly (see `.env.example` for all keys) with `DEEPSEEK_API_KEY` + `MODEL="deepseek/deepseek-chat"` (or chosen provider).
3. Run `fcc-server`, verify Admin UI at `http://127.0.0.1:8082/admin`.
4. Use `fcc-claude` instead of `claude` in **new/low-stakes projects only**. For near-completion projects, keep using real `claude` for core logic; only use `fcc-claude` there for isolated, easily-reviewable tasks (docs, boilerplate).

## Strategy 2 — MCP server trimming (no install needed, do anytime)

Disconnect MCP servers not needed for the current task/project (e.g. Figma, Gmail when idle); reconnect only when actually needed. This is manual, per-session — there is no auto-fallback. Git/GitHub already use the token-cheap path (Bash + `gh` CLI, not MCP) so no action needed there. Confirmed in this project: no Supabase or Vercel MCP server is connected — those integrations happen via the app's own SDK/CLI calls, outside Claude entirely, so no token overhead exists there either.

## Strategy 3 — PrintingPress (installed 2026-07-05, see SETUP.md)

**What it is:** generates lightweight local Go CLIs (+ Claude Code skills) instead of relying on MCP servers for API/website access. Benchmark cited: MCP used ~35x more tokens than the CLI equivalent on the same task, with MCP reliability dropping on harder tasks while CLIs held steady.

**Installed:** Go 1.26.4, `cli-printing-press` v4.27.1 generator binary, 9 factory skills (`printing-press`, `-amend`, `-import`, `-output-review`, `-polish`, `-publish`, `-reprint`, `-retro`, `-score`), plus the `printing-press-library` discovery skill for the 50+ prebuilt CLI catalog. Full command log in [SETUP.md](SETUP.md).

**Status (2026-07-05): DONE.** Gmail CLI generated at `C:\Users\subho\printing-press\library\gmail` (`gmail-pp-cli`), OAuth installed-app flow set up and verified live against the real Gmail account (messages, labels, digest all confirmed working). Passed `/printing-press-polish` (90/100 scorecard). **The Gmail MCP server can be disconnected now** — see [SETUP.md](SETUP.md) 2026-07-05 entry for full detail.

**Already-available library CLIs relevant to other projects:** Supabase CLI (PostgREST/Auth/Storage/Edge Functions) and a Vercel admin CLI both reportedly exist in the library — relevant if Claude is ever wired to manage those services conversationally (not needed today, since those connections are handled outside Claude already).

## Pending task — provider/model fallback chain for free-claude-code

**Confirmed gap (read 2026-07-05):** `api/model_router.py`'s `ModelRouter.resolve()` maps each Claude tier (Opus/Sonnet/Haiku) to exactly **one** fixed `provider/model` ref via `Settings.model_opus/model_sonnet/model_haiku/model`. There is no ordered list of providers/keys to fall back through. `providers/transports/*/recovery.py` only retries a broken *stream* against the *same* provider (mid-stream reconnect), not a switch to a different provider on failure (auth error, rate limit, timeout, etc.).

**Idea:** let each tier be configured with an **ordered list** of provider/model refs (e.g. `MODEL_SONNET="deepseek/deepseek-chat,open_router/openrouter/free,ollama/llama3.1"`) so that if the first provider errors (auth failure, rate limit, timeout, 5xx), the router automatically tries the next one in the list before giving up.

**Not yet implemented — this is a real feature to build, not a config toggle.** When ready to pick this up, start a new session in `C:\Users\subho\reduceclaudememory_usage` and use this prompt:

> Read CLAUDE.md and CONTEXT.md in this repo first. I want to add an ordered provider/model fallback chain to the model routing so that if one configured provider fails (auth error, rate limit / 429, timeout, or 5xx from the upstream), the proxy automatically retries the same logical request against the next provider/model in a configured list, instead of just failing the whole request. Currently `Settings.model_opus/model_sonnet/model_haiku/model` (config/settings.py) and `ModelRouter.resolve()` (api/model_router.py) only support a single provider/model ref per tier — there is no fallback list, and `providers/transports/*/recovery.py` only retries within the same provider/stream, not across providers.
>
> Design and implement this end-to-end, following CLAUDE.md's architecture principles (DRY, shared base classes, no provider-specific leakage into base config, no type ignores) and its cognitive workflow (analyze → plan → execute → verify → propagate). Specifically:
> 1. Decide the config format for an ordered list per tier (e.g. comma-separated `provider/model` refs in the existing env vars, or new `MODEL_SONNET_FALLBACKS`-style vars — pick whichever fits the existing `.env.example` conventions best) and update `.env.example` + `config/settings.py` accordingly.
> 2. Update `ModelRouter` (or introduce a new component) to resolve a tier to an ordered list of `ResolvedModel` candidates instead of a single one.
> 3. Update `ProviderExecutionService.stream()` (api/provider_execution.py) or the calling handlers to catch failures classified as retryable-via-different-provider (check `providers/error_mapping.py` for existing error classification) and re-attempt with the next candidate, logging/tracing each attempt via the existing `trace_event`/`logger` patterns.
> 4. Add tests covering: single-provider config (unchanged behavior), multi-provider fallback triggering on a simulated auth/rate-limit/timeout failure, and exhausting all candidates (should surface a clear final error).
> 5. Update README.md's "Mix Providers By Model Tier" section to document the new fallback capability.
> 6. Bump `pyproject.toml` version per CLAUDE.md's versioning rules (this is a MINOR feature addition) and run `uv lock`.
> 7. Run `./scripts/ci.sh` (or `.ps1` on Windows) before considering this done.
>
> Ask me before starting if the config-format choice (env var shape) needs my input; otherwise proceed and report back with [Files Changed], [Logic Altered], [Verification Method], [Residual Risks] per CLAUDE.md's summary standard.
