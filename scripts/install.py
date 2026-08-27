#!/usr/bin/env python3
"""Cross-harness installer for LazyClaude skills + subagents.

One invocation mounts every agent brief in agents/ into every detected
harness's agent dir (per-harness frontmatter injected) and every skill in
skills/ into ~/.agents/skills/ plus ~/.claude/skills/.

Modes: link (default — agents render into .build/ and symlink back into
this repo; skills symlink directly, so skill edits propagate live and agent
edits propagate on the next run), copy (stamped snapshot files), uninstall
(removes exactly what this tool created). Codex always gets real TOML files
(symlink-following for Codex agent files is unverified).

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
# One entry per agent brief. Per-harness model + one shared thought level.
# A harness key may be absent — the field is then omitted for that harness
# (grok-style neutral). "thought" feeds zcode thoughtLevel, omp thinkingLevel
# and codex model_reasoning_effort (via CODEX_EFFORT).
AGENT_MODELS: dict[str, dict[str, str]] = {
    "10x-scout": {
        "claude": "claude-haiku-4-5",
        "zcode": "custom:builtin%3Azai-coding-plan:GLM-5.3",
        "omp": "@smol",
        "thought": "low",
    },
    "10x-coder": {
        "claude": "claude-sonnet-4-6",
        "zcode": "custom:builtin%3Azai-coding-plan:GLM-5.3",
        "omp": "@task",
        "thought": "high",
    },
    "10x-merger": {
        "claude": "claude-opus-5",
        "zcode": "custom:builtin%3Azai-coding-plan:GLM-5.3",
        "omp": "@slow",
        "thought": "max",
    },
    "10x-reviewer": {
        "claude": "claude-opus-5",
        "zcode": "custom:builtin%3Azai-coding-plan:GLM-5.3",
        "omp": "@slow",
        "thought": "max",
    },
}
CODEX_EFFORT = {"low": "low", "high": "high", "max": "high"}
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
    # grok: name/description only (grok model field UNVERIFIED — omit)
    out = "\n".join(fm) + "\n---\n"
    if stamp:
        out += MD_STAMP + "\n"
    return out + brief.body


def toml_string(value: str) -> str:
    escaped = (value.replace("\\", "\\\\").replace('"', '\\"')
                    .replace("\n", "\\n").replace("\t", "\\t"))
    return f'"{escaped}"'


def render_toml(brief: Brief, thought: str | None) -> str:
    lines = [
        TOML_STAMP,
        f"name = {toml_string(brief.name)}",
        f"description = {toml_string(brief.description)}",
        f"developer_instructions = {toml_string(brief.body)}",
    ]
    if thought:
        lines.append(
            f"model_reasoning_effort = {toml_string(CODEX_EFFORT[thought])}")
    return "\n".join(lines) + "\n"


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
    if path.is_file():
        try:
            return STAMP in path.read_text(encoding="utf-8")
        except OSError:
            return False
    if path.is_dir():
        skill_md = path / "SKILL.md"
        if skill_md.is_file():
            try:
                return STAMP in skill_md.read_text(encoding="utf-8")
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

    def render(self, path: Path, content: str) -> None:
        if path.is_file():
            try:
                if path.read_text(encoding="utf-8") == content:
                    return
            except OSError:
                pass
        self.say(f"render {path}")
        if not self.dry:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")

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
            except OSError:
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
                if harness == "codex":
                    content = render_toml(brief, thought)
                    # Codex: real stamped file (symlinks unverified there).
                    self.ensure_file(agent_dest(home, harness, brief), content)
                    continue
                rendered = render_markdown(brief, harness, model, thought)
                if self.mode == "link":
                    build = REPO / ".build" / harness / (brief.name + ".md")
                    self.render(build, rendered)
                    self.ensure_symlink(agent_dest(home, harness, brief), build)
                else:
                    stamped = render_markdown(brief, harness, model, thought,
                                              stamp=True)
                    self.ensure_file(agent_dest(home, harness, brief), stamped)

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
        if build.is_dir():
            self.say(f"rm     {build}")
            if not self.dry:
                shutil.rmtree(build)
        link = REPO / ".claude" / "agents"
        if link.is_symlink() and is_ours(link):
            self.say(f"rm     {link}")
            if not self.dry:
                link.unlink()
        self.say(f"uninstalled {removed} item(s); foreign files untouched")

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
        installer.say(f"skip   {h} (no {home / CONFIG_ROOT[h]})")

    installer.install_agents(home, briefs, targets)
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
