---
name: multi-agent-image
description: Use for complex raster-image work that benefits from a design compiler: multiple creative directions, prompt packages, batch variants, or style-consistent series. For a one-off image use imagegen; for explicit APIMart 2K/4K or reference-image work use apimart-image-gen.
version: 3.0.0
author: Agent Skill maintainers
license: MIT
metadata:
  hermes:
    tags: [image-generation, multi-agent, gpt-image-2, apimart, design-compiler, case-library, batch, series]
    related_skills: [stable-diffusion]
---

# Multi-Agent Image

`multi-agent-image` is a standalone agent skill for design-led image-generation workflows.

It is designed for cases where a simple one-line prompt is not enough. Instead of sending raw user input directly to an image model, this skill:

1. analyzes the request,
2. compiles it into a design-aware prompt,
3. generates through `gpt-image-2`,
4. archives the result,
5. and optionally reuses successful outputs as future style references.

This skill is independent at runtime. The design compiler is built into this repository and does not require an external skill.

## When to Use

Use this skill when the user wants one or more of the following:

- Design-oriented poster generation
- Product images or ad visuals
- PPT cover visuals or chapter art
- Infographic-like or teaching/demo visuals
- Style reference reuse from prior generations
- Interactive “show examples first, then generate” flow
- Batch generation for multiple directions or aspect ratios
- Series generation where multiple images should share one visual language

Do not use this skill for:

- pixel-accurate UI recreation
- editable charts
- exact typography output inside the image
- tasks that require vector, HTML, or PPT-native assets rather than raster images

## Architecture

```text
User Request
    ↓
[Prompt Engineer]
    ↓
[Style Scout]
    ↓
[Internal Design Compiler]
    ↓
[GPT-Image-2 Generation]
    ↓
[QA + Archive]
    ↓
[Case Library]
```

Optional layers on top of the main path:

- Interactive reference selection
- Batch generation
- Series generation

## Setup

### 1. Use the skill in place

Run supported scripts from this skill directory. Do not run the legacy installer or interactive wrappers; they target a retired runtime layout.

Supported path:

```bash
python scripts/design_image.py --brief "AI训练营招生海报，强调速度、增长、实战" --task poster --aspect 3:4 --prompt-only
```

For direct generation, explicitly set an output directory in the current project:

```bash
python scripts/design_image.py --brief "AI训练营招生海报，强调速度、增长、实战" --task poster --aspect 3:4 --output-dir ./outputs/multi-agent-image
```

### 2. Install Python dependencies

```bash
pip install openai requests
```

### 3. Set API key

```bash
export APIMART_API_KEY="..."
```

`OPENAI_API_KEY` remains a legacy fallback. Never write either key into prompts, skill files, logs, or output artifacts.

## Core Components

### `scripts/design_compiler.py`

Internal prompt compiler.

Responsibilities:

- detect task type
- choose defaults for aspect and quality
- build `design_reasoning`
- compress it into `compiled_brief`
- produce the final generation prompt

This is the core logic that makes the skill independent.

### `scripts/design_image.py`

CLI entrypoint for the internal compiler.

Use it when you want:

- prompt-only output
- a local design compilation test
- direct generation without the full multi-agent workflow

Example:

```bash
python scripts/design_image.py \
  --task poster \
  --brief "AI训练营招生海报，强调速度、增长、实战" \
  --direction balanced \
  --aspect 3:4 \
  --prompt-only
```

It prints:

- `design_reasoning`
- `compiled_brief`
- `prompt`
- `settings`

### `scripts/orchestrator_v2.py`

Main workflow entrypoint.

Responsibilities:

- run prompt analysis
- choose task and generation parameters
- optionally select a reference from the case library
- call the internal compiler
- call GPT-Image-2
- archive outputs
- auto-save successful results into the case library

### `scripts/gpt_image2_generator.py`

Low-level GPT-Image-2 client.

Responsibilities:

- submit async generation tasks
- poll task status
- download image results

Use this when you want direct API access without the full workflow.

### `scripts/case_library.py`

Persistent library of past generations.

Responsibilities:

- save outputs by task type
- store metadata and rating
- search by brief, prompt, or tags
- return image paths for reuse as references

### `scripts/case_selector.py`

Legacy interactive helper. Do not use it in current workflows; present the selected design directions directly in the conversation.

Responsibilities:

- render user-facing selection text
- parse replies like `1`, `n`, `case_001`, or `搜索蓝色`

### `scripts/interactive_run.py`

Two-phase dialogue wrapper.

Use it when the workflow needs to ask the user before generating.

### `scripts/batch_generator_v2.py`

Batch generation entrypoint.

Supports:

- same brief, multiple directions
- same brief, multiple aspect ratios
- multiple briefs in one run

### `scripts/series_generator.py`

Style-consistent series generator.

Workflow:

1. generate a master image
2. extract style signals from its compiled brief
3. generate child images that follow the same visual system

### `templates/linear_batch.py`

Editable template for resumable sequential runs.

Useful when you want:

- explicit scene lists
- filesystem-based progress monitoring
- style propagation from the first generated image

## Internal Design Compiler

The internal compiler produces three layers:

### 1. `design_reasoning`

This captures design intent before generation.

Typical fields:

- `task`
- `communication_goal`
- `audience`
- `channel`
- `visual_system`
- `hierarchy_strategy`
- `safe_zone_strategy`
- `lighting_strategy`
- `palette_strategy`
- `anti_filler_rules`
- `anti_slop_rules`

### 2. `compiled_brief`

This is a compressed design brief for generation.

It includes:

- what the image is for
- what should dominate visually
- what space should remain available
- what to avoid

### 3. `prompt`

Final model-facing prompt used for GPT-Image-2.

The prompt is generated from design logic, not just from a list of style keywords.

## Supported Tasks

The built-in compiler understands these task classes:

- `poster`
- `product`
- `ppt`
- `infographic`
- `teaching`
- `auto`

Default aspect assumptions:

- `poster` → `3:4`
- `product` → `1:1`
- `ppt` → `16:9`
- `infographic` → `4:3`
- `teaching` → `16:9`

Direction modes:

- `conservative`
- `balanced`
- `bold`

Quality modes:

- `draft`
- `final`
- `premium`

Current generation channel:

- `gpt-image-2`

## Usage

### Quick start

```bash
python scripts/quick_start.py "AI训练营招生海报，强调速度、增长、实战"
```

### Prompt-only compilation

```bash
python scripts/design_image.py \
  --task product \
  --brief "高端陶瓷咖啡杯电商首图，温暖晨光，突出釉面质感" \
  --prompt-only
```

### Full generation

Use `design_image.py` with an explicit `--output-dir`, or route the final compiled prompt to `apimart-image-gen`. Do not use the legacy orchestrator wrapper.

### Force task and visual settings

```bash
python scripts/design_image.py --brief "高端咖啡杯商品图" --task product --direction balanced --aspect 1:1 --quality final --output-dir ./outputs/multi-agent-image
```

## Interactive Workflow

Use a two-phase pattern when the user should select a direction before generation.

### Phase 1: prepare directions for the user

Compile two to four directions and present their purpose, composition, palette, ratio, and risks in the conversation.

### Phase 2: execute after the user chooses

```python
from interactive_run import execute

result = execute("帮我做张 AI 训练营海报", user_choice="1", task="poster")
```

Supported reply patterns:

- `1`, `2`, `3`
- `n`
- `y`
- `case_001`
- `搜索蓝色`

## Batch Generation

### Same brief, multiple directions

```python
from batch_generator_v2 import batch_styles

batch_styles("AI训练营海报", task="poster")
```

### Same brief, multiple aspect ratios

```python
from batch_generator_v2 import batch_aspects

batch_aspects("AI训练营海报", task="poster", aspects=["1:1", "16:9", "9:16"])
```

### Multiple briefs

```python
from batch_generator_v2 import batch_briefs

batch_briefs(["海报A", "海报B", "海报C"], task="poster")
```

## Series Generation

Use this when several outputs should feel like the same campaign or product family.

```python
from series_generator import SeriesGenerator

sg = SeriesGenerator()
sg.create_series(
    master_brief="AI训练营系列视觉，科技蓝，专业商务感",
    items=[
        {"name": "主海报", "brief": "AI训练营招生主海报", "aspect": "3:4"},
        {"name": "Banner", "brief": "官网 Banner", "aspect": "16:9"},
        {"name": "朋友圈", "brief": "朋友圈推广方形图", "aspect": "1:1"},
    ],
    task="poster",
    direction="balanced",
)
```

## Case Library

For current workflows, use a project-local case library directory:

```text
./outputs/multi-agent-image/case_library/
```

Output directory:

```text
./outputs/multi-agent-image/
```

Typical case structure:

```text
case_library/
├── poster/
│   └── case_001_example/
│       ├── image.png
│       └── metadata.json
```

Typical metadata fields:

- `case_id`
- `task`
- `brief`
- `prompt`
- `params`
- `tags`
- `rating`

## Validation Guidance

Before generating at scale, test prompt quality first:

```bash
python scripts/design_image.py \
  --task poster \
  --brief "AI训练营招生海报，强调速度、增长、实战" \
  --direction balanced \
  --aspect 3:4 \
  --prompt-only
```

What to check:

- Does `design_reasoning` state a clear communication goal?
- Is there an explicit safe zone?
- Is hierarchy obvious?
- Do `anti_slop_rules` remove HUD overlays, fog, and generic clutter?
- Does the prompt describe a single strong visual idea rather than a pile of elements?

## Current Limits

- Current image provider is centered on `gpt-image-2`
- QA scoring is intentionally lightweight
- Series generation is heavier than one-off generation
- The skill is optimized for raster outputs, not editable assets
- Some reference documents remain longer than necessary, but the main runtime path is consistent

## Version History

- `v1.0.0` Initial multi-agent workflow for GPT-Image-2 generation
- `v2.0.0` Added case library, interactive reference selection, and image-to-image style reuse
- `v2.1.0` Added stronger download retry logic, batch workflows, and series generation
- `v2.2.0` Added reusable installation and runtime layout
- `v3.0.0` Internalized the design compiler and removed external runtime dependency
- `v3.1.0` Defined a runtime-neutral, project-local execution path and retired legacy wrappers
