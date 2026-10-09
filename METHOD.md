# projects/ -- working instructions

Thirty-five independent repositories, one method. Read this before touching anything;
read `INDEX.md` for what each repo is, and the repo's own `PLAN.md` for what comes
next in it.

## The method, which is the point

**Every project is measured against an authority it does not control.** gcc and
clang, the Linux kernel, `dash`, GNU tar, `readelf`, SQLite, Python's `re`. A test
you wrote, checking code you wrote, against a number you worked out yourself,
proves only that you were consistent.

That is not decoration. Most of the defects recorded here were in the test
harness rather than in the code: a suite that passed because it was silently doing
nothing. When adding anything, the question is not "do the tests pass" but **"have
I watched this harness fail?"**

If you add a feature, add the check that an outside authority agrees. If no outside
authority exists for it, say so in the README rather than inventing one.

## How to work here

```sh
./cq            # status across all 35
./cq t          # what to work on: stalest repo first, next planned item in each
./cq c REPO "message"    # runs that repo's tests, commits only if green
./cq a          # status + run every suite (slow: wasmi alone is ~3 min)
./cq gui        # localhost dashboard
```

`cq c` is a gate. It runs the suite against the working tree **before** committing
and refuses if red, or if the repo has no discoverable suite at all. `--no-verify`
exists for deliberately committing a known-red state (bisecting, recording a
reproducer); it should be a decision, never a habit.

Pick work from the repo's `PLAN.md`. The unchecked `- [ ]` items are ordered, and
each one records *why* it is next. 349 of them are queued.

`.portfolio/` renders the whole thing as a PDF, and every number in it comes from
`repos.json`, which is **generated, not written**:

```sh
python3 .portfolio/extract.py > .portfolio/repos.json   # runs all 35 suites, ~15 min
NAME="..." GITHUB="..." .portfolio/render.sh            # build.py, then chromium
```

Refresh it after any commit that changes a test count, or the document quietly
starts claiming last week's numbers -- it had drifted by 38 values once, because
`extract.py` was documented in the README and did not exist.

## Hard rules

1. **Never fabricate commit dates.** There is no `--date` flag in `commitq` and its
   test suite asserts there never will be, by grepping its own source for
   `GIT_AUTHOR_DATE`, `GIT_COMMITTER_DATE` and `add_argument("--date"`. Do not add
   one. A contribution graph is a claim about when work happened.
2. **Every commit must build.** Verified by checking out each commit in turn,
   deleting build artifacts so a stale binary cannot fake a pass, and rebuilding.
   `git stash -u` does NOT stash ignored files, so an audit that relies on it
   produces false passes.
3. **ASCII punctuation only.** No em dashes, en dashes, curly quotes, ellipsis
   characters, arrows, multiplication signs or non-breaking spaces, in prose or in
   code comments. Use `--` for a parenthetical break, `...` for an ellipsis,
   `->` for an arrow, straight quotes.

   **This rule is about prose, not about bytes.** Five files hold non-ASCII on
   purpose and a sweep must leave them alone: `tarx/t/run.sh` and
   `sqlr/t/oracle.py` carry non-ASCII *test data* (filenames and strings whose
   whole point is that they are not ASCII), and `commitq`'s block characters and
   middot are UI glyphs. Replacing those does not tidy anything, it deletes the
   test. A blanket sweep over user-facing strings is already recorded as a
   mistake once: see the stash on `notally-molly`, which downgraded typographic
   apostrophes and ellipses in thirty languages of Android UI text, where the
   ellipsis character is correct and `...` is wrong.
4. **All 35 must stay reproducible.** Any new C repo needs
   `-ffile-prefix-map=$(CURDIR)=.` in `CFLAGS`, or `-g` writes the build directory
   into DWARF `.debug_line_str`. Check with
   `python3 unrepro/unrepro.py check ../REPO --cmd 'make -B'` on a clean tree.
5. **Minimalism.** No frameworks, no test libraries, no abstraction before the
   second use case, fewest files. Standard library only in Python; no dependency
   beyond zlib in C. Mark a deliberate shortcut with a `shortcut:` comment naming
   its ceiling and upgrade path. There are 170 of these; `./cq` has no counter for
   them, and `grep -r` will lie to you here (see the gotcha below). Use:
   `find . -name '*.c' -o -name '*.py' | xargs grep -ho 'shortcut:' | wc -l`

## House conventions

Each repo has a `PLAN.md` with exactly five sections: **Contract**, **Hard
invariant** (the one property that, if violated, means the project failed),
**Oracle** (ranked by how little we control them), **Non-goals**, **Commit
sequence** (`[x]` done / `[ ]` next, each with an indented `why:`).

READMEs state what does **not** work, plainly and in detail. A README that only
lists successes is not finished.

Commit messages explain *why*, name what the oracle proved, and record bugs found
including the ones that were in the harness. Multi-paragraph is normal here.

## Gotchas discovered the hard way

- **`grep -r` silently skips every repo.** The shell used here replaces `grep`
  with a ugrep wrapper that passes `--ignore-files`, so it honours `.gitignore` --
  and this directory's `.gitignore` lists all 39 repo directories by name. The
  result is not an error, it is a confident `0`. Counting shortcut comments this
  way returns 3 instead of 170. Use `find ... -exec grep` for anything that has to
  cross a repo boundary, and treat a suspiciously round zero as this bug first.
- `/tmp` is **tmpfs** and does not survive a reboot. Never leave anything there.
- `wasmi/hist/build.py` does `rmtree('.git')` and rebuilds that repo's history from
  scratch. It is the generator that produced wasmi's 28 commits. Do not run it
  casually.
- All commits currently carry a placeholder author. Before any push:
  `./cq id "Name" "<user>@users.noreply.github.com"`. That rewrites every commit
  and is safe only while nothing has been pushed.
- Nothing has a git remote. Nothing has left this machine.
- Backups: `/home/x/projects-SNAPSHOT-FINAL/` holds a full tarball and a
  `git bundle` per repo. Refresh it after significant work.
- Do not execute build scripts from downloaded third-party tarballs.

## State

270 commits, 18 repos, all suites green, all builds reproducible, every commit
builds. `INDEX.md` has the per-repo invariant table and where each one goes next.
