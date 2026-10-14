# projects/: working instructions

Thirty-eight independent repositories, one method. Read this before touching anything;
read `INDEX.md` for what each repo is, and the repo's own `PLAN.md` for what comes
next in it.

## The method, and the point

Every project is measured against an authority it does not control. gcc and
clang, the Linux kernel, `dash`, GNU tar, `readelf`, SQLite, Python's `re`. A test
you wrote, checking code you wrote, against a number you worked out yourself,
proves only that you were consistent.

That is not decoration. Most of the defects recorded here were in the test
harness, not in the code: a suite that passed because it was silently doing
nothing. When adding anything, the question is not "do the tests pass" but **"have
I watched this harness fail?"**

If you add a feature, add the check that an outside authority agrees. If no outside
authority exists for it, say so in the README instead of inventing one.

Four things learned by doing this repeatedly, all of them cheap to reuse:

1. A test can be true and prove nothing. `g(300)` against `int g(char)`
   returns 44 whether or not the call converts anything, because the callee
   truncates into its own one-byte slot. Ask which direction of a conversion
   the test can actually see.
2. A mutation test can be vacuous the same way. One here deleted a rule
   from the left operand while the case had the interesting type on the
   right, produced byte-identical output, and reported a survivor.
3. A refusal needs an outside authority too. `cc` grew a `refuse()` that
   demands gcc reject the program as well, and it immediately caught `cc`
   rejecting valid C. Its opposite, `unimpl()`, demands gcc *accept* it and
   asserts we refuse cleanly: the failure mode of a missing feature is not a
   missing error message, it is quietly miscompiling something that looked
   close enough.
4. Some properties are invisible until the suite crosses a boundary.
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

`cq c` is a gate. It runs the suite against the working tree before committing
and refuses if red, or if the repo has no discoverable suite at all. `--no-verify`
exists for deliberately committing a known-red state (bisecting, recording a
reproducer). It should be a decision, never a habit.

Pick work from the repo's `PLAN.md`. The unchecked `- [ ]` items are ordered, and
each one records *why* it is next. 344 of them are queued.

Membership is having a `PLAN.md`. That is the rule `extract.py` uses and the
one `commitq`'s gateability guard asserts against, so a directory with a `.git`
and no `PLAN.md` is outside the set, `notally-molly` is an unrelated Android
fork and stays out.

Two repos were invisible for exactly that reason until they were given one:
`ed25519` and `terminfo`, both built in sessions that were interrupted. Both
build and both pass their suites against external oracles. `ed25519` has since
been finished through signing and verification against Project Wycheproof:
`ed25519_sign` and `ed25519_verify` are both in `ed25519.h`. `terminfo` is
still unfinished, but not in the way this said. It does read the string
table, 4584 string capabilities compared byte for byte against `infocmp`.
What it lacks is the ncurses extended section and parameterised strings
evaluated against `tput`. Their READMEs say so first. The lesson is that the
membership rule is silent: a repo with no `PLAN.md` is not reported as missing,
it simply does not appear, so `cq t` never offers work on it and the portfolio
never counts it.

`.portfolio/` renders the whole thing as a PDF, and every number in it comes from
`repos.json`, which is **generated, not written**:

```sh
make portfolio        # runs all 38 suites, ~30 min, then moves repos.json
NAME="..." GITHUB="..." .portfolio/render.sh            # build.py, then chromium
```

Refresh it after any commit that changes a test count, or the document quietly
starts claiming last week's numbers. It had drifted by 38 values once, because
`extract.py` was documented in the README and did not exist.

## Hard rules

1. There is no `--date` flag in `commitq`, and
   its suite asserts the invariant behaviourally: it sets
   `GIT_AUTHOR_DATE=2020-01-01` in the environment, runs a real commit, and
   requires the resulting date to be today. Do not add a `--date` flag. A
   contribution graph is a claim about when work happened.

   This rule used to say the suite "greps its own source for `GIT_AUTHOR_DATE`,
   `GIT_COMMITTER_DATE` and `add_argument("--date"`". Those greps were deleted
   as discredited: `commitq/t/test_commitq.py` records that all six passed
   while the invariant was false, and the sense is now inverted for two of
   the three tokens: `commitq.py` *must contain* `GIT_AUTHOR_DATE`, because
   that is the variable `git_env()` strips from every git subprocess. Only
   `add_argument("--date"` is still grepped for absence. `INDEX.md` carried the
   same stale description.
2. Every commit must build. This is the intent, and it is not currently
   verified. There is no harness that checks out each commit and rebuilds: the
   only script that ever did is `bigint/scratch/audit.sh`, which is untracked
   and hardcoded to one repo. Treat the claim as an aspiration until something
   establishes it collection-wide.

   When writing that harness: delete build artifacts between commits so a
   stale binary cannot fake a pass, and do not reach for `git stash -u`, which
   does NOT stash ignored files and so produces false passes.
3. ASCII punctuation only. No em dashes, en dashes, curly quotes, ellipsis
   characters, arrows, multiplication signs or non-breaking spaces, in prose or in
   code comments. Use `...` for an ellipsis, `->` for an arrow, and straight
   quotes.

   This rule is about prose, not about bytes. Six files hold non-ASCII on
   purpose and a sweep must leave them alone: `tarx/t/run.sh`,
   `sqlr/t/oracle.py` and `gitobj/t/run.sh` carry non-ASCII *test data*
   (filenames and strings whose whole point is that they are not ASCII: the
   last creates a filename with a diaeresis), and `commitq`'s block characters
   and middot are UI glyphs. Replacing those does not tidy anything, it deletes the
   test. A blanket sweep over user-facing strings is already recorded as a
   mistake once: see the stash on `notally-molly`, which downgraded typographic
   apostrophes and ellipses in thirty languages of Android UI text, where the
   ellipsis character is correct and `...` is wrong.
4. All 38 must stay reproducible. Any new C repo needs
   `-ffile-prefix-map=$(CURDIR)=.` in `CFLAGS`, or `-g` writes the build directory
   into DWARF `.debug_line_str`. Check with
   `python3 unrepro/unrepro.py check ../REPO --cmd 'make -B'` on a clean tree.
5. Minimalism. No frameworks, no test libraries, no abstraction before the
   second use case, fewest files. Standard library only in Python; no dependency
   beyond zlib in C. Mark a deliberate shortcut with a `shortcut:` comment naming
   its ceiling and upgrade path. There are 173 of these; `./cq` has no counter for
   them, and `grep -r` will lie to you here (see the gotcha below). Use:
   `find . -name '*.c' -o -name '*.py' | xargs grep -ho 'shortcut:' | wc -l`

## House conventions

Each repo has a `PLAN.md` with at least these five sections: Contract, **Hard
invariant** (the one property that, if violated, means the project failed),
Oracle (ranked by how little we control them), Non-goals, **Commit
sequence** (`[x]` done / `[ ]` next, each with an indented `why:`).

READMEs state what does not work, plainly and in detail. A README that only
lists successes is not finished.

Commit messages explain *why*, name what the oracle proved, and record bugs found
including the ones that were in the harness. Multi-paragraph is normal here.

## Gotchas discovered the hard way

- `grep -r` silently skips every repo. The shell used here replaces `grep`
  with a ugrep wrapper that passes `--ignore-files`, so it honours `.gitignore`,
  and this directory's `.gitignore` lists all 39 repo directories by name. The
  result is a confident `0`, with no error anywhere. Counting shortcut comments this
  way returns 3 instead of 170. Use `find ... -exec grep` for anything that has to
  cross a repo boundary, and treat a suspiciously round zero as this bug first.
- A test that can perform the failure it checks for eventually will.
  `commitq identity` rewrites the author on every commit in 39 repos. Its new
  guard refuses obvious example text, and the test for the guard shelled out
  to `commitq.py` with `cwd` set to the real collection, on the assumption
  that `cwd` chose the tree. It does not: `ROOT` is
  `Path(__file__).parent.parent`, fixed at import. So the mutation run. The
  run that proves the guard is load-bearing, with the guard deliberately
  disabled, rewrote all 37 project repos and reported "151 passed, 1
  failed". `filter-branch -f` does not refuse when `refs/original` exists, it
  overwrites it, so the undo survived only by luck. Anything that writes goes
  against a fixture, and the question to ask of a destructive test is not "is
  it correct" but "what does it do when the thing it tests is broken".
- A rename in a new commit does not remove the old content. `git grep`
  and `git ls-files` read the working tree. A string edited out of a file and
  committed over is still in the blob underneath it, and still on the GitHub
  page for the previous commit. Removing something from history means
  rewriting history. Checking that it is gone means
  `git cat-file --batch-all-objects --batch`, which also sees the unreachable
  objects a rewrite leaves behind, there were 3364 of those after one.
  `cq au` does this.
- `reflog expire` on the branches is not enough: HEAD has its own.
  After a `filter-branch`, the old commits stay in the object database
  until nothing points at them, and `git reflog expire --expire=now
  refs/heads/main` leaves `logs/HEAD` still naming every one of them, so
  `gc --prune=now` keeps them all and the rewrite looks as though it did
  not take. `cq au` reads `cat-file --batch-all-objects`, which sees
  unreachable objects, so it is the thing that notices. Expire HEAD as
  well. Not `--all`, which blanks `git stash list`: terminfo has a stash
  and it is the second time that was nearly lost.

- A detector must not contain what it detects. The deny-list for that scan
  started as a literal regex in the checker, so the first run reported four
  occurrences in this repository: its own source. Whatever is being kept out
  of a repository cannot be written into the thing that keeps it out. It lives
  in an untracked file now.
- A gate check that has never been seen to fail may be checking nothing.
  This is the house rule applied to the house rules. Every check in
  `.portfolio/audit.py` is run twice by `.portfolio/t/test_audit.py`, clean,
  where it must pass, and with its own defect planted, where it must fail.
  Writing those pairs found three checks that could never pass (they flagged
  the comments explaining them) and one whose first version I had expected to
  be fixed by `git gc`, which it is not.
- Clone it alone before believing it works. `make audit-deep` clones each
  repository into a scratch directory with no siblings and runs its suite
  there. `gitobj`'s suite read eight named neighbours at `../<name>/.git`, so
  it passed here and failed five assertions for anyone else: one of them a
  corruption test that, finding no corpus, planted no corruption and then
  reported that the corruption was not caught.
- A missing external oracle is a refusal or a loud skip, never a quiet
  one, and which depends on how much of the oracle it is. `trace` prints
  `SKIP strace not installed` and continues, because strace is one oracle
  among several there. `corex` exits 2 with one line, because `gdb` is the
  only oracle for every fact it checks and the only way to obtain a core, so a
  reduced run would print "0 passed, 0 failed" having checked nothing.
- `/tmp` is tmpfs and does not survive a reboot. Never leave anything there.
  It is also shared: a fixed name there (`/tmp/vtparse-fuzz.bin`) means two
  concurrent runs feed each other their inputs, and a cleanup that sweeps
  `/tmp` while the code honours `$TMPDIR` removes nothing and exits 0.
- `wasmi/hist/build.py` does `rmtree('.git')` and rebuilds that repo's history from
  scratch. It is the generator that produced wasmi's 31 commits. Do not run it
  casually.
- All commits currently carry a placeholder author. Before any push, put the
  values in variables and then `./cq id "$GIT_NAME" "$GIT_EMAIL"`, never
  inline, because the inline form was pasted with the example text still in it
  and rewrote 721 commits to "Your Name". `cq id` refuses obvious example text
  now, and its suite asserts both directions: that the paste is refused, and
  that a real address containing the same substrings ("superuser", "zhouyou")
  is not. That rewrites every commit and is safe only while nothing has been
  pushed.
- Nothing has a git remote. Nothing has left this machine. `cq p` is the
  staged-push front end when that changes: `cq p` alone reports total/pushed/
  local per repo, `cq p REPO N` sends the first N commits and nothing after
  them. It refuses while a repo is still on the placeholder author, since a
  push is what makes a hash permanent.
- `git add -A` at the root will commit a git worktree as a gitlink. The
  `.gitignore` lists every repo directory for this reason, and the local tool
  directories are excluded in `.git/info/exclude`, out of the tracked file
  deliberately, since they are machine state and every clone reads
  `.gitignore`. One of those worktrees appeared mid-session and went straight
  into a commit. A recorded gitlink produces a clone that cannot be checked
  out, and git says so only in a `hint:` block that is easy to scroll past.
  Check with `git ls-tree -r HEAD | awk '$2=="commit"'` after any root
  commit.
- This directory is not yours alone while you are working in it. A
  worktree on `worktree-bunker-site` was created and committed to from
  elsewhere while work was in progress here. That branch is unrelated to this
  collection and is not meant to be published with it: push `HEAD`, never
  `--all`. More generally, leave branches and worktrees you did not make
  alone, and do not assume the root repo's `HEAD` is where you left it.
- Backups: a sibling `projects-SNAPSHOT-FINAL/` directory holds a full tarball
  and a `git bundle` per repo. Refresh it after significant work.
- Do not execute build scripts from downloaded third-party tarballs.
- A flake is a defect. Chase it with a loop that keeps the output.
  `unrepro`'s suite failed once during an `extract.py` run and then passed
  four times in a row, and I recorded it here as unreproduced with two
  guessed candidates: the locale-dependent `ls-order` case and the heavy
  `cc` sibling build. Both guesses were wrong. A loop running `make test`
  until it failed, saving the whole output, caught it on the thirteenth run:
  `ar rcsU` stamps the archive's SYMBOL-INDEX member with the wall clock, so
  the `ar-stamp` case was irreproducible on the clock alone and its bisection
  assertion only passed when both builds landed in the same second.

  Two lessons worth more than the fix. The repo already warned about exactly
  this, `t/cases/date-macro/Makefile` says relying on the wall clock "is
  exactly the flakiness that lets this class of bug survive in real
  projects", so the trap was documented in one case and present in its
  neighbour. And guessing at a flake from its summary line produced two
  wrong answers in about a minute, where a loop produced the right one in
  three. `extract.py` now writes a failing suite's full output to
  `.portfolio/failures/REPO.log` for the same reason.
- Run `make test`, never `sh t/run.sh` directly. 32 repos have a
  `t/run.sh`. Seven of those harnesses compile the code under test
  themselves and so are safe either way: `ed25519`, `jsonc`, `sha2`, `tomlc`,
  `utf8n`, `vtparse`, `xmlc`, each builds its test binaries *from the .c
  file under test*, e.g. vtparse's `build ./t/table_test t/table_test.c
  vtparse.c`.

  The other 25 compile nothing they are testing: every `make test` target
  depends on `all`, so the documented path rebuilds first, but invoked
  directly after an edit they report passes for the binary that was lying
  around. That is not hypothetical, three mutations of `terminfo`'s number
  decoder were each recorded as SURVIVING against a stale binary, and all
  three are caught the moment it is rebuilt.

  This note used to say "14 harnesses" while naming 13, and six of the
  thirteen (`cc`, `corex`, `dbginfo`, `lnk`, `slab`, `trace`) compile
  only *fixtures and workloads*, never the thing under test. So it listed six
  repos as safe to invoke directly when they are precisely the hazard it
  warns about. `grep -E '\-o +[^ ]*REPO' REPO/t/run.sh` is the check. For the
  seven safe ones the .c under test appears as an input.

  `terminfo/t/run.sh` refuses to run when its source is newer than its binary
  and exits non-zero saying so, verified by touching the source. It is the
  pattern to copy: four lines using `-nt`. The other 24 are not guarded,
  because each names its binary differently and 24 tailored edits is a worse
  trade than this note: add the guard to a repo when you are in it for
  another reason.

  The six repos with no `t/run.sh` at all are `commitq`, `rx`, `srcdiff`,
  `tlp`, `unrepro` and `walkv`.
- `pkill -f PATTERN` kills the shell that runs it. Every Bash call here is
  `bash -c '<the whole command>'`, so the pattern you are matching is sitting
  in the invoking shell's own `/proc/*/cmdline`. `pkill -f 'tlp.py reduce'`
  issued in the same command as a `tlp.py reduce` run kills both, and the
  surviving symptom is an exit code of 143 or 144 with no output and no
  explanation. It cost three debugging detours in one session, once sending me
  after a non-existent bug in code whose patch had been killed before it
  wrote. Kill by PID from `pgrep -af`, in a separate call.
- A second `extract.py` now REFUSES, and it used to destroy `repos.json`.
  Two runs both write `repos.json.new` and both `mv` it, so one can move a
  half-written file over the real one, which happened, leaving the file
  empty and recoverable only because it is committed. An earlier overlap
  produced a spurious `commitq: FAILING` instead, because some suites share a
  scratch directory between runs and `prof` asserts sampling ratios.

  Three classes, checked with a sweep over every `t/run.sh`, not from
  memory, and the first sweep I did still missed nine of them, so the list
  below is the one to trust:

  Fixed path, any two concurrent runs collide. `cmark`, `jsonc`, `tomlc`,
  `xmlc`, `corex`, `ed25519`, `sha2`, `utf8n` (all `scratch/`), `derx` and
  `terminfo` and `httpd` (`t/tmp`), and `trace`, which uses 61 fixed
  `t/*.tmp` filenames and no scratch variable at all.

  Keyed by the binary under test. `inflate` and `pngc` use
  `t/tmp/$(basename "$IN")`, so `make test` and `make test-asan` can overlap
  safely but two runs of the *same* binary cannot. inflate's own comment at
  `t/run.sh:11` says so.

  Per-run, safe. `cc`, `lnk` and `tarx` use `t/tmp.$$`; `sqlr` uses
  `work.<pid>`; `prof` and `cc`'s fuzzer use `mktemp`.

  This note originally named cc, lnk, sqlr and tarx as the unsafe ones,
  all four are in the safe class, and then, after I corrected it, named five
  of the twelve unsafe ones. Both versions were written from a sweep whose
  pattern was too narrow: the first matched only `^T=`-style assignments, the
  second missed `S=`, `OUT=`, `work=` and trace's bare filenames.

  `extract.py` takes an exclusive `flock` on `.portfolio/.extract.lock` and
  exits non-zero if another run holds it. It refuses instead of waiting. A
  second concurrent invocation is a mistake, not a queue, and blocking would
  hide it for thirty minutes and then produce the right answer.

  The note that used to sit here said "finish every repo change first, then
  extract once": advice to someone who has already decided to be careful.
  It did not say that the second invocation silently destroys the first's
  output, the part that would have stopped me. I wrote that note and
  then made the mistake twice. Prose is not an interlock.
- `git checkout <file>` as a cleanup reflex deletes uncommitted work. It
  is the natural way to undo a one-line experimental edit, and it is also the
  natural way to undo the two hours of edits sitting in the same file. I ran
  `git checkout -q t/oracle.py` to revert a `sed` probe against sqlr and lost
  six uncommitted fixes in one keystroke. They were only recoverable because
  the patch text was still in the conversation. Commit first, then experiment:
  `git stash` if the work is not commit-ready. Reverting an experiment is
  never urgent enough to skip that.
- `nohup CMD &` plus `run_in_background` reports completion immediately.
  The backgrounding shell exits as soon as it has forked, so the tool fires
  its completion notification for the launcher while the real process keeps
  running. Its output file is empty and exit status is 0, which reads exactly
  like a job that ran and produced nothing. Pick one: `run_in_background`
  alone, or `nohup ... &` with a `pgrep` check afterwards. The hazard here is
  specific: a 30-minute `extract.py` looked finished after two seconds, and
  acting on that would have meant running suites against its held lock.
- `n=$(grep -c PAT f || echo 0)` yields `"0\n0"`, not `0`. `grep -c`
  prints the count *and* exits 1 when the count is zero, so the fallback
  appends a second line and `$((q+n))` dies with "syntax error in expression".
  Drop the `|| echo 0`: the count is already printed. This cost a detour in
  `prof` and then, in the same session as the fix, a second one at the root.

## State

681 commits, 38 repos, all 38 suites green as of the last `make portfolio`.
`INDEX.md` has the per-repo invariant table and where each one goes next.

Two things this line used to assert are not established: "every commit
builds" (hard rule 2: nothing checks it) and "all builds reproducible",
which was measured when the collection was 18 repos and has not been re-run
across all 38. `unrepro`'s own README still lists four siblings as
not-reproducible that now are.

`cc` compiles itself: `make self-host` builds it with itself twice and
asserts the two binaries are byte-identical AND that the stage-2 compiler
passes the whole suite. The second half is not ceremony. At the first green
`cmp cc2 cc3` the stage-2 compiler failed 15 cases, because a compiler that
miscompiles itself consistently reaches a fixpoint without complaint.

It is where the recent work has gone and is the one repo whose README is
worth reading in full. It has a preprocessor (hide sets, `#include`, the full
`#if` family, `#` and `##`, variadic macros), function prototypes, `static`
and `extern`, global initialisers with relocations, variadic definitions
against the real SysV ABI, and bitfields. Eight real glibc headers compile
and a program using `printf` through them runs. Milestone 1 of its PLAN is
complete. 325 + 64 cases, a sanitizer gate, a self-host gate, a differential fuzzer, and every feature mutation-tested with the survivors written down.
