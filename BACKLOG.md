# Backlog

Community feedback and tuning ideas, newest first. Source in brackets.

## Data
- [x] Copy every unique chart on the NAS from the plocate index (31,898 local), including the Rock Band discs and RB1/RB2 DLC.
- [x] Add Drummer's Monthly 1 to 3 and Icebreaker 2022 to data/dmt from the Google Drive zips (not on the NAS drive).
- [ ] Fetch played charts we don't have, by md5: Rock Band Network (849 played), RB3 and RB4 era DLC (about 1,200), and other versions of songs we have (e.g. Rush YYZ, Hail The Sun Domino).
- [x] Old tournaments numbered tiers their own way, so only 2024 on sets the tier scale; older ones still order their own songs. armchair's renumbering (Birdman 3/5/7, Summer Blast 2023 2/4/5/6/7) lands on the same tier medians as this cut. [armchair, Noah]
- [ ] Charter ratings mix standards: Leo switched rating standards at some point, so his older diff_drums don't line up with his newer ones. [armchair]

## Outliers
- [x] No rate from impossible time spans: density chunks at least 0.5s, run gaps at least 15ms (joke tempo maps, stacked notes).
- [x] A drum track with nothing to play rates as easy as it gets.
- [ ] Flag charts beyond human limits (meme charts like Soulless 4) instead of ranking them with everything else.

## Scale
- [ ] Fit one straight line through the tier medians instead of joining the dots, so tiers are evenly spaced and the level histogram is smooth.
- [ ] Say what the scale is for, and its floor and ceiling: DM tier 1 should be about a Rock Band 2 to 3 diff. [Half-Gallon]

## Features
- [ ] Endurance looks underrated. [armchair] Checked against the leaderboard (2026-11-11): it isn't. High-endurance charts are slightly overrated (top 5% by longest dense stretch: model 0.06 too hard, about 3 se) and long charts most of all (rank corr -0.23). Percent forgives fatigue; endurance mostly costs the FC, so the FC readout below is the fix, not a bigger endurance weight.
- [ ] Short hard bursts vs whole-song difficulty: Pieces of You's intro over-rates it; charts with one really hard section (Destrage, Everything Sucks) or inconsistent difficulty get under-rated. Tune how long a hard stretch has to last to count fully, rather than a straight max over sections. [armchair, Half-Gallon]
- [ ] Familiarity: patterns common across the whole library feel natural and should count as easier. Best lead on the chops gap. [armchair: "it doesn't understand what feels natural"]
- [ ] Sticking misses open-handed playing (Shedding), crossunders (As Good As Dead, an FC killer), and lead-foot switching in kick bursts (Warborn). [armchair]
- [ ] Album charts and very long charts behave oddly; length shouldn't inflate difficulty. [armchair]
- [ ] TDEP style charts (Dillinger) trick the model. [armchair]

## Evaluation
- [x] Community claims as a third scorecard (labels/community.txt, printed by report). Car Bomb from armchair: 51 of 53 pairs right.
- [ ] Add more community claims as they come in (one "@ artist | who, where" block each).
- [ ] FC target from is_fc, as its own readout (one awkward spot kills an FC but barely moves percent). [Half-Gallon]
- [ ] A variant without burst axes, closer to how stage tour rates. [Half-Gallon]

## Tools
- [ ] Let people test upcoming tournament setlists (works today: scripts/rate.sh on the setlist folder). [armchair]
