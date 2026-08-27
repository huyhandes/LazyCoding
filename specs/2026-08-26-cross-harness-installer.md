# Spec: Cross-harness installer for LazyClaude skills + subagents

Status: implemented · closed 2026-08-27 (issue #1, tickets #2–#7) · landed on `main` (`36eb432`) · Evidence base: `research/harness-agents-config.md`
(Mirrored to tracker issue #1; acceptance verified by `python3 scripts/test_install.py` — 12/12 — plus the real-machine migration with `.bak` backups.)

## Problem Statement

I maintain LazyClaude, a repo of skills that must work across five coding-agent harnesses
(Claude Code, zcode, oh-my-pi, grok-build, Codex). Skills install fine via `npx skills`, but my
subagents don't: today each harness gets a hand-copied set of agent files, and the copies have
already drifted apart (zcode copies updated 2026-08-25, Claude copies 2026-08-22, omp copies with
different frontmatter). The existing `install.sh` inside 10x-implement only covers three
harnesses, requires editing a block and re-running per harness, blindly overwrites, and does not
install skills at all. There is no off-the-shelf tool that installs agent definitions into all
five harnesses (verified by research). I want one command that installs everything, everywhere,
without drift.

## Solution

A single stdlib Python installer at `scripts/install.py` with a single source of truth for agent
definitions at repo-root `agents/`. One invocation mounts every skill and every agent into every
detected harness (or all five with a flag). In default (dev) mode it symlinks, so edits in the
repo propagate live; in `copy` mode it writes self-identifying snapshot files for end users. It
generates Codex TOML from the markdown briefs, injects per-harness frontmatter (model,
thought-level spelling), refuses to touch files it did not create, and hard-rejects agent names
that collide with any harness builtin. The old `install.sh` and the skill-internal `agents/` dir
are retired in favor of this one tool.

## User Stories

1. As the repo owner, I want one command that installs all skills and agents into all my
   harnesses, so that I never hand-copy agent files again.
2. As the repo owner, I want default installs to symlink instead of copy, so that my edits in
   the repo propagate to every harness without re-running anything.
3. As the repo owner, I want `copy` mode to write plain files, so that end users without the
   repo get working installs.
4. As the repo owner, I want re-running the installer to be idempotent, so that I can run it
   after every change without fear.
5. As the repo owner, I want a dry-run mode that prints the full plan without touching disk, so
   that I can review what will change first.
6. As the repo owner, I want the installer to detect which harnesses exist on the machine (by
   their config dirs) and skip absent ones, so that a fresh machine doesn't sprout junk dirs.
7. As the repo owner, I want a flag to install into all five harnesses even if some dirs don't
   exist yet, so that a new harness install is a one-step setup.
8. As the repo owner, I want the installer to replace the legacy hand-copied agent files from my
   three harness dirs on first run (after showing me the plan), so that the existing drift is
   cleaned up by the same tool.
9. As an end user, I want `git clone` + one command to install skills AND subagents, so that I
   don't need to understand per-harness directories.
10. As an end user, I want `npx skills add huybui/LazyClaude` to keep working unchanged for
    skills, so that the ecosystem install path I know still functions.
11. As an end user using Codex, I want the installer to generate Codex agent TOML files from the
    markdown briefs, so that the 10x team works in Codex too.
12. As an end user using grok-build, I want agents installed into grok's agent dir, so that the
    10x team works there too.
13. As an agent definition author, I want to write one model-neutral brief (name, description,
    prompt body) and configure per-harness model/thought-level in one visible config block, so
    that I never write harness-specific frontmatter by hand.
14. As an agent definition author, I want the installer to fail loudly when an agent has no
    model mapping, so that a new agent can't silently install with the wrong model.
15. As an agent definition author, I want a name that collides with any harness builtin
    (general-purpose, Explore/explore/explorer, plan/Plan, task, worker, default, scout,
    reviewer, security-reviewer, designer, librarian, sonic, claude, fork, statusline-setup,
    claude-code-guide) to be rejected before anything is written, so that I never silently
    shadow a builtin in a harness I don't personally use.
16. As a harness session (zcode, omp, grok, Codex), I receive agent files whose frontmatter uses
    my harness's exact field names and value shapes (zcode `thoughtLevel` + `injectAgentsMd`,
    omp `model: [...]` + `thinkingLevel`, Claude bare `model`, Codex TOML
    `developer_instructions`), so that the agents load with correct behavior on first try.
17. As a careful user, I want the installer to refuse to overwrite a target file it did not
    create (not a symlink into this repo, no installer stamp), so that my own custom agents are
    never clobbered.
18. As a careful user, I want a forced replacement to back up the old file first, so that
    nothing is ever lost irrecoverably.
19. As a careful user, I want generated copy-mode files to carry an installer stamp, so that a
    later run (or I) can tell installer-owned files from hand-written ones.
20. As a careful user, I want an uninstall capability that removes exactly what the installer
    created (symlinks into the repo, stamped files) and nothing else, so that trying LazyClaude
    is reversible.
21. As a developer working inside this repo with Claude Code, I want an in-repo
   `.claude/agents` link to the canonical `agents/` dir, so that project-scope agents load
   automatically during development.
22. As a future skill author in this repo, I want adding `skills/<new>/SKILL.md` to make it
    automatically included by the next installer run, so that new skills need zero installer
    edits.
23. As a future agent author in this repo, I want adding `agents/<new>.md` to be picked up the
    same way, so that scaling to more agents needs zero installer edits (only a model mapping).
24. As the repo owner, I want exit codes 0 success / 1 failure / 2 usage error (130 on SIGINT),
    so that the installer composes with scripts.
25. As the repo owner, I want zero network access and zero third-party dependencies, so that the
    installer runs anywhere Python 3.10+ runs.
26. As the repo owner, I want the installer to mount skills into `~/.agents/skills/` plus a
    Claude-specific `~/.claude/skills/` link, so that the documented dev-mount workflow becomes
    one command.
27. As a reader of the README, I want the install instructions to show the clone-and-run path
    and the `npx skills` path, so that I can pick the one I prefer.

## Implementation Decisions

- **One tool**: `scripts/install.py`, Python 3.10+ stdlib only, `sys.argv` parsing (no
  argparse), interface: optional `link` (default) | `copy` | `uninstall` mode, `--dry-run`,
  `--all`, `--force`, `--harness <name>` (repeatable). Exit codes 0/1/2/130.
- **Canonical layout** (user decision): agent briefs move from
  `skills/10x-implement/agents/` to repo-root `agents/<name>.md`. Briefs are model-neutral
  markdown: `name`, `description` frontmatter + prompt body. `skills/<name>/` layout is
  unchanged (npx-skills compatible, discovery depth 3).
- **Retired**: `skills/10x-implement/install.sh` is deleted (its per-harness frontmatter mapping
  is absorbed); `skills/10x-implement/agents/` moves to `agents/`; `references/INSTALL.md` and
  the AGENTS.md Dev Mount section are rewritten to the one-command workflow.
- **Agent destinations (user scope)**: Claude `~/.claude/agents/`, zcode `~/.zcode/agents/`,
  omp `~/.omp/agent/agents/`, grok `~/.grok/agents/`, Codex `~/.codex/agents/<name>.toml`.
  Detection = does the harness's user config root exist (`~/.claude`, `~/.zcode`, `~/.omp`,
  `~/.grok`, `~/.codex`).
- **Skills destinations**: each `skills/*` → `~/.agents/skills/<name>` plus
  `~/.claude/skills/<name>` (the other four harnesses read `~/.agents/skills` natively).
- **Per-harness frontmatter injection** (extends install.sh's proven mapping): Claude emits
  `model`; zcode emits `model`, `injectAgentsMd: true`, `thoughtLevel`; omp emits
  `model: ["…"]`, `thinkingLevel`; grok emits only `name`/`description` (a grok `model` field is
  UNVERIFIED in primary docs — omit rather than guess); Codex TOML emits `name`, `description`,
  `developer_instructions` (prompt body), `model_reasoning_effort` from the thought-level, and
  omits `model` unless mapped. Frontmatter parsing is a minimal line parser (first `name:` /
  `description:` in the brief), matching install.sh behavior — no YAML dependency.
- **Model mapping config**: an editable block at the top of the script mapping each agent name
  to per-harness `model` + thought-level, preserving install.sh's edit-one-block UX. Unknown
  agent without mapping = hard failure with instruction.
- **Safety**: copy-mode files carry an installer stamp comment; a target is "ours" if it is a
  symlink into this repo or stamped. Foreign targets are never overwritten without `--force`;
  forced replacement renames the old file to `<name>.bak.<n>` first. Reserved-name check runs
  before any write. `--dry-run` prints every planned action.
- **Uninstall**: removes symlinks resolving into this repo and stamped files only.
- **In-repo convenience**: installer also maintains `.claude/agents` → `../agents` inside the
  repo for Claude project-scope loading during development.

## Testing Decisions

- Good tests assert external behavior only: given a fake `HOME` (temp dir) with pre-created
  harness config roots and one foreign agent file, running the installer must produce an exact
  expected tree — and never touch the foreign file.
- **One runnable check** per repo convention (AGENTS.md "Testing & QA"): `scripts/test_install.py`,
  assert-based, run as `python3 scripts/test_install.py`. It executes `install.py` as a
  subprocess against the temp `HOME` (the highest seam — the CLI boundary) and asserts:
  correct destinations per harness; symlink targets in link mode; stamped copies in copy mode;
  exact injected frontmatter per harness (zcode `thoughtLevel`, omp `thinkingLevel` + array
  model, Claude bare model, grok neutral); generated Codex TOML parses (via `tomllib` when the
  interpreter is 3.11+, string asserts otherwise) with `developer_instructions` equal to the
  brief body; reserved-name rejection exits 2 with nothing written; foreign-file protection and
  `--force` backup behavior; dry-run writes nothing; idempotent second run changes nothing.
- Prior art: none in-repo (install.sh shipped untested); this test becomes the repo's reference
  check.
- Behavioral QA after implementation: run the real installer (`--dry-run`, then default) against
  the real HOME to replace the three drifted legacy copies, then confirm the 10x agents fire in
  a live zcode session (AGENTS.md QA rule 1).

## Out of Scope

- Plugin/marketplace packaging (`.claude-plugin/`, grok marketplace PRs) and dotagents
  `agents.toml` — deferred per research; additive later.
- Project-scope installs (`.zcode/agents/`, `.omp/agents/` etc.) — user scope only.
- MCP servers, hooks, or config-file installation — skills and agents only.
- Windows support; non-stdlib dependencies; network access of any kind.
- Versioning/update flows (`skills-lock.json` interplay) — re-run replaces.
- Verifying grok `model` frontmatter behavior (documented UNVERIFIED; revisit when grok is
  installed locally).

## Further Notes

- Evidence and per-harness formats: `research/harness-agents-config.md` (config paths,
  frontmatter fields, builtin-name union table, the three-way drift observation).
- The repo is not yet a git repository; when it becomes one and gains a tracker, this spec file
  should be mirrored to an issue labeled ready-for-agent.
- vercel-labs/skills PR #2026 (open) proposes installing repo `agents/` dirs natively — the
  repo-root `agents/` choice is forward-compatible with it; revisit the installer's agent fan-out
  if it merges.
- Codex on this machine is stale (0.122.0, broken binary): TOML output is validated by the test
  suite against the documented 0.149-era format, not against a live Codex.
- Suggested build path: `10x-implement` on this spec, chunked (1: script core + mapping table;
  2: skills mounting + safety/uninstall; 3: test suite + migration of legacy copies + docs
  rewrite).
