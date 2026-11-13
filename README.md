**Drumchotic** is a tool for rating Clone Hero expert drum charts by difficulty, primarily in relation to how they fare against official Rock Band setlists and Drummer's Monthly Tournament difficulty tiers. It attempts to solve the subjectivity in ranking drum charts by mapping a variety of both heuristic and ML features in an attempt to replicate the relative difficulty of DMBot leaderboard scores. It can also spit out a suggested `diff_drums` and tell you roughly in which ways it is difficult.

Take a look at https://noahbaxter.dev/drumchotic/

## Usage

```
scripts/rate.sh --help                       # every option, and how to read the report
scripts/rate.sh ~/path/to/charts             # rate chart folders on disk
scripts/rate.sh --artist "car bomb"          # or --search, --top N, --tournament
```
