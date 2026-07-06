# Setup Log

Chronological record of what has actually been installed/configured on this machine (subho, Windows 11) for the Claude-usage-reduction effort. Update this file each time a new install step is completed.

## 2026-07-04 — Repo clone

```powershell
cd C:\Users\subho\reduceclaudememory_usage
git clone https://github.com/Alishahryar1/free-claude-code.git .
```

Status: source cloned only. **Not yet installed/configured** — no `fcc-server` run, no `~/.fcc/.env`, no provider API key entered anywhere.

## 2026-07-05 — Go installed

```powershell
winget install GoLang.Go --accept-package-agreements --accept-source-agreements
```

Result: Go 1.26.4 installed system-wide (satisfies PrintingPress's `Go 1.26.3+` requirement).

Verify:
```powershell
go version
# go version go1.26.4 windows/amd64
```

Note: after a fresh `winget install`, PATH only updates in *new* terminal sessions — an already-open terminal needs:
```powershell
$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
```

## 2026-07-05 — PrintingPress installed

Prerequisites already present: Go 1.26.4, Node v24.14.1 / npm 11.11.0.

The official one-liner installer (`scripts/install.sh` in `mvanhorn/cli-printing-press`) **rejects Git Bash on Windows** (OS check fails on `mingw64_nt-10.0-26200`, since it only recognizes `darwin`/`linux`). Ran the installer's two underlying steps directly instead:

**1. Generator binary (via `go install`):**
```bash
go install github.com/mvanhorn/cli-printing-press/v4/cmd/cli-printing-press@latest
```
Installs to `$(go env GOPATH)/bin` — on this machine: `C:\Users\subho\go\bin`. Ensure that directory is on PATH (add to a new terminal's PATH if `cli-printing-press` isn't found).

Verify:
```bash
cli-printing-press --version
# cli-printing-press 4.27.1
```

**2. Factory skills for Claude Code:**
```bash
npx -y skills@latest add mvanhorn/cli-printing-press/skills --skill "*" -g -y -a claude-code
```
Installed 9 skills to `~/.claude/skills/`: `printing-press`, `printing-press-amend`, `printing-press-import`, `printing-press-output-review`, `printing-press-polish`, `printing-press-publish`, `printing-press-reprint`, `printing-press-retro`, `printing-press-score`.

**3. Library discovery skill (separate repo, browses the 50+ prebuilt CLI catalog):**
```bash
npx skills add mvanhorn/printing-press-library/skills/printing-press-library -g -y
```
Installed `printing-press-library` skill. (One unrelated agent target, "PromptScript", failed to install — irrelevant, not used here.)

**Security note from the installer's own risk assessment:** `printing-press-amend` and `printing-press-retro` were flagged Med Risk / had a Snyk alert. These skills run with full agent permissions — review before invoking, especially before pointing anything at sensitive credentials (e.g. Gmail OAuth during the planned Gmail CLI generation).

**Action required after any skill install:** restart the Claude Code session (or start a new one) — skills installed mid-session are not picked up until restart.

## 2026-07-05 — Gmail CLI generated and verified

Generated via `/printing-press` at `C:\Users\subho\printing-press\library\gmail` (binary: `gmail-pp-cli`, module `gmail-pp-cli`). OAuth 2.0 installed-app flow (Desktop app client in Google Cloud project `gmail-cli`), credentials at `~/.gmail-cli/credentials.json`, token cached via the CLI's own config dir after `auth login`. Scopes: `gmail.readonly`, `gmail.send`, `gmail.labels`.

Covers: `messages` (list/get/send/trash/untrash/delete/modify/attachment-get), `threads` (list/get/modify/**timeline** novel), `labels` (list/get/create/delete), `drafts` (list/get/create/send/delete), plus novel commands `digest` (unread grouped by sender/label) and `threads timeline` (thread reconstruction from one live API call). `search`/`sync` come from the generator's framework (local SQLite FTS5 mirror).

**Verified live** against the real Gmail account: `auth login` (OAuth browser flow), `messages list`, `labels list`, `messages get`, `digest` all returned real data successfully.

Ran `/printing-press-polish`: scorecard 88→90/100, verify 100%, tools-audit 17→0 findings, PII-audit 7→0. `ship_recommendation: hold` only because of two **public-library publish gates** (GitHub handle for manifest attribution; formal `phase5-acceptance.json` from a non-interactive live-credential dogfood run) — not because the CLI is broken. Not publishing to the public library was not requested; the CLI is fully functional for personal/local use as-is.

Known pre-existing generator bug (Windows-specific, out of scope for the printed CLI): some `internal/cliutil`/`internal/mcp` generator-owned test suites fail on Windows (file-locking + path-resolution issues) — flagged as a spawned retro task, not fixed in the printed CLI per its own AGENTS.md rules.

**Gmail MCP server can now be disconnected** — this CLI replaces it per the [CONTEXT.md](CONTEXT.md) Strategy 3 plan.

### Not yet done
- `fcc-server` install/config (see [CONTEXT.md](CONTEXT.md) — separate track, no provider API key chosen yet)
- Optional: publish gmail CLI to the public printing-press-library (needs `git config github.user` set + a live-credential phase5 dogfood run) — not required for personal use
