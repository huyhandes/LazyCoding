---
name: 10x-implement
description: "Implement a spec or ticket set with a four-role subagent team — scout, coder, merger, reviewer — each in its own worktree, looping rounds until every acceptance criterion is green."
disable-model-invocation: true
---

Implement the work described by the spec or tickets at 10x speed. You orchestrate; **the team does the typing.**

Four multipliers do the work — name them, don't restate them:

1. **Parallel AFK.** One message, one subagent call per chunk. Stay out of their way until they return.
2. **A team, not clones.** Four roles on tiered models, all on `ponytail` ultra: `10x-scout` (cited evidence), `10x-coder` (+ `tdd`), `10x-merger` (conflicts and the seam, + `fable-thinking`), `10x-reviewer` (four headings, + `fable-thinking`). Briefs live in `agents/` at the repo root; models and thinking levels live in the `AGENT_MODELS` block of `scripts/install.py`.
3. **Worktree per chunk.** Scout and coder for chunk `<slug>` work only in `$CWD/.worktree/<slug>` on branch `10x/<slug>`. Parallel edits never collide mid-flight; collisions surface once, at the merge.
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
printf '/.worktree/\nEVIDENCE.md\n' >> .git/info/exclude   # once per repo: scratch never reaches a branch
git worktree add .worktree/<slug> -b 10x/<slug>            # per chunk
```

## The round

### 1. Decompose

Read the spec or tickets fully, then cut the work into **chunks**. A chunk is the smallest unit that can ship on its own, so a subagent can take it without talking to the others. Each chunk gets:

- a **slug** (its worktree and branch name),
- a **completion criterion** that is checkable ("endpoint returns the documented shape for these inputs, proven by a named test command"), never aspirational ("implement the feature"),
- the **acceptance criteria** from the spec it satisfies, quoted. Every criterion in the spec belongs to exactly one chunk; if one belongs to none, your cut is incomplete.

Good cuts: a slice with one entry point (route, command, screen), a self-contained module, an isolated bug fix. Bad cuts: anything needing a subagent to guess another's in-flight decisions. **Hard ordering** (B's tests need A's types) is allowed — same round, merged in order — but "I'd like A first" is not ordering.

### 2. Scout wave

One `10x-scout` per chunk, all in one message. Each writes `.worktree/<slug>/EVIDENCE.md` and reports a summary. Skip the scout for a chunk whose code you have already read — a scout restating your own context is pure latency, and you already hold the citations.

### 3. Code wave

One `10x-coder` per chunk, all in one message. Hand each: the slug and its worktree path, the completion criterion, the quoted acceptance criteria, and its slice of the codebase. Do not pre-merge their work in your head — they report, the merger integrates.

### 4. Merge

One `10x-merger`, alone: the base branch, the chunk branches, their dependency order, and each chunk's check command. It owns `10x/integrate`, the conflicts, and the gates. A collision on the same lines is a decomposition bug — take its note and cut cleaner next round.

### 5. Review

One `10x-reviewer` on `git diff <base>...10x/integrate`. It returns `## Standards`, `## Spec`, `## Complexity`, `## Criteria`. Aggregate verbatim or lightly cleaned; never rerank across headings.

### 6. Gate

**Done** = every acceptance criterion met with a named passing check, and no hard finding on any heading. Report the round in one line per heading plus the diff size.

Not done: turn each hard finding and each unmet criterion into a chunk, reusing the slug's worktree if it survived, and start the next round without asking. Stop early only when the user says ship.

## When to fall back to single-agent

Parallel beats a team only when the chunks are genuinely independent. One tightly-coupled change with no natural seams: skip the decomposition, run `ponytail` ultra and `tdd` yourself, then dispatch just the reviewer. Forcing a four-role round onto coupled work buys merge conflicts, not speed.

Skills the team invokes by name — spell them however your harness does: `ponytail` (ultra, every role), `tdd`, `code-review`, `ponytail-review`, `resolving-merge-conflicts`, `fable-thinking` (merger, reviewer).
