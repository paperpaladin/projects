# The portfolio site

One self-contained page: `index.html`. No build step, no assets, no
dependencies. Open it in a browser and that is the whole thing.

## Before it goes anywhere public

1. Replace the name. The first line of `<header>` is a placeholder and is
   styled in the alert colour so it cannot be missed:

   ```html
   <div class="who ph">[ your name -- replace this line before publishing ]</div>
   ```

   Put your own name in it and drop the `ph` class. The class is what turns
   off the red. Deliberately not written out here as a line to copy: the one
   time this collection handed out a fill-in-the-blank command, the blank was
   pasted unfilled and rewrote 721 commits.

2. Run `../../cq id`: values through `read` first, never inline, if
   you have not already. Every commit in every repo
   still carries `PLACEHOLDER <placeholder@invalid>`, and the site invites people
   to clone and run the suites. See the root `METHOD.md`.

## Hosting it

GitHub Pages is the shortest path and costs nothing:

```sh
# in a repo named <username>.github.io
cp index.html .
git add index.html && git commit -m "portfolio" && git push
```

It is live at `https://<username>.github.io` within a minute or two. Any static
host works the same way; the page loads nothing from anywhere except Google
Fonts, and degrades to Georgia and a system grotesque if that is blocked.

## What it claims, and where each claim comes from

Every number on the page was taken from a suite run or a commit message in
these repos, not written by hand. If you change a repo, re-check the page:

| Claim on the page | Where it comes from |
|---|---|
| srcdiff 473 lines, 25 tests | `wc -l srcdiff/srcdiff.py`, `make -C srcdiff test` |
| jail 596 lines, 77 tests | `wc -l jail/jail.c`, `make -C jail test` |
| tarx 1,181 lines, 118 tests | `wc -l tarx/tarx.c`, `make -C tarx test` |
| 16 false positives -> 1, 687 files | srcdiff commit `609ad6c` |
| 15 malicious archives | the `EVILS` set in `tarx/t/run.sh` |
| eight assertions, zero passing | jail commits `3a7718b` and `a92f34f` |
| inflate: 146 passing, 192KB leaked | inflate's ASan commit |
| httpd: two of ten cases | httpd's curl `--path-as-is` commit |
| sha2: 54 red, 1 of 65 | sha2's mutation commit |
| walkv: 83 -> 163, fails 20 | walkv commit `4b89a9b` |
| pngc: 71 checks green | pngc's 16-bit sample commit |
| the `make mutants` transcript | verbatim from `make -C walkv mutants` |

The one thing on the page that is not a transcript is the finding list in the
opening exhibit: the fixtures in `srcdiff/t/` are a trimmed 39-file corpus, so
the four filenames shown are real vendored macros from that set but the "16
HIGH findings" count is from the full upstream tarball, as recorded in the
commit. Everything else can be reproduced by running the command next to it.
