"""Rate Clone Hero drum charts (expert drums) and rank them hardest first.

Each chart gets drumchotic's tier (estimated DMT tier) and diff (suggested song.ini diff_drums)
next to the human ones, and the axes that make it hard compared with charts of the same tier.

WHAT TO RATE (combine as many as you like, each gets its own block)
  FOLDER ...                any chart folders on disk, searched all the way down. Works on
                            anything with a notes.mid or notes.chart: your downloads, your own
                            charts, a single song. It does not need to be on a leaderboard or
                            in a tournament. Paths are relative to where you ran the script.

READING THE REPORT
  Two column groups, drumchotic's call and the human one, each with a tier and a diff:
  drumchotic tier   estimated DMT tier. 1 is a typical tier 1 song, 8 a typical tier 8. Past 8
                    keeps counting up (a 10 is as far past 8 as 8 is past 6), 0 is easier than
                    a typical tier 1.
  drumchotic diff   suggested song.ini diff_drums (0 to 6, past 6 keeps counting up)
  human tier        where a DMT tournament placed it (blank if never placed)
  human diff        what its song.ini says (blank if unrated)
  hard for          up to three axes where it beats at least 85% of charts of the same tier.
                    Empty means nothing stands out: it is hard (or easy) evenly.
  Each block opens with the tier range, the axes that come up most, and a histogram.

THE AXES
  speed, density, endurance         peak notes per second, how busy it is overall, how long
                                    the dense stretches last
  kick / hand / one hand burst      short fast runs (fills, kick flurries, up to 8 notes)
  kick / hand / one hand stamina    long runs and sustained rate (blasts, 16th kicks)
  kick / hand / one hand syncopation  off the beat and rhythms that keep changing
  movement                          moving around the kit, toms and cymbal switches
  sticking                          how hard the easiest way to play the hands still is
                                    (hand speed, crossovers, reach)
  linear                            limbs alternating with no two at once
  coordination                      kicks and hands syncopated at the same time
  variety                           how rarely patterns repeat (chops vs groove)

OUTPUT
  The report is printed and also saved as plain text to data/ratings/<date>_<names>.txt
  (or --out), which previews cleanly as a Discord attachment.

LIMITS
  Packed downloads (.sng, .zip, .rar, .7z) aren't read: extract them into folders first.
  Dropbox online-only files are empty placeholders: make the folder available offline.
  Only expert drums are rated. A tier past about 9 is extrapolated, so treat it as rough.

EXAMPLES
  scripts/rate.sh ~/"Clone Hero/Songs"
  scripts/rate.sh ~/Downloads/new-charts --limit 20
  scripts/rate.sh ~/Downloads/new-charts --detail
"""
import argparse
import collections
import os
import re
from datetime import datetime
from pathlib import Path

import numpy as np

from .chart import song
from .measure import features
from .rating import REASONS_SHOWN, Rater, charter_rating, reasons

TITLE_WIDTH = 48       # longer titles are cut
PACKED = ('.sng', '.zip', '.rar', '.7z')    # chart downloads this can't open yet
REPORTS = Path(__file__).resolve().parent.parent / 'data' / 'ratings'


def chart_folders(root):
    return sorted({p.parent for n in song.NOTE_FILES for p in Path(root).rglob(n)})


def fit(text, width):
    return text if len(text) <= width else text[:width - 3] + '...'


def chart_rows(rater, rated, limit, detail):
    """rated: [(title, folder, result)] hardest first -> table lines."""
    shown = rated[:limit] if limit else rated
    width = min(max(len(t) for t, _, _ in shown), TITLE_WIDTH)
    lines = [f"       drumchotic │ human",
             f"  {'#':>3}  tier  diff │ tier  diff  {'chart':{width}}  hard for",
             f"  {'-' * 3}  ----  ---- │ ----  ----  {'-' * width}  {'-' * 8}"]
    for i, (title, folder, res) in enumerate(shown, 1):
        rated_as = charter_rating(folder)
        why = ', '.join(a for a, _, _ in reasons(res)[:REASONS_SHOWN])
        placed = sorted(rater.placed.get(song.md5(folder), ()))
        tier = 'T' + '/'.join(map(str, placed)) if placed else ''
        lines.append(f"  {i:3d}  {res['level']:4.1f}  {res['charter']:4.1f} │ {tier:>4}  {rated_as if rated_as >= 0 else '':>4}"
                     f"  {fit(title, width):{width}}  {why}".rstrip())
        if detail:
            lines += [f"{'':40}{a:22} library {lib:3.0f}%   at its tier {peer:3.0f}%" for a, lib, peer in res['axes']]
    if limit and len(rated) > limit:
        lines.append(f'       ... {len(rated) - limit} easier charts not shown')
    return lines


def summary(rated):
    """How a group's charts spread across levels, and what tends to make them hard."""
    lv = np.array([res['level'] for _, _, res in rated])
    lines = [f'tier {lv.min():.1f} to {lv.max():.1f}, median {np.median(lv):.1f}, '
             f'middle half {np.percentile(lv, 25):.1f} to {np.percentile(lv, 75):.1f}']
    common = collections.Counter(a for _, _, res in rated for a, _, _ in reasons(res)[:REASONS_SHOWN])
    if common:
        lines.append('usually hard for: ' + ', '.join(a for a, _ in common.most_common(3)))
    bins = collections.Counter(int(v) for v in lv)
    most = max(bins.values())
    lines.append('')
    for b in range(min(bins), max(bins) + 1):
        lines.append(f"  {b:>2}  {'█' * round(bins[b] / most * 30):30}  {bins[b] or ''}".rstrip())
    return lines


def group(rater, name, rated, limit, detail):
    """One titled block: summary, then the charts hardest first."""
    head = f'{name.upper()}   {len(rated)} chart{"s" * (len(rated) != 1)}'
    return [head, '=' * len(head)] + summary(rated) + [''] + chart_rows(rater, rated, limit, detail) + ['', '']


def hardest_first(rated):
    return sorted(rated, key=lambda x: -x[2]['score'])


def by_folder(rater, root, limit, detail):
    rated, notes, online_only = [], [], 0
    for folder in chart_folders(root):
        if any(p.exists() and p.stat().st_size == 0 for p in (folder / n for n in song.NOTE_FILES)):
            online_only += 1
            continue
        try:
            chart, meta = song.load(folder)
            feats = features.compute(chart) if chart else None
        except Exception as e:
            notes.append(f'skipped {folder.name}: {type(e).__name__}: {e}')
            continue
        if feats is None:
            notes.append(f'skipped {folder.name}: no expert drums')
            continue
        rated.append((song.title(meta, folder), folder, rater.rate(feats)))
    packed = sum(1 for p in Path(root).rglob('*') if p.suffix.lower() in PACKED)
    if packed:
        notes.append(f'{packed} packed files (.sng or archives) not rated: extract them into folders first.')
    if online_only:
        notes.append(f'{online_only} charts not rated: their files are empty placeholders (Dropbox online-only?). '
                     'Make the folder available offline to rate them.')
    if not rated:
        return [str(root)] + notes + ['']
    out = group(rater, Path(root).name, hardest_first(rated), limit, detail)
    return out[:-1] + notes + [''] if notes else out


LEGEND = [
    'drumchotic  tier  estimated DMT tier (1 to 8; past 8 keeps counting up, 0 = below tier 1)',
    '            diff  suggested song.ini diff_drums (0 to 6; past 6 keeps counting up)',
    'human       tier  where a DMT tournament placed it (blank if never placed)',
    "            diff  what the chart's song.ini says (blank if unrated)",
    'hard for: the axes where this chart beats most charts of the same tier',
]


def report_path(a):
    names = [Path(f).name for f in a.folders]
    slug = re.sub(r'[^a-z0-9]+', '-', ' '.join(names).lower()).strip('-')[:60] or 'ratings'
    return REPORTS / f"{datetime.now():%Y-%m-%d_%H%M%S}_{slug}.txt"


def main():
    p = argparse.ArgumentParser(prog='scripts/rate.sh', description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('folders', nargs='*', metavar='FOLDER', help='chart folders on disk, searched recursively')
    p.add_argument('--limit', type=int, metavar='N', help='show only the N hardest of each block')
    p.add_argument('--detail', action='store_true', help='list every axis under each chart, not just stand-outs')
    p.add_argument('--out', type=Path, metavar='FILE', help='save the report here instead of data/ratings/')
    a = p.parse_args()
    if not a.folders:
        p.print_usage()
        p.exit(2, 'nothing to rate: give a folder (--help explains everything)\n')
    caller = Path(os.environ.get('RATE_CWD', '.'))
    a.folders = [caller / f for f in a.folders]
    a.out = caller / a.out if a.out else None
    rater = Rater()
    lines = []
    for root in a.folders:
        lines += by_folder(rater, root, a.limit, a.detail)
    text = '\n'.join(lines + LEGEND) + '\n'
    print(text)
    out = a.out or report_path(a)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text)
    print(f'-> {out}')


if __name__ == '__main__':
    main()
