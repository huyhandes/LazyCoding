# Install

Two installs: the **skill** (routing + orchestration) and the **team** (the four subagents it dispatches). The skill works without the team only via the single-agent fallback — install the team.

Both come from one command, run from the repo root:

```bash
python3 scripts/install.py
```

It mounts every brief in `agents/` into every harness it detects, and every skill in `skills/` into `~/.agents/skills/` (+ `~/.claude/skills/` when Claude Code is targeted). Restart the session afterwards — skills and agents load at startup.

## Usage

```
python3 scripts/install.py [link|copy|uninstall] [--dry-run] [--all]
                           [--force] [--harness <name>]...
```

| option | effect |
|---|---|
| `link` (default) | skills symlink into the repo (edits propagate live); agents are written as stamped rendered files into each harness's dir and refreshed on each run — re-run after editing a brief. Agents are real files, not symlinks: zcode's agent loader ignores symlinked files, and per-harness frontmatter differs anyway |
| `copy` | stamped snapshot files everywhere, for machines without the repo |
| `uninstall` | removes exactly what the installer created; foreign files untouched |
| `--dry-run` | print the full plan, write nothing |
| `--all` | target all five harnesses even if their config dirs don't exist |
| `--harness <name>` | restrict agents to `claude\|zcode\|omp\|grok\|codex` (repeatable); named harnesses are targeted even if undetected |
| `--force` | back up a foreign target to `<name>.bak.<n>` before replacing it |

Exit codes: `0` success · `1` failure (missing model mapping, foreign target refused) · `2` usage error or reserved agent name · `130` interrupted.

## Destinations

| harness | agents land in | frontmatter injected |
|---|---|---|
| claude | `~/.claude/agents/<name>.md` | bare `model:` |
| zcode | `~/.zcode/agents/<name>.md` | quoted `model:`, `injectAgentsMd: true`, `thoughtLevel:` |
| omp | `~/.omp/agent/agents/<name>.md` | `model: ["…"]`, `thinkingLevel:` |
| grok | `~/.grok/agents/<name>.md` + `[subagents.models]` pins in `~/.grok/config.toml` | `name`/`description` only (grok .md files have no model field); per-type models go to the config table |
| codex | `~/.codex/agents/<name>.toml` | generated TOML: `name`, `description`, `developer_instructions`, `model`, `model_reasoning_effort` |

A harness is detected iff its config dir exists (`~/.claude`, `~/.zcode`, `~/.omp`, `~/.grok`, `~/.codex`); absent ones are skipped. The installer also maintains the in-repo `.claude/agents → ../agents` link for Claude project-scope loading while you develop.

## Models & thinking levels

Briefs in `agents/` are model-neutral (`name`, `description`, prompt body). Per-harness models and the thought ladder live in the **`AGENT_MODELS` block at the top of `scripts/install.py`** — the one place you edit. `thought` is one string shared by every harness, or a dict of per-harness overrides (missing harness → field omitted):

```python
"10x-coder": {
    "claude": "claude-sonnet-5",
    "zcode":  "custom:builtin%3Azai-coding-plan:GLM-5.3",
    "omp":    "@task",
    "codex":  "gpt-5.6-terra",
    "grok":   "grok-4.6",
    "thought": "high",
},
```

Defaults (picked Sept-2026, scoring + sources in `research/model-defaults.md`): fast cheap scout (Haiku / GLM-5.3-Flash @ high — Flash under-reasons at low / Luna / `@smol`), mid-tier coder (Sonnet 5 / GLM-5.3 high / Terra / `@task`), strongest reasoning on merger+reviewer (Opus 5 / GLM-5.3 max / `gpt-5.6` @ xhigh / `@slow`); grok uses `grok-4.6` for every role until a verified fast tier exists. A brief missing from the block is a hard failure (exit 1); an agent named like any harness builtin is rejected before anything is written (exit 2). Re-run the installer after editing briefs or the block.

## Verify

```bash
head -7 ~/.zcode/agents/10x-scout.md   # your harness's dir; model + thinking field present
python3 scripts/test_install.py        # 13 behavioral checks, exit 0
```

Then restart the session.

## Troubleshooting

| symptom | fix |
|---|---|
| dispatch fails: unknown agent type `10x-scout` | agents not installed, or session predates install → run `python3 scripts/install.py`, restart session |
| wrong model / thinking tier running | edit the `AGENT_MODELS` block in `scripts/install.py`, re-run, restart session |
| `refuse … (not created by this installer)` | the target file is hand-written; review `--dry-run`, then re-run with `--force` (old file backed up to `<name>.bak.<n>`) |
| `no model mapping for […]` | add the agent to `AGENT_MODELS` in `scripts/install.py`, re-run |
| `agent name(s) […] collide with a harness builtin` | rename the brief in `agents/` — the name would silently shadow a builtin |
