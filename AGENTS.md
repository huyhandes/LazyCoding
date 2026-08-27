# Repository Guidelines

## Project Overview

LazyClaude is **my own** agent skills, packaged for others. Premise: outsource the code, not the thinking — a skill encodes judgment (when to act, what to refuse, what to check); the agent does the typing.

Scope: self-developed skills only (`10x-implement`, `officecli`, `optimize-claude-md`, …). Vendored skills stay in `~/.agents/skills` where their installer put them — **never** copy one in here.

Current state: `10x-implement` lives here, mounted out via `scripts/install.py` (see Dev Mount). `officecli` and `optimize-claude-md` still live in `~/.agents/skills`; move them into `skills/` and re-run the installer, one at a time.

## Layout

```
skills/<name>/SKILL.md       ← the skill; frontmatter + body (only required file)
skills/<name>/references/    ← progressive-disclosure detail, loaded on demand
skills/<name>/scripts/       ← executable helpers (only where an LLM is wasteful/non-deterministic)
agents/<name>.md             ← canonical agent briefs, single source of truth (model-neutral)
scripts/install.py           ← cross-harness installer: skills + agents, five harnesses
.claude/agents → ../agents   ← convenience link the installer maintains (Claude project scope)
README.md                    ← install instructions for others
```

`npx skills` (vercel-labs/skills) discovers `skills/<name>/SKILL.md` up to three levels deep, so the flat layout above needs no manifest. Install for others once the repo is public on GitHub:

```bash
npx skills add huybui/LazyClaude                    # interactive pick
npx skills add huybui/LazyClaude --skill 10x-implement -g -a claude-code -y
```

## Dev Mount

One command, from the repo root:

```bash
python3 scripts/install.py
```

It symlinks every `skills/*` into `~/.agents/skills/` plus `~/.claude/skills/` — edits in the repo propagate live. Agent briefs in `agents/` are rendered per harness (models/thought-levels from the `AGENT_MODELS` block in `scripts/install.py`) into a gitignored `.build/` and symlinked into each detected harness's agent dir — re-run after editing a brief. Absent harnesses are skipped; `copy` mode writes stamped snapshots for end users; `uninstall` removes exactly what the installer created. Detail: `skills/10x-implement/references/INSTALL.md`.

Claude reads only `name` + `description` at startup; the body loads when the description matches. Restart the session after adding a skill.

## Subagents

Project subagents live canonically in repo-root `agents/<name>.md` (frontmatter: `name`, `description`, optional `tools`, `model`); `.claude/agents` is a link there that the installer maintains, and they are picked up automatically when working inside this repo. `npx skills` installs skills, **not** subagents — so a skill MUST still work when its subagent is absent: describe the delegation in the body, don't hard-depend on a file the installer never copies.

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

## Agent skills

### Issue tracker

Issues are tracked in GitHub Issues (huyhandes/LazyCoding). See `docs/agents/issue-tracker.md`.

### Triage labels

Default five-role vocabulary (`needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`). See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: `CONTEXT.md` + `docs/adr/` at the repo root, created lazily. See `docs/agents/domain.md`.
