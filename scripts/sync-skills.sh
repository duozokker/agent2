#!/usr/bin/env bash
set -euo pipefail

# Sync all SKILL.md files from .claude/skills/ (canonical source) to every
# other host directory. Run after editing any skill.
#
# Usage: ./scripts/sync-skills.sh

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SOURCE_DIR="$REPO_ROOT/.claude/skills"
HOSTS=(".agents" ".gemini" ".codex" ".github")

if [ ! -d "$SOURCE_DIR" ]; then
  echo "Source directory $SOURCE_DIR not found" >&2
  exit 1
fi

synced=0
skipped=0

for skill_dir in "$SOURCE_DIR"/*/; do
  skill_name="$(basename "$skill_dir")"
  for host in "${HOSTS[@]}"; do
    target_dir="$REPO_ROOT/$host/skills/$skill_name"
    target_file="$target_dir/SKILL.md"
    source_file="$skill_dir/SKILL.md"

    [ -f "$source_file" ] || continue

    mkdir -p "$target_dir"

    if [ -f "$target_file" ] && diff -q "$source_file" "$target_file" >/dev/null 2>&1; then
      skipped=$((skipped + 1))
      continue
    fi

    cp "$source_file" "$target_file"
    echo "  ✓ $host/skills/$skill_name/SKILL.md"
    synced=$((synced + 1))
  done
done

echo ""
echo "Synced: $synced  Unchanged: $skipped"
