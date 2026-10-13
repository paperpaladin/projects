#!/usr/bin/env python3
"""Pre-publication audit of the whole collection.

Every check here exists because the thing it checks for actually happened, and
in every case it was found by accident or by a reader rather than by anything
that ran. The list is therefore a list of mistakes, not a list of good ideas:

  objects            A string that had to stay out of the published history
                     was removed from the working files and declared gone.
                     1596 occurrences remained in history -- a rename in a new
                     commit does not touch the blobs underneath it -- and
                     another 3364 sat in unreachable objects after the
                     rewrites. Only `cat-file --batch-all-objects` sees those.
                     The terms themselves are in an untracked deny-list, for
                     the reason given at the check.
  readme             xmlc and zipc had no README.md, so their GitHub pages
                     would have been blank. So would this repository's.
  license            The root repo was missing the LICENSE its 38 children all
                     carried.
  abs_paths          wasmi/hist/build.py hardcoded REPO="/home/x/projects/wasmi"
                     and then deleted REPO/.git. Run from a clone it would
                     have destroyed the original repository's history.
  siblings           gitobj's suite required eight named sibling repositories
                     to exist at ../<name>/.git. Cloned alone it failed five
                     assertions, one of which was a corruption test that
                     planted no corruption.
  placeholders       A documented command containing "Your Name" was pasted
                     with --yes behind it and rewrote 721 commits.
  gitlinks           `git add -A` at the root recorded a worktree as a gitlink,
                     which produces a clone that cannot be checked out.
  backup_refs        refs/original from one rewrite is the undo for that
                     rewrite and nothing else; `filter-branch -f` overwrites
                     it rather than refusing, so stale ones are a false sense
                     of safety.
  authors            Pushing a commit freezes its hash. A placeholder author
                     on a repo that already has a remote can only be fixed by
                     force-pushing over a published branch.
  secrets            Nothing has leaked. This is the check that has to exist
                     before the first time it would have.
  branches           A `--all` push would publish every local branch. One of
                     them is an unrelated project in a worktree.

Run:  python3 .portfolio/audit.py [--deep]

--deep adds the clean-clone check: every repository is cloned to a scratch
directory with no siblings and `make test` is run there. That is the only way
to find out what a suite depends on that is not in the repository, and it is
how the gitobj and wasmi defects above were found. It takes about ten minutes.
"""
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
# Overridable so the suite can point the checks at a fixture collection with a
# defect planted in it. A gate whose checks are never shown to fail is a gate
# that might be checking nothing, which is the shape of defect this file is
# otherwise about -- so it has to be testable against something broken.
ROOT = Path(os.environ.get("AUDIT_ROOT") or HERE.parent)

# Not part of the collection: an unrelated fork kept here for convenience. It
# has its own history by other people and its own remote.
FOREIGN = {"notally-molly"}

passed = 0
failed = 0
notes = []


def reset():
    """Clear the counters so one check can be run on its own, by the suite."""
    global passed, failed, notes
    passed = 0
    failed = 0
    notes = []


def ok(label):
    global passed
    passed += 1
    print("ok   %s" % label)


def no(label, detail=""):
    global failed
    failed += 1
    print("FAIL %s" % label)
    for line in str(detail).splitlines()[:8]:
        print("       %s" % line)


def check(label, bad, render=str):
    """Fail the check if `bad` is non-empty, listing what was found."""
    bad = list(bad)
    if bad:
        no(label, "\n".join(render(b) for b in bad[:8])
           + ("\n... and %d more" % (len(bad) - 8) if len(bad) > 8 else ""))
    else:
        ok(label)
    return not bad


def git(repo, *args, binary=False):
    r = subprocess.run(["git", "-C", str(repo), *args],
                       capture_output=True, text=not binary)
    return r.stdout


def repos():
    """The root repository first, then each project repository."""
    out = [ROOT]
    for p in sorted(ROOT.iterdir()):
        if p.name in FOREIGN or not (p / ".git").is_dir():
            continue
        out.append(p)
    return out


def name_of(repo):
    return "projects" if repo == ROOT else repo.name


def tracked(repo):
    for rel in git(repo, "ls-files").split("\n"):
        if rel:
            yield rel


def read_text(path):
    try:
        return path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return None


# --------------------------------------------------------------- comments
#
# Several checks care whether a path appears in code or in prose about code.
# This is deliberately crude -- a whole-line comment only, no block comments,
# no awareness of strings -- because the alternative is a parser per language
# and the crude version has no false *negatives* in the direction that
# matters: it never excuses a live line.
COMMENT_START = {
    ".py": ("#",), ".sh": ("#",), "": ("#",),
    ".c": ("//", "*", "/*"), ".h": ("//", "*", "/*"),
}


def code_lines(rel, text):
    """(lineno, line) for lines that are not comments or docstrings.

    The docstring tracking is here because without it this module's own
    docstring -- which quotes the absolute paths it exists to forbid -- was
    reported as a violation. A check that flags the explanation of its own
    rule is a check people learn to ignore.
    """
    starts = COMMENT_START.get(Path(rel).suffix, ("#", "//", "*", "/*"))
    quotes = ('"' * 3, "'" * 3)
    in_doc = None
    for i, line in enumerate(text.splitlines(), 1):
        stripped = line.strip()
        if in_doc:
            if in_doc in line:
                in_doc = None
            continue
        opened = False
        for q in quotes:
            if stripped.startswith(q) or stripped.startswith(("r" + q, "b" + q)):
                rest = stripped.split(q, 1)[1]
                if q not in rest:
                    in_doc = q
                opened = True
                break
        if opened:
            continue
        if not stripped or stripped.startswith(tuple(starts)):
            continue
        yield i, line


# =====================================================================
# 1. objects: every object in every database, reachable or not
# =====================================================================
# `git grep` searches the working tree. `ls-files` lists the working tree.
# Both reported zero while 1596 occurrences sat in historical blobs, because
# a rename committed on top of a file does not alter the blobs underneath it.
# This reads the object database itself.
#
# The terms are NOT in this file. They were, as a literal regex, and the first
# run of this check reported four occurrences in the root repository -- its
# own source. A deny-list that is published alongside the thing it denies is
# self-defeating: whatever you are keeping out of the repository, writing it
# into the checker puts it back in. So the terms live in an untracked file and
# this is a generic check, which is also more useful: the next thing worth
# keeping out will be a client name or an internal hostname, not these.
DENYLIST = HERE / "denylist.txt"


def denylist():
    """Patterns from the untracked deny-list, or None if there is not one."""
    if not DENYLIST.exists():
        return None
    pats = [l.strip() for l in DENYLIST.read_text(encoding="utf-8").splitlines()
            if l.strip() and not l.startswith("#")]
    if not pats:
        return None
    return re.compile("|".join(pats).encode(), re.I)


def check_objects():
    pat = denylist()
    if pat is None:
        # A note, not a failure: a clone has no deny-list and should not fail
        # for that. It is the author's machine that must have one, which is
        # why its absence is said out loud rather than passing in silence.
        notes.append("no deny-list at %s, so the object scan did not run. "
                     "One pattern per line; it is gitignored on purpose."
                     % DENYLIST.relative_to(ROOT))
        return True
    bad = []
    for repo in repos():
        out = subprocess.run(
            ["git", "-C", str(repo), "cat-file", "--batch-all-objects", "--batch"],
            capture_output=True).stdout
        hits = pat.findall(out)
        if hits:
            forms = sorted({h.lower().decode("utf-8", "replace") for h in hits})
            bad.append("%s: %d occurrences %s" % (name_of(repo), len(hits), forms))
    return check("no deny-listed string in any object of any repository", bad)


# =====================================================================
# 2 and 3. the two files a reader sees first
# =====================================================================
def check_readme():
    bad = [name_of(r) for r in repos()
           if not any(t.lower() == "readme.md" for t in tracked(r))]
    return check("every repository has a README.md, which is its GitHub page",
                 bad)


def check_license():
    bad = [name_of(r) for r in repos() if "LICENSE" not in set(tracked(r))]
    return check("every repository has a LICENSE", bad)


# =====================================================================
# 4. absolute paths in code
# =====================================================================
ABS = re.compile(r"/home/[A-Za-z0-9_.-]+/|(?<![A-Za-z0-9_.-])/tmp/[A-Za-z0-9_.-]")
CODE_SUFFIX = {".py", ".sh", ".c", ".h", ".mk", ""}

# Deliberate, with the reason. An entry here is a claim that the path is data
# rather than a location this code expects to exist.
ABS_ALLOW = {
    # A tar member whose stored name is absolute. The suite asserts tarx
    # REFUSES to write it, so the path must stay absolute to be the hazard.
    ("tarx", "t/run.sh"),
    # The fixtures that prove THIS check works. A test which demonstrates that
    # an absolute path is caught has to contain an absolute path, in a live
    # line, in a comment and in a docstring -- those three cases are the test.
    # Exempting it is correct, and it is also the file that guarantees the rest
    # of this exemption list is not hiding a real one.
    ("projects", ".portfolio/t/test_audit.py"),
}

# Same reason, for the placeholder check: the fixture for "a pasteable command
# with a blank in it" is a pasteable command with a blank in it.
PLACEHOLDER_ALLOW = {
    ("projects", ".portfolio/t/test_audit.py"),
}


def check_abs_paths():
    bad = []
    for repo in repos():
        for rel in tracked(repo):
            if Path(rel).suffix not in CODE_SUFFIX and Path(rel).name != "Makefile":
                continue
            if (name_of(repo), rel) in ABS_ALLOW:
                continue
            text = read_text(repo / rel)
            if text is None:
                continue
            for lineno, line in code_lines(rel, text):
                if ABS.search(line):
                    bad.append("%s/%s:%d: %s" % (name_of(repo), rel, lineno,
                                                 line.strip()[:70]))
    return check("no absolute /home or /tmp path in tracked code", bad)


# =====================================================================
# 5. required siblings
# =====================================================================
# A suite that reads ../<some other repo> passes for its author and fails for
# everybody else. Intra-repo "../" is fine and extremely common (#include
# "../x.h", running ../prog); what is not fine is naming a sibling.
def check_siblings():
    all_names = {name_of(r) for r in repos()} | FOREIGN
    bad = []
    for repo in repos():
        # ../<own name> is not a sibling reference. t/ lives inside the
        # repository, so "$here/../psh" is psh's own binary one level up --
        # the first version of this check reported psh for depending on psh.
        names = sorted(all_names - {name_of(repo)})
        pat = re.compile(r"\.\./(%s)(?![A-Za-z0-9_.-])" % "|".join(names))
        for rel in tracked(repo):
            if not (rel.startswith(("t/", "tests/")) or
                    Path(rel).name.startswith("test_")):
                continue
            text = read_text(repo / rel)
            if text is None:
                continue
            for lineno, line in code_lines(rel, text):
                m = pat.search(line)
                if m:
                    bad.append("%s/%s:%d references sibling %s: %s"
                               % (name_of(repo), rel, lineno, m.group(1),
                                  line.strip()[:60]))
    return check("no suite requires a sibling repository to exist", bad)


# =====================================================================
# 6. a command a reader can paste with the blank still in it
# =====================================================================
# The actual failure: `commitq identity --name "Your Name" --email
# "USERNAME@..." --yes` was copied out of a status hint, and 721 commits were
# rewritten. The dangerous shape is specifically placeholder text on a line
# that also carries something irreversible.
PLACEHOLDER = re.compile(
    r"your[ _-]?name|yourname|USERNAME@|<user>@|you@example|yourhandle"
    r"|firstname|FIRSTNAME", re.I)
DESTRUCTIVE = re.compile(r"--yes|-f\b|--force|filter-branch|rm -rf|reset --hard"
                         r"|\bcq id\b|identity")


def md_code_lines(text):
    """Lines inside fenced or indented code blocks only.

    A paragraph explaining that "Your Name" was once pasted with --yes behind
    it matches every pattern the dangerous command matches. The difference is
    not the words, it is whether a reader can select the line and run it, so
    prose is skipped and code blocks are not. Recording the incident must not
    be what trips the check that exists because of it.
    """
    fenced = False
    for i, line in enumerate(text.splitlines(), 1):
        if line.lstrip().startswith("```"):
            fenced = not fenced
            continue
        if fenced or line.startswith(("    ", "\t")):
            yield i, line


def check_placeholders():
    bad = []
    for repo in repos():
        for rel in tracked(repo):
            suf = Path(rel).suffix
            if suf not in {".md", ".sh", ".py", ".html"}:
                continue
            if (name_of(repo), rel) in PLACEHOLDER_ALLOW:
                continue
            text = read_text(repo / rel)
            if text is None:
                continue
            # code_lines for source, not every line: this file's own comments
            # quote the command that caused the incident, and the check
            # reported them. The record of why a rule exists must not break
            # the rule.
            lines = (md_code_lines(text) if suf == ".md"
                     else code_lines(rel, text))
            for i, line in lines:
                if PLACEHOLDER.search(line) and DESTRUCTIVE.search(line):
                    bad.append("%s/%s:%d: %s" % (name_of(repo), rel, i,
                                                 line.strip()[:70]))
    return check("no document offers a runnable command with a blank left in it",
                 bad)


# =====================================================================
# 7 to 11. repository state
# =====================================================================
# Each repository's README quotes the summary line its own suite prints,
# usually inside a pasted transcript. Five were stale when this was written:
# commitq said 105 against 156, gitobj 1219 against 2208, terminfo 10 against
# 24, unrepro 109 against 114, tarx 118 against 119. Nothing checked them --
# the drift detector in extract.py reads the two tables in this repository and
# stops there -- and a count in a repo's own README is the first thing a
# reader compares against the suite they just ran.
REPOS_JSON = HERE / "repos.json"

# A repo whose README deliberately quotes something other than the combined
# total. An entry is a claim that the number is informative rather than wrong.
README_COUNT_ALLOW = {
    # cc's Makefile runs two suites and reports 389; the README quotes them
    # separately, as 325 and 64, which is what the transcripts actually show.
    "cc",
    # gitobj's total includes the loose objects of its sibling repositories,
    # so it moves every time anything is committed anywhere in the tree. Its
    # README explains the two numbers and quotes the stable one, 1639 from a
    # clone of gitobj alone; pinning the other would mean re-editing the file
    # after every commit in every other repository.
    "gitobj",
}

SUMMARY_RE = re.compile(r"^([\d,]+) (?:passed|agree|scenarios)", re.M)


def check_readme_counts():
    if not REPOS_JSON.exists():
        notes.append("no repos.json, so README counts were not checked")
        return True
    data = json.loads(REPOS_JSON.read_text())
    bad = []
    for repo in repos():
        name = name_of(repo)
        if name in README_COUNT_ALLOW or name not in data:
            continue
        text = read_text(repo / "README.md")
        if text is None:
            continue
        quoted = [int(q.replace(",", "")) for q in SUMMARY_RE.findall(text)]
        if not quoted:
            continue
        m = re.search(r"[\d,]+", data[name].get("tests") or "")
        if not m:
            continue
        ran = int(m.group(0).replace(",", ""))
        if ran not in quoted:
            bad.append("%s: README says %s, the suite ran %d"
                       % (name, "/".join(str(q) for q in quoted), ran))
    return check("every README's quoted count matches what its suite runs",
                 bad)


def check_repos_json_keys():
    """repos.json must name exactly the repositories that are here.

    Renaming a repository leaves its old name as a key and its new name
    missing. extract.py refuses to run in that state, which is right, but it
    refuses after ten minutes of running every suite and leaves a
    repos.json.new behind. The whole collection's figures are then stale and
    the gate fails 42 assertions for one cause. This is the same information,
    four seconds in.
    """
    if not REPOS_JSON.exists():
        return True
    data = json.loads(REPOS_JSON.read_text())
    here = {name_of(r) for r in repos() if r != ROOT}
    bad = ["%s is a repository with no repos.json entry" % n
           for n in sorted(here - set(data))]
    bad += ["%s has a repos.json entry but is not a repository here" % n
            for n in sorted(set(data) - here)]
    return check("repos.json names exactly the repositories present", bad)


def check_gitlinks():
    bad = []
    for repo in repos():
        for line in git(repo, "ls-tree", "-r", "HEAD").split("\n"):
            parts = line.split()
            if len(parts) > 1 and parts[1] == "commit":
                bad.append("%s: %s" % (name_of(repo), line.strip()[:70]))
    return check("no repository records a gitlink", bad)


def check_backup_refs():
    """refs/original is a live undo before a push and dead weight after one.

    The first version of this check failed on any refs/original at all, which
    is wrong in the direction that matters: immediately after `cq id` those
    refs are the only copy of the pre-rewrite history, and PUBLISH.md tells
    you to keep them until you have pushed and are satisfied. Failing then
    teaches you to delete your own safety net to make a check go green.

    What is actually a defect is carrying them on a repository that already
    has a remote. The history they would restore is the one that was never
    published, so restoring it means force-pushing over a branch other people
    may have, and `filter-branch -f` silently overwrites them anyway -- so
    their presence after a push is a false sense of safety rather than a real
    one.
    """
    bad = []
    pending = []
    for repo in repos():
        refs = [r for r in git(repo, "for-each-ref", "refs/original/",
                               "--format=%(refname)").split("\n") if r]
        if not refs:
            continue
        if git(repo, "remote").strip():
            bad.append("%s: %d refs/original, and it already has a remote"
                       % (name_of(repo), len(refs)))
        else:
            pending.append(name_of(repo))
    if pending:
        # One line, not 38. A note per repository buries the one that matters.
        notes.append("%d repositories hold refs/original, the undo for the "
                     "last rewrite: %s. Clear them once pushed (PUBLISH.md 1)."
                     % (len(pending), " ".join(pending[:6])
                        + (" ..." if len(pending) > 6 else "")))
    return check("no repository keeps refs/original after gaining a remote",
                 bad)


PLACEHOLDER_EMAIL = "placeholder@invalid"


def check_authors():
    bad = []
    for repo in repos():
        has_remote = bool(git(repo, "remote").strip())
        if not has_remote:
            continue
        ids = set(git(repo, "log", "--branches", "--format=%ae%n%ce").split())
        if PLACEHOLDER_EMAIL in ids:
            bad.append("%s has a remote AND placeholder commits: rewriting now "
                       "means force-pushing" % name_of(repo))
    return check("no repository with a remote still has placeholder authors",
                 bad)


SECRET = re.compile(
    r"gh[pousr]_[A-Za-z0-9]{16,}"                 # GitHub tokens
    r"|github_pat_[A-Za-z0-9_]{20,}"
    r"|AKIA[0-9A-Z]{16}"                          # AWS key id
    r"|-----BEGIN [A-Z ]*PRIVATE KEY-----"
    r"|xox[baprs]-[A-Za-z0-9-]{10,}")             # Slack


def check_secrets():
    bad = []
    for repo in repos():
        out = subprocess.run(
            ["git", "-C", str(repo), "cat-file", "--batch-all-objects", "--batch"],
            capture_output=True).stdout
        for m in SECRET.finditer(out.decode("utf-8", "replace")):
            bad.append("%s: %s..." % (name_of(repo), m.group(0)[:12]))
    return check("no credential pattern in any object of any repository", bad)


# A branch that is not the checked-out one is still published by `git push
# --all`. Listed here so that a new one is noticed rather than discovered.
KNOWN_EXTRA_BRANCHES = {
    ("projects", "worktree-bunker-site"),
}


def check_branches():
    bad = []
    for repo in repos():
        head = git(repo, "symbolic-ref", "--short", "HEAD").strip()
        for line in git(repo, "for-each-ref", "refs/heads/",
                        "--format=%(refname:short)").split("\n"):
            b = line.strip()
            if not b or b == head:
                continue
            if (name_of(repo), b) in KNOWN_EXTRA_BRANCHES:
                notes.append("%s has extra branch %s -- push HEAD, never --all"
                             % (name_of(repo), b))
                continue
            bad.append("%s: branch %s is not HEAD and is not in "
                       "KNOWN_EXTRA_BRANCHES" % (name_of(repo), b))
    return check("every unexpected branch is accounted for", bad)


# =====================================================================
# --deep: the clean-clone check
# =====================================================================
def check_clean_clone():
    """Clone each repository alone and run its suite there.

    --no-local forces a real object transfer instead of hardlinks, so the
    clone cannot reach back into the original. The scratch directory holds one
    repository at a time, so a suite that wants a sibling does not find the
    other clones and accidentally pass.
    """
    bad = []
    env = {k: v for k, v in os.environ.items()
           if k not in ("MAKEFLAGS", "MAKELEVEL")}
    for repo in repos():
        if repo == ROOT:
            continue        # its suite measures the collection by design
        with tempfile.TemporaryDirectory() as td:
            dest = Path(td) / repo.name
            c = subprocess.run(["git", "clone", "-q", "--no-local",
                                str(repo), str(dest)], capture_output=True)
            if c.returncode != 0:
                bad.append("%s: clone failed" % repo.name)
                continue
            r = subprocess.run(["make", "test"], cwd=str(dest), env=env,
                               capture_output=True, text=True, timeout=1800)
            if r.returncode != 0:
                tail = (r.stdout or "").strip().splitlines()[-3:]
                bad.append("%s: make test exited %d\n       %s"
                           % (repo.name, r.returncode, " | ".join(tail)))
            else:
                print("     clean clone ok: %s" % repo.name)
    return check("every repository builds and passes from a clone of itself "
                 "alone", bad)


CHECKS = [
    check_objects,
    check_readme,
    check_license,
    check_readme_counts,
    check_repos_json_keys,
    check_abs_paths,
    check_siblings,
    check_placeholders,
    check_gitlinks,
    check_backup_refs,
    check_authors,
    check_secrets,
    check_branches,
]


def main():
    deep = "--deep" in sys.argv
    print("audit: %d repositories%s" % (len(repos()),
                                        ", with the clean-clone check" if deep
                                        else ""))
    for fn in CHECKS:
        fn()
    if deep:
        check_clean_clone()
    for n in notes:
        print("note %s" % n)
    print("\n%d passed, %d failed" % (passed, failed))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
