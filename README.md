# drumchotic

[DRAFT] Rates Clone Hero expert drum charts: an estimated DMT tier, a suggested `diff_drums`,
and the axes that make each chart hard. Fit to DMBot leaderboard scores.

## Usage

Model work (knobs in `drumchotic/tuning.py`):

```
scripts/run.sh [plot ...]                    # re-measure if stale, fit, report, plots into data/plots/
scripts/sync_dmt.sh                          # DMT tournament charts from the NAS into data/dmt
python -m drumchotic.report                  # accuracy, hardest charts, outliers
python -m unittest
```
