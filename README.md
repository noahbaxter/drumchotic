**Drumchotic** is a tool for rating Clone Hero expert drum charts by difficulty, primarily in relation to how they fare against official Rock Band setlists and Drummer's Monthly Tournament difficulty tiers. It attempts to solve the subjectivity in ranking drum charts by mapping a variety of both heuristic and ML features in an attempt to replicate the relative difficulty of DMBot leaderboard scores. It can also spit out a suggested `diff_drums` and tell you roughly in which ways it is difficult.

Explorer: https://noahbaxter.dev/drumchotic/

## Usage

```
scripts/rate.sh --help                       # every option, and how to read the report
scripts/rate.sh ~/path/to/charts             # rate chart folders on disk
scripts/rate.sh --artist "car bomb"          # or --search, --top N, --tournament
```

Model work (knobs in `drumchotic/tuning.py`):

```
scripts/run.sh [plot ...]                    # re-measure if stale, fit, report, plots into data/plots/
scripts/sync_dmt.sh                          # DMT tournament charts from the NAS into data/dmt
scripts/run_fretwork.sh                      # fretwork scores for our chart copies
python -m drumchotic.report                  # accuracy, hardest charts, outliers
python -m drumchotic.audit                   # each axis alone, and the model without it
python -m drumchotic.explain "kick burst"    # where an axis peaks in its hardest charts
python -m unittest
```
