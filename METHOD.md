# projects/: working instructions

Forty-one independent repositories, one method. Read this before touching anything;
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
./cq            # status across all 41
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

`cq t` used a different rule from the other two until it was fixed: it
walked every git repository under the root, so it offered work on
`notally-molly` every run, described as "plan is empty", which reads
as an invitation to write one for the single directory these
instructions say in bold never to modify. It filters on `PLAN.md` now
and prints what it left out, because a filter that hides its own
exclusions repeats the silence described below.

It also said "plan is empty" for a finished plan. `plan_items()`
returns only the unchecked items, so a completed plan and an unwritten
one both produce an empty list, and only `plan_done()` separates them.
Three repositories were reading as unplanned when they were done.

Two repos were invisible for exactly that reason until they were given one:
`ed25519` and `terminfo`, both built in sessions that were interrupted. Both
build and both pass their suites against external oracles. `ed25519` has since
been finished through signing and verification against Project Wycheproof:
`ed25519_sign` and `ed25519_verify` are both in `ed25519.h`. `terminfo` is finished now, and this used to say otherwise. It reads
the string table, 4584 string capabilities byte for byte against
`infocmp`, AND the ncurses extended section, AND parameterised strings
evaluated against `tput`: 3834 evaluations across 43 terminals,
reaching 18 of the stack language's operators, with 9 more covered by
a `tic`-compiled probe entry because no installed terminal uses them. The lesson is that the
membership rule is silent: a repo with no `PLAN.md` is not reported as missing,
it simply does not appear, so `cq t` never offers work on it and the portfolio
never counts it.

`.portfolio/` renders the whole thing as a PDF, and every number in it comes from
`repos.json`, which is **generated, not written**:

```sh
make portfolio        # runs all 41 suites, ~30 min, then moves repos.json
NAME="..." GITHUB="..." .portfolio/render.sh            # build.py, then chromium
```

Refresh it after any commit that changes a test count, or the document
quietly starts claiming last week's numbers. It had drifted by 38 values once, because
`extract.py` was documented in the README and did not exist.

The drift check only catches a row whose last cell is a plain integer,
so `| **1,639** alone |` and `| 216 scenarios |` sailed past it while
the suites had moved to 2,146 and 349. Four rows were stale that way at
once. Compare the tables against `repos.json` directly, not just by
reading what `extract.py` warns about.

Note also that `extract.py` enumerates repositories once at startup, so
a repository created while it runs is not in the output. Add its
editorial entry to `repos.json` by hand and re-run with
`--keep-test-counts`, which re-uses the counts already measured and
runs only the new one's suite.

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
2. Every commit must build, and `cq buildall` is the thing that checks
   it. **847 of 847 commits build**, with 196 more having nothing to
   build, measured 18 October 2026. It was an aspiration in this rule
   for as long as nothing ran it.
   It creates a fresh git worktree per commit with `git worktree add
   --detach` and builds the DEFAULT target there, not `make test`: those
   are different claims and the second is an order of magnitude slower.
   `cq buildall REPO` does one repository, `--last N` the most recent N
   commits of each.

   The two traps this used to warn about are closed by construction
   rather than by care. A stale binary cannot fake a pass because the
   worktree is new and holds no object file, generated header or fetched
   corpus. And nothing stashes, so `git stash -u` not stashing ignored
   files cannot bite.

   The false pass is a case in `commitq`'s suite rather than a sentence
   here: a three-commit fixture whose middle commit does not compile, run
   both ways. The harness reports 2 of 3 and names the commit. Built in
   place with the previous commit's binary left behind and newer than the
   source, `make` reports success on the broken one.
3. ASCII punctuation only. No em dashes, en dashes, curly quotes, ellipsis
   characters, arrows, multiplication signs or non-breaking spaces, in prose or in
   code comments. Use `...` for an ellipsis, `->` for an arrow, and straight
   quotes.

   This rule is about prose, not about bytes. Nine files hold non-ASCII on
   purpose and a sweep must leave them alone. The list is from a sweep, not
   from memory, because the version here used to say six while describing a
   set that was already nine: it named `commitq.py` alone where `README.md`
   and `serve.py` carry the same glyphs.

       find . -path ./notally-molly -prune -o -type f \
         \( -name '*.c' -o -name '*.h' -o -name '*.py' -o -name '*.sh' \
            -o -name '*.md' \) -print | grep -v '/scratch/\|/\.git/\|/hist/' \
         | xargs env LC_ALL=C grep -lP '[^\x00-\x7F]'

   `tarx/t/run.sh`, `sqlr/t/oracle.py` and `gitobj/t/run.sh` carry non-ASCII
   *test data* (filenames and strings whose whole point is that they are not
   ASCII: the last creates a filename with a diaeresis). `commitq.py`,
   `commitq/README.md` and `commitq/serve.py` hold block characters and a
   middot, which are UI glyphs. `bpec/bpec.c`, `bpec/t/encode_cmp.py` and
   `bpec/t/split_cmp.py` hold the byte-level alphabet's own notation, where
   U+0120 is literally how that encoding writes a space, plus corpus strings
   in several scripts. Replacing those does not tidy anything, it deletes the
   test. A blanket sweep over user-facing strings is already recorded as a
   mistake once: see the stash on `notally-molly`, which downgraded typographic
   apostrophes and ellipses in thirty languages of Android UI text, where the
   ellipsis character is correct and `...` is wrong.
4. All 41 must stay reproducible. Any new C repo needs
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
  and this directory's `.gitignore` lists every repo directory by name. The
  result is a confident `0`, with no error anywhere. Counting shortcut comments this
  way returns 3 instead of 170. Use `find ... -exec grep` for anything that has to
  cross a repo boundary, and treat a suspiciously round zero as this bug first.
- A test that can perform the failure it checks for eventually will.
  `commitq identity` rewrites the author on every commit in all of them. Its new
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
- Assert that the new path ran. Adding a second implementation and
  comparing it against the first proves nothing if the new one is not
  actually wired in: the comparison then runs the old code twice and
  agrees with itself. In `ed25519` the guard is an operation counter,
  and it earned itself immediately, because two mutations that point
  the new entry point back at the old implementation fail ONLY the
  count checks. Every value comparison passes under both.

- A seeded check can pass with the seed ignored. `derx`'s first
  determinism assertion compared two fuzzer logs, and the logs differ
  on the line that echoes the seed back, so it passed while `--seed`
  was deliberately unwired. The fix was to compare a digest of the
  generated material rather than the report about it. Whenever a test
  asserts "same seed, same output", ask what it would do if the seed
  were ignored entirely.

- A claim can be false before you arrive and pass anyway on a
  degenerate fixture. `inflate` asserted that output never grows as
  the compression level rises. It had never been true: 2 of 480 level
  pairs over 60 real files already grew. It passed because the only
  fixture was twenty copies of one file, and editing a comment in that
  file broke it. Before strengthening a property, check it against
  something other than the fixture it was written for.

- A truncated failure list hides the worst failure. `bigint` prints
  the first 20 disagreements and appends the driver's exit status
  last, so when the driver died of SIGFPE partway through a chunk, all
  20 slots went to knock-on wrong answers and the crash was never
  mentioned. Terminal failures sort first now. Any report with a cap
  needs an order, not just a limit.

- A guard against a crashed comparator must not also fire on an
  ordinary disagreement. `dbginfo`'s fired on `rc != 0`, which is also
  what its comparison script returns for a normal mismatch, so every
  genuine failure printed a second self-contradicting line and was
  counted twice. It never turned red into green, but it inflated every
  red number it ever reported, including one recorded in a PLAN.

- Backticks in a commit message are command substitution. `cq c REPO
  "..."` passes the message as a double-quoted shell argument, and
  commit messages here quote code constantly. A message saying "the
  failure path called `no`, which is not a function" ran `no`, got
  nothing, and committed "the failure path called , which is not a
  function". The shell also printed `no: command not found`, which in
  a long run reads as output from the tests.

  Use plain quotes in a message, or pass it with
  `git commit --amend -F file` from a file nothing interpolates.
  Worth a scan after a long session: the tell is a sentence with a
  word missing where a word plainly belongs.
- A buffer larger than its data turns the sanitizer off. **EIGHTEEN
  distinct buffers, in twelve repositories.** Nine were found one at a
  time by people who had been told the shape existed: `derx`, `bpec`,
  `jsonc`, `sqlr`, `mydiff` (its undiscarded sequences), twice in
  `wasmi`, `walkv` (a 1025-byte `char key[MAX_KEY + 1]` holding a
  two-byte key) and `utf8n` (512KB holding 400KB). Not one was found by
  the sanitizer, which is the whole point.

  The other nine were found in an afternoon by a `grep`, after nine
  hand-found ones had failed to suggest that a sweep was worth running:
  `prof` 2, `cmark` 3, `tzf` 2, `dbginfo` 1, and `mydiff` again in
  `slurp`. The lesson is not about buffers. Nine independent discoveries
  of one shape is overwhelming evidence that the shape is systemic, and
  the correct response to the third or fourth was a mechanical search of
  every repository, not a ninth careful fix. A defect class found
  repeatedly by hand is a search you have not written yet.

  Four things that sweep got wrong or nearly missed, which is what the
  next one should start from:

  **It is not only doubling buffers.** `tzf`'s `footer_parse` copied a
  25-byte TZ string into `char buf[128]`. Same blindness, no growth
  pattern, invisible to a grep for `cap *= 2`. Any buffer declared
  larger than what goes in it will do.

  **The fix does not travel.** `mydiff` was fixed once already, in the
  sequences it compares, and the commit says so. Nobody looked one
  function away at `slurp`, which holds the untrusted input. `cmark` had
  three: the input, the inline parser's subject, and every node the
  renderer escapes. Sweep the file, not the function.

  **A README can claim a verification that never happened.** `cmark`'s
  README had said for months that "a deliberate heap overread in
  `escape_html` is reported by ASan with a line number". It was false
  when written. Four separate inputs were planted and ASan reported
  nothing for any of them, because all four render out of a doubled
  buffer. The claim was not optimistic, it was untested.

  **The gate is the only witness.** With `dbginfo`'s fix reverted, its
  suite printed `118 passed, 0 failed` beside the new target's FAIL.
  Nothing else in the harness could see the difference, which is exactly
  what you would expect and exactly why the number is no comfort.

  Where it stops: ASan can see the end of a file and not the end of a
  section. A read walking off `.debug_info` into `.debug_abbrev` is
  still inside one live allocation, and sizing the file buffer exactly
  does nothing about it. `jsonc`'s answer -- copy each region into its
  own exact allocation behind a debug flag and run the suite both ways
  -- is the pattern; `dbginfo` has it queued. `cmark` has two cases that
  no allocation size can reach, because it shortens a length without
  touching the buffer, and says so in its README rather than pretending
  otherwise.

  A negative result is still a result. `dbginfo` ran 3,600 mutants and
  89 real binaries through a now-sighted sanitizer and found nothing:
  the blind spot was real, the bug behind it was not. Report that as
  measured, not as reassurance.

  Keep this number current. `walkv` and `utf8n` were found hours apart
  and BOTH were reported as "the eighth", because each had read this
  paragraph while it still said seven; four more in the same afternoon
  each called themselves "the tenth". A stale count here does not just
  misinform, it is the number people cite back, so it propagates into
  commit messages and READMEs that are then wrong about the collection
  they belong to.

  `wasmi`'s pair is the clearest. Its locals-type array doubled, so an
  over-read was not only invisible but PASSED: the garbage byte read
  as 0, which is the validator's own code for the polymorphic unknown
  type, so the module validated. And its linear memory was allocated
  as `pages * 65536 + 1`, which is the most attacker-reachable buffer
  in the program, since wasm addresses index it directly. The second
  was found by scanning for the shape rather than revisiting the
  function that had just been fixed, which is the search that works. A read
  buffer that doubles is 64 KB after reading 1 KB, so a read one byte
  past the end of the input lands 63 KB inside a live allocation and
  ASan says nothing. In `derx`, deleting a bounds check produced 33
  wrong answers and zero sanitizer reports; in `bpec`, a deliberate
  one-past-the-end read produced zero reports untrimmed and two after
  a `realloc` down to the exact length. Both repos had been reporting
  clean ASan runs for weeks over an area smaller than it looked.

  The fix is one `realloc` after the read loop. The check is to plant
  the over-read and require ASan to see it, which `bpec/t/run.sh`
  does as an ordinary case, so reintroducing a rounded-up buffer
  turns the suite red rather than quietly turning the sanitizer off.

  `jsonc` is the one that says how little a single fix is worth. Its
  `slurp` had already been trimmed and documented; the string decode
  buffer one function away had the same shape, rounded a 6-byte
  string up to a 16-byte allocation, and was equally blind. The fix
  did not travel. Look for the shape, not for the function that was
  named last time.

  `jsonc` also shows the other half of the answer. An arena makes
  this permanent, because every object lives inside one big block and
  no sanitizer can see a write cross from one to the next. Its
  `-DJSONC_ARENA_DEBUG` gives every object its own exactly sized
  allocation, and the suite runs both ways, so the speed and the
  sanitizer coverage are both kept instead of one being traded for
  the other quietly.

  The sweep for candidates is crude and the result is a list of
  suspects, not of defects. It has since been run properly and acted
  on: `psh` and `tomlc` are no longer the only repositories that shrink
  a buffer to its data. `walkv`, `utf8n`, `prof`, `cmark`, `tzf`,
  `dbginfo` and `mydiff` all do now, each with a `make overread` target
  that compiles a planted one-past-the-end read and FAILS unless the
  sanitizer reports it. Every one of those targets was watched to go red
  with the fix reverted, so the gate is known to be load-bearing rather
  than assumed to be.

  Copy that target when adding the fix anywhere else. The exit code
  matters: pick one the program cannot produce by other means, so a
  report cannot be confused with a segfault, a usage error or a clean
  refusal. `tzf` uses 86 for that reason and says so.

  What the sweep still cannot see: a fixed-size array that is simply
  bigger than its contents, which is how `tzf`'s second instance hid.
- `cq c` stages the whole tree, so anything not in `.gitignore` gets
  committed. A 288 KB `bpec-asan` binary was tracked for exactly this
  reason, with `.gitignore` listing only the release binary next to
  it, and a subagent swept a `.msg.tmp` into a `derx` commit the same
  way. Check with: tracked files whose first four bytes are
  `7f454c46` are ELF.

  That sweep also finds 19 tracked binaries under `wasmi/hist`,
  `b1` through `b17` plus two bug variants, about 600 KB. They are
  build artifacts of the `c*` sources beside them. They are left
  alone deliberately: that directory belongs to `build.py`, which
  deletes `.git` and rebuilds the history from scratch, and removing
  its inputs or outputs without reading it is not a safe thing to do
  in passing.
- A `rm -rf /tmp/PREFIX.*` sweep takes other people's files. One agent
  cleaning up after `unrepro` removed a pre-existing `/tmp/unrepro.txt`
  that was not its own. `/tmp` is shared, the glob does not know who
  made what, and the file is gone. Delete the exact paths you created.
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

  The dual of it bit later in the same session and deserves its own
  sentence. `until ! pgrep -f PATTERN; do sleep 15; done` never exits,
  because the waiting shell's own command line contains the pattern
  and so matches it. The symptom is not an error: it is a watcher
  reporting that a job is still running hours after it finished, and
  then a second watcher started for the same reason, also never
  exiting. Two were sitting there while the run they watched had been
  green for an hour, and one of them made a four-hour figure out of a
  one-hour job. Use `pgrep -x NAME` for an exact binary name, or wait
  on a PID.
- The root suite cannot be green while any member repo is being
  edited. `test_portfolio.py` runs `extract.py` twice and requires the
  output to equal the checked-in `repos.json` byte for byte, and
  `measure()` counts lines in the WORKING TREE, not in HEAD. So a
  parallel agent part-way through editing `zipc.c` moves `src` by
  ninety lines and the root suite fails with "repos.json is stale:
  re-run extract.py", which is true and not the point. Sync the
  portfolio last, after everything else has committed. Nothing is
  wrong when this happens; the counts are simply of a tree that is
  still moving.
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
  `xmlc`, `corex`, `ed25519`, `sha2`, `utf8n` and `bpec` (all `scratch/`),
  `derx` and `terminfo` and `httpd` (`t/tmp`), and `trace`, which uses 61
  fixed `t/*.tmp` filenames and no scratch variable at all.

  `walkv` was in this list and is not any more: it used a fixed `t/db` plus
  nine fixed `t/*.tmp`, and a backgrounded `make mutants` overlapping a
  foreground `make test` produced 164 invented failures including "prefix
  went backwards: 3 -> 1". That is the single output a crash-consistency
  project most wants to believe, arriving from a collision rather than a
  bug. It now uses `t/w$$.*` with an EXIT trap, and two concurrent runs
  both report 704 passed. The lesson is not about `walkv`: a suite whose
  whole purpose is to detect corruption cannot tell corruption it caused
  from corruption another process caused.

  `bpec` is the sharpest of them because its `scratch/` holds the venv
  and both pinned tokenizer files, not just temporaries, so `make test`
  and `make test-asan` cannot overlap and neither can overlap an
  `extract.py` run. Its ASan pass takes long enough that the temptation
  to start something else in the meantime is real.

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
- A rate limit that the rate-limit API does not report. `gh repo create`
  begins failing after roughly a dozen repositories with "You have created
  too many repositories, too quickly", an hourly cooldown enforced by
  GitHub's abuse system. `gh api rate_limit` reports 4989/5000 core requests
  remaining while every create is being refused, because the two limits are
  unrelated. An hour went into trusting that number over the error text.
  When an API says no, read what it said; do not ask a different endpoint
  whether it meant it.
- Creating a remote and pushing to it authenticate by different paths.
  `gh repo create` uses gh's own stored token; `git push` goes through
  git's credential helper, which `~/.gitconfig` here hardcodes as
  `!/usr/bin/gh auth git-credential`. When gh lives anywhere else, every
  creation succeeds and every push fails, and what is left on GitHub is a
  row of repositories that exist and are empty. Worse, `gh repo list`
  reports `diskUsage: 0KB` for a *correctly* pushed repository too, because
  that figure is computed asynchronously -- so the obvious check for "did
  the content arrive" gives a false alarm. Ask for the branches instead.
- Do not put `/run/host/usr/bin` on `PATH` to reach a host binary from
  inside the toolbox container. That directory also holds the host's `git`,
  built against host libraries, which cannot find its own `remote-https`
  helper here and fails every push with `remote helper 'https' aborted
  session`. Call the host binary by absolute path and leave `PATH` alone.
- `--force-with-lease` refusing with `stale info` is not a reason to reach
  for `--force`. It means the local clone has no remote-tracking ref for
  that branch, so git has no basis on which to judge the lease -- which is
  exactly the case where you have the least idea what is on the remote.
  `git fetch` first, then compare: in `sqlr` the remote's tree turned out to
  be byte-identical to a local commit, so nothing was lost by replacing it.
  That comparison takes a minute and is the whole reason the lease exists.
- A batch script over N repositories must not be `set -e` and nothing else.
  One transient failure on the eleventh of forty-two ended the run and its
  message scrolled off the screen, so the visible symptom was "it stopped"
  with no cause. Run each item in a function called with `|| record-and-
  continue`, and print the names of everything that failed in one block at
  the end, where it cannot scroll past.
- An oracle that asks one question about a megabyte cannot notice a defect
  in one byte of it. `utf8n` deleted its ill-formed-byte comparison and all
  109 assertions still passed, because the hostile-input check handed the
  oracle a single 400kB buffer and asked whether the answer was right --
  and a buffer that size always contains something that forces the same
  answer whether the deleted comparison runs or not. The assertion was
  true, the property it was meant to pin was gone. It took 17 hand-written
  cases and a 50,000-window sweep to make the mutant die. Granularity is
  part of an oracle's strength: one comparison over a corpus is a weaker
  instrument than ten thousand over its windows, even though it reports a
  bigger number.
- A summary line that is printed unconditionally is not a result. `utf8n`'s
  oracle roster printed `ran, table diffed byte for byte` whether or not the
  diff had agreed, so the most reassuring sentence in the output was
  independent of the thing it described. This is the same defect as `wasmi`'s
  reject suite, which declared fifteen rejections while rejecting nothing,
  and it is worth a specific habit: for every line that says a check passed,
  find the branch that would print something else, and if there is no such
  branch the line is decoration.

## State

926 commits across 41 repos and 84 in this one. 344 plan items are queued.
All 41 suites were green together in the `make portfolio` of 17 October
2026, and the root's own three suites pass: 14 audit checks, 52 audit
tests, 276 in `t/`.
`INDEX.md` has the per-repo invariant table and where each one goes next.

"Every commit builds" is established, not asserted: `cq buildall` says
847 of 847, with 196 commits having nothing to build. It creates a
fresh git worktree per commit, reads the Makefile as it was AT that
commit, and builds `all` where there is one.

The first run of it reported 937 of 1040, and almost every one of the
103 was the tool being wrong rather than a commit being broken. Bare
`make` runs the first target, which in `commitq` and `srcdiff` is
`test`, so it ran their suites and recorded the result as whether the
commit built; and it read today's Makefile rather than the commit's,
so 86 root commits that never had one were all reported broken. Worth
remembering before believing any number this harness or another one
prints on its first run.

"All builds reproducible" is still not established. It was measured when
the collection was 18 repos and has not been re-run across all 41.
`profiled` was checked individually when it was added and is
reproducible; the sweep is the thing that has not happened.

This paragraph also used to say `unrepro`'s README still listed four
siblings as not-reproducible after they were fixed. That was true once
and is not now: its README carries the whole arc, including the
re-measurement showing all four reproducible.

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
