#!/usr/bin/env python3
"""Tests for the pre-publication audit.

The audit is wired into `make test`, which makes it the most dangerous file
here: a gate whose checks have quietly stopped checking is worse than no gate,
because it reports assurance instead of nothing. Every check in audit.py exists
because something slipped through unnoticed, and a check that cannot be shown
to fail is in exactly that position itself.

So each check is run twice against a throwaway collection built in a temp
directory: once clean, where it must pass, and once with the defect it is named
after planted, where it must fail. Both directions matter -- a check that
always fails is as useless as one that always passes, and the always-fails kind
is what you get when a pattern is too broad.

No pytest. The fixtures are real git repositories, because most of the checks
read git rather than files.
"""
import os
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import audit  # noqa: E402

passed = 0
failed = 0


def check(label, got, want):
    global passed, failed
    if got == want:
        passed += 1
        print("ok   %s" % label)
    else:
        failed += 1
        print("FAIL %s\n       got  %r\n       want %r" % (label, got, want))


def run(fn, root, denylist=None):
    """Run one audit check against `root`, returning True if it passed."""
    audit.ROOT = Path(root)
    audit.DENYLIST = Path(denylist) if denylist else Path(root) / "no-denylist"
    audit.reset()
    # The checks print. Replacing sys.stdout rather than fd 1: print() writes
    # through the sys.stdout object, so dup2 on the descriptor left every line
    # still appearing, interleaved with this suite's own output.
    import io
    real = sys.stdout
    sys.stdout = io.StringIO()
    try:
        return bool(fn())
    finally:
        sys.stdout = real


def git(repo, *args, **kw):
    return subprocess.run(["git", "-C", str(repo), *args], check=True,
                          capture_output=True, text=True, **kw).stdout


LICENSE_TEXT = "GNU GENERAL PUBLIC LICENSE Version 3\n"


def make_repo(parent, name, files=None, commits=1):
    """A git repository with the two files every check expects to find."""
    r = parent / name
    r.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=r, check=True)
    git(r, "config", "user.name", "T")
    git(r, "config", "user.email", "t@invalid")
    (r / "README.md").write_text("# %s\n\nA fixture.\n" % name)
    (r / "LICENSE").write_text(LICENSE_TEXT)
    for rel, content in (files or {}).items():
        p = r / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)
    for i in range(commits):
        (r / ("f%d.txt" % i)).write_text(str(i))
        git(r, "add", "-A")
        env = dict(os.environ, GIT_AUTHOR_DATE="2001-01-01T00:00:00Z",
                   GIT_COMMITTER_DATE="2001-01-01T00:00:00Z")
        subprocess.run(["git", "commit", "-qm", "c%d" % i], cwd=r, check=True,
                       env=env)
    return r


def make_collection(td, extra=None):
    """A root repository with two project repositories inside it."""
    root = Path(td) / "coll"
    make_repo(Path(td), "coll")
    make_repo(root, "alpha", extra)
    make_repo(root, "beta")
    return root


# =====================================================================
# every check, clean and then broken
# =====================================================================
with tempfile.TemporaryDirectory() as td:
    root = make_collection(td)

    # --- the fixture itself must be clean, or nothing below means anything.
    for fn in (audit.check_readme, audit.check_license, audit.check_abs_paths,
               audit.check_siblings, audit.check_placeholders,
               audit.check_gitlinks, audit.check_backup_refs,
               audit.check_authors, audit.check_secrets,
               audit.check_branches):
        check("clean fixture passes %s" % fn.__name__, run(fn, root), True)

    # --- objects: the deny-list, and the history-not-worktree distinction
    dl = Path(td) / "denylist.txt"
    dl.write_text("forbidden-token\n")
    check("objects passes when nothing is deny-listed",
          run(audit.check_objects, root, dl), True)

    # The point of this check: a string removed from the working tree but
    # still in history. git grep and ls-files both report clean here.
    DATES = dict(os.environ, GIT_AUTHOR_DATE="2001-01-01T00:00:00Z",
                 GIT_COMMITTER_DATE="2001-01-01T00:00:00Z")
    leaky = make_repo(root, "leaky")
    base = git(leaky, "rev-parse", "HEAD").strip()
    (leaky / "notes.md").write_text("forbidden-token is here\n")
    git(leaky, "add", "-A")
    subprocess.run(["git", "commit", "-qm", "add notes"], cwd=leaky,
                   check=True, env=DATES)
    git(leaky, "rm", "-q", "notes.md")
    subprocess.run(["git", "commit", "-qm", "remove it"], cwd=leaky,
                   check=True, env=DATES)
    worktree_clean = "forbidden-token" not in subprocess.run(
        ["git", "-C", str(leaky), "grep", "-r", "forbidden-token"],
        capture_output=True, text=True).stdout
    check("the fixture's working tree really is clean, so this is a "
          "history-only test", worktree_clean, True)
    check("objects fails on a string that survives only in history",
          run(audit.check_objects, root, dl), False)

    # Deleting the file in a later commit does NOT help, which is the entire
    # lesson: the blob stays reachable from the commit that added it, so gc
    # cannot reclaim it. The first version of this test expected gc to be
    # enough and failed -- correctly.
    git(leaky, "reflog", "expire", "--expire=now", "--expire-unreachable=now",
        "--all")
    subprocess.run(["git", "-C", str(leaky), "gc", "--prune=now", "-q"],
                   check=True)
    check("objects still fails after a gc, because the blob is reachable "
          "from the commit that added it", run(audit.check_objects, root, dl),
          False)

    # The remedy is to drop the commit, then let gc reclaim it.
    subprocess.run(["git", "-C", str(leaky), "reset", "--hard", "-q", base],
                   check=True)
    git(leaky, "reflog", "expire", "--expire=now", "--expire-unreachable=now",
        "--all")
    subprocess.run(["git", "-C", str(leaky), "gc", "--prune=now", "-q"],
                   check=True)
    check("objects passes once the commit is gone and the blob is reclaimed",
          run(audit.check_objects, root, dl), True)

    # --- readme
    (root / "alpha" / "README.md").unlink()
    git(root / "alpha", "rm", "-q", "--cached", "README.md")
    subprocess.run(["git", "commit", "-qm", "drop readme"], cwd=root / "alpha",
                   check=True)
    check("readme fails when a repository has none",
          run(audit.check_readme, root), False)
    (root / "alpha" / "README.md").write_text("# alpha\n")
    git(root / "alpha", "add", "-A")
    subprocess.run(["git", "commit", "-qm", "restore readme"],
                   cwd=root / "alpha", check=True)
    check("readme passes once it is back", run(audit.check_readme, root), True)

    # --- license
    git(root / "beta", "rm", "-q", "LICENSE")
    subprocess.run(["git", "commit", "-qm", "drop licence"], cwd=root / "beta",
                   check=True)
    check("license fails when a repository has none",
          run(audit.check_license, root), False)

with tempfile.TemporaryDirectory() as td:
    # --- abs_paths: a live line fails, the same text in a comment does not
    root = make_collection(td, {"tool.py": 'REPO = "/home/someone/projects"\n'})
    check("abs_paths fails on an absolute home path in code",
          run(audit.check_abs_paths, root), False)

with tempfile.TemporaryDirectory() as td:
    root = make_collection(td, {"tool.py": '# REPO used to be "/home/someone/x"\n'})
    check("abs_paths passes when the path is only in a comment",
          run(audit.check_abs_paths, root), True)

with tempfile.TemporaryDirectory() as td:
    root = make_collection(td, {"tool.py": '"""It was "/home/someone/x".\n"""\n'})
    check("abs_paths passes when the path is only in a docstring",
          run(audit.check_abs_paths, root), True)

with tempfile.TemporaryDirectory() as td:
    # --- siblings: naming another repo fails; naming yourself does not
    root = make_collection(td, {"t/run.sh": 'ls ../beta/.git\n'})
    check("siblings fails when a suite reads another repository",
          run(audit.check_siblings, root), False)

with tempfile.TemporaryDirectory() as td:
    root = make_collection(td, {"t/run.sh": 'exec "$(dirname "$0")/../alpha"\n'})
    check("siblings passes when a suite refers to its own repository",
          run(audit.check_siblings, root), True)

with tempfile.TemporaryDirectory() as td:
    # --- placeholders: a code block fails, prose about it does not
    root = make_collection(td, {
        "HOWTO.md": "Run it:\n\n```sh\n./cq id \"Your Name\" --yes\n```\n"})
    check("placeholders fails on a pasteable command with a blank in it",
          run(audit.check_placeholders, root), False)

with tempfile.TemporaryDirectory() as td:
    root = make_collection(td, {
        "HOWTO.md": 'Once, `cq id "Your Name" --yes` was pasted unfilled.\n'})
    check("placeholders passes on prose describing that incident",
          run(audit.check_placeholders, root), True)

with tempfile.TemporaryDirectory() as td:
    # --- backup_refs: live undo is fine, undo after a remote exists is not
    root = make_collection(td)
    alpha = root / "alpha"
    tip = git(alpha, "rev-parse", "HEAD").strip()
    git(alpha, "update-ref", "refs/original/refs/heads/main", tip)
    check("backup_refs passes while the repository has no remote",
          run(audit.check_backup_refs, root), True)
    git(alpha, "remote", "add", "origin", str(Path(td) / "nowhere.git"))
    check("backup_refs fails once the repository has a remote",
          run(audit.check_backup_refs, root), False)

with tempfile.TemporaryDirectory() as td:
    # --- authors: placeholder author plus a remote
    root = make_collection(td)
    alpha = root / "alpha"
    check("authors passes with no remote", run(audit.check_authors, root), True)
    git(alpha, "remote", "add", "origin", str(Path(td) / "nowhere.git"))
    check("authors passes with a remote and a real author",
          run(audit.check_authors, root), True)
    git(alpha, "config", "user.email", audit.PLACEHOLDER_EMAIL)
    git(alpha, "config", "user.name", "PLACEHOLDER")
    (alpha / "more.txt").write_text("x")
    git(alpha, "add", "-A")
    subprocess.run(["git", "commit", "-qm", "placeholder-authored"], cwd=alpha,
                   check=True, env=dict(os.environ,
                                        GIT_AUTHOR_DATE="2001-01-01T00:00:00Z",
                                        GIT_COMMITTER_DATE="2001-01-01T00:00:00Z"))
    check("authors fails on a placeholder commit in a repo with a remote",
          run(audit.check_authors, root), False)

with tempfile.TemporaryDirectory() as td:
    # --- secrets
    root = make_collection(td, {"conf.sh": "TOKEN=ghp_%s\n" % ("a" * 36)})
    check("secrets fails on a credential pattern",
          run(audit.check_secrets, root), False)

with tempfile.TemporaryDirectory() as td:
    # --- branches: an unexpected branch fails, a listed one is a note
    root = make_collection(td)
    git(root / "alpha", "branch", "experiment")
    check("branches fails on a branch that is not HEAD and not listed",
          run(audit.check_branches, root), False)
    audit.KNOWN_EXTRA_BRANCHES = audit.KNOWN_EXTRA_BRANCHES | {
        ("alpha", "experiment")}
    check("branches passes once that branch is accounted for",
          run(audit.check_branches, root), True)

print("\n%d passed, %d failed" % (passed, failed))
sys.exit(1 if failed else 0)
