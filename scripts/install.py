#!/usr/bin/env python3
"""Cross-harness installer for LazyClaude skills + subagents.

One invocation mounts every agent brief in agents/ into every detected
harness's agent dir (per-harness frontmatter injected) and every skill in
skills/ into ~/.agents/skills/ plus ~/.claude/skills/.

Modes: link (default — skills symlink into this repo so edits propagate
live; agents are written as stamped rendered files, refreshed on each run:
zcode's agent loader ignores symlinked files, and agent frontmatter differs
per harness anyway), copy (stamped snapshot files everywhere), uninstall
(removes exactly what this tool created).

Stdlib only, Python 3.10+. Detail: skills/10x-implement/references/INSTALL.md

Usage:
    python3 scripts/install.py [link|copy|uninstall] [--dry-run] [--all]
                               [--force] [--harness <name>]...
        --dry-run           print the full plan, write nothing
        --all               target all five harnesses even if undetected
        --force             back up a foreign target to <name>.bak.<n> first
        --harness <name>    restrict agents to named harnesses (repeatable):
                            claude | zcode | omp | grok | codex
    Exit codes: 0 success · 1 failure · 2 usage error / reserved agent name
                · 130 interrupted
"""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path
from typing import NamedTuple

# ── EDIT ME: models & thought levels ────────────────────────────────────────
# One entry per agent brief, picked Sept-2026 (research/model-defaults.md):
# smallest fast model for the scout, mid tier for the coder, strongest
# reasoning for merger+reviewer. A harness key may be absent — the field is
# then omitted for that harness. "thought" feeds zcode thoughtLevel, omp
# thinkingLevel and codex model_reasoning_effort (via CODEX_EFFORT); it is
# a string shared by every harness, or a dict of per-harness overrides
# (missing harness → field omitted). "grok" never lands in agent frontmatter
# (grok .md files have no model field) — it pins via [subagents.models] in
# ~/.grok/config.toml (grok-build user-guide 16-subagents.md).
AGENT_MODELS: dict[str, dict[str, str | dict[str, str]]] = {
    "10x-scout": {
        "claude": "claude-haiku-4-5",
        "zcode": "custom:builtin%3Azai-coding-plan:GLM-5.3-Flash",
        "omp": "@smol",
        "codex": "gpt-5.6-luna",
        "grok": "grok-build-0.1",
        # Flash under-reasons at low effort — its quality tier starts at
        # high; the other harnesses keep the fast low-effort scout.
        "thought": {"zcode": "high", "omp": "low", "codex": "low"},
    },
    "10x-coder": {
        "claude": "claude-sonnet-5",
        "zcode": "custom:builtin%3Azai-coding-plan:GLM-5.3",
        "omp": "@task",
        "codex": "gpt-5.6-terra",
        "grok": "grok-4.6",
        "thought": "high",
    },
    "10x-merger": {
        "claude": "claude-opus-5",
        "zcode": "custom:builtin%3Azai-coding-plan:GLM-5.3",
        "omp": "@slow",
        "codex": "gpt-5.6",
        "grok": "grok-4.6",
        "thought": "max",
    },
    "10x-reviewer": {
        "claude": "claude-opus-5",
        "zcode": "custom:builtin%3Azai-coding-plan:GLM-5.3",
        "omp": "@slow",
        "codex": "gpt-5.6",
        "grok": "grok-4.6",
        "thought": "max",
    },
}
CODEX_EFFORT = {"low": "low", "high": "high", "max": "xhigh"}
# ────────────────────────────────────────────────────────────────────────────

HARNESSES = ("claude", "zcode", "omp", "grok", "codex")
CONFIG_ROOT = {"claude": ".claude", "zcode": ".zcode", "omp": ".omp",
               "grok": ".grok", "codex": ".codex"}
# Union of builtin agent names across all five harnesses (research:
# harness-agents-config.md). A collision silently shadows a builtin, so the
# installer is the only enforcement point.
RESERVED_NAMES = frozenset({
    "general-purpose", "Explore", "explore", "explorer", "Plan", "plan",
    "task", "worker", "default", "scout", "designer", "reviewer",
    "security-reviewer", "librarian", "sonic", "claude", "fork",
    "statusline-setup", "claude-code-guide",
})

STAMP = "installed-by: lazyclaude scripts/install.py"
MD_STAMP = f"<!-- {STAMP} -->"
TOML_STAMP = f"# {STAMP}"

REPO = Path(__file__).resolve().parent.parent


class UsageError(Exception):
    pass


class Brief(NamedTuple):
    name: str
    description: str
    body: str


# ── brief parsing / rendering ───────────────────────────────────────────────

def load_briefs(agents_dir: Path) -> list[Brief]:
    if not agents_dir.is_dir():
        die(f"no agents dir at {agents_dir} — nothing to install", 1)
    briefs = []
    for path in sorted(agents_dir.glob("*.md")):
        name, description, body = parse_brief(path.read_text(encoding="utf-8"))
        if not name:
            die(f"{path}: missing 'name:' frontmatter line", 1)
        if not description:
            die(f"{path}: missing 'description:' frontmatter line", 1)
        briefs.append(Brief(name, description, body))
    if not briefs:
        die(f"no *.md briefs in {agents_dir}", 1)
    return briefs


def parse_brief(text: str) -> tuple[str, str, str]:
    """First `name:` / `description:` line (value verbatim) + body after the
    closing '---'. Same minimal parsing as the legacy install.sh."""
    lines = text.splitlines(keepends=True)
    delims = [i for i, ln in enumerate(lines) if ln.rstrip("\r\n") == "---"]
    if len(delims) < 2 or delims[0] != 0:
        return "", "", ""
    head = lines[1:delims[1]]
    body = "".join(lines[delims[1] + 1:])
    name = first_field(head, "name")
    description = first_field(head, "description")
    return name, description, body


def first_field(lines: list[str], key: str) -> str:
    prefix = key + ":"
    for ln in lines:
        stripped = ln.rstrip("\r\n")
        if stripped.startswith(prefix):
            return stripped[len(prefix):].lstrip(" ")
    return ""


def render_markdown(brief: Brief, harness: str, model: str | None,
                    thought: str | None, stamp: bool = False) -> str:
    fm = ["---", f"name: {brief.name}", f"description: {brief.description}"]
    if harness == "claude" and model:
        fm.append(f"model: {model}")
    elif harness == "zcode":
        if model:
            fm.append(f'model: "{model}"')
        fm.append("injectAgentsMd: true")
        if thought:
            fm.append(f"thoughtLevel: {thought}")
    elif harness == "omp":
        if model:
            fm.append(f'model: ["{model}"]')
        if thought:
            fm.append(f"thinkingLevel: {thought}")
    # grok: name/description only — grok .md files have no model field;
    # models pin via [subagents.models] in config.toml (install_grok_models)
    out = "\n".join(fm) + "\n---\n"
    if stamp:
        out += MD_STAMP + "\n"
    return out + brief.body


def toml_string(value: str) -> str:
    escaped = (value.replace("\\", "\\\\").replace('"', '\\"')
                    .replace("\n", "\\n").replace("\t", "\\t"))
    return f'"{escaped}"'


def render_toml(brief: Brief, model: str | None, thought: str | None) -> str:
    lines = [
        TOML_STAMP,
        f"name = {toml_string(brief.name)}",
        f"description = {toml_string(brief.description)}",
        f"developer_instructions = {toml_string(brief.body)}",
    ]
    if model:
        lines.append(f"model = {toml_string(model)}")
    if thought:
        if thought not in CODEX_EFFORT:
            die(f"unknown thought level '{thought}' for {brief.name} — fix "
                f"its \"thought\" entry in AGENT_MODELS", 1)
        lines.append(
            f"model_reasoning_effort = {toml_string(CODEX_EFFORT[thought])}")
    return "\n".join(lines) + "\n"


# ── grok per-type model pins ────────────────────────────────────────────────
# grok agent .md files carry no model field; the documented per-type override
# is the [subagents.models] table in ~/.grok/config.toml ("Per-type model
# overrides apply for any parent" — grok-build user-guide 16-subagents.md).
# config.toml is a foreign shared file, so the patch is surgical: only our
# 10x-* keys inside that one table are ever touched.

GROK_MODELS_SECTION = "subagents.models"
GROK_KEY_PREFIX = "10x-"


def grok_key_of(line: str) -> str:
    """Bare key of a TOML key line ('' when the line is not one)."""
    stripped = line.strip()
    if not stripped or stripped.startswith(("#", "[")) or "=" not in stripped:
        return ""
    return stripped.split("=", 1)[0].strip().strip('"').strip("'")


def patch_grok_config(text: str,
                      wanted: dict[str, str]) -> tuple[str, bool] | None:
    """Insert/replace/remove our 10x-* keys in [subagents.models].

    wanted maps agent name → model; an empty dict strips our keys (and the
    table itself when nothing but comments remains). The table is appended
    at EOF when missing. Foreign keys and every other section are left
    byte-identical. Returns (new_text, changed), or None when the config
    defines models as an inline table (`models = {…}` under [subagents]),
    which TOML forbids extending — caller warns and skips."""
    lines = text.splitlines(keepends=True)
    start = None
    end = len(lines)
    for i, ln in enumerate(lines):
        stripped = ln.strip()
        if stripped.startswith("[") and "]" in stripped:
            name = stripped[1:stripped.index("]")].strip()
            if name == GROK_MODELS_SECTION and start is None:
                start = i + 1
            elif start is not None:
                end = i
                break
    if start is None:
        if not wanted:
            return text, False
        if any(grok_key_of(ln) == "models" and "{" in ln for ln in lines):
            return None
        base = text
        if base and not base.endswith("\n"):
            base += "\n"
        if base and not base.endswith("\n\n"):
            base += "\n"
        addition = (f"[{GROK_MODELS_SECTION}]\n"
                    + "".join(f'{k} = "{v}"\n'
                              for k, v in sorted(wanted.items())))
        return base + addition, True
    header = lines[start - 1]
    kept = [ln for ln in lines[start:end]
            if not grok_key_of(ln).startswith(GROK_KEY_PREFIX)]
    if wanted:
        lines[start - 1:end] = (
            [header]
            + [f'{k} = "{v}"\n' for k, v in sorted(wanted.items())]
            + kept)
    elif any(grok_key_of(ln) for ln in kept):
        lines[start - 1:end] = [header] + kept
    else:  # nothing but our comments/blanks would remain — drop the table
        lines[start - 1:end] = []
    new = "".join(lines)
    return new, new != text


# ── paths / ours-predicate ──────────────────────────────────────────────────

def home_path() -> Path:
    home = os.environ.get("HOME", "")
    if not home:
        die("HOME is not set", 1)
    return Path(home)


def agent_dir(home: Path, harness: str) -> Path:
    sub = ("agent", "agents") if harness == "omp" else ("agents",)
    return home.joinpath(CONFIG_ROOT[harness], *sub)


def agent_dest(home: Path, harness: str, brief: Brief) -> Path:
    suffix = ".toml" if harness == "codex" else ".md"
    return agent_dir(home, harness) / (brief.name + suffix)


def is_ours(path: Path) -> bool:
    """A target is ours iff it is a symlink resolving into this repo or a
    file/dir carrying the installer stamp. Foreign targets are never touched
    without --force."""
    if path.is_symlink():
        try:
            resolved = path.resolve()
        except OSError:
            return False
        return resolved == REPO or REPO in resolved.parents
    stamp = STAMP.encode("utf-8")
    if path.is_file():
        try:
            return stamp in path.read_bytes()
        except OSError:
            return False
    if path.is_dir():
        skill_md = path / "SKILL.md"
        if skill_md.is_file():
            try:
                return stamp in skill_md.read_bytes()
            except OSError:
                return False
    return False


# ── plan / execute ──────────────────────────────────────────────────────────

class Installer:
    def __init__(self, mode: str, dry: bool, force: bool) -> None:
        self.mode = mode
        self.dry = dry
        self.force = force
        self.refusals = 0

    def say(self, message: str) -> None:
        print(message)

    def warn(self, message: str) -> None:
        print(message, file=sys.stderr)

    def ensure_symlink(self, dest: Path, target: Path,
                       link_text: str | None = None) -> None:
        link_text = link_text or str(target)
        if dest.is_symlink() and os.readlink(dest) == link_text:
            self.say(f"ok     {dest}")
            return
        if dest.exists() or dest.is_symlink():
            if not self.prepare_replace(dest):
                return
        self.say(f"link   {dest} -> {link_text}")
        if not self.dry:
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.symlink_to(link_text)

    def ensure_file(self, dest: Path, content: str) -> None:
        if dest.is_file() and not dest.is_symlink():
            try:
                if dest.read_text(encoding="utf-8") == content:
                    self.say(f"ok     {dest}")
                    return
            except (OSError, UnicodeDecodeError):
                pass
        if dest.exists() or dest.is_symlink():
            if not self.prepare_replace(dest):
                return
        self.say(f"write  {dest}")
        if not self.dry:
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(content, encoding="utf-8")

    def prepare_replace(self, dest: Path) -> bool:
        """dest exists and is not already correct. True → caller may replace."""
        if is_ours(dest):
            self.say(f"refresh {dest} (ours)")
            if not self.dry:
                self.remove(dest)
            return True
        if not self.force:
            self.refusals += 1
            self.warn(f"refuse {dest} (not created by this installer; "
                      f"use --force to back it up and replace)")
            return False
        backup = backup_path(dest)
        self.say(f"backup {dest} -> {backup}")
        if not self.dry:
            dest.rename(backup)
        return True

    def remove(self, path: Path) -> None:
        if path.is_symlink() or path.is_file():
            path.unlink()
        elif path.is_dir():
            shutil.rmtree(path)

    # ── install ──

    def install_agents(self, home: Path, briefs: list[Brief],
                       targets: list[str]) -> None:
        for harness in targets:
            for brief in briefs:
                mapping = AGENT_MODELS[brief.name]
                model = mapping.get(harness)
                thought = mapping.get("thought")
                if isinstance(thought, dict):
                    thought = thought.get(harness)
                if harness == "codex":
                    content = render_toml(brief, model, thought)
                else:
                    # Real stamped files, not symlinks: zcode's agent loader
                    # collects entries via isFile() and so ignores symlinked
                    # agent files (verified in the zcode.cjs bundle). Skills
                    # are symlinked directories, which every harness follows.
                    content = render_markdown(brief, harness, model, thought,
                                              stamp=True)
                self.ensure_file(agent_dest(home, harness, brief), content)

    def install_grok_models(self, home: Path, briefs: list[Brief]) -> None:
        """Pin 10x-* per-type models in ~/.grok/config.toml."""
        wanted = {b.name: AGENT_MODELS[b.name]["grok"] for b in briefs
                  if AGENT_MODELS[b.name].get("grok")}
        if not wanted:
            return
        path = home / ".grok" / "config.toml"
        try:
            text = path.read_text(encoding="utf-8") if path.is_file() else ""
        except (OSError, UnicodeDecodeError) as exc:
            self.warn(f"refuse {path} ({exc})")
            self.refusals += 1
            return
        result = patch_grok_config(text, wanted)
        if result is None:
            self.refusals += 1
            self.warn(f"refuse {path} (models defined as an inline table — "
                      f"pin [subagents.models] by hand)")
            return
        new, changed = result
        if not changed:
            self.say(f"ok     {path}")
            return
        self.say(f"patch  {path} ({', '.join(sorted(wanted))})")
        if not self.dry:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(new, encoding="utf-8")

    def install_skills(self, home: Path, targets: list[str]) -> None:
        skills_dir = REPO / "skills"
        if not skills_dir.is_dir():
            return
        bases = [home / ".agents" / "skills"]
        if "claude" in targets:
            bases.append(home / ".claude" / "skills")
        for skill in sorted(skills_dir.iterdir()):
            if not (skill / "SKILL.md").is_file():
                continue
            for base in bases:
                dest = base / skill.name
                if self.mode == "link":
                    self.ensure_symlink(dest, skill)
                else:
                    self.ensure_skill_copy(dest, skill)

    def ensure_skill_copy(self, dest: Path, skill: Path) -> None:
        if dest.is_dir() and not dest.is_symlink() and is_ours(dest):
            self.say(f"ok     {dest}")
            return
        if dest.exists() or dest.is_symlink():
            if not self.prepare_replace(dest):
                return
        self.say(f"write  {dest} (stamped copy)")
        if not self.dry:
            shutil.copytree(skill, dest)
            skill_md = dest / "SKILL.md"
            text = skill_md.read_text(encoding="utf-8")
            skill_md.write_text(insert_md_stamp(text), encoding="utf-8")

    def convenience_link(self) -> None:
        """In-repo .claude/agents -> ../agents for Claude project scope."""
        link = REPO / ".claude" / "agents"
        target = REPO / "agents"
        if not target.is_dir():
            return
        self.ensure_symlink(link, target, link_text="../agents")

    # ── uninstall ──

    def uninstall(self, home: Path, targets: list[str]) -> None:
        removed = 0
        for harness in targets:
            removed += self.uninstall_dir(agent_dir(home, harness))
        removed += self.uninstall_dir(home / ".agents" / "skills")
        removed += self.uninstall_dir(home / ".claude" / "skills")
        build = REPO / ".build"
        if build.is_dir():  # legacy: pre-real-file link mode rendered here
            self.say(f"rm     {build}")
            if not self.dry:
                shutil.rmtree(build)
        link = REPO / ".claude" / "agents"
        if link.is_symlink() and is_ours(link):
            self.say(f"rm     {link}")
            if not self.dry:
                link.unlink()
        self.uninstall_grok_models(home)
        self.say(f"uninstalled {removed} item(s); foreign files untouched")

    def uninstall_grok_models(self, home: Path) -> None:
        path = home / ".grok" / "config.toml"
        if not path.is_file():
            return
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            return
        result = patch_grok_config(text, {})
        if result is None:
            self.warn(f"keep   {path} (inline models table — edit by hand)")
            return
        new, changed = result
        if not changed:
            return
        self.say(f"patch  {path} (drop 10x-* model pins)")
        if not self.dry:
            if new.strip():
                path.write_text(new, encoding="utf-8")
            else:  # only our now-empty table ever leaves the file blank
                path.unlink()

    def uninstall_dir(self, directory: Path) -> int:
        if not directory.is_dir():
            return 0
        count = 0
        for path in sorted(directory.iterdir()):
            if is_ours(path):
                self.say(f"rm     {path}")
                if not self.dry:
                    self.remove(path)
                count += 1
            else:
                self.say(f"keep   {path} (not ours)")
        return count


def insert_md_stamp(text: str) -> str:
    """Stamp a copied SKILL.md right after its frontmatter block."""
    lines = text.splitlines(keepends=True)
    delims = [i for i, ln in enumerate(lines) if ln.rstrip("\r\n") == "---"]
    if len(delims) >= 2 and delims[0] == 0:
        idx = delims[1] + 1
        return "".join(lines[:idx]) + MD_STAMP + "\n" + "".join(lines[idx:])
    return MD_STAMP + "\n" + text


def backup_path(dest: Path) -> Path:
    n = 1
    while dest.with_name(f"{dest.name}.bak.{n}").exists():
        n += 1
    return dest.with_name(f"{dest.name}.bak.{n}")


# ── CLI ─────────────────────────────────────────────────────────────────────

def die(message: str, code: int) -> None:
    print(f"install.py: {message}", file=sys.stderr)
    sys.exit(code)


def parse_args(argv: list[str]) -> tuple[str, bool, bool, bool, list[str]]:
    mode = "link"
    dry = all_ = force = False
    harnesses: list[str] = []
    args = list(argv)
    if args and not args[0].startswith("-"):
        mode = args.pop(0)
    if mode not in ("link", "copy", "uninstall"):
        raise UsageError(f"unknown mode '{mode}' (want link|copy|uninstall)")
    i = 0
    while i < len(args):
        arg = args[i]
        if arg in ("--dry-run",):
            dry = True
        elif arg in ("--all",):
            all_ = True
        elif arg in ("--force",):
            force = True
        elif arg in ("--harness",):
            i += 1
            if i >= len(args):
                raise UsageError("--harness needs a value")
            if args[i] not in HARNESSES:
                raise UsageError(
                    f"unknown harness '{args[i]}' (want {'|'.join(HARNESSES)})")
            if args[i] not in harnesses:
                harnesses.append(args[i])
        elif arg in ("-h", "--help"):
            print(__doc__)
            sys.exit(0)
        else:
            raise UsageError(f"unknown argument '{arg}'")
        i += 1
    return mode, dry, all_, force, harnesses


def resolve_targets(home: Path, all_: bool, harnesses: list[str]) -> list[str]:
    if harnesses:
        return harnesses
    detected = [h for h in HARNESSES
                if (home / CONFIG_ROOT[h]).exists()]
    if all_:
        return list(HARNESSES)
    return detected


def main(argv: list[str]) -> int:
    try:
        mode, dry, all_, force, harnesses = parse_args(argv)
    except UsageError as exc:
        print(f"usage error: {exc}", file=sys.stderr)
        print(__doc__, file=sys.stderr)
        return 2

    home = home_path()
    installer = Installer(mode, dry, force)
    targets = resolve_targets(home, all_, harnesses)

    if mode == "uninstall":
        installer.uninstall(home, targets if harnesses or all_ else HARNESSES)
        return 0

    briefs = load_briefs(REPO / "agents")
    reserved = sorted(b.name for b in briefs if b.name in RESERVED_NAMES)
    if reserved:
        die(f"agent name(s) {reserved} collide with a harness builtin — "
            f"rename the brief before installing", 2)
    unmapped = sorted(b.name for b in briefs if b.name not in AGENT_MODELS)
    if unmapped:
        die(f"no model mapping for {unmapped} — add an entry to "
            f"AGENT_MODELS at the top of scripts/install.py", 1)

    skipped = [h for h in HARNESSES if h not in targets]
    for h in skipped:
        root = home / CONFIG_ROOT[h]
        reason = "not targeted" if root.exists() else f"no {root}"
        installer.say(f"skip   {h} ({reason})")

    installer.install_agents(home, briefs, targets)
    if "grok" in targets:
        installer.install_grok_models(home, briefs)
    installer.install_skills(home, targets)
    installer.convenience_link()

    outcome = "would install" if dry else "installed"
    summary = (f"{outcome} {len(briefs)} agent(s) into {len(targets)} "
               f"harness(es), mode={mode}")
    if installer.refusals:
        installer.warn(f"{installer.refusals} foreign target(s) refused "
                       f"(re-run with --force after reviewing --dry-run)")
        return 1
    installer.say(summary)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except KeyboardInterrupt:
        sys.exit(130)
