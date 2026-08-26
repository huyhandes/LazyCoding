# How agent harnesses manage agents, skills, and config

Research for cross-harness support in LazyClaude (zcode, oh-my-pi, Claude Code, grok-build, Codex).
Goal: know each harness's discovery paths, definition formats, config layers, and **builtin agent
names a packaged skill/subagent must not collide with**. Researched 2026-08-26 against primary
sources (local installs, official repos, official docs). Claims marked UNVERIFIED where a primary
source could not settle them.

## Summary matrix

### Agents & skills

| Harness | User agents dir | Project agents dir | Agent format | Skills roots it reads (user) | Reads `~/.agents/skills`? |
|---|---|---|---|---|---|
| Claude Code | `~/.claude/agents/` | `.claude/agents/` (walk-up, closest wins) | MD + YAML | `~/.claude/skills/` | **No** (needs symlink) |
| zcode | `~/.zcode/agents/` (recursive) | `.zcode/agents/` (cwd) | MD + YAML | `~/.zcode/skills/` | **Yes** |
| Codex | `~/.codex/agents/` | `.codex/agents/` (trusted only) | **TOML** | `~/.agents/skills/` (+ deprecated `~/.codex/skills`) | **Yes** (preferred root) |
| oh-my-pi | `~/.omp/agent/agents/` | `.omp/agents/` (walk-up) | MD + YAML | `~/.omp/agent/skills/` | **Yes** (`agents` provider) |
| grok-build | `~/.grok/agents/` | `.grok/agents/` | MD + YAML | `~/.grok/skills/` | **Yes** (scanned at every tier) |

### Config & memory files

| Harness | User config | Project config | Memory file convention |
|---|---|---|---|
| Claude Code | `~/.claude/settings.json` | `.claude/settings.json` + `settings.local.json` + MDM managed | `CLAUDE.md` (AGENTS.md **not** read natively) |
| zcode | `~/.zcode/cli/config.json` | `.zcode/config.json` / `zcode.json` (root→cwd) | `AGENTS.md` (CLAUDE.md not read) |
| Codex | `~/.codex/config.toml` | `.codex/config.toml` (trusted only, key-restricted) | `AGENTS.md` (root→cwd, concatenated) |
| oh-my-pi | `~/.omp/agent/config.yml` (+ `models.yml`, `mcp.json`) | `.omp/config.yml` etc. | `AGENTS.md` (ancestor walk) |
| grok-build | `~/.grok/config.toml` | `.grok/config.toml` (restricted to mcp/plugins/permission) | `AGENTS.md` + `Claude.md`/`CLAUDE.md` etc. — all variants load |

### Builtin agents — the do-not-collide list (union across all five)

| Name | Claude Code | zcode | Codex | omp | grok-build |
|---|---|---|---|---|---|
| `general-purpose` | ● | ● | | | ● |
| `Explore` / `explore` / `explorer` | ● `Explore` | ● `Explore` | ● `explorer` | | ● `explore` |
| `Plan` / `plan` | ● `Plan` | (mode, not agent) | `/plan` mode | `@plan` model role | ● `plan` |
| `task` / `worker` / `default` | | | ● all three | ● `task` (default spawn) | |
| `reviewer`, `security-reviewer` | `/code-review` bundled skill | | reviewer ("guardian") | ● both | |
| `scout`, `designer`, `librarian`, `sonic` | | | | ● all four | |
| `claude`, `fork`, `statusline-setup`, `claude-code-guide` | ● all four | | | | |

Safe rule: a packaged agent name must avoid **every** name above (case-sensitively per harness),
plus bundled-command namespaces (`/review`, `/doctor`, `/verify`, `/skills`, `$skill-creator`,
`$skill-installer`, …). Override semantics differ — Claude Code and grok-build shadow builtins
silently (documented), Codex custom agents take precedence, zcode keeps a reserved-name set
(`general-purpose`, `Explore`) with unspecified collision behavior, omp is first-wins by discovery
order — so a collision never errors, it silently replaces or gets shadowed.

## Observed pain point (why this research exists)

The four `10x-*` subagents exist as **separate physical copies** in three harness agent dirs —
`~/.zcode/agents/`, `~/.claude/agents/`, and `~/.omp/agent/agents/` — and they have already
drifted: zcode copies updated 2026-08-25, Claude copies 2026-08-22, contents differ (`diff`
verified); the omp copy uses omp-specific frontmatter (`model: ["@task"]`, `thinkingLevel`).
Cross-harness agent management is currently manual copy-paste per harness that silently rots.

---

## grok-build

**Identity**: xAI's official, open-source, terminal coding agent (`grok` binary).
Repo: https://github.com/xai-org/grok-build (Apache-2.0, created 2026-07-14, ~26k stars).
Docs: https://docs.x.ai/build/overview. Rust codebase periodically synced from xAI's internal
monorepo; external contributions not accepted; no GitHub releases — install via
`curl -fsSL https://x.ai/cli/install.sh | bash`. Crate version 1.0.10 as of research date.
**Not** a fork of Claude Code — own Rust codebase with in-tree ports of `openai/codex` and
`sst/opencode` tool implementations (THIRD-PARTY-NOTICES). The third-party `superagent-ai/grok-cli`
is an unrelated tool with a similar name.

### Config

Sources: repo user-guide `crates/codegen/xai-grok-pager/docs/user-guide/05-configuration.md`,
`26-config-reference.md`, https://docs.x.ai/build/overview.

| Layer | Path | Notes |
|---|---|---|
| User config | `~/.grok/config.toml` (TOML; `$GROK_HOME` overridable) | `/settings` writes here |
| Project config | `.grok/config.toml` | Restricted to `[mcp_servers]`, `[plugins]`, `[permission]`, `[mcp] max_output_bytes` only |
| Fleet defaults | `managed_config.toml` (`/etc/grok/` then `$GROK_HOME/`) | User config overrides |
| Org-enforced | `requirements.toml` + macOS MDM `ai.x.grok` | Clamps everything |

Precedence (05-configuration.md): CLI flags > env vars > requirements/MDM > `GROK_CONFIG` overlay >
`config.toml` > `managed_config.toml` > defaults. Key tables include `[subagents]`, `[skills]`,
`[plugins]`, `[compat.claude|cursor|codex]`. `grok inspect` reports config sources, instructions,
skills, plugins, hooks, MCP servers.

### Agents / subagents

Sources: user-guide `16-subagents.md`, https://docs.x.ai/build/features/subagents.

- Format: `.md` + YAML frontmatter in `.grok/agents/` (project) or `~/.grok/agents/` (user).
- Confirmed frontmatter fields: `name`, `description`, `tools` (comma list, e.g.
  `tools: search_tool, use_tool, Read`), `mcpInheritance` (`all|none|named:[…]|except:[…]`),
  `permissionMode` (plugins may not set `bypassPermissions`). Complete field list UNVERIFIED — no
  doc enumerates every field.
- Invocation: model-side only, via `spawn_subagent` tool's `subagent_type` param (params: `prompt`,
  `description`, `subagent_type`, `background`, `isolation: none|worktree`, `resume_from`, `cwd`).
  Max nesting depth 1. User-facing manager: `/config-agents` (alias `/agents`).
- Also: plugin-bundled agents (`my-plugin:reviewer`), custom roles (`.grok/roles/*.toml` or
  `[subagents.roles.<name>]` with `description`/`default_capability_mode`/`model`/`prompt_file`),
  and personas (behavioral overlays, `.grok/personas/*.toml` / `~/.grok/personas/*.toml`).

### Builtin agents (do-not-collide)

`general-purpose` (default full-capability child), `explore` (read/search/shell, no edits), `plan`
(drafts plan, no edits). Custom agents "add new types or **shadow these built-ins by name**" —
collisions shadow rather than error, so a name collision silently replaces a builtin. Bundled
personas exist; doc examples name `researcher`, `concise` — full bundled list UNVERIFIED.

### Skills

Sources: user-guide `08-skills.md`, https://docs.x.ai/build/features/skills-plugins-marketplaces.

- Anthropic-style SKILL.md: yes. Frontmatter: `name` (falls back to dir name), `description`
  (routing signal; falls back to first body paragraph); optional `when-to-use`, `allowed-tools`
  (documented as inert — "does not grant or restrict tools"), `argument-hint`, `user-invocable`,
  `disable-model-invocation`, `metadata`, `paths`. `/create-skill` wizard exists. Discrepancy:
  docs.x.ai says `model`/`effort`/`license`/`compatibility` are accepted-but-not-applied; repo
  08-skills.md documents `model` as working — treat `model` behavior as UNVERIFIED.
- Discovery (priority high→low): `./.grok/skills|commands/` → `<repo_root>/.grok/…` →
  `~/.grok/skills|commands/`; **plus `.agents/skills/` scanned at each tier alongside `.grok/`
  (including `~/.agents/skills/`)**; plus `~/.claude/skills|commands/`, `./.claude/skills|commands/`,
  `~/.cursor/skills/`, `./.cursor/skills/`; plus `[skills] paths` in config. Dedup by name, higher
  priority wins; `[skills] ignore`/`disabled` supported.
- Flat `*.md` under `commands/` become slash commands (Claude legacy layout). User-invocable skills
  appear as `/<skill-name>`; collisions get qualified forms like `/local:commit`.

### Memory / instruction files

No `GROK.md`. Per directory (in order) it checks `Agents.md`, `Claude.md`, `CLAUDE.md`,
`CLAUDE.local.md`, `AGENT.md`, `AGENTS.md` — **all matching files load**, walked repo-root → cwd,
deeper files take precedence (user-guide `12-project-rules.md`). Rules dirs: `<dir>/.grok/rules/`
(always), `.claude/rules/`, `.cursor/rules/`, `~/.grok/rules/`. Claude/Cursor compat defaults on.

### Packager notes

- Grok Build reads `~/.agents/skills/` natively — the LazyClaude dev-mount is discoverable as-is.
- Subagents must be placed in `.grok/agents/` + `~/.grok/agents/`; whether `.claude/agents/*.md`
  definitions are auto-read is **ambiguous**: docs.x.ai's compat blurb lists "agents" among
  auto-read Claude artifacts, but the repo's `[compat.claude] agents` cell documents scanning
  `~/.claude/` instruction files, not agent definitions — UNVERIFIED.
- Avoid shadowing `general-purpose`/`explore`/`plan` — collision silently shadows the builtin.

---

## Claude Code

Sources: live official docs at `https://code.claude.com/docs/en/...` (fetched as raw markdown
2026-08-26; old docs.anthropic.com URLs redirect there), anthropics/claude-code repo, and the
installed v2.1.246 binary. Pages cited: sub-agents, skills, settings, managed-settings, memory,
output-styles, plugins-reference, plugin-marketplaces.

### Subagents

**Discovery precedence** (highest → lowest): 1) managed settings (`.claude/agents/` inside the
managed-settings dir) → 2) `--agents` CLI flag (session-only JSON) → 3) project `.claude/agents/`
→ 4) user `~/.claude/agents/` → 5) plugin `agents/` dir. Same-name conflicts resolve to the
higher-priority location. Project discovery walks cwd→repo-root, **closest to cwd wins**
(v2.1.178+). `.claude/agents/` and `~/.claude/agents/` are scanned recursively; identity is the
`name` field only. Plugin agents get scoped ids (`my-plugin:review:security` from nested dirs).
`--add-dir` dirs contribute their `.claude/agents/` too. User+project dirs are **watched and
hot-reload** within seconds (except brand-new agent dirs mid-session).

**Format**: Markdown + YAML frontmatter, body = system prompt (subagents do NOT inherit the main
system prompt). All fields (only `name`, `description` required):

| Field | Notes |
|---|---|
| `name` | Required; lowercase+hyphens; **no `:`** (reserved for plugin scoping; v2.1.218+ rejects) |
| `description` | Required; the delegation routing signal |
| `tools` | Allowlist; inherits all subagent-available tools if omitted |
| `disallowedTools` | Denylist, applied before `tools`; MCP patterns `mcp__<server>__*` ok |
| `model` | `sonnet`/`opus`/`haiku`/`fable`/full ID/`inherit` |
| `permissionMode` | `default`/`acceptEdits`/`auto`/`dontAsk`/`bypassPermissions`/`plan`; **ignored for plugin agents** |
| `maxTurns` | Max agentic turns |
| `skills` | Skills preloaded in full at startup |
| `mcpServers` | Per-agent MCP; ignored for plugin agents |
| `hooks` | Agent-scoped hooks; ignored for plugin agents |
| `memory` | `user`/`project`/`local` → `~/.claude/agent-memory/<name>/` |
| `background` | Force background |
| `effort` | `low…max` |
| `isolation` | `worktree` → temp git worktree |
| `color`, `initialPrompt` | Display; first turn when run as main `--agent` |

Files skipped silently: no `name`, name starting `-` or containing `:`, `name` without
`description`, unparseable YAML.

**Routing**: automatic delegation matches request text against `description`; explicit via
natural-language name-drop, `@agent-<name>` mention, `claude --agent <name>`, or
`"agent": "<name>"` in settings. The tool was renamed Task → Agent in v2.1.63 (`Task()` aliases).
Subagents can nest: **default depth 3** (`CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH`; `1` disables),
**20 concurrent** cap (`CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS`).

### Builtin agents (do-not-collide)

Documented (sub-agents § "Built-in subagents"; verified in v2.1.246 binary): `Explore` (read-only,
skips CLAUDE.md + git status, one-shot), `Plan` (plan-mode research, read-only), `general-purpose`
(default fallback for untyped Agent calls), `claude` (catch-all; default for dispatched background
sessions), `statusline-setup` (Sonnet, `/statusline`), `claude-code-guide` (Haiku),
`fork` (internal type inheriting the whole conversation). Internal, undocumented:
`main-session`, `workflow-subagent`.

- **Users CAN override builtins by name** — documented for `Explore` ("a user or project subagent
  named `Explore` overrides the built-in"); other builtins UNVERIFIED but shadowing is the
  behavior class, so treat all nine names as reserved.
- Disable: `permissions.deny: ["Agent(Explore)"]`; `CLAUDE_CODE_DISABLE_EXPLORE_PLAN_AGENTS=1`;
  `CLAUDE_AGENT_SDK_DISABLE_BUILTIN_AGENTS=1` (SDK).
- Output styles are **not** agents — they modify the main conversation's system prompt only.
- Bunded skills (`/doctor`, `/code-review`, `/debug`, `/run`, `/verify`, …) occupy the command
  namespace; Claude Code reserves its builtin command names even when unavailable.

### Skills

- Locations & conflict order: **enterprise > personal > project**; plugin skills namespaced
  `plugin-name:skill-name` (never conflict); a skill beats a same-name `.claude/commands/` file.
  Folder name `synced` is reserved. Symlinked skill dirs are followed.
- Project skills load from cwd and every parent `.claude/skills/` up to repo root at startup;
  **nested** dirs below cwd lazy-load on first file access, exposed directory-qualified
  (`apps/web:deploy`).
- Frontmatter (all optional; booleans accept `yes/no/on/off/1/0` since v2.1.218): `name`,
  `description` (+`when_to_use`, combined truncation 1,536 chars), `argument-hint`, `arguments`,
  `disable-model-invocation`, `user-invocable`, `allowed-tools`, `disallowed-tools`, `model`,
  `effort`, **`context: fork` + `agent`** (run the skill inside a subagent; builtins or any custom
  agent; default `general-purpose`), `background`, `hooks`, `paths`, `shell`, `metadata`,
  `license`, `compatibility`. claude.ai upload subset hard-errors on extras.
- Progressive disclosure: description always in context; full body injected on invocation and
  persists for the session; supporting files on demand. Compaction re-attaches most-recent per
  skill (5,000 tokens each, 25,000 budget). Live change detection on SKILL.md text.

### Config / settings / memory

- settings.json precedence: **managed (MDM/claude.ai console) > command line >
  `.claude/settings.local.json` > `.claude/settings.json` (shared, committed) >
  `~/.claude/settings.json` (user)**. List keys (e.g. `permissions.allow`) **merge across
  files**. macOS managed path: `/Library/Application Support/ClaudeCode/managed-settings.json`.
  `~/.claude.json` is internal state — don't edit. Relevant keys: `"agent"`, `skillOverrides`,
  `disableBundledSkills`, `permissions.deny` with `Agent(name)`/`Skill(name)` rules.
- CLAUDE.md hierarchy (all concatenated, none overrides): managed → user `~/.claude/CLAUDE.md` →
  project `./CLAUDE.md` or `./.claude/CLAUDE.md` → `./CLAUDE.local.md`; cwd-and-above at launch,
  subdirs lazy-load; `@path` imports; `.claude/rules/*.md`. **AGENTS.md is not read natively** —
  import or symlink it. Subagents load the full CLAUDE.md hierarchy **except Explore and Plan**.

### Skill ↔ subagent interplay & packaging

- (a) SKILL.md with `context: fork` + `agent: <name>`: body becomes the task prompt for that
  agent, backgrounded by default. (b) Agent with `skills:` frontmatter: skill content injected at
  startup (can't preload `disable-model-invocation: true` skills).
- **Skills-directory plugins — the doc-backed way to ship a skill that carries its own subagent**:
  a `<skill>/` folder containing `.claude-plugin/plugin.json` loads in place as a
  `<name>@skills-dir` plugin and may bundle `agents/`, `hooks/`, MCP. A bare skill (no manifest)
  can never include an agent. Project scope requires workspace trust.
- Full plugin layout: `.claude-plugin/plugin.json`, `skills/<name>/SKILL.md`, `agents/*.md`,
  `hooks/hooks.json`, `commands/`, `output-styles/`, `.mcp.json`. Install:
  `claude plugin marketplace add <owner/repo>` + `claude plugin install <p>@<m>`; plugins are
  **copied into a cache on install — edits stop propagating** (same dev-mount caveat as
  `npx skills`).
- Security caveat: plugin-shipped agents have `hooks`/`mcpServers`/`permissionMode` **ignored** —
  "if you need them, copy the agent file into `.claude/agents/` or `~/.claude/agents/`".

## zcode

**Identity**: Z.ai's desktop coding agent (Electron app + `zcode-cli` runtime; local bundle
`/Users/huybui/Applications/ZCode.app/Contents/Resources/glm/zcode.cjs`, 12.5MB minified — cited by
byte offset below). Official docs: https://zcode.z.ai/en/docs (pages: welcome, agents, subagents,
skill, commands, hooks, mcp-services, memory, plugin).

### Config

| Scope | Path | Source |
|---|---|---|
| User config | `~/.zcode/cli/config.json` | bundle ~935317; diagnosing-mcp §1 |
| Workspace config | `<repo>/.zcode/config.json` and/or `<repo>/zcode.json` — every dir from repo root down to cwd is read | bundle ~6946689; diagnosing-mcp §1 |
| MCP fallback | `~/.agents/mcp.json` / `<repo>/.agents/mcp.json` (top-level `mcpServers`) — read only if the same scope's `.zcode` config has no servers | zcode-configuration-guide; diagnosing-mcp §1 |

Local user config on this machine contains only `plugins.enabledPlugins` (`ponytail@ponytail`) —
no secrets. Model-provider registry (with API keys) lives separately in `~/.zcode/v2/config.json`;
builtin-agent overrides live in `~/.zcode/v2/agents-state.json` (`builtInModelOverrides`,
`builtInThoughtLevelOverrides`, `disabledAgentIds`) — i.e. zcode's Settings UI stores builtin
tweaks out-of-band, not by shadowing agent files.

Default schema highlights (bundle ~746782): `modelCatalog`, `permission`, `storage.dir` (defaults
`~/.zcode`; moves the user agents dir with it), `features` (compact/rewind/subagent/memory/skill/
mcp), `mcp.servers`, `plugins`, `skills` (`enabled`, `roots`, `metadataBudget:20000`),
`skillOverrides`/`commandOverrides` (per-absolute-path enable/disable), `hooks`. Runtime also
accepts `subagents.profiles` (inline profiles) — UNVERIFIED beyond one bundle reference.

Precedence: scope ranking `system 0 < user 10 < project 20 < session 30 < env 40 < cli 50`
(bundle ~746273). Skills/commands/instructions: user shadows workspace shadows plugins
(zcode-configuration-guide tables).

### Agents (subagents)

Discovery (bundle ~11835830, `loadZCodeAgentProfiles`):

- **User**: `~/.zcode/agents/**/*.md` (recursive, sorted).
- **Project**: `<workingDirectory>/.zcode/agents/` (runtime-scanned, `source:"project"`;
  `permissionMode` ignored for project-sourced agents).
- **Plugin**: `<pluginRoot>/agents/<name>.md`, exposed as `plugin:agent`. Caveat: the marketplace
  compatibility report classifies plugin `agents` as `diagnosticOnly` / "recorded but not executed"
  — dispatchability UNVERIFIED; no installed plugin here declares agents.
- **No `.agents/agents` and no `.claude/agents` convention exists** — neither appears in the bundle.

Format: Markdown + frontmatter; required `name`, `description` (else diagnostics
`agent_missing_required_frontmatter`, file ignored). Optional: `model`, `thoughtLevel`, `color`,
`permissionMode` (user scope only), `maxTurns`, `memory` (`user|project|local`), `tools`,
`disallowedTools`, `skills`, `background`, `injectAgentsMd`, `mcpServers` (parent server names).
Body = system prompt. Confirmed against local `~/.zcode/agents/10x-*.md` (which use `name`,
`description`, `model: custom:builtin%3Azai-coding-plan:GLM-5.3`, `injectAgentsMd: true`,
`thoughtLevel`) — these are user-scope files placed manually.

Runtime state (not definitions): `~/.zcode/cli/agents/<sess_id>/agent_<id>/` holds metadata +
transcripts per spawned subagent.

### Builtin agents (do-not-collide)

**Exactly two** (bundle ~10322152: reserved-name set `new Set(["general-purpose","Explore"])`):

- `general-purpose` — tools `["*"]`, `injectAgentsMd: true`.
- `Explore` — read-only (`Bash, Glob, Grep, Read, WebFetch, WebSearch, TodoWrite`).

No plan-mode agent — "plan" is a permission mode, not an agent. Verified in live session snapshots
(`profileId: general-purpose|Explore`, `source: "built-in"`). Plugin agents (like `ponytail:*`,
`10x-*` in this session) come from files, not builtins.

### Skills

Discovery order (zcode-configuration-guide; bundle ~6970145): 1) config `skills.roots`,
2) `~/.zcode/skills`, 3) `~/.agents/skills`, 4) `<repo>/.zcode/skills`, 5) `<repo>/.agents/skills`
(at every level cwd→root, deeper wins), 6) enabled plugins. **`~/.claude/skills` is NOT a
discovery root.** Dot-dirs (except `.system`) and `node_modules` skipped. Identity = file path;
same-named skill: first in order wins.

Format: dir + `SKILL.md`; frontmatter `name`, `description` (required; >1024 chars ⇒ dropped),
`when_to_use`, `license`, `metadata`. Body capped 100KB. Routing: no keyword matcher — the model
sees `name` + first ~250 chars of `description` + `when_to_use` each turn under a shared
`metadataBudget: 20000` (overflow degrades to names-only). Invoke via `$name` or `/` menu.

On this machine all non-plugin skills load from `~/.agents/skills/` (52 dirs, `.skill-lock.json`
from the `npx skills` installer) including the symlinked `10x-implement`; plugins supply
`browser-use:*`, `document-skills:*`, `skill-creator`, `ponytail:*`, `zcode-guide:*`.

### AGENTS.md / CLAUDE.md compatibility

- **AGENTS.md is the instruction convention**: workspace `AGENTS.md` walked cwd→root (candidates
  list is exactly `["AGENTS.md"]`, bundle ~1481716) + user `~/.zcode/AGENTS.md` (100KB cap).
  `/init` writes workspace `AGENTS.md`.
- Claude-Code compat is **partial**: reads `.claude-plugin/plugin.json` /
  `.codex-plugin/plugin.json` as plugin-manifest fallbacks; onboarding may copy
  `~/.claude/CLAUDE.md` → `~/.zcode/AGENTS.md`. It does **not** read `CLAUDE.md`, `.claude/agents`,
  or `~/.claude/skills` (Settings → Skills offers explicit *import* from external dirs — symlink or
  copy — not auto-discovery).

### Packager notes

- The current LazyClaude dev mount (`~/.agents/skills` + `~/.claude/skills` symlinks) works for
  zcode via root 3; the `~/.claude/skills` link is irrelevant to zcode.
- Subagents for zcode must go to `~/.zcode/agents/` (user) or `.zcode/agents/` (project) — a
  separate physical location from Claude Code's, which is exactly where the observed copy drift
  comes from.

## Codex

**Sources**: openai/codex repo (rust sources, releases) + official docs — note the docs moved:
developers.openai.com/codex 308-redirects to **learn.chatgpt.com**; repo `docs/*.md` are now
stubs. Stable **0.149.1** (2026-08-24), ~5-day minor cadence with multiple alphas/day — this
surface moves fast; everything below is ~0.149-era.

### Config

- User: `~/.codex/config.toml` (`$CODEX_HOME` overridable). Project: `.codex/config.toml`, loaded
  **only when the project is trusted** (`projects.<path>.trust_level`); cannot override
  provider/auth/notify/profile/telemetry keys.
- Key options: `model`, `review_model`, `model_providers.*`, profiles (`~/.codex/<name>.config.toml`
  + `--profile`), `approval_policy` (incl. granular `skill_approval`), `sandbox_mode`,
  `mcp_servers.*`, `features.*`, `skills.config` (path/enabled), `agents.*`, inline `[hooks]`.
- **`~/.codex/hooks.json` is official** (learn.chatgpt.com/docs/hooks.md): user + project
  `.codex/hooks.json` + plugin `hooks/hooks.json` + managed `requirements.toml`; gated by
  `features.hooks = true` (confirmed present in local config.toml). Events include
  `SubagentStart`/`SubagentStop`. Only the `herdr-agent-state.sh` script it invokes locally is
  user-custom.
- AGENTS.md: global `~/.codex/AGENTS.md` (or `AGENTS.override.md`, first non-empty wins), then
  repo-root→cwd, at most one file per dir (`AGENTS.override.md` > `AGENTS.md` > fallback names via
  `project_doc_fallback_filenames`), concatenated root-down, 32 KiB cap. **No native CLAUDE.md
  fallback**; `/import` migrates Claude Code/Cursor setups.

### Skills

- Discovery (learn.chatgpt.com/docs/build-skills.md): project `.agents/skills` in every dir from
  cwd up to repo root; user `~/.agents/skills`; admin `/etc/codex/skills`; plus OpenAI-bundled
  system skills. `~/.codex/skills` is a **deprecated compat location, still honored**
  (`codex-rs/ext/skills/src/host_roots.rs` ~95–104: "Deprecated user skills location… kept for
  backward compatibility"). Symlinked folders followed; same names not merged. Spec basis:
  agentskills.io "open agent skills standard".
- Format: SKILL.md frontmatter requires `name` + `description`; optional `scripts/`,
  `references/`, `assets/`, `agents/openai.yaml` metadata (`display_name`, `default_prompt`,
  `policy`, `dependencies.tools`). `[[skills.config]]` can disable; policy
  `allow_implicit_invocation` (default true; false = explicit `$skill` only). Listing budget: 2%
  of context or 8,000 chars.
- Timeline: `.agents/skills` support rust-v0.94.0 (2026-02-02); personal `~/.agents/skills` +
  `~/.codex/skills` compat rust-v0.95.0 (2026-02-04); live reload 0.97.0.

### Subagents — they exist (a "Codex has no subagents" claim is stale)

- learn.chatgpt.com/docs/agent-configuration/subagents.md: "ChatGPT Work and Codex can run
  subagent workflows by spawning specialized agents in parallel." Delegation triggers on direct
  request or project/skill instruction — AGENTS.md and skills can instruct delegation. CLI:
  `/agent` (alias `/subagents`) switches threads.
- Config keys (config-reference.md ~592–636): `agents.enabled` (default **true**),
  `agents.max_concurrent_threads_per_session`, `agents.default_subagent_model`,
  `agents.default_subagent_reasoning_effort`, `agents.<name>.description`,
  `agents.<name>.config_file`.
- **Custom agents are TOML, not markdown**: one agent per file in `~/.codex/agents/` (personal) or
  `.codex/agents/` (project, trusted only); required `name`, `description`,
  `developer_instructions`; optional `model`, `model_reasoning_effort`, `sandbox_mode`,
  `mcp_servers`, `skills.config`. **A custom agent named like a built-in takes precedence.**
- Timeline: `/review` used a subagent by v0.80.0 (2026-01-09); multi-agent explorer role v0.92.0
  (2026-01-27); multi-agent V2 stabilized v0.145.0 (2026-07-21).

### Builtin agent-like names (do-not-collide)

Built-in subagents: **`default`, `worker`, `explorer`**, plus the auto-review reviewer agent
(`approvals_reviewer = "auto_review"`; internal codename "guardian"). Command/mode namespace:
`/plan`, `/review` (+cloud Code Review / Security Review), `/agent`, `/side`, `/compact`,
`/skills`, `/hooks`, `/memories`, `/personality`, `/import`. System skills `$skill-creator`,
`$skill-installer`.

### Local caveat

The local `~/.codex` runs npm 0.122.0 with a missing native binary (`codex --version` → ENOENT) —
stale and broken, predating subagents-V2 and the `.agents/skills` docs era. Local `~/.codex/skills`
(Cloudflare skills + `.system/`) is the legacy layout, still honored by current Codex.

## oh-my-pi (omp)

**Identity**: https://github.com/can1357/oh-my-pi (author Can Bölük — note `can1357`), docs at
https://omp.sh, npm `@oh-my-pi/pi-coding-agent` (latest 18.0.6; locally installed 17.2.8).
Self-described fork of Pi by Mario Zechner (badlogic / earendil-works/pi), "rewritten as a
coding-first surface" — TypeScript + ~80k lines Rust native core, MIT. Monorepo keeps `pi-*`
package names.

### Config

| Scope | Path | Notes |
|---|---|---|
| Global | `~/.omp/agent/config.yml` (YAML) | Written on first run; mutated via `omp config set <path> <value>` |
| Models/providers | `~/.omp/agent/models.yml` | `providers.<id>.baseUrl/apiKey/headers` |
| MCP | `~/.omp/agent/mcp.json` | `mcpServers` + `disabledServers` |
| Project | `.omp/` dir: `config.yml`, `settings.json`, `mcp.json`/`.mcp.json`, `agents/`, `skills/`, `rules/`, `prompts/`, `commands/`, `extensions/`, `hooks/`, `AGENTS.md`, … | Source: `packages/coding-agent/src/discovery/builtin.ts` |
| Profiles | `~/.omp/profiles/<name>/agent` | |

Global config keys observed locally: `modelRoles` (roles: default, smol, slow, plan, commit,
vision, designer, task, advisor, tiny — agents reference these via `@task`/`@smol`/… aliases),
`defaultThinkingLevel`, `task` (`eager`, `enableLsp`), `tools.approvalMode`, `compaction`,
`edit.mode: hashline`, `advisor`, `steeringMode`. First run imports rules/skills/MCP from
`.claude`, `.cursor`, `.windsurf`, `.gemini`, `.codex`, `.cline`, `.github/copilot`, `.vscode`.
Standalone `AGENTS.md` discovered by ancestor walk from cwd (`src/discovery/agents-md.ts`).

Env vars (`docs/environment-variables.md`): `PI_CONFIG_DIR` (default `.omp`),
`PI_CODING_AGENT_DIR`, `OMP_WORKTREE_DIR`, ~60 provider `*_API_KEY`s; every `OMP_*` key mirrors to
`PI_*`. `.env` chain: cwd → `~/.omp/agent/.env` → `~/.omp/.env` → `~/.env`.

### Agents

- **Format**: Markdown + frontmatter, body = system prompt. Required `name`, `description`.
  Optional: `tools` (CSV/array), `spawns` (`*`/CSV), `model` (ordered selector list; role aliases
  like `@task` resolve via `modelRoles`), `thinking-level`/`thinking` (local files use camelCase
  `thinkingLevel` — both appear in primary sources; parser aliasing UNVERIFIED), `output` (typed
  JSON schema for validated results), `blocking`, `autoloadSkills`, `read-summarize`, `prewalk`,
  `advisor`. Source: `docs/task-agent-discovery.md` + local files.
- **Discovery, first-wins by name**: 1) project `.omp/agents` (nearest, walk-up) → 2) user
  `~/.omp/agent/agents/*.md` → 3) extension packages `<ext-root>/agents` → 4) Claude marketplace
  plugin `agents/` dirs → 5) bundled agents embedded at build time. **`.claude/agents`,
  `.codex/agents`, `.gemini/agents` are intentionally skipped.** `omp agents unpack [--project]`
  exports bundled defs to disk.
- **Routing**: the `task` tool spawns agents (omitted `agent` defaults to `task`); model precedence
  `task.agentModelOverrides[name]` → frontmatter `model` → parent model. Recursion guarded by
  `PI_BLOCKED_AGENT` + `task.maxRecursionDepth` (default 2).
- **Skills delegating to agents**: no formal API — delegation is by instruction (skill body tells
  the model to spawn via `task`), the same pattern `10x-implement` uses.

### Builtin (bundled) agents (do-not-collide)

From `docs/task-agent-discovery.md` + `packages/coding-agent/src/prompts/agents/*.md`
(`EMBEDDED_AGENT_DEFS`): `scout` (fast read-only explorer), `designer` (UI/UX),
`reviewer` (code review, spawns scout), `security-reviewer` (read-only auditor),
`librarian` (external lib/API research), `task` (general-purpose worker), `sonic` (fast-tier
`task` variant).

### Skills

Anthropic-style `SKILL.md`, **one level only** under a skills root — nested dirs are NOT
discovered (`docs/skills.md`). Frontmatter: `name` (defaults to dir name), `description`,
`globs`, `alwaysApply`, `hide`, `disableModelInvocation` (normalized from
`disable-model-invocation`); unknown keys preserved. `description` required for native
`.omp`/omp-plugins/github providers; claude/codex/agents providers load without it.

Discovery providers, first-wins by name (priority): `native` (100) `.omp` project walk-up +
`~/.omp/agent/skills` → `omp-plugins` (90) → `claude` (80) → `claude-plugins`/`agents`/`codex`
(70) → `opencode` (55) → `github` (30) `.github/skills/` → `omp-managed` (5) auto-learned skills.
**The `agents` provider reads user `~/.agents/skills` (+ `~/.agent/skills`) and project
`.agents/skills` walking up to repo root** (`src/discovery/agents.ts`) — the exact tree
LazyClaude dev-mounts into. Exposure: name+description in system prompt, content via
`read skill://<name>`, optional `/skill:<name>` commands. Filters: `ignoredSkills`,
`includeSkills`, `disabledExtensions: ["skill:<name>"]`.

### Packager notes

- omp picks up `~/.agents/skills/*` natively; the existing dev mount works as-is.
- Subagents for omp must live in `~/.omp/agent/agents/` (user) or `.omp/agents/` (project) — a
  third physical location; on this machine the `10x-*` agents indeed exist there as a third
  drifting copy.
- Avoid colliding with the seven bundled names above; frontmatter maps closely onto Claude's
  (`name`/`description`/`model`/`tools`) but `model` uses role aliases.

## vercel-labs/skills (`npx skills`) — the cross-harness installer

Sources: `github.com/vercel-labs/skills` (npm `skills@1.5.23`, MIT; deps only `tar`+`yaml`,
Node ≥22.20.0). File citations below are repo paths; raw at
`https://raw.githubusercontent.com/vercel-labs/skills/main/<path>`. README headline:
"Supports OpenCode, Claude Code, Codex, Cursor, and 73 more."

### Harness → directory matrix

Mapping lives in `src/agents.ts` (`agents: Record<AgentType, AgentConfig>` with `skillsDir` +
`globalSkillsDir` per agent); `src/constants.ts` defines `AGENTS_DIR = '.agents'` and
`UNIVERSAL_SKILLS_DIR = '.agents/skills'`. Key entries verbatim:

```ts
'claude-code': { skillsDir: '.claude/skills', globalSkillsDir: join(claudeHome, 'skills') }  // $CLAUDE_CONFIG_DIR || ~/.claude
codex:         { skillsDir: '.agents/skills', globalSkillsDir: join(codexHome, 'skills') }  // $CODEX_HOME || ~/.codex
cursor:        { skillsDir: '.agents/skills', globalSkillsDir: join(home, '.cursor/skills') }
cline/amp/...: { skillsDir: '.agents/skills', globalSkillsDir: join(home, '.agents/skills') }
opencode:      { skillsDir: '.agents/skills', globalSkillsDir: join(configHome, 'opencode/skills') }
zcode:         { skillsDir: '.zcode/skills',  globalSkillsDir: join(zcodeHome, 'skills') }   // ~/.zcode/skills
```

~78 agents total in the table (also rendered in README's "Agent support" table, kept in sync by
`scripts/sync-agents.ts`). Notable globals: codex `~/.codex/skills`, gemini-cli `~/.gemini/skills`,
copilot `~/.copilot/skills`, pi `~/.pi/agent/skills`, qwen-code `~/.qwen/skills`,
windsurf `~/.codeium/windsurf/skills`.

**Routing nuance** (`src/installer.ts`, `getAgentBaseDir`/`installSkillForAgent`): universal agents
(`skillsDir === '.agents/skills'`) install into the canonical dir (project `.agents/skills/<name>`
or global `~/.agents/skills/<name>`) and global installs return early — no duplicate symlink into
agent-specific dirs. Non-universal agents (e.g. claude-code) get a **symlink** from their dir into
the canonical copy; on project installs that symlink is skipped unless the agent's config dir
already exists — except claude-code, which is always linked.

### Subagents: NOT installed — skills only

The installer writes only to skills dirs; it **never writes agent/subagent definition files** (no
`.claude/agents/*.md`). Evidence: `src/installer.ts` touches only `skillsDir`/`globalSkillsDir`;
greps for `subagent|/agents/|agentsDir` in `src/agents.ts` match only Eve's subagent *skills* dirs
(`agent/subagents/<name>/skills`), and the only `--subagent` CLI option installs skills *into* Eve
subagent folders. This confirms the repo AGENTS.md claim: `.claude/agents/` subagents stay
repo-local and must be documented in-skill for portability.

### Install mechanics

- **Default mode is "symlink", but symlink-to-snapshot** (`src/installer.ts`, `src/add.ts:770`):
  symlink mode first *copies* the source into the canonical dir, then symlinks agent dirs to that
  canonical copy — it never links back to the source repo. `--copy` forces plain copy. So
  `npx skills add .` installs a snapshot; edits to the source stop propagating (dev-mount symlinks
  remain manual). Symlink failure (e.g. Windows) falls back to copy.
- **Discovery depth**: `DEFAULT_SKILL_CONTAINER_DEPTH = 3` (`src/constants.ts`) — container dirs
  (repo root if it has SKILL.md, `skills/`, `skills/.curated|.experimental|.system/`, and every
  agent skills dir) are walked up to 3 levels; a SKILL.md found shallower shadows anything nested
  below. `--full_depth` searches outside containers; last-resort recursive walk `maxDepth = 5`
  (`src/skills.ts:133`). Archives capped 10 MiB / 25 MiB extracted / 1000 files.
- **Frontmatter** (`src/skills.ts:98-110`): `name` and `description` required (missing ⇒ skill
  skipped), both strings; name normalized `toLowerCase().replace(/[\s_]+/g,'-')`. YAML-only parser;
  `---js` frontmatter refused (RCE avoidance). `metadata.internal: true` hides unless
  `INSTALL_INTERNAL_SKILLS=1`.
- **No AGENTS.md convention**: the promoted convention is the `.agents/skills` *directory*, not
  agents-md files — README/source never reference `AGENTS.md`.
- **Registry**: no registration — `skills add` accepts `owner/repo`, git URLs, local paths, archive
  URLs; private repos reuse local git/gh/SSH creds. Search directory is skills.sh
  (`https://skills.sh`, `/api/search`); how repos get indexed there is UNVERIFIED (not in CLI
  source). Claude `.claude-plugin/marketplace.json` / `plugin.json` manifests are also honored, and
  manifest-declared paths bypass the depth-3 walk (`src/plugin-manifest.ts`).
- **Lockfile**: project installs write `skills-lock.json` (source + hash); `skills update`
  refreshes; `experimental_install` restores only into `.agents/skills`.
- **Builtin-agent name collisions: no handling found** — greps for
  `builtin|collision|conflict|already exists` across add/installer/skills/list/remove/sync return
  nothing relevant. As of v1.5.23 the installer will happily install a skill named like a builtin
  agent; collision-avoidance is the packager's job.

**Implication for LazyClaude**: publishing = push `skills/<name>/` public; `npx skills add
huybui/LazyClaude --skill 10x-implement -g -a claude-code -y` copies into canonical
`~/.agents/skills/<name>` and symlinks `~/.claude/skills/<name>`. The gap the new functionality
must fill: **subagent definitions and per-harness agent dirs are entirely out of `npx skills`
scope** — that's the white space.

## Installing agents — existing options vs custom script (2026-08-26)

Question: can an off-the-shelf tool install agent definitions, or is a custom script required?

### Verdict up front

**No off-the-shelf tool covers all five harnesses.** Three partial routes exist — Sentry
dotagents (Claude + Codex), native plugin systems (Claude + grok + omp), and an emerging
`.agents/agents/` convention — but zcode and Codex have no working packaged-agent path, so **a
small custom fan-out script is required** for full coverage. The script is genuinely small: four
harnesses take the same markdown file, only Codex needs TOML generation.

### Off-the-shelf installers

| Tool | Installs agents to | Verdict |
|---|---|---|
| **Sentry dotagents** (`npx @sentry/dotagents`, v3.0.1, Aug 2026 — getsentry/dotagents) | `.claude/agents/*.md`, `.codex/agents/*.toml` (**Codex TOML handled**), `.cursor/agents/`, `.opencode/agents/`; sources `[[subagents]]` from `agents.toml`, GitHub/git/path | **VIABLE for Claude + Codex (2/5)** — closest thing to "npx skills for agents"; grok listed as target but with no subagent support; zcode/omp not covered |
| wshobson/agents (202-agent catalog) | Claude plugins, `.codex/agents/`, `.opencode/agents/`, `.copilot/agents/`, Antigravity | PARTIAL; a catalog, not a neutral installer |
| ECC / ecc-universal | Claude, Codex TOML, Cursor, OpenCode + instruction-tier targets | PARTIAL; opinionated full system ("do not stack install methods") |
| supagents (fmind/agent-supagents) | Compiles one MD source → Claude/Gemini/Copilot/Cursor/OpenCode/Kilo | PARTIAL; local compiler, no Codex TOML |
| subagents.sh, VoltAgent, codex-marketplace | Claude-only / Codex-only | NOT VIABLE cross-harness |
| **vercel-labs/skills PR #2026** (open, 2026-08-22) | Would install `agents/` from a repo: canonical `.agents/agents/<name>.md` + per-tool symlinks — **"currently just Claude Code"** | NOT YET; watch this — it would standardize the convention |
| vercel-labs/skills PR #1981 (open) | Adds omp as a *skills* target only | NOT YET for agents |

**Zero tools write `~/.zcode/agents/`, `~/.omp/agent/agents/`, or `~/.grok/agents/`** (verified by
the scan; omp/grok are simply absent from every installer's matrix).

### Native per-harness mechanisms

| Harness | Plugin system carries agents? | Mechanism / evidence | Working path for agents |
|---|---|---|---|
| Claude Code | **YES** | Plugin `agents/` dir; `claude plugin marketplace add` + install; third parties publish via anthropics/claude-plugins-community or self-hosted marketplace. Landed in `~/.claude/plugins/cache/...` (snapshot — **no hot-reload**, `/reload-plugins` needed); project/user `.claude/agents/` **override** same-named plugin agents; `hooks`/`mcpServers`/`permissionMode` ignored in plugin agents | plugin, or copy to `~/.claude/agents/` |
| grok-build | **YES** — most complete | `grok plugin install <src> --trust`; plugin folder holds `skills/, commands/, agents/, hooks/, .mcp.json`; **accepts `.claude-plugin/` manifests as-is** and "automatically reads Claude Code marketplaces, plugins, skills, MCPs, agents, hooks"; open PR-based marketplace (xai-org/plugin-marketplace). Plugin agents can't set `permissionMode: bypassPermissions`/`mcpServers`/hooks | plugin (Claude-format works), or copy to `~/.grok/agents/` |
| oh-my-pi | **YES** | `omp plugin install <pkg\|git\|path>` / `omp plugin link` (verified in local `omp plugin --help`); agent discovery tier 3 = `<extension-root>/agents` of installed plugins; tier 4 = **Claude marketplace plugin roots** when the `claude-plugins` provider is enabled. Caveat: `.claude/agents` etc. "intentionally skipped — their frontmatter schema is not the OMP task-agent contract" | omp plugin carrying `agents/`, or copy to `~/.omp/agent/agents/` |
| zcode | **NO** | Plugin manifest *recognizes* an `agents` component (docs show it "read-only under Plugin subagents"), but the official zcode-guide troubleshooting guide lists `agents` among components **"Recorded but not executed"** (diagnosing-plugins SKILL.md); subagents are "User-level only… stored under ~/.zcode/agents/" (zcode docs). Zero plugins in the local cache ship `agents/` | **copy to `~/.zcode/agents/` only** |
| Codex | **NO** | Real plugin system (`.codex-plugin/plugin.json`, `codex plugin add <p>@<m>`, shared with ChatGPT) but the manifest spec fields end at `skills`, `hooks`, `mcpServers`, `apps`, `interface` — **no agents field**; subagents docs "document no plugin or marketplace mechanism for shipping agent definitions" | hand-placed TOML in `~/.codex/agents/` (or dotagents) |

### Real-world case study: ponytail

The one package distributed multi-harness on this machine (zcode plugin 4.8.4, omp npm plugin,
Claude plugin 4.6.0) maintains **~17 host adapters** (`.claude-plugin/`, `.codex-plugin/`,
`pi-extension/`, `gemini-extension.json`, `.cursor/rules/`, …) and ships **zero agent definitions
to any host** — every adapter delivers skills, hooks, commands, or instruction-tier rules
(`docs/agent-portability.md`). Its omp manifest uses the `pi` package.json convention
(`"pi": {"extensions": [...], "skills": ["./skills"]}`); its zcode/Claude installs come from its
own GitHub repo acting as a marketplace (`.claude-plugin/marketplace.json`, `source: "./"`).
The ecosystem's most-portable package chose to sidestep agent distribution entirely.

### Decision for LazyClaude (final design, 2026-08-26)

Chosen option — **canonical `agents/` dir + one stdlib installer** (minimal solution covering
all five harnesses; plugin manifests / dotagents / marketplace deferred as additive extras):

```
LazyCoding/
  skills/<name>/SKILL.md     ← unchanged, npx-skills compatible
  agents/<name>.md           ← NEW: single source of truth (10x-* moves here; drift ends)
  scripts/install.py         ← NEW: the installer
  .claude/agents → ../agents ← in-repo symlink for Claude project-scope agents
```

- `agents/` at repo root = the emerging convention (dotagents discovers `agents/` source dirs;
  vercel PR #2026 installs from the same dir) — future tooling consumes the repo unchanged.
- `install.py` (default): dev symlink mount — skills → `~/.agents/skills/` + `~/.claude/skills/`;
  agents → `~/.claude/agents/`, `~/.zcode/agents/`, `~/.omp/agent/agents/`, `~/.grok/agents/`;
  **Codex TOML generated** → `~/.codex/agents/<name>.toml` (`name`, `description`,
  `developer_instructions` ← body). `install.py copy`: snapshot install for end users
  (`git clone && ./scripts/install.py copy`); `npx skills add` remains the skills discovery
  channel. Safety: `--dry-run`, no clobbering files it didn't create, backup-before-replace,
  exit codes 0/1/2/130.
- Harness-specific frontmatter (`model`, thought/effort level) lives in the script's config dict,
  not the canonical files — default unmapped = omit field (inherit parent). Rationale: model
  identifiers are the least portable field (Claude aliases vs zcode provider ids vs omp `@roles`
  vs Codex model ids).
- Reserved-name assert against the builtin union table (§ Builtin agents do-not-collide) —
  collisions silently shadow in every harness, so the installer is the only enforcement point.
- Deferred (additive, not load-bearing): `.claude-plugin/plugin.json` for Claude+grok marketplace
  installs; `agents.toml` for dotagents (Claude+Codex) users; curl one-liner wrapper once public.

## Cross-harness synthesis for LazyClaude

### 1. The skills layer has converged; the agents layer has not

All five harnesses consume Anthropic-style `SKILL.md` skills, and four of five (zcode, Codex, omp,
grok-build) read `~/.agents/skills/` directly — the existing dev mount already works for them;
only Claude Code needs the extra `~/.claude/skills` symlink the mount script already creates.
Skill *content* is portable; the only per-harness skill deltas are routing budgets and a few
inert frontmatter keys.

Agent definitions are the opposite: five different locations, two formats (MD+YAML ×4,
**TOML ×1** for Codex), and divergent optional fields. `npx skills` installs skills only and
never writes agent files (verified in its source) — so subagent fan-out is genuine white space,
which matches the drift observed in the `10x-*` copies.

### 2. What a cross-harness agent manager needs to do

Keep **one canonical definition per agent in the repo** (e.g. `skills/<name>/agents/*.md`,
alongside the skill that dispatches it — mirroring the existing repo layout) and fan out at
mount/install time:

| Target | Action | Translation needed |
|---|---|---|
| `~/.claude/agents/` | copy (or bundle via skills-dir plugin, below) | none — canonical format |
| `~/.zcode/agents/` | copy | drop/handle `permissionMode` (ignored for project scope); map `model` to zcode provider ids |
| `~/.omp/agent/agents/` | copy | map `model` to omp role aliases (`@task`, `@smol`); `thinkingLevel` |
| `~/.grok/agents/` | copy | near-identical format; `mcpInheritance` available |
| `~/.codex/agents/` | **generate TOML** | `name`, `description`, `developer_instructions` ← body; `model_reasoning_effort` ← effort/thoughtLevel; skills → `skills.config` |

Field-level portability: `name` + `description` are the only universal required fields (every
harness rejects files without them). `tools` lists differ per harness (zcode's `Explore` uses
zcode tool names; omp CSV/array; codex TOML array) — safest to omit `tools` (inherit all) unless a
read-only guarantee is needed. `model` is the least portable field (Claude aliases vs zcode
provider ids vs omp `@roles` vs Codex model ids) — keep per-harness overrides in the mount config
rather than in the canonical file.

Symlinks instead of copies are untested on most targets (zcode/omp/grok agent dirs) — a mount
script should prefer symlink-then-verify with copy fallback, or just copy + stamp a header for
drift detection. Claude Code, zcode, and omp all hot-reload agent dirs, so symlinks would give
live dev-mount semantics like the skills side has today.

### 3. Not overlapping builtins — concrete rules

1. **Reserved-name set** (union, from the table above): `general-purpose`, `Explore`, `explore`,
   `explorer`, `Plan`, `plan`, `task`, `worker`, `default`, `scout`, `designer`, `reviewer`,
   `security-reviewer`, `librarian`, `sonic`, `claude`, `fork`, `statusline-setup`,
   `claude-code-guide`. Note `scout`/`reviewer` collide with **omp builtins** even though they're
   common agent names — a packaged agent currently named `scout` or `reviewer` would shadow omp's.
   The `10x-*` prefix convention is safe in all five.
2. **Descriptions must not claim builtin territory.** Every harness routes by matching request
   text against agent `description` (Claude Code, zcode, grok) or spawns explicitly — a packaged
   agent whose description says "explore the codebase read-only" will steal `Explore`/`explore`
   delegations even with a distinct name. Describe the skill's specific dispatch contract
   ("dispatched by the 10x-implement skill to work exclusively in its worktree"), as the current
   `10x-*` agents already do.
3. **Skill frontmatter `agent:` references** (Claude Code `context: fork`) should name only
   packaged agents, never builtins, or the skill silently changes behavior when a builtin is
   overridden.
4. **Command namespace**: avoid skill names matching bundled commands/skills — Claude Code's
   `/review`-family and Codex's `$skill-creator`/`$skill-installer` are reserved even when
   unavailable.

### 4. Claude-specific packaging option

A skill folder containing `.claude-plugin/plugin.json` loads in place as a `<name>@skills-dir`
plugin and may bundle its own `agents/` — the doc-backed way to ship a skill + its subagent for
Claude Code with zero install steps. Caveats: plugin agents have `hooks`/`mcpServers`/
`permissionMode` ignored, and project scope requires workspace trust. Worth considering for
`10x-implement` since its agents are already Claude-shaped.

### 5. Remaining unknowns (flagged, not blocking)

- Whether zcode/omp/grok agent dirs follow **symlinked** files (likely, unverified — test before
  relying on symlink fan-out).
- grok-build: whether `.claude/agents/*.md` are auto-read (docs ambiguous, UNVERIFIED).
- zcode: collision behavior when a user agent is named `general-purpose`/`Explore` (reserved set
  exists; shadow vs reject unknown).
- Codex custom-agent TOML is ~1 month old (V2 stabilized 2026-07-21) and the local install is
  broken/stale at 0.122.0 — verify against a current binary before shipping the TOML generator.
