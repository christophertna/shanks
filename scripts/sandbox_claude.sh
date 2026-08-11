#!/bin/bash
# Wrap a build-agent CLI invocation in an OS-level sandbox confined to one
# target directory, so a compromised or misdirected agent can't write
# outside the project worktree it's meant to stay in.
#
# Usage: sandbox_claude.sh <target-dir> <command> [args...]
#
# macOS only for now (uses the native `sandbox-exec` Seatbelt sandbox, so no
# extra dependency). Falls back to running the command unsandboxed, with a
# warning, on other platforms or if sandbox-exec isn't available: this is a
# defense-in-depth layer on top of the tool allowlist and the
# dangerous-command hook guard, not the only one, so failing open here beats
# refusing to run the build agent at all where there's no sandbox.
#
# Writes are confined to the target directory, a fresh private temp
# directory made for this one invocation (not the whole shared system temp
# tree, which would also expose every other process's temp files), and the
# CLI's own config/cache under $HOME. Reads and network are left
# unrestricted, matching Codex's `--sandbox workspace-write` semantics
# (write-scoped, not read- or network-scoped).
set -euo pipefail

if [ "$#" -lt 2 ]; then
  echo "usage: sandbox_claude.sh <target-dir> <command> [args...]" >&2
  exit 64
fi

TARGET_DIR="$1"
shift

if [[ "$(uname -s)" != "Darwin" ]] || ! command -v sandbox-exec >/dev/null 2>&1; then
  echo "sandbox_claude.sh: no OS-level sandbox on this platform; running $1 unsandboxed." >&2
  exec "$@"
fi

TARGET_DIR="$(cd "$TARGET_DIR" && pwd -P)"
SANDBOX_TMPDIR="$(mktemp -d "${TMPDIR:-/tmp}/shanks-sandbox.XXXXXX")"
SANDBOX_TMPDIR="$(cd "$SANDBOX_TMPDIR" && pwd -P)"
trap 'rm -rf "$SANDBOX_TMPDIR"' EXIT

case "$TARGET_DIR$HOME$SANDBOX_TMPDIR" in
  *'"'*)
    echo "sandbox_claude.sh: refusing a path containing a double quote." >&2
    exit 1
    ;;
esac

PROFILE=$(cat <<SANDBOX
(version 1)
(deny default)
(allow process-fork process-exec)
(allow file-read*)
(allow file-write*
  (subpath "$TARGET_DIR")
  (subpath "$SANDBOX_TMPDIR")
  (subpath "$HOME/.claude")
  (subpath "$HOME/.codex")
  (subpath "$HOME/.npm")
  (subpath "$HOME/.cache"))
(allow file-write-data (literal "/dev/null"))
(allow network*)
(allow mach-lookup)
(allow signal (target self))
(allow sysctl-read)
(allow iokit-open)
SANDBOX
)

TMPDIR="$SANDBOX_TMPDIR" TMP="$SANDBOX_TMPDIR" TEMP="$SANDBOX_TMPDIR" \
  sandbox-exec -p "$PROFILE" "$@"
