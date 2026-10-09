# Integration Guide

Use this guide when another skill or engineering project wants to reuse `browser-automation-toolbox` instead of re-implementing browser automation.

## Choose an Integration Mode

### 1. Skill Wrapper

Use this when building another WorkBuddy skill.

Add a short dependency note to the wrapping skill's `SKILL.md`:

```markdown
## Browser Automation

For browser interaction, use `browser-automation-toolbox` as the substrate. Prefer the default engine order `cloak > browser-act > kimi > playwright`. Read its `references/browser-act.md` before using browser-act-specific adapter commands. Read its `references/platform-scraping-patterns.md` before scraping B站、小红书、抖音、微博 or similar public-content platforms. After a run reveals reusable platform lessons, record them with `scripts/record_platform_experience.py` in that toolbox.
```

The wrapper skill should own domain logic: keywords, aggregation, scoring, report format. This toolbox should own browser execution, fallback, screenshots, dependency checks, and platform scraping lessons.

### 2. CLI Integration

Use this when the caller can write a plan JSON and run a command.

```bash
python <toolbox>/scripts/browser_orchestrator.py run --plan ./plan.json --output-dir ./browser_run --engine-order cloak,browser-act,kimi,playwright --max-attempts-per-engine 2
```

The result is written to `browser_orchestrator_report.json`. Treat `ok=false` plus `failure_kind` as machine-readable control signals.

### 3. Python Subprocess Wrapper

Use this when integrating from a Python project without importing internal engine classes.

```python
import json
import subprocess
import sys
from pathlib import Path

TOOLBOX = Path.home() / ".workbuddy" / "skills" / "browser-automation-toolbox"
plan_path = Path("plan.json")
plan_path.write_text(json.dumps({
    "url": "https://example.com",
    "headless": False,
    "actions": [{"type": "evaluate", "name": "title", "script": "document.title"}],
}, ensure_ascii=False), encoding="utf-8")

subprocess.check_call([
    sys.executable,
    str(TOOLBOX / "scripts" / "browser_orchestrator.py"),
    "run",
    "--plan", str(plan_path),
    "--output-dir", "browser_run",
    "--engine-order", "cloak,browser-act,kimi,playwright",
])

report = json.loads(Path("browser_run/browser_orchestrator_report.json").read_text(encoding="utf-8"))
```

### 4. Embedded Copy

Use this only when the target project cannot depend on the user-level skill path.

Copy these files:

- `scripts/browser_orchestrator.py`
- `scripts/bootstrap_browser_engines.py`
- `scripts/record_platform_experience.py` if the project will update lessons
- `references/engine-contract.md`
- `references/dependencies.md`
- `references/browser-act.md` if browser-act fallback is enabled
- `references/kimi-webbridge.md` if Kimi fallback is enabled
- `references/platform-scraping-patterns.md` if public platform scraping is included

Keep the default priority order unless the target project documents a stronger reason.

## Responsibilities Boundary

| Layer | Owns |
|---|---|
| Wrapper skill/project | domain keywords, data schema, report format, scheduling, business rules |
| browser-automation-toolbox | engine fallback, browser actions, dependency checks, login/captcha handoff, screenshots, platform scraping lessons |
| Aggregator | dedupe, time parsing, relevance filtering, final output validation |

## Experience Update Hook

After a run, wrappers should call:

```bash
python <toolbox>/scripts/record_platform_experience.py --platform <platform> --lesson "<lesson>" --evidence "<evidence>" --action "<next-time action>" --source "<wrapper skill or project>"
```

Only record lessons that are likely to help future runs.
