# Branching: names, lifecycle, ledger, monitoring

One 10x run in a target repo owns a `<spec>` name and three name shapes. NOTHING else branches.

| Object | Pattern | Example |
|---|---|---|
| Chunk branch | `<type>/<spec>/<slug>` | `feat/auth-mvp/endpoints` |
| Integration branch | `integrate/<spec>` | `integrate/auth-mvp` |
| Worktree | `.worktree/<spec>/<slug>` | `.worktree/auth-mvp/endpoints` |
| Fallback branch (single-agent) | `<type>/<spec>` | `refactor/config-purge` |

## Naming rules

- `<type>` MUST come from the closed list: `feat fix docs refactor perf test chore`. One type per chunk; the spec's primary type (picked at decompose) headlines the landing commit.
- `<spec>` MUST be kebab-case, ASCII, ≤30 chars, picked once per run. Two concurrent runs on different specs never collide; the same spec is one-run-at-a-time.
- `<slug>` MUST follow the same rules and MUST stay stable across rounds: round 2 re-creates the branch under the same name after round 1's was squash-deleted. The name is the concept; the branch is the incarnation.
- `10x/` MUST NOT appear in branch names. The skill's fingerprint lives in commit trailers: `git log --grep='^10x-'`.

## Lifecycle (squash twice)

1. **Create** — orchestrator, per chunk: `git worktree add .worktree/<spec>/<slug> -b <type>/<spec>/<slug>`.
2. **Code** — coder: small TDD commits on the chunk branch. `EVIDENCE.md` and anything under `.worktree/` are NEVER committed.
3. **Integrate** — merger: round 1 `git checkout -B integrate/<spec> <base>`; later rounds `git checkout integrate/<spec>` and merge only that round's new branches; NEVER reset it — resolved conflicts live in its squash commits. Per chunk, in dependency order: `git merge --squash <type>/<spec>/<slug>`, resolve, commit immediately with the chunk template. One commit per chunk; the coder's red/green history dies with the branch.
4. **Review** — `git diff <base>...integrate/<spec>`.
5. **Chunk cleanup** — merger, after gates, for chunks that landed cleanly and passed: `git worktree remove .worktree/<spec>/<slug>` and `git branch -D <type>/<spec>/<slug>` (capital D: a squashed branch is never ancestry-merged). Failed chunks keep both for the next round.
6. **Ship** — orchestrator, when the gate is done and the user says ship: `git checkout <base> && git merge --squash integrate/<spec>`, commit with the landing template, then `git branch -D integrate/<spec>`. After ship, the landing commit is the run's ONLY survivor — it is the durable record.

## Commit templates

Chunk squash on `integrate/<spec>` (ephemeral — dies with the branch):

    <type>: <summary> (round <n>)

    check: <chunk check command and result>

    10x-chunk: <type>/<spec>/<slug>

Landing squash on base (durable):

    <type>(<spec>): <run summary>

    10x-chunk: <type>/<spec>/<slug> · round <n> · check: <result>
    10x-round: <n> · hard findings: <k> → <slugs>

    10x-spec: <spec>

One `10x-chunk:` line per chunk, in merge order; one `10x-round:` line per round after round 1.

## Monitoring cheat-sheet

| Question | Command |
|---|---|
| Active specs | `git branch --list 'integrate/*'` |
| Chunks in flight | `git worktree list` |
| Chunk ledger mid-run | `git log --oneline integrate/<spec>` |
| Everything the team made | `git log --grep='^10x-'` |
| One chunk, post-ship | `git log --grep='^10x-chunk:.*<slug>'` |
| One run, post-ship | `git log --grep='^10x-spec: <spec>'` |

## Fallback (single-agent)

Coupled work skips chunks: branch `<type>/<spec>` in the main working tree, no worktree (nothing to isolate). The reviewer diffs `git diff <base>...<type>/<spec>`. Ship with the same squash step and landing template — one `10x-chunk: <type>/<spec>` line.
