# Skill Evaluation Guide

This guide defines how `browser-automation-toolbox` evaluates and enhances other browser automation skills.

## When to Evaluate

Trigger evaluation when any of these user intents are detected:

- "评估我的 XXX skill"
- "XXX skill 参考下 toolbox"
- "看看 XXX 缺什么能力"
- "把 toolbox 能力合入 XXX"
- "评估 XXX 的浏览器方案"

## Evaluation Dimensions

### 1. Engine Coverage

| Level | Criteria |
|-------|----------|
| Full | Supports 3+ engines with priority order and fallback |
| Partial | Supports 2 engines or single engine with basic retry |
| Minimal | Single engine, no fallback mechanism |

Toolbox baseline: 4 engines (cloak, browser-act, kimi, playwright) with configurable priority.

### 2. Failure Intelligence

| Capability | Toolbox Implementation |
|------------|----------------------|
| Failure kind classification | 7 kinds: dependency_missing, login_wall, captcha, selector_drift, network_timeout, capability_gap, unknown |
| Per-attempt evidence | screenshot + URL + error + engine name + attempt number |
| Retry policy | configurable per-engine attempts (default 2) |
| Cross-engine switch | automatic after max attempts exhausted |

### 3. Dependency Strategy

| Approach | Toolbox Behavior |
|----------|-----------------|
| Lazy install | Only when selected engine needs it |
| Managed env | Prefers project venv / managed Python |
| No global pollution | Never installs to user global unless approved |

### 4. Platform Engineering

| Feature | Toolbox Has | How to Check in Target |
|---------|-----------|----------------------|
| Platform-specific extractors | XHS / B站 / 抖音 / 微博 patterns | Look for selector strategies per platform |
| SPA vs paginated handling | Different scroll/page strategies | Check if infinite-scroll vs URL paging is distinguished |
| Dedupe strategy | Link-based + normalized keys | Look for dedup logic |
| Time normalization | Per-platform date parsers | Check time parsing code |
| Experience accumulation | record_platform_experience.py | Look for lesson-recording mechanism |

### 5. Integration Readiness

Check if target can be wrapped by toolbox:

- Does it have a CLI entry point?
- Does it accept a plan JSON?
- Can its output be parsed into the standard result contract?

## Gap Report Template

```
## Evaluation: <target-skill-name>
**Date**: <ISO date>
**Evaluator**: browser-automation-toolbox

### Summary
- Overall Score: X/10
- Critical Gaps: N
- Recommendations: N

### Detailed Findings

#### [CRITICAL] <gap title>
- **What's missing**: description
- **Toolbox solution**: which file/section to merge
- **Effort**: low / medium / high
- **Impact**: what this fixes

#### [RECOMMENDED] <gap title>
...

#### [NICE-TO-HAVE] <gap title>
...

### Merge Plan
1. [ ] Copy <source> → <destination>
2. [ ] Update <file> to reference new capability
3. [ ] Test with <platform/scenario>

### What Target Already Does Well
- <acknowledgment of existing strengths>
```

## Auto-Merge Rules

1. **Always ask before merging** — never silently modify another skill
2. **Preserve existing code** — merge as additive enhancement, not replacement
3. **Adapt paths** — adjust imports/references to match target structure
4. **Add attribution** — include comment: `# Enhanced by browser-automation-toolbox`
5. **Test after merge** — run a smoke test on the enhanced target
6. **Record evaluation** — append summary to `references/skill-evaluations.md`

## Limitations

- Cannot evaluate skills that are not readable (binary-only or encrypted)
- Cannot guarantee merged code works without testing on target environment
- Platform-specific patterns may need adaptation beyond what toolbox provides
- User preference overrides should always be respected over toolbox defaults

## Detailed Check Dimensions (10-point)

Use this 10-point checklist when the target skill is closely related to browser automation. For each dimension, mark as ✅ / ⚠️ / ❌ and provide one-line evidence.

| # | Dimension | What to Check | Toolbox Baseline |
|---|-----------|---------------|-----------------|
| 1 | Engine diversity | Does it support multiple engines? Which ones? | 4 engines (cloak, browser-act, kimi, playwright) |
| 2 | Priority & fallback | Is there a defined priority order? Does it retry per engine before switching? | `cloak > browser-act > kimi > playwright` + per-engine retry |
| 3 | Lazy dependency setup | Are dependencies installed on first use, not at load time? | Lazy install only when engine selected |
| 4 | Failure classification | Does it distinguish dependency_missing / login_wall / captcha / selector_drift / network / capability_gap? | 7 failure kinds with evidence |
| 5 | Evidence collection | Does it save screenshots + error context per failed attempt? | Per-attempt: screenshot + URL + error + engine + attempt# |
| 6 | Platform patterns | Does it have field-tested extractors for target platforms? | XHS / B站 / 抖音 / 微博 in `platform-scraping-patterns.md` |
| 7 | Experience accumulation | Can lessons be recorded back into the skill after each run? | `record_platform_experience.py` |
| 8 | Action chain contract | Is there a standardized plan JSON format for browser actions? | plan JSON: goto / wait / click / fill / press / scroll / evaluate / extract_text / screenshot |
| 9 | Human handoff | Does it pause for login/captcha and resume? | Visible-mode + pause + resume once |
| 10 | Extensibility | Can new engines be added with declared priority positions? | EngineRegistry + named priority slots |

## Output Example (Full)

```
Target: my-xhs-scraper
Status: EVALUATED
Date: 2026-06-22
Evaluator: browser-automation-toolbox

Gaps found:
  [CRITICAL] Single-engine only (playwright) — no fallback when blocked
  [CRITICAL] No failure classification — cannot distinguish captcha vs selector drift
  [RECOMMENDED] Missing platform-specific XHS extractor patterns
  [RECOMMENDED] No lazy dependency setup — forces install at load time
  [NICE-TO-HAVE] No experience accumulation mechanism

Merged from toolbox:
  ✓ references/platform-scraping-patterns.md → XHS section copied
  ✓ scripts/browser_orchestrator.py → adapted as multi-engine runner
  ✓ Failure kind enum added to error handler
```
