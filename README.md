# drumchotic

[DRAFT] Rates Clone Hero expert drum charts: an estimated DMT tier, a suggested `diff_drums`,
and the axes that make each chart hard. Fit to DMBot leaderboard scores.

## Usage

Model work (knobs in `drumchotic/tuning.py`):

```
scripts/run.sh [plot ...]                    # re-measure if stale, fit, report, plots into data/plots/
scripts/sync_dmt.sh                          # DMT tournament charts from the NAS into data/dmt
scripts/run_fretwork.sh                      # fretwork scores for our chart copies
python -m drumchotic.report                  # accuracy, hardest charts, outliers
python -m drumchotic.explain "kick burst"    # where an axis peaks in its hardest charts
python -m unittest
```
