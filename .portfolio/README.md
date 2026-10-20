# portfolio

Generates `portfolio.pdf` from the repositories themselves.

    read -rp 'name:   ' NAME
    read -rp 'handle: ' GITHUB
    NAME="$NAME" GITHUB="$GITHUB" ./render.sh

The values go through `read` instead of being written into the line, because
this file used to show them inline and `build.py` would print whatever it was
given onto the cover. Example text now resolves to empty and gets the red
"[ your name ]" block instead, so a forgotten value is loud,
not plausible, but a line that cannot be pasted wrongly beats a line that is
caught after being pasted wrongly.

`repos.json` is extracted from the repos, commit counts from `git`, line counts
from tracked files, test counts from actually running each suite, so the
document cannot drift from the work it describes. Regenerate it with:

    make portfolio

That takes about half an hour, because it runs all thirty-eight suites; `wasmi` alone is
about three. It is a separate script from `build.py` for exactly that reason.

Four fields per repo are editorial: `blurb`, `oracle`, `invariant`, `group`,
and are read back out of the existing `repos.json`, because no measurement
produces a sentence. A repo with a `PLAN.md` and no editorial text is an error,
not a silent omission, and so is an entry describing a repo that is no
longer there.

It had drifted anyway, because this script was documented and did not exist.
The claim above was true of the design and false of the artifact. Its shipped PDF carried 38 stale values, including test counts from five suites that had
since grown and a commit total six behind. Two of the stale figures were not
merely old but wrong in a way no edit would have caught, because they came from
walking the tree instead of asking `git`:

- `lnk` was credited with 2,873 test lines. 2,456 of those were
  `t/tmp.pages.c`, a generated file that is gitignored and was never part of
  the repo.
- `psh` was credited with 63, which was `t/run.sh` alone: the 208-script
  corpus that the harness actually runs did not count at all.

Totals went *down* as a result, from 11,503 test lines to 8,732. A number that
only ever moves up is worth being suspicious of.

## Decisions worth knowing

Fonts are local only. Headless chromium has no network, so a webfont would
silently fall back and the PDF would not match the design. Noto Serif Condensed /
Noto Serif / Hack are all installed here and embed correctly, and the audit now
reads the font table out of the finished PDF on every run rather than leaving
that confirmation in somebody's shell history.

It checks three things, because the interesting failure is not the obvious one.
A face falling out of the design entirely shows up as a stranger in the table --
Liberation, DejaVu, whatever fontconfig offers next. But if Noto Serif Condensed
stops being installed, chromium falls back down the CSS stack to plain Noto
Serif, which is itself one of the three, so forbidding strangers would pass
while every heading had quietly lost its width. So each of the three faces must
be PRESENT, not merely permitted. The third check is that each is embedded; the
first version of it accepted a font that was not, because it tested whether any
of the emb/sub/uni columns said yes rather than the one that matters.

Both substitutions are produced for real in the suite, by rendering throwaway
pages through the same chromium and reading them with the same pdffonts. A
check against a silent failure is worth very little if nobody has watched it
go red.

The two data-fill colours were validated, not chosen by eye. `#0E8F85` and
`#A1551D` pass all six checks against the paper surface (CVD Delta-E 12.6,
normal-vision Delta-E 21.0). The darker brand teal `#0A6B6B` is used for type and rules
only. As a data fill it FAILS the chroma floor at 0.079 and reads gray. That is
exactly the kind of thing you cannot eyeball.

Three layout bugs were found by rendering the PDF and looking at it, not by
reading the source: arrow labels clipping into the boxes they sat between, map
annotations running past the right edge of the viewBox, and a caption describing
dashed arrows that no longer existed. A colour validator checks colour; nothing
checks geometry except your eyes.
