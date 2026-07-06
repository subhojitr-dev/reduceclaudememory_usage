# Token/Cost Comparison Tests

Two separate A/B tests. Each test needs **two brand-new, separate Claude Code sessions** — never reuse a window, and never run both halves of a test in the same session. Reusing a session carries over context from the first half and makes the `/cost` (or `/usage`) number meaningless for comparison.

`/cost` (aliased to `/usage` in recent builds) does not compare anything itself — it just reports the token/cost total for *that one session*. You run it once per session, write down the number, then hand both numbers to me afterward for interpretation.

---

## Test 1 — PrintingPress CLI vs. default (WebSearch/MCP) research

**What it measures:** whether answering a research question via a local `hackernews-pp-cli` (lightweight, lazy-loaded) costs fewer tokens than the default approach (WebSearch tool / live API fetch, more context-heavy).

### Session 1 — baseline (no CLI mentioned)
1. Open a brand-new terminal, start a fresh `claude` session, in any working directory (project path doesn't matter for this test).
2. Ask exactly:
   > What is Hacker News currently saying about AI coding agents — what are the recurring opinions/complaints?
3. Wait for the full response.
4. Type `/cost` (or `/usage`). Write down the number → **A**.
5. Close the session. Don't reuse it for anything else.

### Session 2 — CLI-directed
1. Open a **different**, brand-new terminal, start a fresh `claude` session.
2. Ask exactly:
   > Use the hackernews CLI to answer: What is Hacker News currently saying about AI coding agents — what are the recurring opinions/complaints?
3. Wait for the full response.
4. Type `/cost` (or `/usage`). Write down the number → **B**.
5. Close the session.

### Report back
Give me both numbers, A and B, plus which session actually used the CLI vs. fell back to something else (check the response — if PATH somehow isn't picked up in a given terminal, it may still fall back to WebSearch; note that if so).

---

## Test 2 — fcc-claude (OpenRouter free models) vs. real Claude

**What it measures:** token/dollar cost difference between routing a coding request through real Claude vs. through the `free-claude-code` proxy (OpenRouter free-tier models, with fallback chain).

**Prerequisite (already done):** `.env` in `C:\Users\subho\reduceclaudememory_usage` has `OPENROUTER_API_KEY` set, with:
- Primary model: `open_router/qwen/qwen3-next-80b-a3b-instruct:free`
- Fallback chain: `nvidia/nemotron-3-super-120b-a12b:free` → `meta-llama/llama-3.3-70b-instruct:free` (Sonnet tier also falls back to real `anthropic/claude-sonnet-5` as a last resort)

### Session 1 — real Claude (baseline)
1. Open a brand-new terminal, start a fresh `claude` session (real Claude, not the proxy) in any project you'd normally use.
2. Ask a representative coding task — pick something concrete and repeatable, e.g.:
   > Write a Python function that takes a list of dicts and groups them by a given key, returning a dict of lists.
3. Wait for the full response.
4. Type `/cost` (or `/usage`). Write down the number → **A**.
5. Close the session.

### Session 2 — fcc-claude (proxy)
1. Open a **different**, brand-new terminal.
2. `cd C:\Users\subho\reduceclaudememory_usage`
3. Start the proxy-backed session instead of plain `claude`:
   ```
   uv run fcc-claude
   ```
   (Confirm `fcc-server` is running first — check `http://127.0.0.1:8082/admin` loads in a browser. It was already running as of 2026-07-05.)
4. Ask the **exact same** representative task as Session 1, word-for-word.
5. Wait for the full response.
6. Type `/cost` (or `/usage`). Write down the number → **B**.
7. Also note: which model actually answered (check the admin UI at `http://127.0.0.1:8082/admin` or the response itself) — since there's a 3-model fallback chain, it may not always be the primary model.
8. Close the session.

### Report back
Give me both numbers (A and B), plus:
- Which model actually served Session 2's request (primary or a fallback)
- Any noticeable quality difference in the two code answers (this is a cost test, not a quality test, but worth noting if the free model's answer was visibly worse/wrong — that's a real tradeoff, not just a number)

---

## Results Table (fill in after running both tests)

| Test | Session 1 (baseline) | Session 2 (alternate) | Difference | Notes |
|---|---|---|---|---|
| 1 — PrintingPress CLI vs. WebSearch | A = | B = | | |
| 2 — Real Claude vs. fcc-claude (OpenRouter) | A = | B = | | |

Bring me the filled-in numbers and I'll interpret the deltas and update the memory/CONTEXT.md with the outcome.
