#!/usr/bin/env python3
"""
Harness Engineering Framework - Scaffold Generator

Generates the complete harness framework structure in a target project directory.
Handles template variable substitution and existing file detection.
"""

import argparse
import json
import os
import shutil
import sys
from pathlib import Path


def parse_args():
    parser = argparse.ArgumentParser(description='Initialize Harness Engineering Framework')
    parser.add_argument('--project-name', required=True, help='Name of the project')
    parser.add_argument('--tech-stack', default='', help='Technology stack (e.g., "React + Node.js")')
    parser.add_argument('--project-type', default='', help='Project type (e.g., "web app", "API service")')
    parser.add_argument('--target-dir', required=True, help='Target project directory')
    return parser.parse_args()


def get_skill_dir():
    """Get the directory where this script lives (the skill root)."""
    return Path(__file__).resolve().parent.parent


def substitute(template: str, project_name: str, tech_stack: str, project_type: str) -> str:
    """Replace template variables."""
    return (template
            .replace('{{PROJECT_NAME}}', project_name)
            .replace('{{TECH_STACK}}', tech_stack or 'Not specified')
            .replace('{{PROJECT_TYPE}}', project_type or 'General')
            .replace('{{DATE}}', __import__('datetime').date.today().isoformat()))


def generate_file(template_path: Path, target_path: Path, project_name: str,
                  tech_stack: str, project_type: str, force: bool = False):
    """Generate a single file from a template."""
    if target_path.exists() and not force:
        print(f"  SKIP (exists): {target_path}")
        return False

    target_path.parent.mkdir(parents=True, exist_ok=True)

    if template_path.suffix in ('.md', '.txt', '.json'):
        content = template_path.read_text(encoding='utf-8')
        content = substitute(content, project_name, tech_stack, project_type)
        target_path.write_text(content, encoding='utf-8')
    else:
        # Binary or script files - copy as-is
        shutil.copy2(template_path, target_path)
        if template_path.suffix == '.py':
            target_path.chmod(target_path.stat().st_mode | 0o755)

    print(f"  CREATE: {target_path}")
    return True


def merge_settings(target_dir: Path):
    """Merge hook settings into existing .claude/settings.json."""
    settings_path = target_dir / '.claude' / 'settings.json'
    skill_dir = get_skill_dir()
    template_settings = skill_dir / 'templates' / 'settings.json'

    if not template_settings.exists():
        print("  SKIP: No settings template found")
        return

    template_content = json.loads(template_settings.read_text(encoding='utf-8'))

    if settings_path.exists():
        existing = json.loads(settings_path.read_text(encoding='utf-8'))
        # Merge hooks
        if 'hooks' in template_content:
            if 'hooks' not in existing:
                existing['hooks'] = template_content['hooks']
            else:
                for hook_type in template_content['hooks']:
                    if hook_type not in existing['hooks']:
                        existing['hooks'][hook_type] = template_content['hooks'][hook_type]
                    else:
                        # Append new hooks, avoiding duplicates
                        existing_matchers = {h.get('matcher', '') for h in existing['hooks'][hook_type]}
                        for new_entry in template_content['hooks'][hook_type]:
                            new_matcher = new_entry.get('matcher', '')
                            if new_matcher not in existing_matchers:
                                existing['hooks'][hook_type].append(new_entry)
        # Merge permissions
        if 'permissions' in template_content:
            if 'permissions' not in existing:
                existing['permissions'] = template_content['permissions']
            else:
                for perm_type in ('allow', 'deny'):
                    if perm_type in template_content['permissions']:
                        if perm_type not in existing['permissions']:
                            existing['permissions'][perm_type] = template_content['permissions'][perm_type]
                        else:
                            existing_set = set(existing['permissions'][perm_type])
                            for item in template_content['permissions'][perm_type]:
                                if item not in existing_set:
                                    existing['permissions'][perm_type].append(item)
        settings_path.write_text(json.dumps(existing, indent=2, ensure_ascii=False), encoding='utf-8')
        print(f"  MERGE: {settings_path}")
    else:
        settings_path.parent.mkdir(parents=True, exist_ok=True)
        settings_path.write_text(json.dumps(template_content, indent=2, ensure_ascii=False), encoding='utf-8')
        print(f"  CREATE: {settings_path}")


def main():
    args = parse_args()
    target_dir = Path(args.target_dir).resolve()
    skill_dir = get_skill_dir()
    templates_dir = skill_dir / 'templates'

    if not target_dir.exists():
        print(f"Error: Target directory does not exist: {target_dir}")
        sys.exit(1)

    print(f"\nInitializing Harness Engineering Framework in: {target_dir}")
    print(f"Project: {args.project_name}")
    print(f"Tech stack: {args.tech_stack or 'Not specified'}")
    print(f"Project type: {args.project_type or 'General'}")
    print()

    # Define generation order (paths relative to templates/ and target/)
    file_mappings = [
        # Phase 1: Root
        ('CLAUDE.md', 'CLAUDE.md'),

        # Phase 2: Documentation
        ('docs/architecture.md', 'docs/architecture.md'),
        ('docs/golden-principles.md', 'docs/golden-principles.md'),
        ('docs/sprint-workflow.md', 'docs/sprint-workflow.md'),
        ('docs/contracts/TEMPLATE.md', 'docs/contracts/TEMPLATE.md'),

        # Phase 3: Agents
        ('agents/planner.md', '.claude/agents/planner.md'),
        ('agents/generator.md', '.claude/agents/generator.md'),
        ('agents/evaluator.md', '.claude/agents/evaluator.md'),
        ('agents/doc-gardener.md', '.claude/agents/doc-gardener.md'),

        # Phase 4: Commands
        ('commands/plan.md', '.claude/commands/plan.md'),
        ('commands/build.md', '.claude/commands/build.md'),
        ('commands/qa.md', '.claude/commands/qa.md'),
        ('commands/sprint.md', '.claude/commands/sprint.md'),

        # Phase 5: Hooks
        ('hooks/loop-detector.py', '.claude/hooks/loop-detector.py'),
        ('hooks/pre-completion-check.py', '.claude/hooks/pre-completion-check.py'),
        ('hooks/context-injector.py', '.claude/hooks/context-injector.py'),
    ]

    created = 0
    skipped = 0

    for template_rel, target_rel in file_mappings:
        template_path = templates_dir / template_rel
        target_path = target_dir / target_rel

        if not template_path.exists():
            print(f"  WARN: Template not found: {template_path}")
            continue

        if generate_file(template_path, target_path, args.project_name,
                         args.tech_stack, args.project_type):
            created += 1
        else:
            skipped += 1

    # Ensure empty dirs exist
    for empty_dir in ('docs/specs', 'docs/plans'):
        (target_dir / empty_dir).mkdir(parents=True, exist_ok=True)

    # Merge settings
    merge_settings(target_dir)

    print(f"\nDone! Created {created} files, skipped {skipped} existing files.")
    print(f"\nNext steps:")
    print(f"  1. Review CLAUDE.md for project overview")
    print(f"  2. Run /plan <feature-description> to create your first spec")
    print(f"  3. Run /sprint <feature-description> for a full cycle")


if __name__ == '__main__':
    main()
