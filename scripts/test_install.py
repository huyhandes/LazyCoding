#!/usr/bin/env python3
"""Behavioral check for scripts/install.py. Run: python3 scripts/test_install.py

Builds throwaway fixture repos (a copy of install.py + synthetic briefs and
a skill), runs it as a subprocess against a fake HOME — the CLI seam — and
asserts the externally visible tree. No frameworks, no committed fixtures.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

INSTALL_PY = Path(__file__).resolve().parent / "install.py"
CFG_ROOT = {"claude": ".claude", "zcode": ".zcode", "omp": ".omp",
            "grok": ".grok", "codex": ".codex"}
AGENT_DIR = {"claude": ".claude/agents", "zcode": ".zcode/agents",
             "omp": ".omp/agent/agents", "grok": ".grok/agents",
             "codex": ".codex/agents"}
ZCODE_MODEL = "custom:builtin%3Azai-coding-plan:GLM-5.3"
ZCODE_SCOUT_MODEL = "custom:builtin%3Azai-coding-plan:GLM-5.3-Flash"
MD_STAMP = "<!-- installed-by: lazyclaude scripts/install.py -->"

BRIEFS = {
    "10x-scout": ("Fixture scout", "Scout body.\n"),
    "10x-coder": ('Fixture coder', 'Coder "quoted" body.\n'),
    "10x-merger": ("Fixture merger", "Merger body.\n"),
}


def make_repo(tmp: Path, extra_briefs: dict[str, tuple[str, str]] | None = None,
              skill: str = "fixture-skill") -> Path:
    repo = tmp / "repo"
    (repo / "scripts").mkdir(parents=True)
    shutil.copy2(INSTALL_PY, repo / "scripts" / "install.py")
    agents = repo / "agents"
    agents.mkdir()
    for name, (desc, body) in {**BRIEFS, **(extra_briefs or {})}.items():
        (agents / f"{name}.md").write_text(
            f"---\nname: {name}\ndescription: {desc}\n---\n{body}",
            encoding="utf-8")
    skill_dir = repo / "skills" / skill
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        f"---\nname: {skill}\ndescription: fixture skill\n---\nSkill body.\n",
        encoding="utf-8")
    return repo


def make_home(tmp: Path, harnesses: list[str]) -> Path:
    home = tmp / "home"
    home.mkdir()
    for h in harnesses:
        (home / CFG_ROOT[h]).mkdir(parents=True)
    return home


def run(repo: Path, home: Path, *args: str) -> subprocess.CompletedProcess:
    env = dict(os.environ, HOME=str(home))
    return subprocess.run(
        [sys.executable, str(repo / "scripts" / "install.py"), *args],
        cwd=repo, env=env, capture_output=True, text=True)


def snapshot(*roots: Path) -> dict[str, str]:
    snap: dict[str, str] = {}
    for root in roots:
        if not root.exists():
            snap[str(root)] = "absent"
            continue
        for p in [root, *sorted(root.rglob("*"))]:
            if p.is_symlink():
                snap[str(p)] = "link:" + os.readlink(p)
            elif p.is_dir():
                snap[str(p)] = "dir"
            elif p.is_file():
                snap[str(p)] = "file:" + p.read_text(encoding="utf-8",
                                                     errors="replace")
    return snap


def tree_paths(root: Path) -> set[str]:
    return {str(p) for p in root.rglob("*")} if root.exists() else set()


# ── scenarios ───────────────────────────────────────────────────────────────

def check_1_link_default(tmp: Path) -> None:
    repo = make_repo(tmp)
    home = make_home(tmp, ["claude", "zcode", "omp", "grok"])
    foreign = home / ".claude" / "agents" / "custom.md"
    foreign.parent.mkdir(parents=True)
    foreign.write_text("hand-written\n", encoding="utf-8")
    before = foreign.read_text(encoding="utf-8")

    result = run(repo, home)
    assert result.returncode == 0, f"exit {result.returncode}: {result.stderr}"

    for h in ["claude", "zcode", "omp", "grok"]:
        dest = home / AGENT_DIR[h] / "10x-scout.md"
        # Agents are real stamped files: zcode's loader ignores symlinked
        # agent files, so link mode must not symlink them.
        assert dest.is_file() and not dest.is_symlink(), \
            f"{dest} not a real file"
        assert MD_STAMP in dest.read_text(encoding="utf-8"), f"{dest} unstamped"
    assert not (repo / ".build").exists(), "agents must not render into .build"

    zcode = (home / AGENT_DIR["zcode"] / "10x-scout.md").read_text(encoding="utf-8")
    assert 'model: "%s"' % ZCODE_SCOUT_MODEL in zcode, zcode
    assert "injectAgentsMd: true" in zcode, zcode
    # scout thought is a per-harness dict: zcode Flash needs high
    assert "thoughtLevel: high" in zcode, zcode
    zcoder = (home / AGENT_DIR["zcode"] / "10x-coder.md").read_text(encoding="utf-8")
    assert 'model: "%s"' % ZCODE_MODEL in zcoder and "thoughtLevel: high" in zcoder, zcoder
    omp = (home / AGENT_DIR["omp"] / "10x-scout.md").read_text(encoding="utf-8")
    assert 'model: ["@smol"]' in omp, omp
    assert "thinkingLevel: low" in omp, omp
    claude = (home / AGENT_DIR["claude"] / "10x-scout.md").read_text(encoding="utf-8")
    assert "model: claude-haiku-4-5" in claude, claude
    claude_coder = (home / AGENT_DIR["claude"] / "10x-coder.md").read_text(encoding="utf-8")
    assert "model: claude-sonnet-5" in claude_coder, claude_coder
    grok = (home / AGENT_DIR["grok"] / "10x-scout.md").read_text(encoding="utf-8")
    for banned in ("model", "thought", "thinking", "inject"):
        assert not any(ln.startswith(banned) for ln in grok.splitlines()), grok
    grok_cfg = (home / ".grok" / "config.toml").read_text(encoding="utf-8")
    assert "[subagents.models]" in grok_cfg, grok_cfg
    assert '10x-scout = "grok-build-0.1"' in grok_cfg, grok_cfg

    assert foreign.read_text(encoding="utf-8") == before, "foreign file touched"
    for dest in (home / ".agents" / "skills" / "fixture-skill",
                 home / ".claude" / "skills" / "fixture-skill"):
        assert dest.is_symlink() and \
            dest.resolve() == (repo / "skills" / "fixture-skill").resolve(), \
            f"skill not mounted at {dest}"
    link = repo / ".claude" / "agents"
    assert link.is_symlink() and os.readlink(link) == "../agents", link
    assert not (home / ".codex").exists(), "undetected codex was created"


def check_2_codex_toml(tmp: Path) -> None:
    repo = make_repo(tmp)
    # Swap the scout codex model and delete the coder's, so both "mapped"
    # and "unmapped" paths are exercised end to end.
    script = repo / "scripts" / "install.py"
    script.write_text(
        script.read_text(encoding="utf-8")
        .replace('"codex": "gpt-5.6-luna",',
                 '"codex": "fixture-codex-model",')
        .replace('"codex": "gpt-5.6-terra",\n        ', ""),
        encoding="utf-8")
    home = make_home(tmp, ["codex"])
    result = run(repo, home)
    assert result.returncode == 0, f"exit {result.returncode}: {result.stderr}"
    assert not (home / ".claude").exists(), \
        "claude-only skill dir created although claude is undetected"
    toml = home / ".codex" / "agents" / "10x-scout.toml"
    assert toml.is_file() and not toml.is_symlink(), f"{toml} not a real file"
    content = toml.read_text(encoding="utf-8")
    assert "# installed-by: lazyclaude scripts/install.py" in content, content
    if sys.version_info >= (3, 11):
        import tomllib
        data = tomllib.loads(content)
        assert data["name"] == "10x-scout", data
        assert data["description"] == "Fixture scout", data
        assert data["developer_instructions"] == "Scout body.\n", data
        assert data["model_reasoning_effort"] == "low", data
        assert data["model"] == "fixture-codex-model", data
        coder = tomllib.loads(
            (home / ".codex" / "agents" / "10x-coder.toml").read_text(encoding="utf-8"))
        assert coder["developer_instructions"] == 'Coder "quoted" body.\n', coder
        assert coder["model_reasoning_effort"] == "high", coder
        assert "model" not in coder, "unmapped codex model must be omitted"
        merger = tomllib.loads(
            (home / ".codex" / "agents" / "10x-merger.toml").read_text(encoding="utf-8"))
        assert merger["model_reasoning_effort"] == "xhigh", \
            "thought max must map to codex xhigh"
        assert merger["model"] == "gpt-5.6", merger
    else:
        assert 'developer_instructions = "Scout body.\\n"' in content, content
        assert 'model_reasoning_effort = "low"' in content, content
        assert 'model = "fixture-codex-model"' in content, content
        merger = (home / ".codex" / "agents" / "10x-merger.toml").read_text(encoding="utf-8")
        assert 'model_reasoning_effort = "xhigh"' in merger, merger
        assert 'model = "gpt-5.6"' in merger, merger


def check_3_detection_and_all(tmp: Path) -> None:
    repo = make_repo(tmp)
    home = make_home(tmp, ["claude", "zcode"])
    result = run(repo, home)
    assert result.returncode == 0, result.stderr
    assert not (home / ".grok").exists(), "absent harness was not skipped"
    result = run(repo, home, "--all")
    assert result.returncode == 0, result.stderr
    assert (home / ".grok" / "agents" / "10x-scout.md").is_file(), \
        "--all did not populate grok"
    assert "[subagents.models]" in \
        (home / ".grok" / "config.toml").read_text(encoding="utf-8"), \
        "--all did not pin grok models"


def check_4_harness_filter(tmp: Path) -> None:
    repo = make_repo(tmp)
    home = make_home(tmp, ["claude", "zcode"])
    result = run(repo, home, "--harness", "claude")
    assert result.returncode == 0, result.stderr
    assert (home / ".claude" / "agents" / "10x-scout.md").is_file()
    zcode_agents = home / ".zcode" / "agents"
    assert not zcode_agents.exists() or not any(zcode_agents.iterdir()), \
        "--harness claude touched zcode"
    assert (home / ".agents" / "skills" / "fixture-skill").is_symlink(), \
        "skills should mount regardless of --harness"


def check_5_dry_run(tmp: Path) -> None:
    repo = make_repo(tmp)
    home = make_home(tmp, ["claude", "zcode", "omp", "grok"])
    before = tree_paths(home)
    result = run(repo, home, "--dry-run")
    assert result.returncode == 0, result.stderr
    assert tree_paths(home) == before, "dry-run wrote into HOME"
    assert "link" in result.stdout, "dry-run did not print a plan"
    assert not (repo / ".build").exists(), "dry-run created .build"
    assert not (repo / ".claude").exists(), "dry-run created in-repo .claude"


def check_6_reserved_name(tmp: Path) -> None:
    repo = make_repo(tmp, extra_briefs={"scout": ("Collision", "Body.\n")})
    home = make_home(tmp, ["claude"])
    before = tree_paths(home)
    result = run(repo, home)
    assert result.returncode == 2, f"reserved name exit {result.returncode}"
    assert tree_paths(home) == before, "reserved-name run wrote files"
    assert not (repo / ".build").exists(), "reserved-name run created .build"


def check_7_missing_mapping(tmp: Path) -> None:
    repo = make_repo(tmp, extra_briefs={"10x-ghost": ("No mapping", "Body.\n")})
    home = make_home(tmp, ["claude"])
    before = tree_paths(home)
    result = run(repo, home)
    assert result.returncode == 1, f"missing mapping exit {result.returncode}"
    assert "AGENT_MODELS" in result.stderr, result.stderr
    assert tree_paths(home) == before, "missing-mapping run wrote files"


def check_8_idempotent(tmp: Path) -> None:
    repo = make_repo(tmp)
    home = make_home(tmp, ["claude", "zcode", "codex"])
    assert run(repo, home).returncode == 0
    first = snapshot(home, repo / ".build")
    result = run(repo, home)
    assert result.returncode == 0, result.stderr
    assert snapshot(home, repo / ".build") == first, "second run changed the tree"


def check_9_foreign_and_force(tmp: Path) -> None:
    repo = make_repo(tmp)
    home = make_home(tmp, ["claude", "zcode"])
    foreign = home / ".zcode" / "agents" / "10x-scout.md"
    foreign.parent.mkdir(parents=True)
    foreign.write_text("precious hand-edit\n", encoding="utf-8")

    result = run(repo, home)
    assert result.returncode == 1, f"foreign refusal exit {result.returncode}"
    assert foreign.read_text(encoding="utf-8") == "precious hand-edit\n", \
        "foreign file was modified"
    assert "--force" in (result.stdout + result.stderr)
    assert (home / ".claude" / "agents" / "10x-scout.md").is_file(), \
        "other harnesses should still install"

    result = run(repo, home, "--force")
    assert result.returncode == 0, result.stderr
    backup = home / ".zcode" / "agents" / "10x-scout.md.bak.1"
    assert backup.read_text(encoding="utf-8") == "precious hand-edit\n", \
        "backup lost the original bytes"
    replaced = home / ".zcode" / "agents" / "10x-scout.md"
    assert replaced.is_file() and not replaced.is_symlink(), \
        "--force did not replace with our stamped file"
    assert MD_STAMP in replaced.read_text(encoding="utf-8")


def check_10_copy_mode(tmp: Path) -> None:
    repo = make_repo(tmp)
    home = make_home(tmp, ["claude", "zcode", "omp", "grok", "codex"])
    result = run(repo, home, "copy")
    assert result.returncode == 0, result.stderr
    for h in ["claude", "zcode", "omp", "grok"]:
        dest = home / AGENT_DIR[h] / "10x-scout.md"
        assert dest.is_file() and not dest.is_symlink(), f"{dest} not a copy"
        assert "<!-- installed-by: lazyclaude scripts/install.py -->" in \
            dest.read_text(encoding="utf-8"), f"{dest} unstamped"
    zcode = (home / AGENT_DIR["zcode"] / "10x-scout.md").read_text(encoding="utf-8")
    assert 'model: "%s"' % ZCODE_SCOUT_MODEL in zcode \
        and "thoughtLevel: high" in zcode, zcode
    claude = (home / AGENT_DIR["claude"] / "10x-scout.md").read_text(encoding="utf-8")
    assert "model: claude-haiku-4-5" in claude, claude
    grok_cfg = (home / ".grok" / "config.toml").read_text(encoding="utf-8")
    assert '10x-scout = "grok-build-0.1"' in grok_cfg, grok_cfg
    skill_copy = home / ".agents" / "skills" / "fixture-skill" / "SKILL.md"
    assert skill_copy.is_file(), "skill not copied"
    assert "installed-by: lazyclaude scripts/install.py" in \
        skill_copy.read_text(encoding="utf-8"), "skill copy unstamped"
    assert not (repo / ".build").exists(), "copy mode should not use .build"

    before = snapshot(home)
    assert run(repo, home, "copy").returncode == 0
    assert snapshot(home) == before, "second copy run rewrote files"


def check_11_uninstall(tmp: Path) -> None:
    repo = make_repo(tmp)
    home = make_home(tmp, ["claude", "zcode", "codex"])

    assert run(repo, home).returncode == 0  # link install
    assert run(repo, home, "uninstall").returncode == 0
    assert not (home / ".claude" / "agents" / "10x-scout.md").exists(), \
        "uninstall left our symlink"
    assert not (repo / ".build").exists(), "uninstall left .build"
    assert not (repo / ".claude" / "agents").exists(), "uninstall left convenience link"
    assert not (home / ".agents" / "skills" / "fixture-skill").exists()

    assert run(repo, home, "copy").returncode == 0  # copy install
    foreign_agent = home / ".claude" / "agents" / "custom.md"
    foreign_agent.write_text("mine\n", encoding="utf-8")
    foreign_skill = home / ".agents" / "skills" / "officecli"
    foreign_skill.mkdir(parents=True)
    (foreign_skill / "SKILL.md").write_text("---\nname: officecli\n---\n",
                                            encoding="utf-8")
    # foreign binary file next to scanned entries — must not crash is_ours
    foreign_blob = home / ".agents" / "skills" / "icon.png"
    foreign_blob.write_bytes(bytes([0x89, 0x50, 0x4E, 0x47, 0xB8, 0xFF]) * 4)
    assert run(repo, home, "uninstall").returncode == 0
    assert not (home / ".claude" / "agents" / "10x-scout.md").exists(), \
        "uninstall left stamped copy"
    assert not (home / ".codex" / "agents" / "10x-scout.toml").exists()
    assert not (home / ".claude" / "skills" / "fixture-skill").exists()
    assert foreign_agent.read_text(encoding="utf-8") == "mine\n", \
        "uninstall touched a foreign agent"
    assert (foreign_skill / "SKILL.md").is_file(), "uninstall touched a foreign skill"
    assert foreign_blob.read_bytes()[:4] == b"\x89PNG", \
        "uninstall touched a foreign binary"


def check_12_usage_errors(tmp: Path) -> None:
    repo = make_repo(tmp)
    home = make_home(tmp, [])
    for args in (["frobnicate"], ["--wat"], ["--harness", "vibes"], ["link", "extra"]):
        result = run(repo, home, *args)
        assert result.returncode == 2, f"{args} exit {result.returncode}"


def check_13_grok_config_surgery(tmp: Path) -> None:
    repo = make_repo(tmp)
    home = make_home(tmp, ["grok"])
    cfg = home / ".grok" / "config.toml"
    cfg.write_text(
        '[subagents.models]\nexplore = "grok-4.6"\n\n[mcp_servers.foo]\n'
        'url = "https://example.test"\n',
        encoding="utf-8")
    foreign = cfg.read_text(encoding="utf-8")

    result = run(repo, home)
    assert result.returncode == 0, result.stderr
    text = cfg.read_text(encoding="utf-8")
    assert 'explore = "grok-4.6"' in text, "foreign model pin lost"
    assert "[mcp_servers.foo]" in text and 'url = "https://example.test"' in text, \
        "foreign section touched"
    assert '10x-scout = "grok-build-0.1"' in text and '10x-merger = "grok-4.6"' in text, text
    assert text.index("[subagents.models]") < text.index("[mcp_servers.foo]"), text

    assert run(repo, home).returncode == 0  # idempotent
    again = cfg.read_text(encoding="utf-8")
    assert again.count('10x-scout =') == 1, "second run duplicated our keys"
    assert again == text, "second run rewrote the config"

    assert run(repo, home, "uninstall").returncode == 0
    stripped = cfg.read_text(encoding="utf-8")
    assert "10x-" not in stripped, "uninstall left our pins"
    assert 'explore = "grok-4.6"' in stripped and "[mcp_servers.foo]" in stripped, \
        "uninstall touched foreign config"

    # inline models table must be refused, file untouched
    cfg.write_text('[subagents]\nmodels = { explore = "grok-4.6" }\n',
                   encoding="utf-8")
    before = cfg.read_text(encoding="utf-8")
    result = run(repo, home)
    assert result.returncode == 1, f"inline-table refusal exit {result.returncode}"
    assert cfg.read_text(encoding="utf-8") == before, "refused config was modified"
    assert "inline table" in result.stderr, result.stderr

    # uninstall on a config we never touched: no-op
    cfg.write_text("[other]\nkey = 1\n", encoding="utf-8")
    assert run(repo, home, "uninstall").returncode == 0
    assert cfg.read_text(encoding="utf-8") == "[other]\nkey = 1\n"


CHECKS = [check_1_link_default, check_2_codex_toml, check_3_detection_and_all,
          check_4_harness_filter, check_5_dry_run, check_6_reserved_name,
          check_7_missing_mapping, check_8_idempotent, check_9_foreign_and_force,
          check_10_copy_mode, check_11_uninstall, check_12_usage_errors,
          check_13_grok_config_surgery]


def main() -> int:
    failed = 0
    for check in CHECKS:
        try:
            with tempfile.TemporaryDirectory() as tmp:
                check(Path(tmp))
            print(f"PASS {check.__name__}")
        except AssertionError as exc:
            failed += 1
            print(f"FAIL {check.__name__}: {exc}")
        except OSError as exc:
            failed += 1
            print(f"FAIL {check.__name__}: {exc}")
    print(f"{len(CHECKS) - failed}/{len(CHECKS)} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
