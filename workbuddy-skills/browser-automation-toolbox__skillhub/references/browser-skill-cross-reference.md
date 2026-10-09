# BrowserSkill Cross-Reference

## Status

BrowserSkill is **NOT** an engine in this toolbox's fallback chain. It is a **complementary tool** that the agent may recommend when the task profile matches. The user installs it independently on demand.

## What BrowserSkill Is

- **Repo**: https://github.com/Tencent/BrowserSkill (Tencent, MIT)
- **One-liner**: Local bridge that lets shell-capable AI Agents drive the user's real logged-in browser without disturbing their normal browsing.
- **Architecture**: `bsk` CLI + local daemon ↔ browser extension ↔ real browser (Chrome / Edge / Chromium). WebSocket on 127.0.0.1 only. **No cloud component.**
- **Maturity note**: Early stage (low commit count, few releases). Treat API/CLI as unstable; verify against the upstream repo before relying on any specific subcommand.

## Differentiated Capability (Why It Exists)

BrowserSkill solves a problem that none of `cloak / browser-act / kimi / playwright` in this toolbox solve:

> **Reusing the user's already-logged-in browser session**, in a separate Agent Window, without forcing a re-login in an isolated profile.

This is valuable when:

- The target site is an internal / personal system where creating a separate automation account is not allowed or impractical (e.g., personal WeChat, internal admin tools, paid subscriptions).
- The user is already logged in via their daily browser and the task is light (read, copy, summarize, click one button).
- Anti-bot / anti-detection is **not** a concern (the site trusts the user).
- The user wants to keep browsing their main window while the agent works in a separate Agent Window.

## When to Use BrowserSkill vs This Toolbox

Use this decision table when a browser task arrives. Pick the first row whose condition matches.

| Condition | Use |
|-----------|-----|
| Task needs to operate on the user's already-logged-in session AND the site is not anti-bot sensitive | **BrowserSkill** |
| Task is public-content scraping (XHS / B站 / 抖音 / 微博 / similar) | **This toolbox** (cloak or browser-act per platform override) |
| Task needs strong anti-detection on external sites | **This toolbox** (cloak first) |
| Task needs multi-engine fallback (high reliability) | **This toolbox** |
| Task needs headless batch processing | **This toolbox** (cloak headless / playwright) |
| Task is purely on local apps or automation-insensitive pages | **This toolbox** (playwright) |

If unsure, default to **this toolbox**. BrowserSkill is opt-in for the explicit "reuse my login" scenario.

## What BrowserSkill Does NOT Provide

- ❌ Anti-detection / anti-fingerprinting (no Chromium-layer patching, no CDP trace cleanup)
- ❌ Multi-engine fallback
- ❌ Platform-specific scraping patterns (XHS / B站 / 抖音 / 微博)
- ❌ Experience accumulation mechanism
- ❌ Headless batch mode (it operates a visible Agent Window by design)

If any of the above is required, BrowserSkill is the wrong tool.

## Installation (When the User Decides to Use It)

BrowserSkill is installed **independently** from this toolbox. Do not bundle it.

### Step 1 — Install `bsk` CLI

**macOS / Linux**:
```bash
curl -fsSL https://raw.githubusercontent.com/Tencent/BrowserSkill/main/install.sh | sh
```

**Windows (PowerShell)**:
```powershell
irm https://raw.githubusercontent.com/Tencent/BrowserSkill/main/install.ps1 | iex
```

Verify: `bsk --version`

### Step 2 — Install the browser extension

From Chrome Web Store: https://chromewebstore.google.com/detail/hhcmgoofomhgciiibhipgmgkgnoenaoi

### Step 3 — Install the agent skill (so the agent harness knows how to call `bsk`)

```bash
bsk install-skill
```

Use `Space` to select your agent harness (Cursor / Claude Code / Codex / OpenClaw / CodeBuddy / WorkBuddy / Pi / Hermes Agent), `Enter` to install.

Other shell-capable agents: manually copy `skill/SKILL.md` from the repo to the harness's skills directory.

## How the Two Coexist

```
┌─────────────────────────────────────────────────┐
│  Agent decides per task:                        │
│  ┌─────────────────┐    ┌────────────────────┐  │
│  │ browser-        │    │ BrowserSkill       │  │
│  │ automation-     │    │ (if installed)     │  │
│  │ toolbox         │    │                    │  │
│  │                 │    │ for: reuse user    │  │
│  │ for: scraping,  │    │ login, light task, │  │
│  │ anti-bot,       │    │ non-anti-bot       │  │
│  │ multi-engine    │    │ internal systems   │  │
│  │ fallback        │    │                    │  │
│  └─────────────────┘    └────────────────────┘  │
└─────────────────────────────────────────────────┘
```

The two do not call each other. They are parallel options the agent picks based on the task profile.

## Recommended Workflow When Recommending BrowserSkill

1. Confirm the task genuinely matches BrowserSkill's profile (see decision table above).
2. Check whether `bsk` is already installed: `bsk --version` (exit 0 = installed).
3. If not installed, **ask the user** whether they want to install it now (do not auto-install).
4. If the user agrees, run the install commands in Step 1–3 above.
5. After install, the user's agent harness will pick up BrowserSkill's own `SKILL.md`. The user can then invoke it via `/browser-skill ...` (or equivalent).
6. Record any platform-specific lesson learned during the BrowserSkill run into this toolbox's `references/platform-scraping-patterns.md` only if the lesson is also applicable to the cloak/browser-act engines. BrowserSkill-specific quirks belong in BrowserSkill's own repo issues, not here.

## Maintenance Notes

- This document is a **pointer**, not a mirror. Always verify install commands and extension URL against the upstream repo before recommending.
- If BrowserSkill graduates to stable maturity (50+ commits, stable API), revisit the option of integrating it as a 5th engine in this toolbox.
- If BrowserSkill adds anti-detection or platform scraping capabilities, the boundary between the two tools may blur — re-evaluate the split at that point.
