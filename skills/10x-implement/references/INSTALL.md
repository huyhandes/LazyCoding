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
| `link` (default) | skills symlink into the repo (edits propagate live); agent files render into a gitignored `.build/` inside the repo and symlink back — agent edits propagate on the **next run**, so re-run after editing a brief |
| `copy` | stamped snapshot files everywhere, for machines without the repo |
| `uninstall` | removes exactly what the installer created; foreign files untouched |
| `--dry-run` | print the full plan, write nothing |
| `--all` | target all five harnesses even if their config dirs don't exist |
| `--harness <name>` | restrict agents to `claude\|zcode\|omp\|grok\|codex` (repeatable) |
| `--force` | back up a foreign target to `<name>.bak.<n>` before replacing it |

Exit codes: `0` success · `1` failure (missing model mapping, foreign target refused) · `2` usage error or reserved agent name · `130` interrupted.

## Destinations

| harness | agents land in | frontmatter injected |
|---|---|---|
| claude | `~/.claude/agents/<name>.md` | bare `model:` |
| zcode | `~/.zcode/agents/<name>.md` | quoted `model:`, `injectAgentsMd: true`, `thoughtLevel:` |
| omp | `~/.omp/agent/agents/<name>.md` | `model: ["…"]`, `thinkingLevel:` |
| grok | `~/.grok/agents/<name>.md` | `name`/`description` only (grok `model` field unverified — omitted) |
| codex | `~/.codex/agents/<name>.toml` | generated TOML: `name`, `description`, `developer_instructions`, `model_reasoning_effort` |

A harness is detected iff its config dir exists (`~/.claude`, `~/.zcode`, `~/.omp`, `~/.grok`, `~/.codex`); absent ones are skipped. The installer also maintains the in-repo `.claude/agents → ../agents` link for Claude project-scope loading while you develop.

## Models & thinking levels

Briefs in `agents/` are model-neutral (`name`, `description`, prompt body). Per-harness models and one shared thought level live in the **`AGENT_MODELS` block at the top of `scripts/install.py`** — the one place you edit:

```python
"10x-coder": {
    "claude": "claude-sonnet-4-6",
    "zcode":  "custom:builtin%3Azai-coding-plan:GLM-5.3",
    "omp":    "@task",
    "thought": "high",
},
```

Defaults ship the zcode/GLM-5.3 ladder (scout `low`, coder `high`, merger/reviewer `max`); swap in your own per harness. A brief missing from the block is a hard failure (exit 1); an agent named like any harness builtin is rejected before anything is written (exit 2). Re-run the installer after editing briefs or the block.

## Verify

```bash
head -7 ~/.zcode/agents/10x-scout.md   # your harness's dir; model + thinking field present
python3 scripts/test_install.py        # 12 behavioral checks, exit 0
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
