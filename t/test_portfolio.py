#!/usr/bin/env python3
"""Tests for the portfolio generator. The oracle is git, plus the repos.

The document's whole claim is that its numbers come from the work rather than
from whoever typed them last, so the test that matters is "does the shipped
document agree with git". That half is read-only and runs against the real
repos. The other half -- the extractor's own behaviour -- runs against
throwaway repos created in a tempdir, the same way commitq's suite does, so
nothing here touches the eighteen.

This exists because the opposite was true for a while: the README documented
extract.py, extract.py did not exist, and the shipped PDF carried 38 stale
values with nothing to notice it.

No pytest, no network. `python3 t/test_portfolio.py`.
"""
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / ".portfolio"))
sys.path.insert(0, str(ROOT / "commitq"))
import extract  # noqa: E402

PORTFOLIO = ROOT / ".portfolio"
REPOS_JSON = PORTFOLIO / "repos.json"

passed = 0
failed = 0


def ok(label):
    global passed
    passed += 1
    print("ok   %s" % label)


def bad(label, *detail):
    global failed
    failed += 1
    print("FAIL %s" % label)
    for d in detail:
        print("       %s" % d)


def check(label, got, want):
    if got == want:
        ok(label)
    else:
        bad(label, "got  %r" % (got,), "want %r" % (want,))


def truthy(label, cond, *detail):
    if cond:
        ok(label)
    else:
        bad(label, *detail)


def sh(*args, cwd=None):
    return subprocess.run(args, cwd=cwd, capture_output=True, text=True,
                          timeout=120)


def mkrepo(parent, name, files, ignore=None):
    """A throwaway git repo with one commit, so commit_count has something."""
    d = Path(parent) / name
    (d / "t").mkdir(parents=True)
    for rel, text in files.items():
        p = d / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
    if ignore:
        (d / ".gitignore").write_text(ignore + "\n")
    sh("git", "init", "-q", "-b", "main", ".", cwd=d)
    sh("git", "config", "user.name", "T", cwd=d)
    sh("git", "config", "user.email", "t@invalid", cwd=d)
    sh("git", "add", "-A", cwd=d)
    sh("git", "commit", "-q", "-m", "one", cwd=d)
    return d


# ================================================ the document agrees with git

DATA = json.loads(REPOS_JSON.read_text())
HTML = (PORTFOLIO / "portfolio.html").read_text()

truthy("repos.json is not empty", len(DATA) >= 1, "found %d" % len(DATA))

for name in sorted(DATA):
    repo = ROOT / name
    if not (repo / ".git").exists():
        bad("%s: repos.json names a repo that is not here" % name)
        continue
    real = int(sh("git", "rev-list", "--count", "HEAD", cwd=repo).stdout.strip())
    check("%s: commit count matches git" % name, DATA[name]["commits"], real)

# The generated page has to carry those numbers, not merely be built from a
# file that had them. A build.py that dropped a field would otherwise pass
# everything above.
for name in sorted(DATA):
    want = "%d commits" % DATA[name]["commits"]
    truthy("%s: the page states its commit count" % name,
           re.search(re.escape(want), HTML) is not None,
           "no %r in portfolio.html" % want)

for name in sorted(DATA):
    truthy("%s: the page states its test result" % name,
           DATA[name]["tests"].split(",")[0] in HTML,
           "no %r in portfolio.html" % DATA[name]["tests"].split(",")[0])

# Headline totals are the sum of the parts, not a separately typed number.
def commas(n):
    return format(n, ",d")

for field, label in (("commits", "commits"), ("src", "source lines"),
                     ("test", "test lines")):
    total = sum(DATA[r][field] for r in DATA)
    truthy("page total for %s is the sum of the parts (%s)" % (label, commas(total)),
           commas(total) in HTML or str(total) in HTML,
           "neither %r nor %r in portfolio.html" % (commas(total), str(total)))

# Every repo described must still be a member, and every member described.
members = {r.name for r in extract.members(ROOT)}
check("every member repo is in repos.json", sorted(members - set(DATA)), [])
check("every repos.json entry is a member", sorted(set(DATA) - members), [])

# No suite may be reported as failing or absent in a document we ship.
for name in sorted(DATA):
    t = DATA[name]["tests"]
    truthy("%s: reported suite result is a pass" % name,
           not t.startswith("FAILING") and t != "NO SUITE", t)


# The PDF is what actually gets sent to anyone, and until now only the HTML was
# checked -- so a stale portfolio.pdf sitting next to a fresh portfolio.html
# passed everything. pdftotext is the reader; it is a different program from the
# one that wrote the file, which is the point.
#
# Checked more loosely than the HTML on purpose. The PDF is a typeset document:
# a figure can be split across a line, and the text extractor reorders columns.
# So each number is looked for as a bare string rather than in context, and the
# assertion is that every figure is present somewhere -- which is still enough
# to catch the two failures that matter, a PDF built from different data and a
# PDF that was never rebuilt.
PDF = PORTFOLIO / "portfolio.pdf"
if not PDF.exists():
    bad("portfolio.pdf does not exist")
elif sh("pdftotext", "-v").returncode not in (0, 99):
    print("SKIP pdftotext is not installed, so the PDF cannot be read")
else:
    text = sh("pdftotext", str(PDF), "-").stdout
    truthy("the PDF has extractable text", len(text) > 2000, "%d chars" % len(text))
    # "28 commits", not "28". A bare number is too weak to fail: planting a
    # commit count of 999 passed, because "999" occurs inside some other
    # figure on the page. pdftotext keeps the number and its unit together, so
    # the pair is both checkable and specific.
    missing = [n for n in sorted(DATA)
               if "%d commits" % DATA[n]["commits"] not in text]
    check("every repo's commit count appears in the PDF", missing, [])
    # The PDF must be at least as new as the data it claims to show. Chromium
    # exits 0 on some failures, so a crashed render is otherwise
    # indistinguishable from a finished one.
    truthy("the PDF is no older than repos.json",
           PDF.stat().st_mtime >= REPOS_JSON.stat().st_mtime - 1,
           "pdf %d, json %d -- re-run .portfolio/render.sh"
           % (PDF.stat().st_mtime, REPOS_JSON.stat().st_mtime))
    truthy("the PDF is no older than the page it was made from",
           PDF.stat().st_mtime >= (PORTFOLIO / "portfolio.html").stat().st_mtime - 1,
           "re-run .portfolio/render.sh")

# This repo must never contain a gitlink. The sibling projects are independent
# repositories that happen to live next to this one, and `git add -A` records
# such a directory as mode 160000 -- a bare commit SHA with no submodule
# config, useless to a clone and describing nothing. It happened on the first
# new sibling, so it is a test rather than a note: forgetting to add a project
# to .gitignore now fails here instead of producing a broken commit.
links = [l.split("\t", 1)[1] for l in
         sh("git", "ls-files", "-s", cwd=ROOT).stdout.splitlines()
         if l.startswith("160000")]
check("no sibling repo is committed as a gitlink", sorted(links), [])

# And every sibling repo must actually be ignored, which is the other half: the
# check above passes trivially if nothing has been staged yet.
unignored = [d.name for d in sorted(ROOT.iterdir())
             if d.is_dir() and (d / ".git").exists() and d != ROOT
             and not sh("git", "check-ignore", "-q", d.name, cwd=ROOT).returncode == 0]
check("every sibling repo is gitignored", unignored, [])

# ============================================ the extractor, on throwaway repos

with tempfile.TemporaryDirectory() as tmp:
    editorial = {"blurb": "b", "oracle": "o", "invariant": "i", "group": "g"}

    r = mkrepo(tmp, "alpha", {
        "PLAN.md": "- [x] done one\n- [x] done two\n- [ ] 01 next\n",
        "alpha.c": "/* shortcut: a shortcut */\nint main(void){return 0;}\n",
        "t/run.sh": "#!/bin/sh\necho hi\n",
    })

    rec = extract.records([r], {"alpha": dict(editorial, tests="7 passed")},
                          keep_counts=True)["alpha"]
    check("editorial text is carried through",
          {k: rec[k] for k in extract.EDITORIAL}, editorial)
    check("commits come from git", rec["commits"], 1)
    check("plan done is counted", rec["done"], 2)
    check("plan todo is counted", rec["todo"], 1)
    check("shortcut comments are counted", rec["shortcuts"], 1)
    check("source and test lines are split by path",
          (rec["src"], rec["test"]), (2, 2))
    check("--keep-test-counts carries the old string", rec["tests"], "7 passed")

    # A repo the editorial file does not describe must stop the build. Silently
    # omitting it would publish a portfolio missing a project.
    try:
        extract.records([r], {}, keep_counts=True)
        bad("an undescribed repo refuses to build")
    except SystemExit as e:
        truthy("an undescribed repo refuses to build", "alpha" in str(e), str(e))

    # And an entry whose repo is gone must stop it too, in the other direction.
    try:
        extract.records([r], {"alpha": dict(editorial, tests="7 passed"),
                              "ghost": dict(editorial, tests="9 passed")},
                        keep_counts=True)
        bad("a stale entry refuses to build")
    except SystemExit as e:
        truthy("a stale entry refuses to build", "ghost" in str(e), str(e))

    # Untracked and ignored files must not count. This is the bug that made
    # lnk look like it had 2,873 lines of tests when 2,456 of them were a
    # generated file that is not in the repo at all.
    before = extract.measure(r)
    (r / "t" / "tmp_generated.c").write_text("x\n" * 500)
    (r / "untracked.c").write_text("y\n" * 500)
    check("an ignored file does not change the counts", extract.measure(r), before)

    # hist/ is excluded by name: those are a history generator's snapshots.
    h = mkrepo(tmp, "beta", {
        "PLAN.md": "- [ ] 01 x\n",
        "beta.c": "int x;\n",
        "hist/v1.c": "int x;\n" * 300,
    })
    check("hist/ is excluded from the line count", extract.measure(h)[0], 1)

    # members() is what keeps a stray checkout out of the document.
    nop = mkrepo(tmp, "notaplan", {"README.md": "not one of them\n"})
    truthy("a repo with no PLAN.md is not a member",
           not (nop / "PLAN.md").exists() and "notaplan" not in members)


# =================================================== the extractor is repeatable

a = sh(sys.executable, str(PORTFOLIO / "extract.py"), "--keep-test-counts",
       cwd=ROOT)
b = sh(sys.executable, str(PORTFOLIO / "extract.py"), "--keep-test-counts",
       cwd=ROOT)
check("extract.py exits zero", a.returncode, 0)
truthy("two runs produce identical output", a.stdout == b.stdout)
truthy("the output it produces is the output that is checked in",
       a.stdout == REPOS_JSON.read_text(),
       "repos.json is stale: re-run extract.py")

bogus = sh(sys.executable, str(PORTFOLIO / "extract.py"), "--nope", cwd=ROOT)
check("an unknown flag is refused", bogus.returncode, 1)


print("\n%d passed, %d failed" % (passed, failed))
sys.exit(1 if failed else 0)
