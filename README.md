# LazyClaude

Agent skills, packaged for others. Premise: **outsource the code, not the thinking** — a skill encodes judgment (when to act, what to refuse, what to check); the agent does the typing.

Shipped today: **[10x-implement](skills/10x-implement/SKILL.md)** — implement a spec or ticket set with a four-role subagent team (scout, coder, merger, reviewer), each in its own worktree, looping rounds until every acceptance criterion is green.

## Install

Two paths. Pick one.

### Path A — everything (skills + the 10x subagent team)

One command mounts every skill and every agent into every harness it finds on your machine (Claude Code, zcode, oh-my-pi, grok-build, Codex):

```bash
git clone https://github.com/huybui/LazyClaude && cd LazyClaude
python3 scripts/install.py             # link mode (default): edits in the repo propagate
python3 scripts/install.py copy        # snapshot files instead of links
python3 scripts/install.py uninstall   # removes exactly what the installer created
```

`--dry-run` prints the full plan without writing; `--force` backs up a foreign file to `<name>.bak.<n>` before replacing it; `--all` targets all five harnesses even if some aren't installed yet. Models and thinking levels are configured in one editable block at the top of [`scripts/install.py`](scripts/install.py). Python 3.10+, stdlib only, no network.

**Restart your session after installing** — skills and agents load at startup.

### Path B — skills only (no subagents)

```bash
npx skills add huybui/LazyClaude                        # interactive pick
npx skills add huybui/LazyClaude --skill 10x-implement -g -a claude-code -y
```

`npx skills` installs skills only — it never writes subagent definitions. The 10x team (and any future agents) need Path A.

## Layout

```
skills/<name>/SKILL.md       the skill (npx-skills compatible)
agents/<name>.md             canonical agent briefs — single source of truth
scripts/install.py           the cross-harness installer
```

Detail on the installer: [skills/10x-implement/references/INSTALL.md](skills/10x-implement/references/INSTALL.md).
