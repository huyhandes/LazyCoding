# Install

Two installs: the **skill** (routing + orchestration) and the **team** (the four subagents it dispatches). The skill works without the team only via the single-agent fallback — install the team.

## 1. The skill

```bash
npx skills add huybui/LazyClaude --skill 10x-implement
```

Restart the session after installing — skills and agents load at startup.

## 2. The agents

Briefs live in `agents/`; they carry no models. Models are yours, set in one place — the EDIT-ME block at the top of `install.sh`:

```bash
cd <skill-dir>            # where npx skills put 10x-implement
$EDITOR install.sh        # HARNESS + one "<model> [thinking]" line per role
./install.sh
```

Re-run after editing the briefs or the block. It overwrites `10x-*.md` in the agent dir; your config is the block, never the installed files.

### Per-harness specifics

| harness | agent dir | model format | thinking |
|---|---|---|---|
| claude | `~/.claude/agents` | plain name: `claude-haiku-4-5` | no field exists — ignored |
| omp | `~/.omp/agent/agents` | gateway tag: `@task` | `thinkingLevel:` |
| zcode | `~/.zcode/agents` | fully-qualified, quoted: `custom:builtin%3Azai-coding-plan:GLM-5.3` | `thoughtLevel:` |

### Default ladder (shipped in the block)

| role | tier | thinking |
|---|---|---|
| 10x-scout | cheapest strong model | low |
| 10x-coder | workhorse | high |
| 10x-merger | strongest | max |
| 10x-reviewer | strongest | max |

The block ships the zcode/GLM-5.3 ladder; commented lines inside it carry the claude and omp equivalents — swap them in.

## Verify

```bash
head -7 ~/.zcode/agents/10x-scout.md   # your harness's dir; model + thinking field present
```

Then restart the session.

## Troubleshooting

| symptom | fix |
|---|---|
| dispatch fails: unknown agent type `10x-scout` | agents not installed, or session predates install → run `./install.sh`, restart session |
| wrong model running | edit the EDIT-ME block, re-run `./install.sh`, restart session |
| `HARNESS='…' — want claude\|omp\|zcode` | typo in the block's `HARNESS=` line |
