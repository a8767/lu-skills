# Kimi WebBridge Deferred Setup

Use this reference only when the fallback chain reaches `kimi` or the user explicitly requests Kimi WebBridge.

## Principle

Do not require Kimi browser plugin or bridge setup when this toolbox is installed or loaded. Kimi setup is deferred because many browser automation tasks complete with CloakBrowser or Playwright.

## Detection

The orchestrator treats Kimi as configured if either variable exists:

- `KIMI_WEBBRIDGE_URL`: HTTP endpoint accepting a JSON POST payload with `{url, actions, headless, output_dir}`.
- `KIMI_WEBBRIDGE_COMMAND`: local command that accepts the same JSON payload on stdin and writes JSON to stdout.

## User Guidance When Missing

When `kimi` is selected but no bridge is detected, tell the user:

1. This task has fallen back to Kimi because CloakBrowser attempts failed.
2. Kimi requires a local WebBridge / browser extension connection.
3. Configure either:
   - `KIMI_WEBBRIDGE_URL=http://127.0.0.1:<port>/run`
   - or `KIMI_WEBBRIDGE_COMMAND="<path-to-kimi-bridge-cli> run"`
4. After configuration, rerun the same plan. Do not change the action chain unless the prior failure was selector drift.

## Expected Bridge Response

The bridge should return JSON:

```json
{
  "ok": true,
  "outputs": {"items": []},
  "artifacts": ["kimi_screenshot.png"],
  "current_url": "https://example.com"
}
```

On failure:

```json
{
  "ok": false,
  "error": "login required",
  "failure_kind": "login_required",
  "artifacts": []
}
```

## Notes

- Keep Kimi second in default priority: `cloak > kimi > playwright`.
- Do not ask the user to configure Kimi until it is actually needed.
- If the bridge response is not valid JSON, classify as `engine_capability_gap` or `setup_required` depending on stderr.