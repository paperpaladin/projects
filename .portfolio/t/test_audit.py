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
import json
import os
import shutil
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
               audit.check_branches, audit.check_invisible,
               audit.check_tracked_binaries):
        check("clean fixture passes %s" % fn.__name__, run(fn, root), True)

    DATES_EARLY = dict(os.environ, GIT_AUTHOR_DATE="2001-01-01T00:00:00Z",
                       GIT_COMMITTER_DATE="2001-01-01T00:00:00Z")

    # --- a tracked compiled binary
    #
    # Recognised by its first four bytes rather than by its name, so
    # the planted one is called "data" with no extension: a check
    # matching names would pass this and miss exactly the file that
    # gets committed by accident.
    binrepo = make_repo(root, "hasbin")
    (binrepo / "data").write_bytes(b"\x7fELF\x02\x01\x01" + b"\0" * 57)
    git(binrepo, "add", "-A")
    subprocess.run(["git", "commit", "-qm", "oops"], cwd=binrepo, check=True,
                   env=DATES_EARLY)
    check("a tracked ELF is caught however it is named",
          run(audit.check_tracked_binaries, root), False)
    git(binrepo, "rm", "-q", "data")
    subprocess.run(["git", "commit", "-qm", "remove it"], cwd=binrepo,
                   check=True, env=DATES_EARLY)
    check("...and passes once it is gone",
          run(audit.check_tracked_binaries, root), True)

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

    # --- invisible characters
    # Same history-only lesson as above, and the same remedy, so this only
    # plants it and checks both ends.
    zw = make_repo(root, "zerowidth")
    zwbase = git(zw, "rev-parse", "HEAD").strip()
    (zw / "doc.md").write_text("a word\u200bbroken by nothing visible\n")
    git(zw, "add", "-A")
    subprocess.run(["git", "commit", "-qm", "add doc"], cwd=zw, check=True,
                   env=DATES)
    git(zw, "rm", "-q", "doc.md")
    subprocess.run(["git", "commit", "-qm", "remove it"], cwd=zw, check=True,
                   env=DATES)
    check("invisible fails on a zero width space that survives only in "
          "history", run(audit.check_invisible, root), False)

    subprocess.run(["git", "-C", str(zw), "reset", "--hard", "-q", zwbase],
                   check=True)
    git(zw, "reflog", "expire", "--expire=now", "--expire-unreachable=now",
        "--all")
    subprocess.run(["git", "-C", str(zw), "gc", "--prune=now", "-q"],
                   check=True)
    check("invisible passes once that commit is gone",
          run(audit.check_invisible, root), True)

    # The false positive this check was first written with. U+00AD encodes as
    # the two bytes c2 ad, and that pair turns up by chance in compressed
    # data: a raw-byte scan of the real collection reported 143 soft hyphens
    # and 126 arabic letter marks, every one of them inside a PDF, a PNG or a
    # wasm fixture. Planting the exact pair in a file that declares itself
    # binary with a NUL must not be a hit.
    (zw / "fixture.bin").write_bytes(
        b"\x89PNG\r\n\x1a\n\x00" + b"\xc2\xad" * 4 + b"\xe2\x80\x8b")
    git(zw, "add", "-A")
    subprocess.run(["git", "commit", "-qm", "add a binary fixture"], cwd=zw,
                   check=True, env=DATES)
    check("invisible ignores those byte pairs inside binary, which is the "
          "false positive it was first written with",
          run(audit.check_invisible, root), True)

    # And the containing-what-it-detects trap, one directory over from the
    # deny-list version of it: audit.py names these codepoints, so it must
    # name them as escapes and never as the characters themselves.
    src = (HERE.parent / "audit.py").read_text()
    check("audit.py does not itself contain any character it rejects",
          [c for c in set(src) if ord(c) in audit.INVISIBLE], [])

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

# --------------------------------------------- README counts vs the suite
#
# Five READMEs quoted stale counts when this check was written, including one
# off by a single test. Nothing compared them: extract.py's drift detector
# reads the two tables in the root repository and stops there, while the
# number a reader actually checks is the one in the repo they just cloned.
with tempfile.TemporaryDirectory() as td:
    root = make_collection(td)
    (root / ".portfolio").mkdir(parents=True, exist_ok=True)
    json_path = root / ".portfolio" / "repos.json"

    def write_json(tests):
        json_path.write_text(json.dumps(
            {"alpha": {"tests": tests}, "beta": {"tests": "7 passed, 0 failed"}}))

    _orig_dl = audit.REPOS_JSON
    audit.REPOS_JSON = json_path
    try:
        write_json("500 passed, 0 failed")
        (root / "alpha" / "README.md").write_text(
            "# alpha\n\n```\n$ make test\n500 passed, 0 failed\n```\n")
        check("README counts pass when they match", 
              run(audit.check_readme_counts, root), True)

        (root / "alpha" / "README.md").write_text(
            "# alpha\n\n```\n$ make test\n499 passed, 0 failed\n```\n")
        check("...and fail when off by one",
              run(audit.check_readme_counts, root), False)

        # A README that quotes several numbers is fine as long as the total
        # is among them -- cc quotes its two component suites.
        (root / "alpha" / "README.md").write_text(
            "# alpha\n\n```\n325 passed, 0 failed\n500 passed, 0 failed\n```\n")
        check("...and pass when the total is one of several quoted",
              run(audit.check_readme_counts, root), True)

        # A README quoting no summary at all is not a failure.
        (root / "alpha" / "README.md").write_text("# alpha\n\nNo numbers.\n")
        check("...and pass when a README quotes no count",
              run(audit.check_readme_counts, root), True)

        # Missing repos.json is a note, not a failure: a clone of one repo
        # has no collection-wide figures to compare against.
        audit.REPOS_JSON = root / ".portfolio" / "absent.json"
        check("...and pass, with a note, when there is no repos.json",
              run(audit.check_readme_counts, root), True)
    finally:
        audit.REPOS_JSON = _orig_dl

# ------------------------------------------- repos.json names what is here
#
# Renaming dwarfdump to dbginfo left the old key in repos.json and the new
# repository missing from it. extract.py refuses to run in that state, which
# is correct, but it refuses ten minutes in, after running every suite, and
# the gate then reported 42 failures for the one cause.
with tempfile.TemporaryDirectory() as td:
    root = make_collection(td)
    (root / ".portfolio").mkdir(parents=True, exist_ok=True)
    jp = root / ".portfolio" / "repos.json"
    _orig = audit.REPOS_JSON
    audit.REPOS_JSON = jp
    try:
        jp.write_text(json.dumps({"alpha": {}, "beta": {}}))
        check("repos.json keys pass when they match the directories",
              run(audit.check_repos_json_keys, root), True)

        jp.write_text(json.dumps({"alpha": {}, "beta": {}, "oldname": {}}))
        check("...and fail on an entry for a repository that is not here",
              run(audit.check_repos_json_keys, root), False)

        jp.write_text(json.dumps({"alpha": {}}))
        check("...and fail on a repository with no entry",
              run(audit.check_repos_json_keys, root), False)

        audit.REPOS_JSON = root / ".portfolio" / "gone.json"
        check("...and pass when there is no repos.json at all",
              run(audit.check_repos_json_keys, root), True)
    finally:
        audit.REPOS_JSON = _orig

# ------------------------------------------------- the exemption lists
#
# Two checks have allowlists: a path that is data rather than a location
# (tarx's absolute tar member) and the fixtures that prove those checks work,
# which have to contain what the checks look for.
#
# An allowlist is a hole, and a hole whose entry no longer matches a real file
# is worse than one that does: it exempts nothing while reading as though it
# exempts something, and a typo in the path exempts a file nobody meant to
# exempt. So every entry must name a file that is actually tracked.
audit.ROOT = Path(__file__).resolve().parent.parent.parent
real = {}
for _r in audit.repos():
    real[audit.name_of(_r)] = set(audit.tracked(_r))
for lst, what in ((audit.ABS_ALLOW, "ABS_ALLOW"),
                  (audit.PLACEHOLDER_ALLOW, "PLACEHOLDER_ALLOW")):
    for repo_name, rel in sorted(lst):
        check("%s entry %s/%s names a tracked file" % (what, repo_name, rel),
              rel in real.get(repo_name, set()), True)

# Same rule, different shape: this one is a set of repository names.
for repo_name in sorted(audit.README_COUNT_ALLOW):
    check("README_COUNT_ALLOW entry %s names a real repository" % repo_name,
          repo_name in real, True)

# ---------------------------------------------------------------------------
# The font check, against PDFs chromium actually produces.
#
# This one cannot be tested by planting a defect in a fixture repository,
# because what it reads is a rendered PDF. The substitutions are therefore
# produced for real: the same chromium that renders the portfolio, the same
# pdffonts that reads it, and two HTML pages whose font stacks reproduce the
# two ways the typography can silently change.
#
# `font-family: "Missing", sans-serif` is the fall-through that lands outside
# the design entirely -- Liberation or DejaVu, whatever fontconfig offers.
# The second page asks only for Hack and Noto Serif, which is what the
# document looks like if Noto Serif Condensed stops being installed: every
# face in it is still one of the three, which is precisely why forbidding
# strangers is not enough on its own.

def render_pdf(tmp, name, style, body):
    html = Path(tmp) / (name + ".html")
    pdf = Path(tmp) / (name + ".pdf")
    html.write_text("<style>%s</style><body>%s</body>" % (style, body))
    r = subprocess.run(
        ["chromium", "--headless", "--disable-gpu", "--no-sandbox",
         "--no-pdf-header-footer", "--print-to-pdf=%s" % pdf,
         "file://%s" % html],
        capture_output=True, text=True, timeout=180)
    if not pdf.exists():
        return None
    del r
    f = subprocess.run(["pdffonts", str(pdf)], capture_output=True, text=True)
    return f.stdout


if not shutil.which("chromium") or not shutil.which("pdffonts"):
    # Loudly. A skipped test is not a passing one, and this is the test that
    # keeps a silent-substitution check from becoming a tautology.
    print("note chromium or pdffonts is missing, so the font check was NOT"
          " exercised against real substitutions")
else:
    with tempfile.TemporaryDirectory() as _tmp:
        _stranger = render_pdf(_tmp, "stranger",
                               'body{font-family:"NoSuchFaceAtAll",sans-serif}',
                               "fell outside the design")
        _narrow = render_pdf(_tmp, "narrow",
                             'body{font-family:"Hack"}'
                             'p{font-family:"Noto Serif"}',
                             "code<p>body text</p>")

        check("a fall-through to a face outside the design is rejected",
              any("not one of the three designed faces" in b
                  for b in audit.font_problems(_stranger or "")), True)

        # The specific point: every face in this PDF IS one of the three.
        check("that PDF contains no stranger-free excuse",
              any("is in the PDF and is not one of the three" in b
                  for b in audit.font_problems(_narrow or "")), False)
        check("a missing condensed face is rejected even though every face"
              " present is intended",
              any("NotoSerif-Condensed" in b and "does not appear" in b
                  for b in audit.font_problems(_narrow or "")), True)

        # And the positive direction, so the check is not simply always red.
        _real = PORTFOLIO_PDF = audit.HERE / "portfolio.pdf"
        if _real.exists():
            _out = subprocess.run(["pdffonts", str(_real)],
                                  capture_output=True, text=True).stdout
            check("the shipped portfolio.pdf passes the font check",
                  audit.font_problems(_out), [])
            check("all three designed faces are found in it",
                  sorted(audit.pdf_font_families(_out)),
                  ["Hack", "NotoSerif", "NotoSerif-Condensed"])

# A font that is present but not embedded is the third failure, and it needs
# no renderer: it is a column in the table pdffonts prints. The row below is
# the shipped PDF's own first line with "yes" changed to "no" in the embedded
# column, which is the one thing about this input that is synthetic, and it is
# synthetic because chromium cannot be asked to reference a font it did not
# embed.
check("a font that is present but not embedded is rejected",
      any("is not embedded" in b for b in audit.font_problems(
          "name                 type          encoding    emb sub uni object ID\n"
          "-------------------- ------------- ----------- --- --- --- ---------\n"
          "AAAAAA+Hack-Bold     CID TrueType  Identity-H  no  yes yes       4 0\n"
          "BAAAAA+NotoSerif-CondensedBold CID TrueType Identity-H yes yes yes 5 0\n"
          "CAAAAA+NotoSerif-Regular CID TrueType Identity-H yes yes yes 6 0\n")),
      True)

# The credential check has one exemption, for repositories whose subject is
# finding credentials. An exemption nobody has tried to abuse is a hole of
# unknown size, so these are the four cases that matter: the two shapes it is
# meant to let through, and the two nearly identical ones it must not.

def secret_allowed(text):
    """True if audit would let this text through the credential check."""
    m = audit.SECRET.search(text)
    if m is None:
        return True
    return audit.is_unusable_as_a_credential(m.group(0),
                                             text[m.end():m.end() + 40])


# Assembled at run time rather than written out. The strings below are
# byte-for-byte what the check sees, but no blob in this repository contains
# one, so the credential scan does not report its own test fixtures. The
# alternative was to exempt this file by path, and the scan reads objects
# rather than the working tree precisely so that a secret which was committed
# and later deleted is still found; a path exemption would not survive that.
TOKEN = "ghp_" + "0" * 36
PEM = "-" * 5 + "BEGIN OPENSSH PRIVATE " + "KEY" + "-" * 5
AWS = "AKIA" + "IOSFODNN7EXAMPLE"
SLACK = "xoxb-" + "0" * 12 + "-abcdefghij"

check("a token whose body is all zeros is allowed",
      secret_allowed("token=" + TOKEN), True)
check("a PEM header over key material saying it is not a key is allowed",
      secret_allowed(PEM + "\nnotarealkey\n"), True)

# One zero changed to a one. Nothing else differs.
check("a token with one non-zero character is NOT allowed",
      secret_allowed("token=" + TOKEN[:-1] + "1"), False)
check("a PEM header over anything else is NOT allowed",
      secret_allowed(PEM + "\nb3BlbnNzaC1rZXk\n"), False)

# And the shapes the exemption says nothing about must still fail.
check("an AWS key id is NOT allowed", secret_allowed(AWS), False)
check("a Slack token is NOT allowed", secret_allowed(SLACK), False)

print("\n%d passed, %d failed" % (passed, failed))
sys.exit(1 if failed else 0)
