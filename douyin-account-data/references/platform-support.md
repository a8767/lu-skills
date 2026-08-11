# Platform support

## macOS: Ego Lite

Full collection on macOS uses Ego Lite and the `ego-browser` command.

1. Open the official Ego Lite website at `https://lite.ego.app/` and download the Mac version from `https://lite.ego.app/zh-cn/download?auto=1`.
2. Install and launch it.
3. Complete onboarding so Ego Lite can install `ego-browser` and its Agent Skill.
4. Log into the user's own Douyin Creator Center inside Ego Lite.
5. Reopen the Agent if it cannot discover the newly installed browser Skill.

Ego Lite supports Apple Silicon and Intel Macs. The browser login state stays in Ego Lite; this Skill must not extract it.

Run from the Skill repository root:

```bash
bash skills/douyin-account-data/scripts/collect.sh \
  --dashboard-root "<Personal AI Workbench root>" \
  --vault-root "<private knowledge-base root>"
```

## Windows: bundled Playwright adapter

Windows collection is supported through the bundled headed Playwright adapter. It reproduces the macOS official-export coverage, then reuses the same inventory, analysis, Workbench contract, quality gates, rollback, and atomic publishing code.

Prerequisites:

- Python 3.10 or newer;
- Node.js 20 or newer;
- a private knowledge-base directory;
- permission to access the Douyin Creator Center account being collected.

From PowerShell in the Skill repository root, install an isolated environment and Playwright Chromium:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r skills\douyin-account-data\requirements-windows.txt
.\.venv\Scripts\python.exe -m playwright install chromium
.\.venv\Scripts\python.exe skills\douyin-account-data\scripts\collect_playwright.py --check
```

Then collect and publish:

```powershell
.\.venv\Scripts\python.exe skills\douyin-account-data\scripts\collect_playwright.py `
  --dashboard-root "<Personal AI Workbench root>" `
  --vault-root "<private knowledge-base root>"
```

The first run opens a visible Chromium window. The user completes QR login or any account confirmation in that window; the adapter continues after the Creator Center is ready. Later runs reuse the dedicated profile stored by default under the current Windows user's local application-data directory.

Optional browser choices:

```powershell
# Use an installed Microsoft Edge instead of Playwright Chromium.
.\.venv\Scripts\python.exe skills\douyin-account-data\scripts\collect_playwright.py `
  --browser-channel msedge `
  --dashboard-root "<Personal AI Workbench root>" `
  --vault-root "<private knowledge-base root>"
```

Use `--profile-dir` only when a different dedicated directory is required. It must remain outside the public Skill repository, Workbench, and private knowledge base. Never point the adapter at a person's normal Chrome or Edge profile.

## Browser and privacy model

The Playwright adapter:

1. launches a headed persistent context with a dedicated local profile;
2. lets the user perform login and verification directly in the real browser window;
3. navigates only visible Creator Center pages and clicks official export controls;
4. does not read cookies, serialize authentication state, intercept responses, or call private endpoints;
5. writes Excel files and necessary page evidence to a unique system temporary directory;
6. deletes temporary capture material on success or failure;
7. preserves the last valid `current.json` unless the complete quality gate passes.

Playwright's documentation warns that authentication state can contain reusable cookies and headers, and current Chrome policy does not support automating the normal default profile. See:

- `https://playwright.dev/docs/auth`
- `https://playwright.dev/docs/api/class-browsertype#browser-type-launch-persistent-context`

## Linux

Linux can run Workbench, the synthetic demo, and public-web research. The browser adapter uses cross-platform Playwright APIs, but the Douyin Creator Center flow has not been validated on Linux. Use manually downloaded official Excel files unless the user explicitly accepts an experimental run and the same quality gates pass.

## Implementation references

- `XBuilderLAB/cheat-on-content`: persistent Playwright profile, QR login, and shared browser-session patterns. This Skill does not use its response-interception strategy.
- `NanmiCoder/MediaCrawler`: Windows Chrome/Edge discovery, persistent contexts, login handoff, and standard-mode fallback. Its license differs, so this repository treats it as an architecture reference and does not copy its source.
