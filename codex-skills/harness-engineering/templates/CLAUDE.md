# {{PROJECT_NAME}}

> Harness Engineering Framework activated. Plan-Build-Verify workflow enabled.

## Quick Reference

| Command | Purpose |
|---------|---------|
| `/plan <description>` | Create a feature spec from 1-4 sentences |
| `/build` | Build the latest spec via sprint workflow |
| `/qa` | Run evaluator against current code |
| `/sprint <description>` | Full Plan-Build-Verify cycle |

## Architecture

See [docs/architecture.md](docs/architecture.md) for system design.

## Golden Principles

See [docs/golden-principles.md](docs/golden-principles.md) — these are non-negotiable.

## Agents

| Agent | Role | Trigger |
|-------|------|---------|
| planner | Expand brief prompts into specs | `/plan` |
| generator | Implement features in sprints | `/build` |
| evaluator | Test and grade implementations | `/qa` |
| doc-gardener | Maintain documentation freshness | Sprint complete |

## Sprint Workflow

1. **Plan**: Planner creates spec in `docs/specs/`
2. **Contract**: Generator + Evaluator agree on "done" criteria
3. **Build**: Generator implements one sprint
4. **Verify**: Evaluator tests against contract (threshold: 80/100)
5. **Fix**: If score < 80, Generator fixes (max 3 iterations)
6. **Complete**: Update docs, run doc-gardener

See [docs/sprint-workflow.md](docs/sprint-workflow.md) for full process.

## Project Structure

```
docs/
  architecture.md     -- System design
  golden-principles.md -- Core rules
  sprint-workflow.md  -- Sprint process
  contracts/          -- Sprint "done" definitions
  specs/              -- Feature specifications
  plans/              -- Implementation plans
.claude/
  agents/             -- Agent definitions
  commands/           -- Slash commands
  hooks/              -- Automated guards
```

## Hooks Active

- **Loop detection**: Blocks after 5 edits to same file
- **Pre-completion checklist**: Verifies before marking done
- **Context injection**: Adds environment info at session start

## Tech Stack

{{TECH_STACK}}
