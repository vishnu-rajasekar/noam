#!/usr/bin/env bash
set -euo pipefail

usage() {
  echo "usage: $0 TASK-NNN short-name [base-ref]" >&2
  exit 2
}

[[ $# -ge 2 && $# -le 3 ]] || usage
task_id="$1"
slug="$2"
base_ref="${3:-main}"

[[ "$task_id" =~ ^TASK-[0-9]{3}$ ]] || usage
[[ "$slug" =~ ^[a-z0-9]+(-[a-z0-9]+)*$ ]] || usage

repo_root="$(git rev-parse --show-toplevel)"
cd "$repo_root"

git rev-parse --verify HEAD >/dev/null 2>&1 || {
  echo "error: create the reviewed bootstrap commit before using worktrees" >&2
  exit 1
}

[[ -z "$(git status --porcelain)" ]] || {
  echo "error: primary worktree must be clean before task delegation" >&2
  exit 1
}

base_sha="$(git rev-parse --verify "${base_ref}^{commit}")"
branch="agent/claude/${task_id,,}-${slug}"
worktree="$repo_root/.worktrees/${task_id,,}-${slug}"

[[ ! -e "$worktree" ]] || {
  echo "error: worktree path already exists: $worktree" >&2
  exit 1
}

git show-ref --verify --quiet "refs/heads/$branch" && {
  echo "error: branch already exists: $branch" >&2
  exit 1
}

git worktree add -b "$branch" "$worktree" "$base_sha"

echo "task=$task_id"
echo "base=$base_sha"
echo "branch=$branch"
echo "worktree=$worktree"
