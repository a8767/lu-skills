---
name: douyin-account-data
description: Collect the user's own authorized Douyin Creator Center analytics on macOS or Windows, validate the official exports, and update the complete data contract consumed by Personal AI Workbench. Use when the user asks to pull, refresh, validate, or display their own Douyin account data in the Workbench. Do not use for other creators, public-account scraping, private messages, content strategy, or topic recommendations.
---

# Douyin Account Data

## Scope

Only collect data from a Douyin Creator Center account that the user has explicitly authorized. Use Ego Lite on macOS or the bundled Playwright adapter on Windows. Produce data facts for Personal AI Workbench; do not generate content recommendations, account strategy, or publishing actions.

The Windows adapter uses a dedicated local browser profile and the same official-export, validation, and atomic-publish pipeline as macOS. Linux remains unverified; on Linux, explain the limitation and use manually downloaded official Excel files unless the user explicitly asks to test the adapter there. Never claim partial data is complete.

## Required inputs

Resolve both paths before collection:

- Personal AI Workbench root containing `Workbench/server/vault-index.mjs`.
- A private knowledge-base root where `30_self_media/douyin/` may be written.

Prefer paths explicitly provided by the user, then `PERSONAL_DASHBOARD_ROOT` and `PERSONAL_DASHBOARD_VAULT_ROOT`. If either path remains unknown, ask the user. Never guess a username, home directory, repository name, or Vault name.

Read [platform-support.md](references/platform-support.md) when setup, Ego Lite, login, Windows, or Linux is involved. Read [data-contract.md](references/data-contract.md) before changing collection coverage or the Workbench output schema.

## Safety gate

Before running:

1. Confirm the account belongs to the user or the user is authorized to access it.
2. On macOS, confirm Ego Lite is installed and onboarding is complete. On Windows, confirm the Playwright requirements and Chromium browser are installed.
3. On macOS, confirm the user has logged into Creator Center inside Ego Lite. On Windows, open the headed Playwright browser and let the user complete first-run QR login or verification there.
4. Confirm the target knowledge base is private and is not the public synthetic demo directory in a Git repository.
5. Confirm `node`, Python, and `openpyxl` are available. macOS also requires `jq` and `ego-browser`; Windows requires the Python `playwright` package and an installed Playwright Chromium browser.

Never read, print, copy, or export cookies, passwords, login tokens, or session parameters. On Windows, Playwright may keep the user's login state only inside its dedicated local profile outside the Skill repository, Workbench, and Vault; never inspect, copy, or commit that directory. Let the user complete first-run QR login in the visible browser. Stop and hand control back on CAPTCHA, phone confirmation, account selection, permission denial, or rate limiting.

## Collect and publish

On macOS, run the Ego Lite entry point:

```bash
bash <本 Skill 目录>/scripts/collect.sh \
  --dashboard-root <Personal AI Workbench 根目录> \
  --vault-root <私人知识库根目录>
```

On Windows PowerShell, after completing the setup in [platform-support.md](references/platform-support.md), run:

```powershell
.\.venv\Scripts\python.exe skills\douyin-account-data\scripts\collect_playwright.py `
  --dashboard-root "<Personal AI Workbench 根目录>" `
  --vault-root "<私人知识库根目录>"
```

Do not run `scripts/playwright_collect.py` directly for a normal collection. It is the low-level browser backend; `collect_playwright.py` adds temporary-directory isolation, validation, rollback, and atomic publishing.

The script must:

1. Reuse the authorized login state from Ego Lite on macOS or the dedicated Playwright profile on Windows.
2. Download official account, follower, work, collection, and per-work detail exports into a uniquely created system temporary directory.
3. Capture only the page evidence required for fields without official Excel coverage.
4. Inventory and parse the exports.
5. Reject missing, duplicate, invalid, or internally inconsistent data.
6. Build the exact Workbench model using the installed Workbench parser.
7. Atomically replace `<Vault>/30_self_media/douyin/` only after all quality gates pass.
8. Delete temporary exports and page snapshots on success or failure.
9. Verify the published `current.json` before reporting success.

Use `--work-ids <comma-separated platform work ids>` only when the user explicitly asks to refresh specific work details or when automatic discovery cannot find them. Never place real work IDs in this repository or its documentation.

## Completion report

Report:

- collection status;
- target `current.json` path;
- capture time;
- number of works and deep-detail packages;
- account daily row count and collection count;
- quality status;
- whether temporary sources were deleted;
- any unavailable fields or platform coverage limits.

Do not print raw downloaded rows, private page text, work IDs, account identifiers, local browser paths, or session-bearing URLs.
