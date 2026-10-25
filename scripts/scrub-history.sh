#!/usr/bin/env bash
# Purge the DriveRack admin password and the BLU link/Dante MAC addresses from every
# commit on GitHub, so the repo can go public (basement-sound#3).
#
# The current files already say "<redacted>" (and venu360_backup.py now writes that),
# but every commit before #3 still holds the real values in backups/.
#
# Run it after #3 has merged, from a clean checkout of this repo:
#
#   scripts/scrub-history.sh          # rewrite a fresh mirror and verify it - pushes nothing
#   scripts/scrub-history.sh --push   # the same, then force-push and verify again from GitHub
#
# --push needs the `main-protected` ruleset paused (it blocks force-pushes). Turn it back on after.
#
# Steps:
#   1. Refuse if this checkout has uncommitted changes: once history is rewritten, every
#      checkout has to be reset to the new main, and that would throw them away.
#   2. Make a fresh `git clone --mirror` of origin in a temp dir.
#   3. Read the values to remove from every version of the backup files in that mirror, so
#      the secrets are never written into this script, and write them to a replacements file
#      (`value==><redacted>`) that is deleted on exit. Only their count and lengths are
#      printed. Finding none means history is already clean, and the script stops there.
#   4. Run `git filter-repo --sensitive-data-removal --replace-text` on the mirror.
#   5. Check the rewritten mirror: `git log -p --all` holds none of the values, and main's
#      tree is unchanged (main's tip is already redacted, so a changed tree means the rewrite
#      touched something else - or #3 hasn't merged yet).
#   6. Without --push, print the push command and stop. With --push, push, confirm main on
#      GitHub is the rewritten one, then clone GitHub afresh and check every ref again.
#
# Why not `git push --mirror`: a mirror clone also fetches GitHub's refs/pull/*/head, which
# GitHub never lets anyone update, so --mirror always fails on them (and would also push
# filter-repo's refs/replace/*). Branches and tags are pushed explicitly instead.
#
# Those PR refs are the catch: they keep the old commits reachable on GitHub - the PR
# pages show them - until GitHub Support removes them. The final check lists which refs
# still hold the values and exits 2 if any do. Don't flip the repo public until that is
# settled (Support ticket, or Tony accepts it).
#
# Idempotent: every run starts from a fresh mirror, and filter-repo is deterministic, so a
# second run rewrites to the same commits and its push changes nothing.
#
# Exit: 0 clean, 1 refused or failed, 2 pushed and branches clean but PR refs still hold the values.
set -euo pipefail

PUSH=0
case "${1:-}" in
  "") ;;
  --push) PUSH=1 ;;
  *) echo "usage: $0 [--push]" >&2; exit 1 ;;
esac

UVX=$(command -v uvx || echo /opt/homebrew/bin/uvx)
REPO=$(git -C "$(dirname "$0")" rev-parse --show-toplevel)
if [ -n "$(git -C "$REPO" status --porcelain)" ]; then
  echo "Refusing: $REPO has uncommitted changes. Commit or discard them first." >&2
  exit 1
fi
URL=$(git -C "$REPO" remote get-url origin)   # read now: filter-repo may drop the mirror's origin

WORK=$(mktemp -d "${TMPDIR:-/tmp}/scrub-history.XXXXXX")
MIRROR="$WORK/mirror.git"
REPL="$WORK/replacements.txt"
trap 'rm -f "$REPL"' EXIT

# How many lines of `git log -p` over the given refs (default: all) hold a value. Always
# assign it (n=$(count ...)) before testing it, so a failing git log stops the script
# instead of reading as a clean 0.
count() {   # count <repo> <value> [rev-list args...]
  local repo=$1 value=$2 log; shift 2
  [ $# -gt 0 ] || set -- --all
  log=$(git -C "$repo" log -p "$@") || return 1
  printf '%s\n' "$log" | grep -c -F -e "$value" || true
}

echo "== Mirror-cloning $URL"
git clone --quiet --mirror --no-local "$URL" "$MIRROR"   # --no-local: filter-repo wants a packed clone
MAIN=$(git -C "$MIRROR" symbolic-ref HEAD)
MAIN_TREE=$(git -C "$MIRROR" rev-parse "$MAIN^{tree}")

echo "== Collecting the values to remove from every version of backups/"
python3 -I - "$MIRROR" "$REPL" <<'PY'
import os, re, subprocess, sys
mirror, out = sys.argv[1], sys.argv[2]
git = lambda *a: subprocess.run(["git", "-C", mirror, *a], capture_output=True, check=True).stdout
FIELDS = rb"Password|MacAddr|MasterMacAddr|PrimaryMacAddr|SecondaryMacAddr"
PATTERNS = [re.compile(rb'\\\\SV\\\\(?:' + FIELDS + rb')": "([^"]*)"'),   # JSON dumps
            re.compile(rb'^  (?:' + FIELDS + rb') = (.*)$', re.M)]        # text snapshot
values = set()
for rev in git("rev-list", "--all", "--", "backups/").split():
    for path in git("ls-tree", "-r", "--name-only", rev, "--", "backups/").splitlines():
        blob = git("cat-file", "blob", rev + b":" + path)
        for pat in PATTERNS:
            values.update(v for v in pat.findall(blob) if v and v != b"<redacted>")
fd = os.open(out, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
with os.fdopen(fd, "wb") as f:
    for v in sorted(values, key=len, reverse=True):
        f.write(v + b"==><redacted>\n")
print(f"{len(values)} distinct value(s), lengths {sorted(len(v) for v in values)}")
PY
VALUES=()
while IFS= read -r line; do VALUES+=("${line%%==>*}"); done < "$REPL"
if [ ${#VALUES[@]} -eq 0 ]; then
  echo "Nothing to scrub: no ref holds an unredacted value. History is already clean."
  rm -rf "$WORK"
  exit 0
fi
for i in "${!VALUES[@]}"; do
  n=$(count "$MIRROR" "${VALUES[$i]}")
  echo "   value $((i + 1)): $n line(s) in git log -p --all before the rewrite"
  [ "$n" -gt 0 ] || { echo "   ...but it should appear at least once; extraction is wrong" >&2; exit 1; }
done

echo "== Rewriting the mirror with git filter-repo"
(cd "$MIRROR" && "$UVX" --from git-filter-repo git-filter-repo \
  --sensitive-data-removal --replace-text "$REPL" --replace-message "$REPL")
echo "   (Not filter-repo's 'git push --force --mirror origin' above - see why at the top of this script.)"

echo "== Verifying the rewritten mirror"
FAIL=0
for i in "${!VALUES[@]}"; do
  n=$(count "$MIRROR" "${VALUES[$i]}")
  echo "   value $((i + 1)): $n line(s) in git log -p --all"
  [ "$n" -eq 0 ] || FAIL=1
done
if [ "$(git -C "$MIRROR" rev-parse "$MAIN^{tree}")" != "$MAIN_TREE" ]; then
  echo "   main's tree changed - has #3 merged? The rewrite must only touch old commits." >&2
  FAIL=1
fi
if [ "$FAIL" -ne 0 ]; then
  echo "Verification failed; nothing pushed. Mirror left at $MIRROR" >&2
  exit 1
fi
echo "   clean, and main's tree is unchanged"

PUSH_CMD=(git -C "$MIRROR" push --force "$URL" '+refs/heads/*:refs/heads/*' '+refs/tags/*:refs/tags/*')
if [ "$PUSH" -eq 0 ]; then
  echo
  echo "Dry run - nothing pushed. Mirror left at:"
  echo "  $MIRROR"
  echo "To push: pause main-protected, then re-run with --push (it also re-verifies from"
  echo "GitHub), or run by hand:"
  echo "  ${PUSH_CMD[*]}"
  exit 0
fi

echo "== Force-pushing branches and tags to $URL"
"${PUSH_CMD[@]}"
NEW_MAIN=$(git -C "$MIRROR" rev-parse "$MAIN")
if [ "$(git ls-remote "$URL" "$MAIN" | cut -f1)" != "$NEW_MAIN" ]; then
  echo "GitHub's $MAIN is not the rewritten one. Is main-protected paused?" >&2
  exit 1
fi

echo "== Verifying a fresh mirror clone of GitHub"
CHECK="$WORK/check.git"
git clone --quiet --mirror --no-local "$URL" "$CHECK"
FAIL=0
for i in "${!VALUES[@]}"; do
  n=$(count "$CHECK" "${VALUES[$i]}" --branches --tags)
  echo "   value $((i + 1)): $n line(s) in branches and tags"
  [ "$n" -eq 0 ] || FAIL=1
done
if [ "$FAIL" -ne 0 ]; then
  echo "Branches or tags on GitHub still hold a value. Fresh clone left at $CHECK" >&2
  exit 1
fi
DIRTY=()
for ref in $(git -C "$CHECK" for-each-ref --format='%(refname)' refs/pull); do
  for v in "${VALUES[@]}"; do
    n=$(count "$CHECK" "$v" "$ref")
    if [ "$n" -ne 0 ]; then DIRTY+=("$ref"); break; fi
  done
done
rm -rf "$WORK"

echo
echo "Branches and tags on GitHub are clean."
echo "Every other clone and worktree (both Macs) still has the old history: re-clone, or"
echo "'git fetch && git reset --hard origin/main' and delete old branches. Never push or merge"
echo "an old branch - that brings the values back."
if [ ${#DIRTY[@]} -gt 0 ]; then
  echo
  echo "STILL REACHABLE on GitHub through PR refs, which only GitHub Support can remove:"
  printf '  %s\n' "${DIRTY[@]}"
  echo "The PR pages show those old commits. Open a GitHub Support ticket (give them the PR"
  echo "refs above and filter-repo's First Changed Commit), or have Tony accept it, before"
  echo "flipping public."
  exit 2
fi
echo "No PR ref holds the values either. Safe to flip public."
