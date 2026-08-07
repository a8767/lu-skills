#!/usr/bin/env python3
"""Generate small integration snippets for wrapping browser-automation-toolbox."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def toolbox_path() -> str:
    return str(Path(__file__).resolve().parents[1])


def skill_snippet(name: str) -> str:
    return f"""## Browser Automation

Use `browser-automation-toolbox` for browser execution in `{name}`. Keep domain logic in this skill; delegate engine fallback, dependency checks, login/captcha handoff, screenshots, and platform scraping patterns to the toolbox.

Default engine order: `cloak > browser-act > kimi > playwright`.

Before scraping B站、小红书、抖音、微博 or similar public-content platforms, read:

- `browser-automation-toolbox/references/platform-scraping-patterns.md`
- `browser-automation-toolbox/references/engine-contract.md`
- `browser-automation-toolbox/references/browser-act.md` when using browser-act adapters

After a run reveals a reusable platform lesson, append it with:

```bash
python <browser-automation-toolbox>/scripts/record_platform_experience.py --platform <platform> --lesson "<lesson>" --evidence "<evidence>" --action "<next action>" --source "{name}"
```
"""


def python_snippet(name: str) -> str:
    tb = toolbox_path().replace("\\", "\\\\")
    return f'''import json
import subprocess
import sys
from pathlib import Path

TOOLBOX = Path(r"{tb}")
OUTPUT_DIR = Path("browser_run")
PLAN_PATH = Path("{name}_plan.json")

plan = {{
    "url": "https://example.com",
    "headless": False,
    "actions": [
        {{"type": "wait", "seconds": 1}},
        {{"type": "evaluate", "name": "title", "script": "document.title"}},
        {{"type": "screenshot", "path": "after.png"}},
    ],
}}
PLAN_PATH.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")

subprocess.check_call([
    sys.executable,
    str(TOOLBOX / "scripts" / "browser_orchestrator.py"),
    "run",
    "--plan", str(PLAN_PATH),
    "--output-dir", str(OUTPUT_DIR),
    "--engine-order", "cloak,browser-act,kimi,playwright",
    "--max-attempts-per-engine", "2",
])

report = json.loads((OUTPUT_DIR / "browser_orchestrator_report.json").read_text(encoding="utf-8"))
print(json.dumps(report, ensure_ascii=False, indent=2))
'''


def plan_snippet(name: str) -> str:
    plan = {
        "name": name,
        "url": "https://example.com",
        "profile_dir": "~/.cloakbrowser-profile",
        "headless": False,
        "actions": [
            {"type": "wait", "seconds": 1},
            {"type": "evaluate", "name": "title", "script": "document.title"},
            {"type": "extract_text", "name": "body", "selector": "body"},
            {"type": "screenshot", "path": "after.png"},
        ],
    }
    return json.dumps(plan, ensure_ascii=False, indent=2)


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate browser-automation-toolbox integration snippets")
    parser.add_argument("--mode", choices=["skill", "python", "plan"], required=True)
    parser.add_argument("--name", default="wrapper-skill")
    parser.add_argument("--output", default="", help="Optional output file")
    args = parser.parse_args()

    if args.mode == "skill":
        content = skill_snippet(args.name)
    elif args.mode == "python":
        content = python_snippet(args.name)
    else:
        content = plan_snippet(args.name)

    if args.output:
        Path(args.output).write_text(content, encoding="utf-8")
        print(args.output)
    else:
        print(content)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
