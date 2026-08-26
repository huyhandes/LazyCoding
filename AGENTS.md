# Repository Guidelines

## Project Overview

LazyClaude is **my own** agent skills, packaged for others. Premise: outsource the code, not the thinking — a skill encodes judgment (when to act, what to refuse, what to check); the agent does the typing.

Scope: self-developed skills only (`10x-implement`, `officecli`, `optimize-claude-md`, …). Vendored skills stay in `~/.agents/skills` where their installer put them — **never** copy one in here.

Current state: `10x-implement` moved in and symlinked back (see Dev Mount). `officecli` and `optimize-claude-md` still live in `~/.agents/skills`; move them the same way, one at a time.

## Layout

```
skills/<name>/SKILL.md       ← the skill; frontmatter + body (only required file)
skills/<name>/references/    ← progressive-disclosure detail, loaded on demand
skills/<name>/scripts/       ← executable helpers (only where an LLM is wasteful/non-deterministic)
.claude/agents/<name>.md     ← subagents skills delegate to
README.md                    ← install instructions for others
```

`npx skills` (vercel-labs/skills) discovers `skills/<name>/SKILL.md` up to three levels deep, so the flat layout above needs no manifest. Install for others once the repo is public on GitHub:

```bash
npx skills add huybui/LazyClaude                    # interactive pick
npx skills add huybui/LazyClaude --skill 10x-implement -g -a claude-code -y
```

## Dev Mount

Symlink, don't copy — `npx skills add .` installs a snapshot copy, so edits stop propagating.

```bash
n=10x-implement
mv ~/.agents/skills/$n skills/$n                      # first move only
rm -rf ~/.agents/skills/$n ~/.claude/skills/$n        # drop stale dir/link
ln -sfn "$PWD/skills/$n" ~/.agents/skills/$n          # Cursor/Codex/Cline family
ln -sfn "$PWD/skills/$n" ~/.claude/skills/$n          # Claude Code
```

Claude reads only `name` + `description` at startup; the body loads when the description matches. Restart the session after adding a skill.

## Subagents

Project subagents live in `.claude/agents/<name>.md` (frontmatter: `name`, `description`, optional `tools`, `model`) and are picked up automatically when working inside this repo. `npx skills` installs skills, **not** subagents — so a skill MUST still work when its subagent is absent: describe the delegation in the body, don't hard-depend on a file the installer never copies.

## Conventions

- **Frontmatter**: `name` (kebab-case, == directory name) and `description`. The description is the routing signal — write the trigger phrases a user would actually say, not a summary. Optional: `disable-model-invocation: true` for explicit-invoke-only skills, `allowed-tools`, `license`, `version`.
- **Naming**: verb-first for actions (`optimize-claude-md`), noun for reference packs (`terraform-best-practices`).
- **Body**: imperative, second person, RFC-2119 (`MUST`/`NEVER`/`SHOULD`). Tables and short lists over prose. State the rule, then one example — no rationale essays. SKILL.md stays a router; one topic per file under `references/`.
- **Python**: 3.10+, stdlib only, type hints, `sys.argv[1]` over argparse, exit codes `0/1/2/130`. Subprocess: fixed arg list, never `shell=True`.
- **Bash**: `#!/usr/bin/env bash` + `set -euo pipefail`.
- **Safety**: no unrestricted writes outside the target file, cap input size before any API call, back up out-of-tree under `XDG_DATA_HOME`, restore-and-abort on repeated failure.
- No build, lint, or package manager step. Markdown + stdlib Python + bash.

## Testing & QA

No framework — verification is behavioral:

1. **Skill change**: run it against a real task; confirm the trigger fires and the body is followed. A routing bug lives in the `description` and is invisible to any file-level check.
2. **Script change**: run the script on a real input.
3. **New non-trivial logic**: leave exactly one runnable check — an `assert`-based `__main__` self-check or one small `test_*.py`. No fixtures, no frameworks.

A skill that never fires is worse than an untested one.
