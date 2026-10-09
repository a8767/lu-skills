---
name: firecrawl-crawl
description: |
  Bulk-extract many pages from one site or section. Use for "crawl", "everything under /docs", or content spanning linked pages.
allowed-tools:
  - Bash(firecrawl *)
  - Bash(npx firecrawl-cli *)
---

# firecrawl crawl

Bulk extract content from a website. Crawls pages following links up to a depth/limit.

## Scope And Failure Boundaries

Use crawl when multiple linked pages are required; for one known page, use `scrape`. Keep the crawl within the supplied site and requested path; do not broaden to other sections or subdomains unless asked. Set explicit `--limit` and `--max-depth` values that fit the requested scope. If a job fails, times out, or returns fewer pages than expected, report its job ID/status and observed page count, and label the output partial rather than complete.

**Prerequisite:** `crawl` requires authentication (no keyless free tier); without credentials the CLI prompts an interactive login.

## Quick start

```bash
# Crawl a docs section
firecrawl crawl "<url>" --include-paths /docs --limit 50 --wait -o .firecrawl/crawl.json

# Full crawl with depth limit
firecrawl crawl "<url>" --max-depth 3 --wait --progress -o .firecrawl/crawl.json

# Check status of a running crawl
firecrawl crawl <job-id>
```

Run `firecrawl crawl --help` for the full option list.

**Done when:** the crawl reaches a terminal status and the saved output under `.firecrawl/` contains the expected pages.

## Tips

- Use `--wait` when you need the results immediately. It has no default timeout; use `--timeout <seconds>` to bound polling. Without `--wait`, crawl returns a job ID for async polling.
- **Scope crawls with `--include-paths`** whenever the request names a section — crawl only the pages you need.
- Crawl consumes credits per page. Check `firecrawl credit-usage` before large crawls (`credit-usage` requires authentication).

## See also

- [firecrawl-scrape](../firecrawl-scrape/SKILL.md) — scrape individual pages
- [firecrawl-map](../firecrawl-map/SKILL.md) — discover URLs before deciding to crawl
- [firecrawl-download](../firecrawl-download/SKILL.md) — download site to local files (uses map + scrape)
- [firecrawl-build-scrape](https://github.com/firecrawl/skills/tree/main/skills/build/firecrawl-build-scrape) — building bulk extraction into an app instead of running it here
