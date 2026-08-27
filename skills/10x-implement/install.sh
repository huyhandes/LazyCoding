#!/usr/bin/env bash
# 10x-implement team installer. Edit the block below, run this file. That's the whole UX.
# Detail: references/INSTALL.md
# ponytail: no tool allowlists emitted — the briefs state read-only in prose.
set -euo pipefail

# ── EDIT ME, then run ./install.sh ──────────────────────────────
HARNESS=zcode # claude | omp | zcode
DEST=         # install dir; empty = harness default

# One "<model> [thinking]" per role. thinking: low|high|max — omp and
# zcode only; claude agents have no thinking field and ignore it.
SCOUT="custom:builtin%3Azai-coding-plan:GLM-5.3 low"
CODER="custom:builtin%3Azai-coding-plan:GLM-5.3 high"
MERGER="custom:builtin%3Azai-coding-plan:GLM-5.3 max"
REVIEWER="custom:builtin%3Azai-coding-plan:GLM-5.3 max"

# claude: SCOUT="claude-haiku-4-5 low"  CODER="claude-sonnet-4-6 high"
#         MERGER="claude-opus-5 max"    REVIEWER="claude-opus-5 max"
# omp:    SCOUT="@smol low"  CODER="@task high"  MERGER="@slow max"  REVIEWER="@slow max"
# ────────────────────────────────────────────────────────────────

here=$(cd "$(dirname "$0")" && pwd)
field() { sed -n "s/^$2: *//p" "$1" | sed -n 1p; } # brief frontmatter `key: value`

case $HARNESS in
claude) DEST=${DEST:-$HOME/.claude/agents} ;;
omp) DEST=${DEST:-$HOME/.omp/agent/agents} ;;
zcode) DEST=${DEST:-$HOME/.zcode/agents} ;;
*)
	echo "HARNESS='$HARNESS' — want claude|omp|zcode (edit the block above)" >&2
	exit 2
	;;
esac

mkdir -p "$DEST"
for brief in "$here"/../../agents/*.md; do
	name=$(field "$brief" name)
	[ -n "$name" ] || { echo "$brief: missing name: line" >&2; exit 1; }
	case $name in
	10x-scout) line=$SCOUT ;;
	10x-coder) line=$CODER ;;
	10x-merger) line=$MERGER ;;
	10x-reviewer) line=$REVIEWER ;;
	*)
		echo "$brief: no model var for '$name' — add VAR=... to the EDIT-ME block and a case line here" >&2
		exit 1
		;;
	esac
	[ -n "$line" ] || { echo "role '$name': empty model — fill its var in the EDIT-ME block" >&2; exit 1; }
	set -- $line
	model=$1
	thinking=${2:-}

	{
		echo '---'
		echo "name: $name"
		echo "description: $(field "$brief" description)"
		case $HARNESS in
		omp)
			echo "model: [\"$model\"]"
			if [ -n "$thinking" ]; then echo "thinkingLevel: $thinking"; fi
			;;
		zcode)
			# fully-qualified provider ref, quoted: custom:builtin%3A<provider>:<Model>
			echo "model: \"$model\""
			echo 'injectAgentsMd: true'
			if [ -n "$thinking" ]; then echo "thoughtLevel: $thinking"; fi # zcode spells it thoughtLevel; omp uses thinkingLevel
			;;
		*) echo "model: $model" ;;
		esac
		echo '---'
		awk 'seen>=2 {print} seen<2 && /^---$/ {seen++}' "$brief"
	} >"$DEST/$name.md"
	echo "$DEST/$name.md ($model${thinking:+ $thinking})"
done
