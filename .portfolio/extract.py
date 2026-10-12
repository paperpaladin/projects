#!/usr/bin/env python3
"""Extract repos.json from the repositories themselves.

    cd /home/x/projects && python3 .portfolio/extract.py > .portfolio/repos.json

Every number in portfolio.pdf comes from repos.json, and the whole point of
generating that file rather than writing it is that the document then cannot
claim something the work does not support.  It had drifted anyway, because this
script was documented in the README and did not exist: commit counts, line
counts and test counts in the shipped PDF were from whenever they were last
typed in.

Four fields per repo are editorial -- blurb, oracle, invariant, group -- and are
read back out of the existing repos.json, because no measurement produces a
sentence.  Everything else is measured here.

Running every suite takes a few minutes, wasmi alone about three.  That is the
price of the test counts being real, and it is the reason this is a separate
script from build.py rather than something build.py does on every render.

`--keep-test-counts` carries the previous `tests` string across instead of
running anything.  It exists because the test suite has to exercise everything
else in here without spending three minutes doing it, and it is honest about
what it costs: the test counts are then inherited rather than measured, which
makes it the wrong thing to use before publishing.

Run this on an otherwise idle machine, and never two at once.  Two mechanisms
make a loaded run lie:

  - cc, lnk, sqlr and tarx still use a fixed scratch path inside their own t/
    directory, so two concurrent runs clobber each other's fixtures and the
    loser reports failures it did not have.
  - prof asserts sampling ratios, which is a claim about timing, so it fails
    under competition for the CPU.

Both were observed: a second extraction running alongside the first recorded
cc as FAILING, then prof as FAILING, and each of them passes on its own.  The
backstop is t/test_portfolio.py, which refuses to accept a FAILING or NO SUITE
string in a document meant to be published.
"""
import json
import pathlib
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "commitq"))
import commitq  # noqa: E402  (path has to be set up first)

EDITORIAL = ("blurb", "oracle", "invariant", "group")
SRC_EXT = (".c", ".h", ".py", ".sh")


def is_test(rel):
    return rel.startswith(("t/", "tests/")) or Path(rel).name.startswith("test_")


def line_count(path):
    try:
        with path.open(errors="replace") as fh:
            return sum(1 for _ in fh)
    except OSError:
        return 0


def tracked(repo):
    """Tracked source files, as repo-relative paths.

    git ls-files rather than walking the tree.  A walk counts build products
    and whatever the last test run left behind, which is how the line totals in
    INDEX.md came to be roughly twice what the repos actually hold -- a
    gitignored 2456-line generated file in lnk/t was most of one repo's count.

    wasmi/hist is excluded: 21,000 lines across 156 files, which are the
    per-commit snapshots its history generator replays, not source anyone
    wrote.  Counting them would triple that repo and mean nothing.
    """
    for rel in commitq.git(repo, "ls-files").split("\n"):
        if rel.endswith(SRC_EXT) and not rel.startswith("hist/"):
            yield rel


def measure(repo):
    src = test = shortcuts = 0
    for rel in tracked(repo):
        path = repo / rel
        n = line_count(path)
        if is_test(rel):
            test += n
        else:
            src += n
        try:
            shortcuts += path.read_text(errors="replace").count("shortcut:")
        except OSError:
            pass
    return src, test, shortcuts


def suite_summary(repo, keep=None):
    """The last non-blank line the suite prints, which is where every one of
    these puts its own count.

    A failing or missing suite says so in the field rather than contributing a
    number that reads like a pass.  That matters more here than anywhere else:
    this string goes straight into a document shown to people who cannot run
    the tests themselves.
    """
    if keep is not None:
        return keep
    ok, out, found = commitq.run_tests(repo)
    if not found:
        return "NO SUITE"
    lines = [l.strip() for l in out.splitlines() if l.strip()]

    # A repo whose `make test` runs more than one suite prints more than one
    # summary, and taking the last line silently reports only the last suite.
    # cc was recorded as "64 passed" while actually running 291 + 64: not a
    # wrong number, a number about a smaller thing than it appeared to
    # describe. Every "N passed, M failed" line is summed instead.
    summaries = [l for l in lines if re.fullmatch(r"\d+ passed, \d+ failed", l)]
    if len(summaries) > 1:
        passed = sum(int(l.split()[0]) for l in summaries)
        failed = sum(int(l.split()[2]) for l in summaries)
        summary = "%d passed, %d failed (%d suites)" % (passed, failed, len(summaries))
    elif summaries:
        summary = summaries[0]
    else:
        # The LAST line that looks like a count, not the last line.
        #
        # run_tests merges stdout and stderr, and the two are buffered
        # independently, so a build message written to stderr can land after
        # the summary written to stdout. utf8n's card published
        # "UCD 18.0.0: 5982 decomp records, 6828 pool words," in a field
        # labelled Result -- a true sentence about the corpus that says
        # nothing about whether the suite passed -- while `make test` on its
        # own ends with "107 passed, 0 failed". derx's card has the same
        # shape.
        #
        # So the summary is searched for rather than assumed to be last.
        # The patterns are the shapes these suites actually print; a repo
        # whose summary matches none of them still falls back to the last
        # line, which is the old behaviour and is better than nothing.
        shapes = (
            r"\d+ passed, \d+ failed.*",
            r"\d+ agree, \d+ disagree.*",
            r"\d+ of \d+ .*",
            r".*\b\d+ passed\b.*",
        )
        summary = None
        for shape in shapes:
            hits = [l for l in lines if re.fullmatch(shape, l)]
            if hits:
                summary = hits[-1]
                break
        if summary is None:
            summary = lines[-1] if lines else "(no output)"
    if ok:
        return summary
    # Keep the whole output of a failing suite. The summary line is all that
    # reaches repos.json, and that is right for the document -- but it threw
    # away the only evidence of what went wrong, which matters most for a
    # suite that fails under a full extract and passes on its own.
    #
    # unrepro did exactly that: "FAILING: 100 passed, 1 failed" during an
    # extract, then 101/0 on four consecutive runs afterwards, with no record
    # of which assertion it was. Not reproduced and therefore not fixed; the
    # least this can do is make the next occurrence diagnosable.
    try:
        log = pathlib.Path(__file__).resolve().parent / "failures"
        log.mkdir(exist_ok=True)
        (log / ("%s.log" % repo.name)).write_text(out)
    except OSError:
        pass          # a missing log must not change the verdict
    return "FAILING: " + summary


def members(root):
    """The repos that belong in the portfolio: a PLAN.md is what makes one.

    Without that rule any checkout left sitting under root joins the document --
    there is an upstream Android fork next to these eighteen, and it has no
    PLAN.md precisely because it is not one of them.

    root itself is excluded even though it is a repo with a PLAN.md. It holds
    this generator, the index and the working instructions: it is what presents
    the eighteen rather than one of them, and a document that listed itself as
    a project would be describing its own table of contents.
    """
    return [r for r in commitq.repos()
            if r != root and (r / "PLAN.md").exists()]


def records(repos, old, keep_counts=False, log=None):
    """Build the repos.json body for `repos`, carrying editorial text from `old`.

    Separated from main() so it can be run against throwaway repos in a
    tempdir, which is how it is tested; commitq's own suite works the same way.
    Both error paths raise SystemExit rather than warning, because a portfolio
    that silently omits a repo, or silently keeps describing one that is gone,
    is worse than one that refuses to build.
    """
    out = {}
    for repo in repos:
        prose = old.get(repo.name)
        if prose is None:
            raise SystemExit(
                "extract: %s has no editorial text in repos.json.\n"
                "  Add blurb, oracle, invariant and group for it by hand;\n"
                "  refusing to emit a repo described by nothing." % repo.name)
        src, test, shortcuts = measure(repo)
        rec = {k: prose[k] for k in EDITORIAL}
        rec.update(commits=commitq.commit_count(repo),
                   src=src,
                   test=test,
                   done=commitq.plan_done(repo),
                   todo=len(commitq.plan_items(repo)),
                   shortcuts=shortcuts,
                   tests=suite_summary(
                       repo, prose.get("tests") if keep_counts else None))
        out[repo.name] = rec
        if log:
            print("extract: %-12s %s" % (repo.name, rec["tests"]), file=log)

    gone = sorted(set(old) - set(out))
    if gone:
        raise SystemExit(
            "extract: repos.json describes %s, which is no longer here.\n"
            "  Remove the entry, or find out where the repo went."
            % ", ".join(gone))
    return out


def main():
    args = sys.argv[1:]
    keep_counts = "--keep-test-counts" in args
    for a in args:
        if a != "--keep-test-counts":
            sys.exit("extract: unknown argument %s\n"
                     "  usage: extract.py [--keep-test-counts]" % a)

    old = json.loads((HERE / "repos.json").read_text())
    out = records(members(ROOT), old, keep_counts, log=sys.stderr)
    json.dump(out, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
