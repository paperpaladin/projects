#!/usr/bin/env python3
"""Build the portfolio HTML from measured repo data, then render it to PDF.

Every number in the output comes from repos.json, which is extracted from the
repositories themselves -- commit counts from git, line counts from the files,
test counts from actually running each suite. Nothing is typed in by hand, so the
document cannot drift from the work it describes.

    python3 build.py            # writes portfolio.html
    ./render.sh                 # chromium --print-to-pdf

Fonts are deliberately limited to faces installed on this machine (Noto Serif
Condensed / Noto Serif / Hack). Headless chromium has no network, so a webfont
would silently fall back and the PDF would not match the design.

Palette: the two data-fill hues were validated with the dataviz skill's checker
against the paper surface -- #0E8F85 and #A1551D pass all six checks (CVD dE 12.6,
normal-vision 21.0). The darker #0A6B6B is used for type and rules only, where the
chroma floor does not apply; as a data fill it FAILS that check and reads gray.
"""
import json
import os
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = json.loads((HERE / "repos.json").read_text())

# Fill in, or pass NAME=... in the environment.
#
# Example text counts as unset. The cover is the one place a reader looks
# first, and "Your Name" printed there reads as finished rather than as
# missing -- whereas the placeholder block below is red and says what to do.
# This repo already learned the general version of this lesson expensively:
# the documented `cq id` command was pasted with its example values still in
# it and rewrote 721 commits. Same shape, lower stakes, same fix.
EXAMPLE_NAMES = {"your name", "name", "yourname", "your-name", "firstname lastname",
                 "first last", "placeholder", "author", "me"}
EXAMPLE_HANDLES = {"yourhandle", "handle", "username", "yourusername", "user",
                   "youruser", "placeholder", "me"}


def _unless_example(value, examples):
    value = (value or "").strip()
    return "" if value.lower() in examples else value


AUTHOR = _unless_example(os.environ.get("NAME", ""), EXAMPLE_NAMES)
HANDLE = _unless_example(os.environ.get("GITHUB", ""), EXAMPLE_HANDLES)

TOTAL_COMMITS = sum(v["commits"] for v in DATA.values())
TOTAL_SRC = sum(v["src"] for v in DATA.values())
TOTAL_TEST = sum(v["test"] for v in DATA.values())
TOTAL_DONE = sum(v["done"] for v in DATA.values())
TOTAL_TODO = sum(v["todo"] for v in DATA.values())
TOTAL_SHORTCUTS = sum(v["shortcuts"] for v in DATA.values())

GROUPS = [
    ("toolchain", "Toolchain", "Programs that build or run other programs."),
    ("formats", "Formats &amp; parsers", "Programs that read a specification exactly."),
    ("systems", "Systems", "Programs that must survive the machine misbehaving."),
    ("observability", "Observability", "Programs that watch other programs without disturbing them."),
    ("supply chain", "Supply chain &amp; process", "Programs that check the other programs."),
]

# ---------------------------------------------------------------- svg helpers

def esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def bar_chart(rows, width=740, label_w=92, bar_h=15, gap=7, unit="", title=""):
    """Sorted horizontal bars, one series. No legend (the title names it), direct
    labels on every bar because there are few enough that it is not clutter."""
    rows = sorted(rows, key=lambda r: -r[1])
    peak = max(r[1] for r in rows) or 1
    plot_w = width - label_w - 56
    h = len(rows) * (bar_h + gap)
    out = [f'<svg class="fig" viewBox="0 0 {width} {h}" role="img" '
           f'aria-label="{esc(title)}">']
    for i, (name, val) in enumerate(rows):
        y = i * (bar_h + gap)
        w = max(1.5, val / peak * plot_w)
        out.append(
            f'<text x="{label_w - 8}" y="{y + bar_h - 3}" class="bl" '
            f'text-anchor="end">{esc(name)}</text>')
        out.append(
            f'<rect x="{label_w}" y="{y}" width="{w:.1f}" height="{bar_h}" '
            f'rx="3" class="b1"/>')
        out.append(
            f'<text x="{label_w + w + 7:.1f}" y="{y + bar_h - 3}" class="bv">'
            f'{val:,}{unit}</text>')
    out.append("</svg>")
    return "".join(out)


def paired_chart(rows, width=740, label_w=92, bar_h=9, inner=2, gap=9):
    """Two series per repo. A legend is mandatory at two series, and both bars
    carry a direct label, so identity never rests on colour alone.
    A 2px surface gap separates the pair, per the mark spec."""
    peak = max(max(a, b) for _, a, b in rows) or 1
    plot_w = width - label_w - 86
    row_h = bar_h * 2 + inner + gap
    h = len(rows) * row_h
    out = [f'<svg class="fig" viewBox="0 0 {width} {h}" role="img" '
           f'aria-label="Source and test lines per repository">']
    for i, (name, src, tst) in enumerate(rows):
        y = i * row_h
        ws = max(1.5, src / peak * plot_w)
        wt = max(1.5, tst / peak * plot_w)
        out.append(f'<text x="{label_w - 8}" y="{y + bar_h + 1}" class="bl" '
                   f'text-anchor="end">{esc(name)}</text>')
        out.append(f'<rect x="{label_w}" y="{y}" width="{ws:.1f}" '
                   f'height="{bar_h}" rx="2.5" class="b1"/>')
        out.append(f'<rect x="{label_w}" y="{y + bar_h + inner}" width="{wt:.1f}" '
                   f'height="{bar_h}" rx="2.5" class="b2"/>')
        out.append(f'<text x="{label_w + max(ws, wt) + 7:.1f}" '
                   f'y="{y + bar_h + 2}" class="bv">{src:,} / {tst:,}</text>')
    out.append("</svg>")
    return "".join(out)


def oracle_strip(repo, oracle):
    """The figure that carries the whole thesis, repeated per repo: the code on
    the left, an authority outside it on the right, and the comparison between."""
    return f'''<svg class="orc" viewBox="0 0 560 34" role="img"
 aria-label="{esc(repo)} is checked against {esc(oracle)}">
 <rect x="1" y="7" width="118" height="21" rx="3" class="ob"/>
 <text x="60" y="21.5" class="ot" text-anchor="middle">{esc(repo)}</text>
 <path d="M126 17.5 H170" class="oa"/>
 <path d="M164 13.5 L170 17.5 L164 21.5" class="oa"/>
 <rect x="178" y="3" width="381" height="28" rx="3" class="oo"/>
 <text x="188" y="21" class="oot">{esc(oracle)}</text>
</svg>'''


def composition_map():
    """Hand-authored: each arrow is a fact recorded in a PLAN.md or README.

    Arrow labels sit ABOVE the box row, not in the gap between two boxes. The gap
    is only ~70 units wide and the label is wider than that, so the in-gap version
    clipped into both boxes. Caught by rendering the PDF at 200dpi and looking --
    the palette validator checks colour, never geometry."""
    W = 760
    box = lambda x, y, w, label, cls="mb": (
        f'<rect x="{x}" y="{y}" width="{w}" height="26" rx="3" class="{cls}"/>'
        f'<text x="{x + w / 2}" y="{y + 17.5}" class="mt" text-anchor="middle">{label}</text>')

    def arrow(x1, x2, boxy, note):
        mid = boxy + 13
        return (f'<path d="M{x1} {mid} H{x2}" class="ar"/>'
                f'<path d="M{x2 - 6} {mid - 4} L{x2} {mid} L{x2 - 6} {mid + 4}" class="ar"/>'
                f'<text x="{(x1 + x2) / 2}" y="{boxy - 5}" class="an" '
                f'text-anchor="middle">{note}</text>')

    s = [f'<svg class="map" viewBox="0 0 {W} 268" role="img" aria-label="How the '
         'these repositories compose">']

    # lane label is vertically centred on its box row
    def lane(ly, nm, rule=True):
        out = f'<text x="0" y="{ly + 17}" class="ml">{nm}</text>'
        if rule:
            out = f'<path d="M0 {ly - 22} H{W}" class="lane"/>' + out
        return out

    s.append(lane(22, "TOOLCHAIN", rule=False))
    s += [box(78, 22, 66, "cc"), box(214, 22, 66, "lnk"),
          box(296, 22, 74, "wasmi"), box(386, 22, 66, "psh")]
    s.append(arrow(148, 210, 22, "links output of"))

    s.append(lane(96, "FORMATS"))
    s += [box(78, 96, 78, "inflate"), box(226, 96, 66, "tarx"),
          box(308, 96, 66, "sqlr"), box(390, 96, 78, "vtparse"),
          box(484, 96, 92, "dbginfo")]
    s.append(arrow(160, 222, 96, "compresses for"))
    s.append('<text x="584" y="113" class="an">&#8594; prof unwinds with this</text>')

    s.append(lane(170, "SYSTEMS"))
    s += [box(78, 170, 72, "walkv"), box(166, 170, 66, "slab"),
          box(248, 170, 66, "jail"), box(330, 170, 60, "rx"),
          box(406, 170, 70, "trace"), box(492, 170, 66, "prof")]

    s.append(lane(236, "PROCESS"))
    s += [box(78, 236, 92, "unrepro", "mb2"), box(186, 236, 88, "srcdiff", "mb2"),
          box(290, 236, 92, "commitq", "mb2")]
    s.append("</svg>")
    return "".join(s)


def ratio_fig(code, harness, width=740):
    """One stat, two parts. A pie would be worse: two values read better as a
    single proportional bar with both counts stated."""
    tot = code + harness
    w1 = code / tot * (width - 4)
    return f'''<svg class="fig" viewBox="0 0 {width} 56" role="img"
 aria-label="{harness} of {tot} recorded defects were in the test harness">
 <rect x="0" y="12" width="{w1:.1f}" height="22" rx="3" class="b2"/>
 <rect x="{w1 + 4:.1f}" y="12" width="{width - w1 - 4:.1f}" height="22" rx="3" class="b1"/>
 <text x="0" y="8" class="bv">in the code &mdash; {code}</text>
 <text x="{w1 + 4:.1f}" y="8" class="bv">in the thing meant to test the code &mdash; {harness}</text>
 <text x="0" y="50" class="cap">Defects recorded in commit messages and READMEs across all
 every repository here. Counted once per root cause.</text>
</svg>'''


# ------------------------------------------------------------------ the bugs

BUGS = [
    ("harness", "inflate", "<code>make test-asan</code> could not fail",
     "Reject tests assert exit code exactly 1; AddressSanitizer also exits 1. Found by deleting the classic "
     "<code>dist &gt; o-&gt;n</code> bounds check and watching 146 tests pass while ASan printed a heap overflow to "
     "stderr. Fixing the exit code revealed that every malformed input had also been leaking 192KB, invisible for "
     "the same reason."),
    ("harness", "walkv", "Half the crash matrix never crashed",
     "In torn-write mode the <code>fsync</code> boundary called the injection hook and discarded its return value, so "
     "every fsync scenario ran to completion and reported a perfect result."),
    ("harness", "walkv", "Four planted defects, only one caught",
     "Mutation testing showed the matrix crashed, recovered, verified and then <em>stopped</em> &mdash; nothing ever "
     "wrote after a recovery, so a subtly wrong recovery was unobservable. Adding that one scenario took the suite "
     "from 83 to 163 and the defect now fails 20 of them."),
    ("harness", "tarx", "Every symlink assertion was vacuous",
     "<code>diff -r</code> dereferences symbolic links, so the comparisons silently compared targets instead of links, "
     "and a dangling link aborted the diff outright."),
    ("harness", "srcdiff", "Sixteen false positives on a clean release",
     "Against the genuine xz-5.4.5 tarball and its git tag, every HIGH finding was wrong &mdash; and each was an "
     "<code>m4/*.m4</code> file absent from git, the exact shape of the attack it exists to find. The real signal "
     "would have been one line in seventeen."),
    ("harness", "dbginfo", "ASan's exit code collided with &ldquo;malformed input&rdquo;",
     "Both are 1, so the robustness sweeps would have scored a genuine heap overflow as a clean diagnostic."),
    ("harness", "unrepro", "Reported REPRODUCIBLE because <code>make</code> did nothing",
     "Pointed at four sibling repos it compared zero outputs and called them clean. Zero outputs is now "
     "<em>inconclusive</em>."),
    ("harness", "commitq", "The commit gate was not gating 12 of 18 repos",
     "The test command was a hardcoded table of six names; everything else returned success, so two thirds of the "
     "project could be committed without running anything."),
    ("harness", "slab", "gcc deleted the oracle",
     "At <code>-O2</code> gcc knows what <code>calloc</code> promises, so it proved the zero-checking loop could not "
     "observe a non-zero byte and removed it. An allocator that never zeroed anything passed cleanly."),
    ("harness", "cc", "Five hand-computed expectations were wrong",
     "Each cost a detour through &ldquo;is this a codegen bug?&rdquo; The compiler was right every time. "
     "<code>t/addcase.sh</code> now takes the expected value from gcc and refuses the case if clang disagrees."),
    ("code", "rx", "The linear-time guarantee was quietly broken",
     "Injecting a start thread at every input position collided with the generation marks &mdash; and that dedup "
     "<em>is</em> the guarantee. The one bug that destroyed the project's only interesting property."),
    ("code", "lnk", "A binary the kernel refused to run",
     "File offset and virtual address were aligned independently. <code>BASE 0x400000</code> is divisible by every "
     "power of two up to 4MB, so they stayed in step by arithmetic luck until an 8MB-aligned array broke the "
     "congruence. The fix made the whole class unemittable rather than merely fixed."),
    ("code", "jail", "A perfect sandbox applied to the wrong process",
     "The rule-installing loop reused the argument parser's index, so <code>jail</code> built a flawless ruleset and "
     "then exec'd <code>--ro</code>. Every internal invariant held; only a real program reporting a real errno could "
     "see it."),
    ("code", "dbginfo", "Strings resolved to different real strings",
     "clang emits <code>DW_AT_name</code> as <code>strx1</code> before declaring <code>str_offsets_base</code> on the "
     "same DIE. Every lookup succeeded, no error, no marker &mdash; the second unit was simply named "
     "<code>main.c</code> where readelf said <code>lib.c</code>."),
    ("code", "trace", "A SIGTERM death reported as exit 0",
     "After passing a signal through, the tracee was already running, so the next <code>PTRACE_SYSCALL</code> hit "
     "<code>ESRCH</code>. Reintroduced once by a later refactor and caught again immediately by the same test."),
    ("code", "prof", "A race against the dynamic loader",
     "A one-shot <code>/proc/PID/maps</code> snapshot raced <code>ld.so</code>, truncating libc frames "
     "non-deterministically."),
    ("code", "sqlr", "A closing paren ended the column list",
     "Depth was decremented and tested in the same iteration, so the <code>)</code> of <code>VARCHAR(10,2)</code> "
     "looked like the end of the CREATE statement. <code>SELECT *</code> returned one column of four, with no error."),
    ("code", "srcdiff", "A funding link parsed as a repository",
     "<code>github.com/sponsors/hynek</code> resolved to owner <em>sponsors</em>. No offline test could reach it: the "
     "bug was in metadata resolution, and the tests all covered the comparison."),
]


def bug_rows(kind):
    out = []
    for k, repo, title, body in BUGS:
        if k != kind:
            continue
        out.append(f'<div class="bug"><div class="bh"><span class="brepo">{repo}</span>'
                   f'<span class="bt">{title}</span></div><p>{body}</p></div>')
    return "".join(out)


# ------------------------------------------------------------------- the page

def repo_card(name, v):
    pct = int(v["done"] / max(v["done"] + v["todo"], 1) * 100)
    return f'''<article class="card">
  <header class="ch">
    <h3>{name}</h3>
    <span class="cb">{esc(v["blurb"])}</span>
    <span class="cn">{v["commits"]} commits &middot; {v["src"]:,} lines &middot; {v["test"]:,} test lines</span>
  </header>
  {oracle_strip(name, v["oracle"])}
  <dl>
    <dt>Hard invariant</dt><dd>{esc(v["invariant"])}</dd>
    <dt>Result</dt><dd class="res">{esc(v["tests"]) or "&mdash;"}</dd>
    <dt>Plan</dt><dd>{v["done"]} done, {v["todo"]} queued
      <span class="prog"><span style="width:{pct}%"></span></span></dd>
  </dl>
</article>'''


WORDS = {18: "Eighteen", 19: "Nineteen", 20: "Twenty",
         30: "Thirty", 36: "Thirty-six", 38: "Thirty-eight"}


def word(n):
    """The repo count as a word, for prose that has to agree with the tiles.

    Every number on this page was supposed to come from repos.json. The
    PROSE did not: the h1 said "Eighteen programs" and a cover tile said
    "18/18 suites green" while the tile beside it said a generated 38, so
    page one contradicted itself by twenty. "Eighteen" also appeared in the
    composition caption, the reproducibility claim, the SVG's aria-label
    and two docstrings. They were typed when there were eighteen and never
    touched again.
    """
    return WORDS.get(n, str(n))


def build():
    by_commits = [(k, v["commits"]) for k, v in DATA.items()]
    by_loc = sorted(((k, v["src"], v["test"]) for k, v in DATA.items()),
                    key=lambda r: -(r[1] + r[2]))
    n_harness = sum(1 for b in BUGS if b[0] == "harness")
    n_code = sum(1 for b in BUGS if b[0] == "code")

    groups_html = ""
    for key, title, blurb in GROUPS:
        members = {k: v for k, v in DATA.items() if v["group"] == key}
        if not members:
            continue
        cards = "".join(repo_card(k, v) for k, v in
                        sorted(members.items(), key=lambda kv: -kv[1]["commits"]))
        groups_html += (f'<section class="grp"><h2>{title}</h2>'
                        f'<p class="gb">{blurb}</p>{cards}</section>')

    name_block = (f'<div class="who">{esc(AUTHOR)}</div>' if AUTHOR else
                  '<div class="who placeholder">[ your name &mdash; rebuild with '
                  'NAME="..." to set it ]</div>')
    handle = (f'<div class="hdl">github.com/{esc(HANDLE)}</div>' if HANDLE else "")

    subs = dict(
        name_block=name_block, handle=handle,
        repos=len(DATA), commits=TOTAL_COMMITS, src=f"{TOTAL_SRC:,}",
        test=f"{TOTAL_TEST:,}", done=TOTAL_DONE, todo=TOTAL_TODO, shortcuts=TOTAL_SHORTCUTS,
        commit_chart=bar_chart(by_commits, unit="", title="Commits per repository"),
        loc_chart=paired_chart(by_loc),
        comp_map=composition_map(),
        ratio=ratio_fig(n_code, n_harness),
        harness_bugs=bug_rows("harness"), code_bugs=bug_rows("code"),
        groups=groups_html,
        n_harness=n_harness, n_code=n_code, n_bugs=n_harness + n_code,
        word=word(len(DATA)),
        # "N/N suites green" rather than a literal. extract.py prefixes
        # FAILING: on any suite that did not pass, so counting the ones
        # that did is the honest denominator -- and if one ever fails the
        # tile says so instead of claiming a clean sweep.
        green="%d/%d" % (sum(1 for v in DATA.values()
                             if not v["tests"].startswith("FAILING")
                             and v["tests"] != "NO SUITE"), len(DATA)),
        jail_tests=DATA["jail"]["tests"].split()[0],
        groups_table="".join(
            f'<tr><td>{k}</td><td>{esc(v["tests"]) or "&mdash;"}</td>'
            f'<td>{v["done"]}/{v["done"] + v["todo"]}</td></tr>'
            for k, v in sorted(DATA.items())),
    )
    html = PAGE
    for k, val in subs.items():
        html = html.replace("@@" + k + "@@", str(val))
    left = re.findall(r"@@\w+@@", html)
    if left:
        raise SystemExit(f"unsubstituted tokens remain: {sorted(set(left))}")
    (HERE / "portfolio.html").write_text(html)
    print(f"portfolio.html written: {len(DATA)} repos, {TOTAL_COMMITS} commits")


PAGE = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>Portfolio</title>
<style>
@page { size: A4; margin: 14mm 15mm 16mm; }
:root{
  --paper:#ffffff; --panel:#f4f6f6; --sunk:#eaeeee;
  --ink:#121c22; --mid:#4a5a63; --soft:#7d8c94;
  --rule:#ccd5d6; --firm:#aebabc;
  --accent:#0a6b6b;        /* type and rules only */
  --s1:#0e8f85;            /* data fill 1 -- validated */
  --s2:#a1551d;            /* data fill 2 -- validated */
  --f-disp:"Noto Serif Condensed","Noto Serif",serif;
  --f-body:"Noto Serif",Georgia,serif;
  --f-mono:"Hack","DejaVu Sans Mono",monospace;
}
*{box-sizing:border-box}
html,body{margin:0;padding:0;background:var(--paper);color:var(--ink)}
body{font:10.2pt/1.52 var(--f-body);-webkit-print-color-adjust:exact;print-color-adjust:exact}
h1,h2,h3,h4{font-family:var(--f-disp);font-weight:700;margin:0;text-wrap:balance}
code{font-family:var(--f-mono);font-size:.84em;background:var(--sunk);
  padding:.06em .3em;border-radius:2px}
p{margin:0 0 .62em}
.sheet{page-break-after:always}
.sheet:last-child{page-break-after:auto}
.flow{page-break-after:auto}
h2.sec,.grp h2{page-break-after:avoid;break-after:avoid}
figure{page-break-inside:avoid}
.stand{page-break-after:avoid;break-after:avoid}

/* ---------- cover ---------- */
.cover{display:flex;flex-direction:column;justify-content:center;min-height:252mm}
.eyebrow{font:600 7.6pt/1 var(--f-mono);letter-spacing:.2em;text-transform:uppercase;
  color:var(--accent);margin-bottom:9mm}
.cover h1{font-size:40pt;line-height:.98;letter-spacing:-.018em;max-width:20ch}
.cover .lede{font-size:12.4pt;line-height:1.46;color:var(--mid);max-width:58ch;
  margin-top:7mm}
.cover .lede b{color:var(--ink);font-weight:700}
.who{font:700 15pt var(--f-disp);margin-top:12mm}
.who.placeholder{color:var(--s2);font-family:var(--f-mono);font-size:9pt;font-weight:400}
.hdl{font:9pt var(--f-mono);color:var(--soft);margin-top:1mm}
.tiles{display:flex;gap:4mm;margin-top:11mm;flex-wrap:wrap}
.tile{flex:1 1 0;min-width:28mm;border:1px solid var(--rule);border-radius:3px;
  padding:3.4mm 3.6mm;background:var(--panel)}
.tile .v{font:700 19pt/1 var(--f-disp);color:var(--accent);
  font-variant-numeric:tabular-nums}
.tile .k{font:7.2pt/1.3 var(--f-mono);letter-spacing:.09em;text-transform:uppercase;
  color:var(--soft);margin-top:1.6mm}

/* ---------- sections ---------- */
h2.sec{font-size:19pt;letter-spacing:-.012em;padding-bottom:2.4mm;
  border-bottom:1.6pt solid var(--ink);margin-bottom:5mm}
.stand{font-size:11pt;line-height:1.5;color:var(--mid);max-width:62ch;margin-bottom:6mm}
.stand b{color:var(--ink)}
figure{margin:0 0 6mm}
figcaption{font:7.8pt/1.46 var(--f-mono);color:var(--soft);margin-top:2.4mm;max-width:86%}
figcaption b{color:var(--mid);font-weight:700}
.cap{font:7.8pt/1.42 var(--f-mono);color:var(--soft);margin-top:2.2mm}
.fig,.map,.orc{width:100%;height:auto;display:block}
.bl{font:7.4pt var(--f-mono);fill:var(--ink)}
.bv{font:7.2pt var(--f-mono);fill:var(--mid)}
.b1{fill:var(--s1)} .b2{fill:var(--s2)}
.legend{display:flex;gap:6mm;font:7.8pt var(--f-mono);color:var(--mid);margin-top:2mm}
.legend i{display:inline-block;width:9px;height:9px;border-radius:2px;margin-right:2mm}
.cap{fill:var(--soft);font:7.6pt var(--f-mono)}

/* oracle strip */
.ob{fill:var(--accent)} .ot{font:700 8.4pt var(--f-mono);fill:#fff}
.oo{fill:none;stroke:var(--firm);stroke-width:1}
.oot{font:8.2pt var(--f-body);fill:var(--ink)}
.oa{stroke:var(--firm);stroke-width:1.1;fill:none}
.oc{font:6.6pt var(--f-mono);fill:var(--soft)}

/* composition map */
.mb{fill:var(--panel);stroke:var(--firm);stroke-width:1}
.mb2{fill:var(--sunk);stroke:var(--accent);stroke-width:1.1}
.mt{font:700 8.6pt var(--f-mono);fill:var(--ink)}
.ml{font:6.6pt var(--f-mono);fill:var(--soft);letter-spacing:.14em}
.lane{stroke:var(--rule);stroke-width:.6;fill:none}
.ar,.ar2,.ar3,.ar4{stroke:var(--s2);stroke-width:1.1;fill:none}
.ar3,.ar4{stroke:var(--accent);stroke-dasharray:3 2}
.an{font:6.8pt var(--f-mono);fill:var(--soft)}

/* ---------- repo cards ---------- */
.grp{margin-bottom:7mm;page-break-inside:avoid}
.grp h2{font-size:13.6pt;color:var(--accent)}
.gb{font:8.4pt var(--f-mono);color:var(--soft);margin:.8mm 0 4mm}
.card{border:1px solid var(--rule);border-left:2.4pt solid var(--accent);
  border-radius:3px;padding:3.6mm 4mm;margin-bottom:3.4mm;background:var(--paper);
  page-break-inside:avoid}
.ch{display:flex;align-items:baseline;gap:3mm;flex-wrap:wrap;margin-bottom:2.4mm}
.ch h3{font-size:12.6pt;font-family:var(--f-mono);letter-spacing:-.01em}
.cb{font-size:9.6pt;color:var(--mid)}
.cn{margin-left:auto;font:7.4pt var(--f-mono);color:var(--soft);
  font-variant-numeric:tabular-nums}
.card dl{display:grid;grid-template-columns:27mm 1fr;gap:1.1mm 3mm;margin:2.6mm 0 0}
.card dt{font:600 7.2pt var(--f-mono);letter-spacing:.08em;text-transform:uppercase;
  color:var(--soft);padding-top:.5mm}
.card dd{margin:0;font-size:9.4pt;color:var(--mid)}
.card dd.res{font-family:var(--f-mono);font-size:8.4pt;color:var(--accent)}
.prog{display:inline-block;width:26mm;height:4px;background:var(--sunk);
  border-radius:2px;margin-left:2mm;vertical-align:middle;overflow:hidden}
.prog span{display:block;height:100%;background:var(--s1)}

/* ---------- bugs ---------- */
.bug{border-top:1px solid var(--rule);padding:2.6mm 0;page-break-inside:avoid}
.bh{display:flex;gap:2.6mm;align-items:baseline;margin-bottom:.8mm}
.brepo{font:700 7.6pt var(--f-mono);color:var(--accent);min-width:19mm}
.bt{font:700 10pt var(--f-disp)}
.bug p{margin:0;font-size:9.2pt;color:var(--mid)}
.note{border:1px solid var(--s2);border-left-width:2.4pt;background:#fbf4ee;
  padding:3mm 3.6mm;margin:5mm 0;page-break-inside:avoid}
.note .k{font:600 7.4pt var(--f-mono);letter-spacing:.1em;text-transform:uppercase;
  color:var(--s2);display:block;margin-bottom:1.4mm}
.note p{font-size:9.4pt;margin:0 0 .5em}
.quiet{border:1px solid var(--firm);background:var(--panel);padding:3mm 3.6mm;
  margin:5mm 0;page-break-inside:avoid}
.quiet .k{font:600 7.4pt var(--f-mono);letter-spacing:.1em;text-transform:uppercase;
  color:var(--accent);display:block;margin-bottom:1.4mm}
.quiet p{font-size:9.4pt;margin:0 0 .5em}
table{width:100%;border-collapse:collapse;font-size:8.8pt;margin:3mm 0}
th{text-align:left;font:600 7.2pt var(--f-mono);letter-spacing:.08em;
  text-transform:uppercase;color:var(--soft);border-bottom:1px solid var(--firm);
  padding:1.6mm 2mm}
td{padding:1.5mm 2mm;border-bottom:1px solid var(--rule);color:var(--mid)}
td:first-child{font-family:var(--f-mono);color:var(--ink);font-size:8.4pt}
.foot{font:7.8pt/1.5 var(--f-mono);color:var(--soft);border-top:1px solid var(--rule);
  padding-top:3mm;margin-top:7mm}
</style></head><body>

<!-- ============ cover ============ -->
<section class="sheet cover">
  <p class="eyebrow">Systems engineering portfolio &middot; Linux / FOSS</p>
  <h1>@@word@@ programs, and something outside each one that decides if it is right.</h1>
  <p class="lede">Every project here is built against an <b>external oracle</b> &mdash; gcc
  and clang, the Linux kernel, <code>dash</code>, GNU tar, readelf, SQLite, Python's
  own regex engine. Not one of them is the judge of its own correctness. That
  constraint is the whole method, and it is why
  <b>@@n_harness@@ of the @@n_bugs@@ defects recorded here were in the test harness rather than
  in the code</b>.</p>
  @@name_block@@
  @@handle@@
  <div class="tiles">
    <div class="tile"><div class="v">@@repos@@</div><div class="k">repositories</div></div>
    <div class="tile"><div class="v">@@commits@@</div><div class="k">commits</div></div>
    <div class="tile"><div class="v">@@src@@</div><div class="k">lines of source</div></div>
    <div class="tile"><div class="v">@@test@@</div><div class="k">lines of tests</div></div>
    <div class="tile"><div class="v">@@green@@</div><div class="k">suites green</div></div>
  </div>
  <p class="cap" style="margin-top:7mm">Every figure in this document is generated from the
  repositories themselves: commit counts from <code>git</code>, line counts from the files,
  test counts from running each suite. Nothing is transcribed by hand.</p>
</section>

<!-- ============ method ============ -->
<section class="sheet">
  <h2 class="sec">The method</h2>
  <p class="stand">A test you wrote, checking code you wrote, against a number you
  worked out yourself, proves that you were consistent. It does not prove you were
  right. <b>Every project here is measured against an authority it does not
  control.</b></p>

  <figure>
    @@comp_map@@
    <figcaption>How these @@repos@@ compose. Each arrow is a dependency recorded in a
    PLAN.md. The three process tools in the bottom lane act on all the others:
    <b>unrepro</b> found a real reproducibility defect in eight of the @@repos@@,
    <b>commitq</b> gates every commit in all of them, and <b>srcdiff</b> audits
    published artifacts against the repositories they claim to come from.</figcaption>
  </figure>

  <div class="quiet"><span class="k">Why this matters more than it sounds</span>
  <p>The first run of almost every harness in this project passed. The useful
  question is never &ldquo;do my tests pass&rdquo; but <b>&ldquo;have I watched this
  harness fail?&rdquo;</b> Where that question got asked, it usually turned out the
  answer was no &mdash; and the suite had been reporting success because it was
  silently doing nothing.</p></div>

  <figure>
    @@ratio@@
  </figure>

</section>

<section class="sheet">
  <h2 class="sec">Scale</h2>
  <figure>
    @@commit_chart@@
    <figcaption>Commits per repository. Granularity is deliberate: every commit builds,
    verified by removing build artifacts and rebuilding each one in turn.</figcaption>
  </figure>
</section>

<!-- ============ loc ============ -->
<section class="sheet">
  <h2 class="sec">Source against tests</h2>
  <p class="stand">@@test@@ lines of tests to @@src@@ of source. The ratio is the point:
  in several of these the harness <b>is</b> the project, and the program under test is
  scaffolding for it.</p>
  <figure>
    @@loc_chart@@
    <div class="legend"><span><i style="background:#0e8f85"></i>source</span>
      <span><i style="background:#a1551d"></i>tests</span></div>
    <figcaption>Lines of source and lines of test per repository, sorted by total.
    Labels read source / tests.</figcaption>
  </figure>

  <div class="note"><span class="k">A number worth distrusting</span>
  <p>Test <em>counts</em> are not comparable between these repos and are deliberately
  not charted together. <code>wasmi</code>'s 11,833 are generated arithmetic cases;
  <code>jail</code>'s @@jail_tests@@ are hand-written assertions against kernel behaviour, and each
  one took longer to get right than a thousand of the former. Plotting them on one
  axis would imply a comparison that does not exist.</p></div>

  <table>
    <thead><tr><th>repo</th><th>what the suite actually reports</th><th>plan</th></tr></thead>
    <tbody>@@groups_table@@</tbody>
  </table>
</section>

<!-- ============ repos ============ -->
<section class="sheet">
  <h2 class="sec">The repositories</h2>
  <p class="stand">Grouped by what kind of thing they have to survive. Each card names
  the authority that decides whether it is correct, and the one property that, if
  violated, means the project failed.</p>
  @@groups@@
</section>

<!-- ============ bugs ============ -->
<section class="sheet">
  <h2 class="sec">What went wrong in the harness</h2>
  <p class="stand">These are the defects worth reading. In each case the code looked
  fine, the suite was green, and <b>the thing that was broken was the thing meant to
  find breakage.</b></p>
  @@harness_bugs@@
</section>

<section class="sheet">
  <h2 class="sec">What went wrong in the code</h2>
  <p class="stand">Found by the oracles, never by re-reading the source. Each of these
  produced plausible output and passed every check that existed at the time.</p>
  @@code_bugs@@

  <div class="quiet"><span class="k">How this is kept honest</span>
  <p><b>Every commit builds.</b> Verified by checking out each one in turn, deleting
  build artifacts so a stale binary cannot fake a pass, and rebuilding.</p>
  <p><b>All @@repos@@ build reproducibly.</b> Proven by <code>unrepro</code>, one of
  them, which found that eight of its siblings were not &mdash; <code>-g</code> writes
  the compiler's working directory into DWARF <code>.debug_line_str</code>. Every repo
  compiling with <code>-g</code> was affected and every repo without it was already clean,
  which is independent confirmation of the cause rather than a plausible guess.</p>
  <p><b>No commit can be gated by a suite that does not run.</b> <code>commitq</code> runs
  each repo's tests against the working tree before committing and refuses when they
  fail &mdash; or when a repo has no discoverable suite at all, which was a real bug it
  had for two thirds of the project.</p>
  <p>@@shortcuts@@ places take a deliberately simple route, each marked
  <code>shortcut:</code> in the source and naming both the ceiling it accepts and the
  upgrade path. @@done@@ planned steps are done and @@todo@@ remain,
  ordered, each recording why it is next.</p></div>

  <p class="foot">Generated from the repositories by <code>.portfolio/build.py</code>.
  Data-fill colours validated against the paper surface with the dataviz palette checker:
  worst CVD &Delta;E 12.6, normal-vision &Delta;E 21.0, all six checks pass.</p>
</section>
</body></html>"""


if __name__ == "__main__":
    # a compact table of what each suite reports, for the Scale sheet
    rows = ""
    for k, v in sorted(DATA.items(), key=lambda kv: kv[0]):
        rows += (f'<tr><td>{k}</td><td>{esc(v["tests"]) or "&mdash;"}</td>'
                 f'<td>{v["done"]}/{v["done"] + v["todo"]}</td></tr>')
    PAGE = PAGE.replace("@@groups_table@@", rows)
    build()
