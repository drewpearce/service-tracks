#!/usr/bin/env bash
# PreToolUse hook: block Edit/Write to secret-bearing files.
# Reads the hook payload (JSON on stdin), inspects the target path, and exits 2
# (which blocks the tool call and feeds stderr back to Claude) for .env files and
# key/cert material. Template files (.env.example etc.) are allowed.
set -euo pipefail

payload="$(cat)"
path="$(printf '%s' "$payload" \
  | python3 -c 'import json,sys; print(json.load(sys.stdin).get("tool_input",{}).get("file_path",""))' \
  2>/dev/null || true)"
[ -z "$path" ] && exit 0

base="$(basename "$path")"
blocked=0

case "$base" in
  .env.example|.env.sample|.env.template|.env.*.example) blocked=0 ;;
  .env|.env.*)                                           blocked=1 ;;
esac
case "$path" in
  *.pem|*.key|*.p12|*.pfx|*.keystore)                    blocked=1 ;;
esac

if [ "$blocked" = "1" ]; then
  echo "Blocked edit to '$path': this looks like a secret/credential file (.env or key/cert material)." >&2
  echo "Editing secrets through Claude is disabled by .claude/hooks/block-secret-edits.sh. Edit it manually if intentional." >&2
  exit 2
fi
exit 0
