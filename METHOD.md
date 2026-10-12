# projects/ -- working instructions

Thirty-eight independent repositories, one method. Read this before touching anything;
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

Four things learned by doing this repeatedly, all of them cheap to reuse:

1. **A test can be true and prove nothing.** `g(300)` against `int g(char)`
   returns 44 whether or not the call converts anything, because the callee
   truncates into its own one-byte slot. Ask which direction of a conversion
   the test can actually see.
2. **A mutation test can be vacuous the same way.** One here deleted a rule
   from the left operand while the case had the interesting type on the
   right, produced byte-identical output, and reported a survivor.
3. **A refusal needs an outside authority too.** `cc` grew a `refuse()` that
   demands gcc reject the program as well, and it immediately caught `cc`
   rejecting valid C. Its opposite, `unimpl()`, demands gcc *accept* it and
   asserts we refuse cleanly: the failure mode of a missing feature is not a
   missing error message, it is quietly miscompiling something that looked
   close enough.
4. **Some properties are invisible until the suite crosses a boundary.**
   Internal linkage does nothing observable inside one file; a variadic
   overflow path is unreachable from a compiler that stops at six arguments.
   Both needed the suite to build two objects, or to let gcc make the call.

## How to work here

```sh
./cq            # status across all 38
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
each one records *why* it is next. 344 of them are queued.

**Membership is having a `PLAN.md`.** That is the rule `extract.py` uses and the
one `commitq`'s gateability guard asserts against, so a directory with a `.git`
and no `PLAN.md` is outside the set -- `notally-molly` is an unrelated Android
fork and stays out.

Two repos were invisible for exactly that reason until they were given one:
`ed25519` and `terminfo`, both built in sessions that were interrupted. Both
build, both pass their suites against external oracles, and both are
**unfinished** -- `ed25519` has no signing function and `terminfo` does not
read the string table. Their READMEs say so first. The lesson is that the
membership rule is silent: a repo with no `PLAN.md` is not reported as missing,
it simply does not appear, so `cq t` never offers work on it and the portfolio
never counts it.

`.portfolio/` renders the whole thing as a PDF, and every number in it comes from
`repos.json`, which is **generated, not written**:

```sh
python3 .portfolio/extract.py > .portfolio/repos.json   # runs all 38 suites, ~30 min
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

   **This rule is about prose, not about bytes.** Six files hold non-ASCII on
   purpose and a sweep must leave them alone: `tarx/t/run.sh`,
   `sqlr/t/oracle.py` and `gitobj/t/run.sh` carry non-ASCII *test data*
   (filenames and strings whose whole point is that they are not ASCII -- the
   last creates a filename with a diaeresis), and `commitq`'s block characters
   and middot are UI glyphs. Replacing those does not tidy anything, it deletes the
   test. A blanket sweep over user-facing strings is already recorded as a
   mistake once: see the stash on `notally-molly`, which downgraded typographic
   apostrophes and ellipses in thirty languages of Android UI text, where the
   ellipsis character is correct and `...` is wrong.
4. **All 38 must stay reproducible.** Any new C repo needs
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
- **`git add -A` at the root will commit a git worktree as a gitlink.** The
  `.gitignore` already lists every repo directory for this reason; worktrees
  under `.tool-state/worktrees/` are now listed too, because one appeared
  mid-session and went straight into a commit. A recorded gitlink produces a
  clone that cannot be checked out, and git says it in a `hint:` block that
  is easy to scroll past. Check with
  `git ls-tree -r HEAD | awk '$2=="commit"'` after any root commit.
- **Other sessions share this directory.** A worktree on
  `worktree-bunker-site` was created and committed to while this session was
  running, by something else. Leave other branches and worktrees alone, and
  do not assume the root repo's HEAD is where you left it.
- Backups: `/home/x/projects-SNAPSHOT-FINAL/` holds a full tarball and a
  `git bundle` per repo. Refresh it after significant work.
- Do not execute build scripts from downloaded third-party tarballs.
- **A flake is a defect; chase it with a loop that keeps the output.**
  `unrepro`'s suite failed once during an `extract.py` run and then passed
  four times in a row, and I recorded it here as unreproduced with two
  guessed candidates -- the locale-dependent `ls-order` case and the heavy
  `cc` sibling build. Both guesses were wrong. A loop running `make test`
  until it failed, saving the whole output, caught it on the thirteenth run:
  `ar rcsU` stamps the archive's SYMBOL-INDEX member with the wall clock, so
  the `ar-stamp` case was irreproducible on the clock alone and its bisection
  assertion only passed when both builds landed in the same second.

  Two lessons worth more than the fix. The repo already warned about exactly
  this -- `t/cases/date-macro/Makefile` says relying on the wall clock "is
  exactly the flakiness that lets this class of bug survive in real
  projects" -- so the trap was documented in one case and present in its
  neighbour. And guessing at a flake from its summary line produced two
  wrong answers in about a minute, where a loop produced the right one in
  three. `extract.py` now writes a failing suite's full output to
  `.portfolio/failures/REPO.log` for the same reason.
- **Run `make test`, never `sh t/run.sh` directly.** 14 harnesses compile the
  binary under test themselves (cc, corex, dwarfdump, ed25519, jsonc, lnk,
  sha2, slab, tomlc, trace, utf8n, vtparse, xmlc) and are safe either way.
  The other 18 compile nothing: every `make test` target depends on `all`, so
  the documented path rebuilds first, but invoked directly after an edit they
  report passes for the binary that was lying around. That is not
  hypothetical -- three mutations of `terminfo`'s number decoder were each
  recorded as SURVIVING against a stale binary, and all three are caught the
  moment it is rebuilt.

  `terminfo/t/run.sh` now refuses to run when its source is newer than its
  binary, and exits non-zero saying so. It is the pattern to copy: four lines
  using `-nt`. The other 18 are **not** guarded, because each names its
  binary differently and 18 tailored edits is a worse trade than this note --
  add the guard to a repo when you are in it for another reason.
- **`pkill -f PATTERN` kills the shell that runs it.** Every Bash call here is
  `bash -c '<the whole command>'`, so the pattern you are matching is sitting
  in the invoking shell's own `/proc/*/cmdline`. `pkill -f 'tlp.py reduce'`
  issued in the same command as a `tlp.py reduce` run kills both, and the
  surviving symptom is an exit code of 143 or 144 with no output and no
  explanation. It cost three debugging detours in one session, once sending me
  after a non-existent bug in code whose patch had been killed before it
  wrote. Kill by PID from `pgrep -af`, in a separate call.
- **A second `extract.py` now REFUSES, and it used to destroy `repos.json`.**
  Two runs both write `repos.json.new` and both `mv` it, so one can move a
  half-written file over the real one -- which happened, leaving the file
  empty and recoverable only because it is committed. An earlier overlap
  produced a spurious `commitq: FAILING` instead, because cc, lnk, sqlr and
  tarx use fixed scratch paths and `prof` asserts sampling ratios.

  `extract.py` takes an exclusive `flock` on `.portfolio/.extract.lock` and
  exits non-zero if another run holds it. Refusing rather than waiting: a
  second concurrent invocation is a mistake, not a queue, and blocking would
  hide it for thirty minutes and then produce the right answer.

  The note that used to sit here said "finish every repo change first, then
  extract once" -- advice to someone who has already decided to be careful.
  It did not say that the second invocation silently destroys the first's
  output, which is the part that would have stopped me. I wrote that note and
  then made the mistake twice. Prose is not an interlock.

## State

612 commits, 38 repos, all builds reproducible, every commit
builds. `INDEX.md` has the per-repo invariant table and where each one goes next.

`cc` compiles itself: `make self-host` builds it with itself twice and
asserts the two binaries are byte-identical AND that the stage-2 compiler
passes the whole suite. The second half is not ceremony -- at the first green
`cmp cc2 cc3` the stage-2 compiler failed 15 cases, because a compiler that
miscompiles itself consistently reaches a fixpoint without complaint.

It is where the recent work has gone and is the one repo whose README is
worth reading in full. It has a preprocessor (hide sets, `#include`, the full
`#if` family, `#` and `##`, variadic macros), function prototypes, `static`
and `extern`, global initialisers with relocations, variadic definitions
against the real SysV ABI, and bitfields. Eight real glibc headers compile
and a program using `printf` through them runs. Milestone 1 of its PLAN is
complete. 325 + 64 cases, a sanitizer gate, a self-host gate, a differential fuzzer, and every feature mutation-tested with the survivors written down.
