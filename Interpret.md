# What This Tool Actually Does

**Correction to your assumption first:** this does NOT intelligently switch to a free model "only when needed" while otherwise using real Claude. It's a full swap — it runs a local proxy that pretends to be Anthropic's API, and Claude Code sends ALL its requests to that proxy instead of Anthropic's servers. The proxy then forwards those requests to whatever model/provider you configured (free or paid, but not Claude). So when you use this, you are not using Anthropic's Claude models at all — you're using a different LLM (DeepSeek, Gemini, Kimi, local Ollama models, etc.) but through the same `claude` command-line interface and UI you're used to.

In short: it doesn't reduce Claude usage inside a session — it **replaces Claude entirely** for that session with another (often free) model, while keeping the Claude Code tool/interface.

## How It Works (layman's terms)

1. Claude Code CLI normally sends your prompts to `api.anthropic.com`.
2. This tool starts a small local server on your machine (`fcc-server`) that looks exactly like Anthropic's API to Claude Code.
3. You point Claude Code at this local server instead (via environment variables), using a special launcher command `fcc-claude` instead of `claude`.
4. The local server takes your request, translates it, and sends it to whichever real LLM provider you picked (e.g. NVIDIA NIM, OpenRouter, Gemini, DeepSeek, Groq, or a model running locally on your own PC via Ollama/LM Studio).
5. The response gets translated back into the format Claude Code expects, so Claude Code has no idea it's not talking to real Claude.

Net effect: same interface, different (usually cheaper/free) brain behind it.

## Prerequisites

- **Python 3.14** and **uv** (a Python package manager) — the install script installs these for you if missing.
- **Claude Code CLI** already installed (or the installer installs it).
- An API key from at least one supported provider, OR a locally-running model (Ollama / LM Studio / llama.cpp — no key needed, runs on your machine, fully free but uses your own GPU/CPU).
  - Good free/cheap options: **NVIDIA NIM** (free key, generous), **OpenRouter** (has free-tagged models), **Google Gemini** (free tier).
- Windows, since you're on Win11: PowerShell install script works fine.

## Setup Steps

1. Install (PowerShell):
   ```powershell
   irm "https://github.com/Alishahryar1/free-claude-code/blob/main/scripts/install.ps1?raw=1" | iex
   ```
2. Start the proxy:
   ```powershell
   fcc-server
   ```
   It prints an Admin UI URL like `http://127.0.0.1:8082/admin`.
3. Open that Admin UI in your browser, paste an API key for one provider (e.g. `NVIDIA_NIM_API_KEY`), click **Validate** then **Apply**.
4. Set the `MODEL` field to the model slug you want (default is already filled in for NVIDIA NIM).
5. Instead of running `claude` to start a session, run:
   ```powershell
   fcc-claude
   ```
   This launches Claude Code pointed at your local proxy instead of Anthropic.

Keep `fcc-server` running in the background any time you want to use `fcc-claude`.

## Using It With Any Project

This is **project-agnostic** by design — the proxy runs globally on your machine, not inside any repo. To use it with any of your projects (Immigration Web App, TradingView, Election Forecast, etc.):

1. Make sure `fcc-server` is running (once, in any terminal).
2. `cd` into whichever project directory you want to work on.
3. Run `fcc-claude` there instead of `claude`.

That's it — no per-project config needed. Claude Code will behave normally (same file access, same working directory), it's just answering your prompts with a different underlying model.

## Important Caveats

- **Quality tradeoff**: free/cheap models are generally weaker than Claude Sonnet/Opus at coding tasks — expect more mistakes, especially on complex multi-file work.
- **This does not save your real Claude Code usage/quota in a hybrid way.** While `fcc-claude` is active, you are 100% on the alternate model — not blending with Anthropic's models at all. If you want actual Claude (Sonnet/Opus) for a task, just run plain `claude` instead (don't use `fcc-claude` for that session).
- Some "free" providers have rate limits or require signup; local models (Ollama etc.) are the only truly unlimited/free option but need your own hardware and are typically much weaker.
- Running two systems (`fcc-server` proxy + your normal `claude` installs) side by side is fine — you choose per-session which command to run.
