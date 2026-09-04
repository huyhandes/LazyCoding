# Model + thought-level defaults for the 10x team

Research for the `AGENT_MODELS` block in `scripts/install.py`. Decided 2026-09-04
against primary sources (official harness docs, vendor announcements, local
installs). Re-check when a generation ships; the availability axis below is what
catches stale pins.

## Decision

| role | claude | zcode | codex | omp | grok |
|---|---|---|---|---|---|
| 10x-scout | `claude-haiku-4-5` | `GLM-5.3-Flash` @ `high` | `gpt-5.6-luna` @ `low` | `@smol` @ low | `grok-build-0.1` |
| 10x-coder | `claude-sonnet-5` | `GLM-5.3` @ `high` | `gpt-5.6-terra` @ `high` | `@task` @ high | `grok-4.6` |
| 10x-merger | `claude-opus-5` | `GLM-5.3` @ `max` | `gpt-5.6` @ `xhigh` | `@slow` @ max | `grok-4.6` |
| 10x-reviewer | `claude-opus-5` | `GLM-5.3` @ `max` | `gpt-5.6` @ `xhigh` | `@slow` @ max | `grok-4.6` |

Shape: fast cheap scout (latency — it is the pipeline head and blocks the coder),
mid tier on the coder (highest token volume), strongest reasoning on
merger+reviewer (only quality gate, low volume). Every harness's own docs
converge on this split.

## Scoring metric

Cell score per (harness, role) = `0.45·capability + 0.20·latency + 0.20·cost +
0.15·availability`, each axis 0–10:

- **capability** — delivered agentic-coding capability of model@effort vs the
  role's requirement (scout 5.0, coder 7.5, merger/reviewer 9.0, from the briefs'
  duties). Bar met → 10; undershoot penalized 2× (a failed chunk costs a redo
  round).
- **latency** — speed class damped by role sensitivity (scout 1.0, others
  0.5–0.6).
- **cost** — $/token class damped by role volume share (coder 1.0, scout 0.7,
  merger/reviewer 0.5).
- **availability** — does the exact string+effort resolve in that harness today
  (current+documented 10, brand-new catalog entry 7, stale pin 3).

Findings it produced: Flash@low is the *worst* scout variant; Flash@high beats
GLM-5.3@low on quality/cost but trails on wall-clock (more thinking tokens);
Claude `effort` overrides score negative (Opus/Sonnet 5 adaptive thinking already
clears each bar — effort only buys latency/cost); codex with no models pinned was
the weakest harness (8.09 → 9.07).

## Evidence anchors (Sept 2026)

- **Codex**: GPT-5.6 = Sol/Terra/Luna (`gpt-5.3-codex` deprecated 2026-07).
  Official subagents doc maps explorer→Terra/Luna, implementer→`gpt-5.6`,
  reviewer→Terra@high; efforts `low…xhigh` (+ conditional `max`/`ultra`).
  Pricing Sol $5/$30, Terra $2.50/$15, Luna $1/$6 (Luna cut 80% 2026-07-30).
- **zcode**: GLM-5.3 efforts are exactly `low/high/max` (default max).
  GLM-5.3-Flash (2026-08-26): 320B/18B-active hybrid attention, 3× less
  attention compute than GLM-5.3, outperforms GLM-5.2, at max effort 29.0 vs
  Opus 4.8's 29.5 on Z.ai Code Bench; offered via Coding Plan. Community PSA
  (r/ZaiGLM): Flash@low is "very dumb", high≈max in quality — hence Flash scout
  runs @ high, not low.
- **claude**: Sonnet 5 current for implementation subagents (`claude-sonnet-5`,
  $3/$15); Opus 5 strongest agentic ($5/$25); Haiku 4.5 still the small tier.
  Fable 5 rejected for merger/reviewer: loses 7/8 head-to-heads vs Opus 5 at
  $10/$50 with mandatory 30-day retention.
- **grok**: agent `.md` files have no model field; the documented per-type
  override is `[subagents.models]` in `~/.grok/config.toml` (user-guide
  16-subagents.md: `explore = "grok-4.6"`; settings-reference: map of
  subagent → model id, applies for any parent) — the installer patches only
  its own `10x-*` keys there. Fast tier verified 2026-09-04:
  `grok-build-0.1` (x.ai/news/grok-build-0.1 + docs.x.ai catalog) is the
  coding-specialized cheap tier — $1/$2 per 1M (vs `grok-4.6` $2/$6), 256k
  context, 100+ tok/s, cheapest text model in the catalog — so the scout
  pins it; coder/merger/reviewer stay on `grok-4.6` (CursorBench 69.9%
  high-effort vs no comparable score for grok-build-0.1 — the 2× undershoot
  penalty keeps consequential roles on the flagship). If the string ever
  fails to resolve, `grok-build` is the settings-reference-exemplified
  rolling alias.
- **omp**: `@smol/@task/@slow` are modelRoles aliases resolved from the user's
  `~/.omp/agent/config.yml` — the right abstraction for a model-agnostic
  harness; unchanged.

## Caveats

- Codex multi-agent V2 (0.144.x) had a community-reported regression where
  spawn-time model/effort options vanished from the spawn schema; custom-agent
  TOML defaults remain documented — verify on a current binary before relying
  on per-agent pins in production.
- zcode Flash pinned as `custom:builtin%3Azai-coding-plan:GLM-5.3-Flash`
  (matches catalog naming); the app's bundled catalog may lag the docs — if the
  agent fails to resolve its model, update ZCode or temporarily revert the scout
  row to `GLM-5.3` @ `low`.
- Codex coder: `terra@medium` is the cheaper alternative the metric scores a
  hair higher; `terra@high` chosen for tail insurance on hard chunks (official
  "trace complex logic" guidance). A/B with real traces if coder cost matters.
