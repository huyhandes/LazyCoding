---
name: 10x-implement
description: "Implement a spec or ticket set with a four-role subagent team — scout, coder, merger, reviewer — each in its own worktree, looping rounds until every acceptance criterion is green."
disable-model-invocation: true
---

Implement the work described by the spec or tickets at 10x speed. You orchestrate; **the team does the typing.**

Four multipliers do the work — name them, don't restate them:

1. **Parallel AFK.** One message, one subagent call per chunk. Stay out of their way until they return.
2. **A team, not clones.** Four roles on tiered models, all on `ponytail` ultra: `10x-scout` (cited evidence), `10x-coder` (`tdd` only when opted in), `10x-merger` (conflicts and the seam, + `fable-thinking`), `10x-reviewer` (four headings, + `fable-thinking`). Briefs live in `agents/` at the repo root; models and thinking levels live in the `AGENT_MODELS` block of `scripts/install.py`.
3. **Worktree per chunk.** Scout and coder for chunk `<slug>` of spec `<spec>` work only in `$CWD/.worktree/<spec>/<slug>` on branch `<type>/<spec>/<slug>`. Parallel edits never collide mid-flight; collisions surface once, at the merge.
4. **Rounds until done.** A round is scout → code → merge → review. You loop rounds; the user's spec, not your patience, decides when to stop.

## Install the team (self-check before the first round)

Check the team before the first round — a dispatch that fails mid-wave costs the whole round. The four roles exist iff `10x-scout.md` is in your harness's agent dir: `~/.claude/agents/`, `~/.omp/agent/agents/`, or `~/.zcode/agents/`.

Missing → install, then restart the session (agents load at startup):

```bash
python3 scripts/install.py   # from the LazyClaude repo root; models → AGENT_MODELS block
```

Per-harness detail: `references/INSTALL.md`. Never open a round with a role missing — fall back to single-agent (below) instead.

## Setup

```bash
printf '/.worktree/\nEVIDENCE.md\n' >> .git/info/exclude           # once per repo: scratch never reaches a branch
git worktree add .worktree/<spec>/<slug> -b <type>/<spec>/<slug>   # per chunk
```

Full naming grammar, lifecycle, commit templates, and the monitoring cheat-sheet: `references/BRANCHING.md`.

## The round

### 1. Decompose

Read the spec or tickets fully, then cut the work into **chunks**. Name the run `<spec>` once (kebab-case, ≤30 chars) and pick its primary `<type>` — the landing commit headlines with it. A chunk is the smallest unit that can ship on its own, so a subagent can take it without talking to the others. Each chunk gets:

- a **slug** (kebab-case, ≤30 chars, stable across rounds — its worktree and branch name),
- a **type** from the closed list `feat fix docs refactor perf test chore`,
- a **completion criterion** that is checkable ("endpoint returns the documented shape for these inputs, proven by a named test command"), never aspirational ("implement the feature"),
- the **acceptance criteria** from the spec it satisfies, quoted. Every criterion in the spec belongs to exactly one chunk; if one belongs to none, your cut is incomplete.

Good cuts: a slice with one entry point (route, command, screen), a self-contained module, an isolated bug fix. Bad cuts: anything needing a subagent to guess another's in-flight decisions. **Hard ordering** (B's tests need A's types) is allowed — same round, merged in order — but "I'd like A first" is not ordering.

### 2. Scout wave

One `10x-scout` per chunk, all in one message. Each writes `.worktree/<slug>/EVIDENCE.md` and reports a summary. Skip the scout for a chunk whose code you have already read — a scout restating your own context is pure latency, and you already hold the citations.

### 3. Code wave

One `10x-coder` per chunk, all in one message. Hand each: the slug and its worktree path, the completion criterion, the quoted acceptance criteria, and its slice of the codebase. Append `TDD: on` only when the user asked for test-first — TDD is off by default (red-green slows a chunk; the coder still proves every completion criterion with a named check either way). Do not pre-merge their work in your head — they report, the merger integrates.

### 4. Merge

One `10x-merger`, alone: the base branch, the chunk branches, their dependency order, and each chunk's check command. It owns `integrate/<spec>`, the conflicts, and the gates — every chunk lands as one squashed commit. A collision on the same lines is a decomposition bug — take its note and cut cleaner next round.

### 5. Review

One `10x-reviewer` on `git diff <base>...integrate/<spec>`. It returns `## Standards`, `## Spec`, `## Complexity`, `## Criteria`. Aggregate verbatim or lightly cleaned; never rerank across headings.

### 6. Gate

**Done** = every acceptance criterion met with a named passing check, and no hard finding on any heading. Report the round in one line per heading plus the diff size.

Not done: turn each hard finding and each unmet criterion into a chunk, reusing the slug's worktree if it survived, and start the next round without asking. Stop early only when the user says ship.

## Ship

When the gate is done and the user says ship, squash the run onto base as one commit, then delete the integration branch:

```bash
git checkout <base> && git merge --squash integrate/<spec> && git branch -D integrate/<spec>
```

The landing commit is the run's only durable record — subject `<type>(<spec>): <run summary>`, one `10x-chunk:` line per chunk, trailer `10x-spec: <spec>`. Templates and the monitoring cheat-sheet: `references/BRANCHING.md`.

## When to fall back to single-agent

Parallel beats a team only when the chunks are genuinely independent. One tightly-coupled change with no natural seams: skip the decomposition, work on branch `<type>/<spec>` in the main tree (no worktree — nothing to isolate), run `ponytail` ultra yourself — and `tdd` too if TDD is on — then dispatch just the reviewer on `git diff <base>...<type>/<spec>`. Forcing a four-role round onto coupled work buys merge conflicts, not speed.

Skills the team invokes by name — spell them however your harness does: `ponytail` (ultra, every role), `tdd` (coder, opt-in), `code-review`, `ponytail-review`, `resolving-merge-conflicts`, `fable-thinking` (merger, reviewer).
