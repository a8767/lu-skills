# browser-act Integration

browser-act is the second-priority engine in this toolbox:

```text
cloak > browser-act > kimi > playwright
```

Use it after CloakBrowser fails when the task needs robust agent-oriented browser automation, session isolation, screenshots, form/file workflows, proxy/session handling, or human-agent collaboration.

## Lazy Setup

Do not install browser-act when the toolbox is loaded or installed.

Runtime behavior:

1. Check `BROWSER_ACT_BIN` first.
2. Then check whether `browser-act` is on `PATH`.
3. If missing, report `dependency_missing` by default.
4. Only when the caller explicitly passes `--install-missing`, install with:

```bash
uv tool install browser-act-cli --python 3.12
```

If `uv` is missing, stop with `dependency_missing` and ask the caller to install `uv` or manually provide `BROWSER_ACT_BIN`.

## Mandatory Core Guide

Before any browser-act command, load and save the full core guide:

```bash
browser-act get-skills core --skill-version 2.0.2
```

Do not truncate this output. It contains browser selection rules, safety constraints, and current environment status. The orchestrator saves it as `browser_act_core_attempt<N>.txt` in the output directory.

## Execution Adapter Contract

The toolbox does not guess browser-act subcommands. browser-act's operational guide may evolve, and unsafe guessing can violate confirmation or browser-selection rules.

To let the orchestrator execute via browser-act, provide one of:

- `plan.browser_act_command`: command string or argument list.
- `plan.browser_act_args`: argument list or string appended to the `browser-act` executable.
- `BROWSER_ACT_RUN_COMMAND`: environment command used as an adapter.

The orchestrator passes the full action plan JSON on stdin and expects either:

1. JSON on stdout matching the normal engine result shape, or
2. Plain stdout, which is captured as `outputs.stdout` and treated as success when exit code is 0.

Example plan fragment:

```json
{
  "url": "https://example.com",
  "browser_act_args": ["<subcommand-from-core-guide>", "<arg1>", "<arg2>"],
  "actions": [
    {"type": "evaluate", "name": "title", "script": "document.title"}
  ]
}
```

## Failure Semantics

- Missing CLI: `dependency_missing`.
- CLI installed but no adapter command: `setup_required`.
- `get-skills core` failure: `setup_required` or `dependency_missing` depending on stderr.
- Adapter non-zero exit: classify from stderr/stdout.

## Wrapper Guidance

A wrapper skill can use browser-act in two ways:

1. Keep default fallback order and let browser-act run only after CloakBrowser fails.
2. Explicitly set `--engine-order browser-act,cloak,kimi,playwright` for browser-act-specific tasks.

When a browser-act run reveals reusable platform behavior, record it with `scripts/record_platform_experience.py` just like other engines.
