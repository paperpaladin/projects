# projects

Thirty-six repositories. Every one is a working program with an **external
oracle** -- something outside the author's control that decides whether the code
is right. Pure C or standard-library Python throughout; no frameworks, no package
managers, no dependency beyond `zlib`. Every repo has `make test` and it passes.
Every commit builds, verified by removing build artifacts and rebuilding each one.

All of them produce **reproducible builds**, verified by `unrepro` -- one of the
thirty-six.

## Start here

```sh
cd /home/x/projects
./cq id "Your Name" "<username>@users.noreply.github.com"   # do this FIRST
./cq a        # status + run every suite
./cq t        # what to work on next, stalest repo first
./cq gui      # http://127.0.0.1:8787
```

Every commit currently carries a placeholder author so nothing had to guess at
yours. `cq id` rewrites all 636 and fixes each repo's config. Safe now; don't do
it after pushing. Use the `users.noreply.github.com` address -- commit emails are
public and scraped.

## Start with cc

`cc` is a C compiler that compiles itself. `make self-host` builds it with
itself, builds it again with the result, and checks the two binaries are
byte-identical -- then runs the whole suite against the stage-2 compiler,
because the fixpoint proves the compiler is *stable* and not that it is
*correct*. The first time `cmp cc2 cc3` came out green, the stage-2 compiler
still failed 15 cases.

It has a preprocessor with the hide-set rules, function prototypes, bitfields,
variadic functions checked against glibc's own `va_arg`, and it compiles
`<stdio.h>` and friends out of `/usr/include`.

## The repos

| repo | lang | what it is | the oracle | tests |
|---|---|---|---|---|
| [cc](cc/) | C | C compiler for x86-64, **self-hosting** | gcc **and** clang, and itself | **325** + 64 cpp |
| [lnk](lnk/) | C | static ELF linker | the kernel runs it, or it doesn't | 29 |
| [wasmi](wasmi/) | C | WebAssembly interpreter | expectations computed in Python | **11,833** |
| [psh](psh/) | C | POSIX shell subset | `dash`, stdout **and** exit status | **207 agree** |
| [rx](rx/) | C | linear-time regex engine | Python's `re` | **15,500 cases** |
| [inflate](inflate/) | C | DEFLATE/gzip codec | `gzip -d` accepts our output | 162 |
| [tarx](tarx/) | C | tar reader/writer | GNU `tar`, bidirectional | 118 |
| [sqlr](sqlr/) | C | SQLite file-format reader | libsqlite3 itself | 114 agree |
| [vtparse](vtparse/) | C | VT500 parser + wcwidth | published table, **3584/3584** | 98 |
| [unrepro](unrepro/) | Py | build-reproducibility differ | planted causes, 7/7 diagnosed | 101 |
| [dwarfdump](dwarfdump/) | C | DWARF debug-info parser | `readelf` | 85 |
| [jail](jail/) | C | Landlock sandbox | the kernel -- denied means EACCES | 77 |
| [commitq](commitq/) | Py | multi-repo commit gate + GUI | throwaway repos in a tempdir | 94 |
| [walkv](walkv/) | C | WAL key-value store | crash at every I/O boundary | 216 scenarios |
| [slab](slab/) | C | LD_PRELOAD malloc replacement | real programs, identical output | 31 |
| [trace](trace/) | C | ptrace syscall tracer, follows children | `strace -c` / `strace -f -c` | 43 |
| [srcdiff](srcdiff/) | Py | finds shipped code absent from the repo | **real xz artifacts** + live PyPI | 25 |
| [prof](prof/) | C | sampling profiler | a planted hot loop, known 10:1 ratios | 15 |
| [cmark](cmark/) | C | CommonMark parser | the spec's own spec.json | **652/652** |
| [tomlc](tomlc/) | C | TOML 1.0.0 parser | toml-test + stdlib tomllib | **709/709** |
| [utf8n](utf8n/) | C | Unicode normalisation | NormalizationTest.txt | **806,840 assertions** |
| [sha2](sha2/) | C | SHA-2, HMAC, PBKDF2 | NIST CAVP vectors | 2561 vectors |
| [pngc](pngc/) | C | PNG decoder | PngSuite | 162 + 14 refused |
| [jsonc](jsonc/) | C | RFC 8259 JSON parser | JSONTestSuite | 95/95, 188/188 |
| [bigint](bigint/) | C | Arbitrary-precision integers | Python's native int | 7.3M fuzz cases |
| [mydiff](mydiff/) | C | Myers diff and patch | GNU diff AND GNU patch | 995 |
| [httpd](httpd/) | C | HTTP/1.1 static server | curl + RFC 9112 | 226 |
| [corex](corex/) | C | ELF core dump reader | gdb, value by value | 71 |
| [derx](derx/) | C | ASN.1 DER / X.509 reader | openssl asn1parse | 10,822 elements |
| [seccompc](seccompc/) | C | seccomp policy compiler | the kernel | 125 |
| [sockv](sockv/) | C | socket lister via netlink | the kernel | 82 |
| [tzf](tzf/) | C | TZif reader, RFC 8536 | zoneinfo | 34 |
| [gitobj](gitobj/) | C | git object database reader/writer | the object name is its own SHA-1 | 322 |
| [zipc](zipc/) | C | ZIP reader/writer | Info-ZIP `unzip`/`zip`, bidirectional | 55 |
| [xmlc](xmlc/) | C | XML 1.0 well-formedness checker | W3C conformance suite, 2585 cases | 83 |
| [tlp](tlp/) | Py | metamorphic SQL logic-bug finder | a relation SQLite must satisfy with **itself** | 36 |

Worth running once each:

```sh
cd cc        && make diff-test      # vs gcc and clang
cd rx        && make bench          # 1ms where python-re takes >5s
cd walkv     && make test-asan      # the whole crash matrix under ASan+UBSan
cd trace     && ./trace -cf ls      # follow children
cd jail      && ./jail --ro /usr -- cat /etc/passwd   # denied, cleanly
cd srcdiff   && python3 srcdiff.py audit attrs       # live supply-chain audit
cd unrepro   && python3 unrepro.py check ../cc --cmd 'make -B'
```

Several compose. `cc` + `lnk` together remove the binutils dependency, which is
`cc`'s milestone-3 goal. `inflate` is what `tarx` needs for compression. `unrepro`
already found and fixed a real defect in eight of its siblings.

## This directory is also a repo

Nineteen repositories now, but still eighteen projects. The nineteenth is this
directory: `INDEX.md`, `METHOD.md`, the `cq` wrapper and `.portfolio/`. All of
it was tracked by nothing until it became a repo, for a reason worth naming --
`commitq.repos()` only ever looked *downward* from the root, so the root itself
was invisible to the tool whose entire job is to notice unverified work. It is
listed first by `./cq` and gated by the same `cq c` as everything else; its
suite is `t/test_portfolio.py`.

The eighteen stay independent. They are named one by one in `.gitignore` rather
than matched by a pattern, because a pattern would silently swallow a
nineteenth project the day it appeared.

It is not one of the eighteen and does not appear in the PDF. Those are
programs judged by authorities outside the author; a document has no such
authority for its prose. Only its figures are checkable, and those are
checked -- see `PLAN.md` here for the contract.

## The PDF

`.portfolio/` renders all eighteen into one document. Every figure in it is
generated rather than typed:

```sh
python3 .portfolio/extract.py > .portfolio/repos.json   # runs all 18 suites
NAME="Your Name" GITHUB="yourhandle" .portfolio/render.sh
```

`extract.py` reads commit counts from `git`, line counts from tracked files only,
and test counts from actually running each suite; the four prose fields per repo
are editorial and are preserved across regeneration. Re-run it after anything
that moves a number.

## Working from here

`commitq` is the loop:

```sh
./cq t                      # pick the stalest repo
#  ... do the next [ ] item from its PLAN.md ...
./cq c cc "..."             # runs the tests, commits only if green
```

`commit` runs the suite **against the working tree before committing** and refuses
if it is red. `--no-verify` is there for when red is deliberate -- bisecting, or
recording a reproducer before the fix.

`./cq s REPO` groups a large diff by role and emits a reviewable script, ordering
implementation before its tests and docs last, so every commit leaves the tree in
a state where running the tests means something.

There is no `--date` flag anywhere, and `commitq`'s own suite asserts there never
will be -- it greps for `add_argument("--date"`, `GIT_AUTHOR_DATE` and
`GIT_COMMITTER_DATE` and fails if any appears. The way to a dense graph is `cq t`
plus small commits.

## The PLAN.md convention

Every repo has a `PLAN.md` with the same five sections. **Read it first when
picking a repo back up after a gap.**

- **Contract** -- the interface, and what must not break.
- **Hard invariant** -- the one property that, if violated, means the project
  failed:

  | repo | invariant |
  |---|---|
  | cc | the self-host fixpoint: `cmp cc2 cc3` |
  | lnk | every executable emitted runs, or we refused to emit it |
  | wasmi | a malformed module is rejected or traps, never corrupts the host |
  | psh | stdout and exit status identical to `dash`, every corpus script |
  | rx | a pc enters a thread list at most once per input position |
  | inflate | `gzip` accepts everything we emit; we decode everything it emits |
  | tarx | GNU tar agrees both ways, **and** no member escapes the destination |
  | sqlr | output byte-identical to SQLite; malformed input errors, never crashes |
  | vtparse | never allocates, never reads past its byte, matches the published table |
  | unrepro | never report clean on a build that is not reproducible |
  | dwarfdump | every fact printed agrees with readelf |
  | jail | an ungranted path is never reachable, and the child cannot relax itself |
  | commitq | no commit is ever created with a date other than now |
  | walkv | recovered state is a prefix with no holes |
  | slab | two live allocations never overlap; every pointer correctly aligned |
  | trace | tracing does not change the traced program |
  | srcdiff | no false negatives in HIGH, **and** few enough false positives that a real one is visible |
  | prof | profiling does not change the profiled program |

- **Oracle** -- ranked by how little the author controls them.
- **Non-goals** -- what keeps each project finishable. Some are permanent:
  backreferences in `rx` are incompatible with its invariant, so the answer is no,
  not later.
- **Commit sequence** -- `[x]` done, `[ ]` next, each carrying *why*, the files, and
  the test that would prove it. Ordered; each entry is the next thing that moves an
  oracle.

## Where each one goes next

The single highest-value step per repo, from its plan:

- **cc** -- the preprocessor. `#include`, macros, `#if`, token pasting, hide-set
  expansion. Last real blocker on self-hosting, and it will take longer than
  everything before it combined: glibc's headers weaponise GNU C, so
  `__attribute__`, statement expressions, `typeof` and `__builtin_*` all appear
  before you reach anything useful.
- **wasmi** -- vendor the official WebAssembly spec testsuite and publish the real
  pass rate. 11,833 self-authored cases is a weaker claim than any external score,
  and the README says so.
- **slab** -- a free-span cache for large allocations, then a `PROT_NONE` tail so
  a large block can grow without copying. Those two are the whole remaining gap:
  `realloc`-grow is 81x glibc and large churn 8x, both syscall-bound. Per-thread
  magazines are done, which took four-thread churn from 21x to about even.
- **inflate** -- lazy match evaluation, then cost-based block boundaries. The
  encoder builds its own Huffman trees now, which took text from 1.30x `gzip -6`
  to 1.01x, so what is left in the gap is the match search.
- **srcdiff** -- bulk mode: walk the top 1000 PyPI packages and publish an aggregate
  finding with a measured false-positive rate. The xz test is done and it rewrote
  the tool (see below). Next structural gap: vendored files with no canonical copy
  on the host cannot be checked at all, and that is where an xz-shaped file would
  now hide.
- **walkv** -- `dm-log-writes` on the host. Mutation testing is done and it proved
  the point: removing `fsync` **entirely** leaves all 163 scenarios green, because
  the page cache outlives the process. Only a device-level replay can see that.
- **lnk** -- link against glibc. The blockers are known and ordered:
  `R_X86_64_GOTPCRELX`, archive member extraction with a pull-to-fixpoint loop,
  `.init_array`, the linker-defined `_end`/`__bss_start`, `PT_TLS` for `errno`, and
  `R_X86_64_IRELATIVE` for the ifunc `memcpy`.
- **trace** -- `-e` filtering and `-p` attach, then `-T` timing, which is the
  prerequisite for the three-generation overhead table the project exists to make.
- **psh** -- shell functions, then positional parameters and `"$@"`, then the
  `modernish` compliance suite. Here-documents are done, including `<<-` and the
  quoted-delimiter form, at 185 corpus scripts agreeing with `dash`.
- **prof** -- DWARF `.eh_frame` unwinding. Frame pointers are why it cannot profile
  optimised libc.
- **unrepro** -- an `LD_PRELOAD` shim over `readdir` that reverses directory
  order, which is the largest remaining detection gap: a build that globs is
  order-dependent, and on ext4 the order is stable per directory, so the bug is
  invisible on the machine that has it. The no-op-versus-reproduced confusion is
  fixed -- an output is now any file the build *rewrote*, by hash, mtime or
  ctime.
- **vtparse** -- grapheme cluster segmentation, then a `vttest` conformance table
  across xterm/foot/alacritty.
- **jail** -- Landlock network rules; ABI 4 is available on this kernel and
  unused. `--rox` and `--rw-no-exec` are done; `--deny PATH` is next, and has
  to be built out of sibling grants because Landlock has no deny rule.
- **commitq** -- split by hunk rather than by file, so one file touched for two
  reasons becomes two commits.

## What does not work here

About this directory, not the eighteen; each of those has its own list.

- **`INDEX.md` drifts by design.** The commit totals, line totals and per-repo
  test counts below are maintained by hand while `.portfolio/repos.json`
  measures the same things. They were eight commits and two thousand lines out
  of date when this became a repo. Item 06 in `PLAN.md` is to generate them or
  cut them.
- **Only the HTML is checked, not the PDF.** `t/test_portfolio.py` asserts that
  every figure appears in `portfolio.html`, because that is text. The PDF is
  what actually gets sent to anyone, and a stale `portfolio.pdf` sitting next
  to a fresh `portfolio.html` passes everything today.
- **Nothing checks the PDF's geometry.** A colour validator checks colour.
  Three layout bugs -- clipped arrow labels, annotations past the viewBox edge,
  a caption describing arrows that no longer existed -- were found by rendering
  the document and looking at it, and would be found the same way again.
- **Nothing checks the PDF's typography or geometry.** `render.sh` now refuses
  to leave a PDF that is missing or older than the page it came from, and the
  suite reads the figures back out with `pdftotext`, but no check looks at
  where anything sits on the page or which fonts were embedded.
- **A full regeneration takes minutes**, because it runs all eighteen suites.
  `--keep-test-counts` makes it instant by inheriting the previous counts
  instead of measuring them, which is right for the test suite and wrong
  before publishing.
- **The editorial prose is not checked by anything.** Four fields per repo --
  blurb, oracle, invariant, group -- are written by hand and carried across
  regenerations. If one of them stops being true, nothing says so.

## Four things the author got wrong, caught by the work

- **`sqlite3` CLI was assumed installed.** It isn't. Inferred from a permission
  rule instead of checked. `sqlr` substituted python3's binding to the same
  libsqlite3 3.46.1 and documented the substitution everywhere.
- **"Verify all 4096 (state,byte) pairs"** was wrong instruction: the published DEC
  table has **14 states, not 16**. `vtparse` used 3584 and said so rather than
  inflating the denominator.
- **A build-audit script produced false passes.** `git stash -u` does not stash
  *ignored* files, so a stale binary survives `git checkout` and makes `make`
  succeed without recompiling. The real audit removes artifacts before each build.
- **Five hand-computed test expectations were wrong** while the compiler was right,
  every time. That is why `cc/t/addcase.sh` exists: it takes the expected value
  from gcc, cross-checks against clang, and refuses the case if they disagree.

## The pattern: the harness is usually the bug

Across eighteen repos built largely in parallel, the defect was in the *test rig*
far more often than in the code:

- **`inflate`'s ASan target could not fail.** Reject tests assert exit code exactly
  1; ASan also exits 1. Found by deleting the classic `dist > o->n` bounds check
  and watching 146 tests pass while ASan printed a heap overflow to stderr. Fixing
  it revealed every malformed input had been leaking 192KB, invisible for the same
  reason.
- **`dwarfdump` resolved strings against the wrong base** and got back *different
  real strings* -- no error, no marker, plausible output, wrong answer. clang emits
  `DW_AT_name` as `strx1` before declaring `str_offsets_base` on the same DIE.
- **`dwarfdump`'s ASan exit code collided** with its own "malformed input" status,
  so robustness sweeps would have scored a heap overflow as a clean diagnostic.
- **`tarx`'s symlink assertions were vacuous** because `diff -r` dereferences
  links. It also found a real security bug: setuid/setgid/sticky bits restored from
  an untrusted archive, where GNU tar correctly drops them.
- **`walkv`'s torn-write scenarios never crashed.** The fsync boundary called the
  injection hook and discarded its return, so half the matrix reported a perfect
  prefix because it never ran.
- **`walkv` then failed its own mutation test.** Of four planted defects only one
  was caught: the matrix crashed, recovered, verified and *stopped*, so nothing
  ever wrote after a recovery and a subtly-wrong recovery was unobservable. Adding
  that one scenario took it from 83 to 163 and the defect now fails 20.
- **`jail` built a flawless sandbox and applied it to the wrong process** -- the
  rule loop reused the argument parser's index. Every internal invariant held;
  only a real program reporting a real errno could see it.
- **`slab` found gcc deleting its own `calloc` zero-check**, because gcc knows what
  `calloc` promises. Six mutants now prove the oracle has teeth.
- **`wasmi` found zero arithmetic divergences**, so it mutation-tested its own
  suite with 13 injected bugs -- all 13 caught. Then gcc's `-Wsequence-point` found
  what 11,833 green cases could not: undefined behaviour that happened to compile
  the right way.
- **`unrepro` reported REPRODUCIBLE on four repos** because `make` was a no-op.
  Zero outputs is now `inconclusive`. The guard then started firing on the
  *opposite* case, which looks identical from outside: a perfectly reproducible
  build rewrites its products to the bytes already in the tree, so "did anything
  change" answers no and the tool refused to compare the outputs it had just
  rebuilt. An output is now any file the build **rewrote**.
- **`inflate`'s length limiter had never executed.** Dynamic Huffman went in, all
  148 checks passed, and the ratio on the project's own source went from 1.30x to
  1.01x -- and then raising the 15-bit code-length cap to 16 left the suite green,
  as did deleting the limiter outright, because not one of eleven fixtures
  produced a tree deeper than 14 bits. The fixture that forces it had to be
  constructed: Fibonacci frequencies, laid out so every three-byte window in the
  file is unique and LZ77 cannot blur them.
- **`inflate`'s ratio assertion had no opinion about coding.** Its bound was 2x,
  which fixed Huffman codes already met at 1.30x, so it only ever guarded against
  a regression to storing everything.
- **`slab`'s footprint test could not report an improvement.** It read
  `getrusage(RUSAGE_CHILDREN).ru_maxrss` after each child, but that field is the
  maximum over every child already reaped, so running glibc then the preload and
  dividing gave `max(a,b)/a` -- a ratio that can never fall below 1.00. It had
  teeth only in the direction of slab being worse, which is the direction that
  mattered, which is why it survived.
- **`rx`'s unanchored-search implementation broke its own linear-time guarantee**
  by colliding with the generation marks that *are* the guarantee.
- **`prof`'s one-shot `/proc/PID/maps` snapshot raced `ld.so`**, truncating libc
  frames non-deterministically.
- **`lnk` aligned file offset and virtual address independently.** `BASE 0x400000`
  is divisible by every power of two up to 4MB, so they stayed in step by
  arithmetic luck until an 8MB-aligned array broke the congruence. The fix made the
  whole class unemittable rather than merely fixed.

Not one of those was found by re-reading the code.

## The finding that rewrote a tool

`srcdiff`'s whole claim was that it catches the xz-utils shape: code shipped in a
release tarball that was never in git. Every test behind that claim was a
four-file toy project with one planted divergence.

Pointed at the **genuine xz-5.4.5 release tarball** against its **genuine git
tag**, it produced **16 HIGH findings, all false** -- and every one of them was an
`m4/*.m4` file present in the tarball and absent from git. Which is the exact
shape of the attack. The real signal would have been one line in seventeen.

The cause is structural and was invisible from the toy fixtures: `libtoolize` and
`gettextize` vendor those macros in **from the build host**, so the project's
repository is the wrong oracle for them. And no name-based allowlist can fix it,
because **`build-to-host.m4` is a legitimate gettext macro** -- it ships at
`/usr/share/aclocal/build-to-host.m4` on any machine with gettext installed. The
attacker didn't invent a filename; they shipped a modified copy of a real one.
That is why it survived review.

The fix is a second oracle: compare vendored files against the canonical copy on
the build host, and use the in-band version marker (`serial`, `scriptversion`,
`timestamp`, `VERSION`) to decide what a difference means. Different marker means
a different upstream release and is suppressed; **same marker with different bytes
means the file claims to be a revision it is not** -- a file modified in place does
not advertise itself as a new release.

16 false positives down to 1, and an injected `build-to-host.m4` with its serial intact
is reported immediately. One false positive is left in deliberately: `nls.m4`,
where upstream reflowed a comment without bumping the serial. A normalisation
broad enough to absorb that would also absorb an injected comment block.

The compromised 5.6.1 tarball is unobtainable -- Debian's archive carries only
`5.6.1+really5.4.5-1`, their revert -- so the test reproduces the *technique*
against a clean release and says so. Detection keys on provenance, never on
recognising a payload.

## The loop that closed

`unrepro`, built in this same batch, found that eight sibling repos were not
reproducible: `cc`, `walkv`, `rx`, `trace`, `dwarfdump`, `lnk`, `prof`, `vtparse`.
Cause in every case `build-path` -- `-g` writes the compiler's working directory
into DWARF `.debug_line_str`, and the section grew by exactly the difference in
path length. It named the byte offset, the section, and the fix.

The correlation was exact: **every repo compiling with `-g` was irreproducible,
every repo without it was already clean.** That is independent confirmation the
cause is DWARF path embedding rather than a plausible-looking guess.

`-ffile-prefix-map=$(CURDIR)=.` fixes all eight. `prof` needed it twice -- once on
`CFLAGS` and once on `TCFLAGS`, which builds the frame-pointer workload -- and only
a tool reporting *per output* rather than per repo made the remaining half visible.

All 18 now report `REPRODUCIBLE across all varied conditions`.

## Backups

```
/home/x/projects-SNAPSHOT-FINAL/     full tar + per-repo bundles
/home/x/projects-SNAPSHOT-2352/
/home/x/projects-backup-20261005-2336/
```

Restore any repo: `git clone /home/x/projects-SNAPSHOT-FINAL/bundles/jail.bundle jail`

`/tmp` on this machine is **tmpfs** and does not survive a reboot. `wasmi/hist/`
was rescued from it -- the generator that built that repo's 28-commit history, which
would otherwise have been lost.
