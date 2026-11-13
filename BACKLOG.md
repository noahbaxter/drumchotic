# Backlog

Plans, community feedback and tuning ideas. Source in brackets; the raw threads are in data/feedback/ (gitignored), findings in docs/findings.md.

## Next up, in order
1. FC signal (Noah 2026-11-11): a chart with many scores but few FCs is harder than one with as many scores and lots of FCs. The export has is_fc per score. Fit an FC difficulty per chart with the players' skills from fit/players.py as offsets (logistic: P(FC) from skill minus FC difficulty), then: show it as an FC readout, check how it relates to the percent difficulty and the length discount (long songs should be harder to FC), and test whether blending it into the training target helps tiers and community.
2. Flag charts beyond human limits.
3. Sticking rework (sticking plus movement are worth about 0.008 Spearman today; see docs/findings.md).
4. Hand endurance (armchair: Breaking the Habit), likely through the FC readout.

## Product
- [ ] State what the rating is, on the site and in the README, for users as well as us: misses on expert 2x kick (accuracy, not score or star power, passing doesn't count); 0 means easier than a typical tier 1 tournament song; the top end is anchored by absurd charts (quadruple kick, Venetian Snares); the goal is an average difficulty that doesn't over-reward any one skill, the way tournament tiers try to. [Half-Gallon: "they just need to be stated and understood on your side AND the user side"]
- [ ] Decide the floor and ceiling deliberately. Half-Gallon: DM tier 1 should sit around a Rock Band 2 to 3 diff, so the floor is much lower than today's; a ceiling is required, the question is how much room to leave above (stage tour debated room for 300 BPM slop). Noah: a proper 0 to 10 would be nice. [Half-Gallon, Noah]
- [ ] Explain the axes in plain words on the site (armchair asked what speed vs density means). [armchair]
- [ ] Suggest a difficulty when exporting a chart from chartchotic. [Noah, end goal]
- [ ] Let people test upcoming tournament setlists (works today with scripts/rate.sh on the setlist folder; armchair and Pile are using the site for the next setlist). [armchair]

## Infrastructure
- [x] bazzite runs the heavy work: scripts/remote.sh sends the working tree (uncommitted edits included) and runs features, report, audit, web, rate or test there, pulling results back. Repo at ~/drumchotic (git remote `bazzite`), own venv, data/charts as a local copy (virtiofs to the NAS is too slow to walk).
- [x] Cache each chart's hand assignment (sticking is 90% of measuring time): rebuilds that don't touch sticking or parsing run about 20 times faster. Per-feature-group caching isn't worth it (all other features are under 5% of the time).
- [ ] Keep bazzite's chart copy in sync with the NAS (bazzite can't reach nasmox by name; relay through the Mac from the plocate list), then point publish_web.sh and serve.sh at remote builds.
- [ ] Give bazzite all 16 host threads in Proxmox (it has 8): a cold full build is about 17 min today. [needs Noah]
- [ ] Delete the Mac's data/charts (2.9 GB) once bazzite does all measuring.
- [ ] From the rebuild agent: modules run outside the repo root silently find no data (pipeline.DATA is cwd-relative); check page and explorer peer windows differ by one (601 vs 600); the live-reload server doesn't watch data/dmt, leaderboards or results.

## Data
- [x] Copy every unique chart on the NAS from the plocate index (31,898 local), including the Rock Band discs and RB1/RB2 DLC.
- [x] Add Drummer's Monthly 1 to 3 and Icebreaker 2022 to data/dmt from the Google Drive zips (not on the NAS drive).
- [x] Old tournaments numbered tiers their own way, so only 2024 on sets the tier scale; older ones still order their own songs. armchair's renumbering (Birdman 3/5/7, Summer Blast 2023 2/4/5/6/7) lands on the same tier medians as this cut. [armchair, Noah]
- [ ] Fetch played charts we don't have, by md5: Rock Band Network (849 played), RB3 and RB4 era DLC (about 1,200), and other versions of songs we have (e.g. Rush YYZ, Hail The Sun Domino).
- [ ] Easy-end data: our leaderboard skews to strong players, so the bottom is the least certain part. Candidates: official Rock Band setlists' within-set order (Half-Gallon: their floor is too low and ceiling way too low, so use order only, not their numbers), full band charters who do easier bands (Half-Gallon, Paramore and the like), Josh's charts. [Half-Gallon, Noah]
- [ ] Charter ratings mix standards: Leo switched rating standards at some point, so his older diff_drums don't line up with his newer ones. [armchair]
- [x] Sudden death sets: their tiers are the same as their tournament's, so SD songs join the tournament's tiers; Icebreaker 2023's Pro SD isn't tiered and stays out. [armchair]

## Outliers
- [x] No rate from impossible time spans: density chunks at least 0.5s, run gaps at least 15ms (joke tempo maps, stacked notes).
- [x] A drum track with nothing to play rates as easy as it gets.
- [ ] Flag charts beyond human limits (meme charts like Soulless 4, programmed remixes, extratone and breakcore) instead of ranking them with everything else. Noah: hard to count those as valuable at the top.
- [ ] Add highfine's pick, the Never Kill a Mouse demo, to the anchor charts. [highfine]

## Scale
- [x] Fit one straight line through the tier medians instead of joining the dots, so tiers are evenly spaced and the level histogram is smooth.
- [ ] Offer a 50/50 blend of overall difficulty and difficulty within the band's catalog, Half-Gallon's own approach since customs skew too hard to compare across. [Half-Gallon]

## Features
- [ ] Endurance: armchair says it's underrated, especially hand endurance (Breaking the Habit). Checked against the leaderboard (2026-11-11): overall it isn't; high-endurance charts are slightly overrated and long charts most of all (rank corr -0.23). Percent forgives fatigue and endurance mostly costs the FC, so look at hand endurance on its own and through the FC readout. [armchair]
- [ ] Short hard bursts vs whole-song difficulty: Pieces of You's intro over-rates it; charts with one really hard section (Destrage, Everything Sucks) or inconsistent difficulty get under-rated. Half-Gallon: drop or limit the metrics that let quick bursts inflate the overall number. Noah's idea: rate each section and look at the hardest. Tune how long a hard stretch has to last to count fully. [armchair, Half-Gallon, Noah]
- [x] Familiarity: patterns common across the whole library feel natural and should count as easier. Built in as the rare patterns axis (runs of 6 onsets); it barely moves the pop punk and math rock outliers, which follow the charter instead (docs/findings.md). [armchair: "it doesn't understand what feels natural", Noah]
- [ ] Sticking misses open-handed playing (Shedding), crossunders (As Good As Dead, an FC killer), and lead-foot switching in kick bursts (Warborn). [armchair]
- [ ] TDEP style charts (Dillinger) trick the model. [armchair]
- [ ] Rename "linear" to "alternation": it counts blast beats too (Noah), and consider splitting blasts out.
- [ ] Lockslip gut check: End the Conversation is too low (its ending), Inglorius is too high. Add as a community claim once checked. [Noah]

## Evaluation
- [x] Community claims as a third scorecard (labels/community.txt, printed by report). Car Bomb from armchair: 51 of 53 pairs right.
- [ ] Add more community claims as they come in (one "@ artist | who, where" block each).
- [ ] Compare against tournament tiers, not against other raters: Half-Gallon says the tier comparison is the meaningful one and the other rater measures a different thing (apples and oranges). If a comparison is wanted, tweak our formula into a like-for-like version and compare our two versions to each other. [Half-Gallon]
- [ ] FC target from is_fc, as its own readout (one awkward spot kills an FC but barely moves percent). [Half-Gallon]
- [ ] A variant without burst axes, closer to how stage tour rates (rating all difficulties easy to hard plus star power). [Half-Gallon]
- [ ] A five-family readout like stage tour's pentagon, where the single number is the pentagon's average. [Half-Gallon]
