# PLAN

## Contract

This repository is what sits above the eighteen: `INDEX.md` as the entry point,
`METHOD.md` as the working instructions, `cq` as the wrapper around `commitq`,
and `.portfolio/` as the generator that renders all eighteen into one PDF.

`.portfolio/extract.py` writes `repos.json` by measuring the repositories --
commit counts from `git`, line counts from tracked files, plan counts from each
`PLAN.md`, test counts from actually running each suite. `.portfolio/build.py`
turns that into `portfolio.html` and `render.sh` prints it to PDF with headless
chromium. Four fields per repo are editorial and are carried across
regenerations, because no measurement produces a sentence.

The eighteen stay independent repositories. They are listed by name in
`.gitignore` and nothing here tracks them, vendors them, or makes them
submodules.

## Hard invariant

**No figure in the published document is anything other than what the
repositories currently say.**

When the document and the work disagree, the document is wrong. This is the
only property here worth a test, and it is the one that failed: the README
documented `extract.py`, `extract.py` did not exist, and the shipped PDF
carried 38 stale values -- test counts from five suites that had since grown, a
commit total six behind, and two line counts that had never been right at all
because they came from walking the tree instead of asking `git`.

A document about verified work that is itself unverified is worse than no
document, because it borrows the credibility of the thing it misreports.

## Oracle

Ranked by how little this repo controls them, most independent first:

1. **`git`.** Commit counts come from `rev-list --count`, and the suite asserts
   that every number in `repos.json` still equals what `git` says. Nothing here
   gets a vote on that.
2. **The eighteen suites, run.** The test counts in the document are the last
   line each suite prints, captured by running it. A suite that fails or is
   missing lands in the field as `FAILING:` or `NO SUITE` rather than as a
   number that reads like a pass, and the suite here refuses to accept either
   in a document.
3. **`git ls-files`.** Line counts cover tracked files only. Walking the tree
   instead is what credited `lnk` with 2,873 test lines, 2,456 of which were a
   gitignored generated file.
4. **The generated page.** Every per-repo figure must appear in
   `portfolio.html`, so a `build.py` that drops a field fails rather than
   rendering a document that merely came from good data. Deleting one field
   turns 18 assertions red.
5. **Throwaway repos in a tempdir.** The extractor's refusals -- a member repo
   with no editorial text, an editorial entry whose repo is gone, an ignored
   file, a `hist/` snapshot -- are driven against repos built for the purpose,
   so no test mutates one of the eighteen. Same method as `commitq`'s own
   suite.
6. **Itself, twice.** Two runs must agree byte for byte, and the `repos.json`
   checked in must equal what `extract.py` produces right now. That last one
   is the catch-all: any drift at all, from any cause, turns it red.

## Non-goals

- **Being one of the eighteen.** Those are programs measured against
  authorities outside the author. A document has no such authority for its
  prose, and pretending otherwise would be the exact dishonesty the method
  exists to avoid. Only its *figures* are checkable, and those are checked.
- Tracking the eighteen as submodules, subtrees, or a monorepo.
- Generating the editorial text. `blurb`, `oracle`, `invariant` and `group` are
  written by hand and preserved across regeneration.
- A web site, a CI pipeline, hosting, or a deploy step.
- Webfonts. Headless chromium has no network, so a webfont falls back silently
  and the PDF stops matching the design. Fonts are local only.
- Being fast. A full regeneration runs all eighteen suites and takes minutes.
  `--keep-test-counts` is for the test suite, not for publishing.

## Commit sequence

- [x] 01 the repo itself: `.gitignore` naming the eighteen, the working
      instructions, the index, the `cq` wrapper, the portfolio generator, and
      `extract.py`, which had been documented without existing.
      why: everything above the eighteen was tracked by nothing. `commitq`
      only ever looked *downward* from the root for repos, so the root itself
      was invisible to the tool that gates every other commit here -- which is
      also why nobody noticed. The first commit has to be the one that makes
      the rest reviewable.
- [ ] 02 assert the figures in `portfolio.pdf`, not only in `portfolio.html`
      why: the suite checks the HTML because that is text. The PDF is what gets
      sent to anyone, and nothing currently proves the two agree -- a stale
      `portfolio.pdf` next to a fresh `portfolio.html` passes everything today.
      `pdftotext` is installed and already used by hand to spot-check it.
- [ ] 03 make `render.sh` refuse to leave a PDF older than its HTML
      why: the failure above is reachable by a chromium crash, and chromium
      exits 0 on some of them. The check is a timestamp comparison; the point
      is that a half-finished render must not look like a finished one.
- [ ] 04 verify the embedded fonts are the three intended faces
      why: the README says the fonts were confirmed by reading the font table
      out of the finished PDF, and that confirmation lives in shell history. If
      a face stops being installed the render silently substitutes and the
      document's typography is no longer the one that was designed.
- [ ] 05 a geometry check, or an honest statement that there is not one
      why: three layout bugs were found by rendering the PDF and looking at it.
      The colour validator checks colour and nothing checks geometry. Either
      something can assert that no text box overflows its frame, or the README
      should stop implying the document is checked when that part is eyeballed.
- [ ] 06 fold `INDEX.md`'s hand-maintained figures into the generated ones
      why: `INDEX.md` repeats commit totals, line totals and per-repo test
      counts that `repos.json` already measures, which means it drifts by
      design -- it was eight commits and two thousand lines out when this repo
      was created. Either generate that table or cut the numbers from it.
- [ ] 07 a `cq`-visible staleness warning when `repos.json` is behind `git`
      why: the suite catches it, but only when run. `cq` already prints a
      nudge when nothing was committed today; the document being behind the
      work is the same shape of problem and belongs in the same place.
