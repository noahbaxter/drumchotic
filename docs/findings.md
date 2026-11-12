# Findings

What we measured, what we tried, and what it showed, so nothing has to be rediscovered. Newest first within each section. Plans and feedback live in BACKLOG.md.

## Where the model stands (2026-11-11, feature/v2)
- Leaderboard: held-out Spearman 0.912 over 7,279 charts. DMT tiers in order: 0.932 (15 tournaments). Community claims: 53 of 53 pairs (100%). With the length discount; without it 0.908 / 0.932 / 96%.
- Library: 17,976 charts with expert drums out of 31,898 unique charts on the NAS (the rest have no drums track). 2 charts have a drums track with nothing to play; they rate as easiest.
- The hardest charts are meme or impossible charts (Snailfetus, ExileLord Soulless 4 and 5, quadruple kick demos), up to tier 21.

## Scale
- Tier scale anchors on tournaments from 2024 on only (Icebreaker 2024 and 2026, Summer Blast 2024 and 2025, Legacy Cup 2025). Older tournaments numbered tiers their own way. armchair's renumbering (Birdman 3/5/7, Summer Blast 2023 2/4/5/6/7) lands within 0.05 of the same tier medians as the 2024 cut, so it agrees.
- Tier medians from 2024 on (model score): T1 -1.12, T2 -0.79, T3 -0.29, T4 +0.03, T5 +0.39, T6 +0.64, T7 +1.23. T8 has 19 songs, under the 20 needed to anchor.
- Joining tier medians dot to dot made the tier histogram steppy (gaps 0.15 to 0.56) and parked 176 charts at tier 0. One straight line fit through the medians fixed both; each tier median lands within 0.2 of its tier.
- Charter ratings (song.ini diff_drums) below 2 don't follow difficulty: 0 mostly means unrated and 1 and 2 overlap. The diff scale is built from 2 up.
- The scale's floor and ceiling were never stated. Half-Gallon: DM tier 1 should be about a Rock Band 2 to 3 diff.

## What the misses look like
- Endurance is not underrated against the leaderboard (armchair thought it was). Charts with the longest dense stretches are slightly overrated (top 5%: model 0.06 too hard, about 3 se). Length is the strongest leftover signal: rank corr -0.23 between chart length and (leaderboard minus model), so long charts are rated too hard. Percent scoring forgives fatigue; endurance mostly costs the FC.
- Every axis has a small negative correlation (-0.05 to -0.07) with the miss: the model slightly overrates charts that are hard on anything.
- Chops charts (Matt McGuire, Luke Holland, Xane60 remixes) read easier than players find them: held-out mean 0.12 vs leaderboard 0.45. About a third of that gap is leaderboard bias (length and kick-heavy charts); tournament tiers show no hand-heavy vs kick-heavy bias. Pop punk (Rise Against) -0.57 vs -0.67, about right.

## Length, silence and average NPS (2026-11-11)
- Built in as a hinge (tuning.LENGTH_DISCOUNT): only charts longer than the training median (222 s) are discounted, slope -0.237 per log second past it. Against the straight line (-0.186, which also lifts short charts): leaderboard 0.9116 vs 0.9124, tiers 0.9319 vs 0.9313, community both 53/53, all inside noise. Held-out mean miss by length (off, then on): under 222 s -0.07 / -0.03, 222 to 400 s +0.02 / +0.01, 400 to 900 s +0.15 / 0.00, 900 to 1800 s +0.32 / -0.03, 1800 s+ +0.59 / +0.05. Full albums take up to 1.8 tiers off (BTBAM Colors), discographies about 3.
- Silence doesn't change difficulty per the leaderboard: playing share, longest rest, rests over 2 s and total rest time all correlate -0.04 to -0.01 with the model's miss. Near-empty charts already land at tier 0 to 0.6 (4'33", Nirvana Polly, jingles). Mostly-silent charts with real playing rate by what's played, and the leaderboard agrees.
- Average NPS (notes over the whole span, gaps included) adds nothing: 0.908 with or without it, as an axis or inside density or endurance; alone 0.686 vs density 0.864. Most charts play 92 to 100% of their span, so it's nearly density. Good for explaining axes (speed = max, density = median, average = overall), not for the model.
- What the misses do follow is amount: total notes (-0.22) and span (-0.21). A length correction (log seconds, fit inside each fold on training charts only, on top of the axis model): leaderboard 0.908 to 0.912, tiers 0.932 to 0.931 (flat), community 96% to 100% (the two Car Bomb misses come right). Slope -0.186 per log second: doubling a song's length costs about 0.13 model units, about a third of a tier; album-length charts about half a tier. Notes instead of seconds: 0.913 / 0.929 / 98%. Fits the stated target (accuracy: a miss is a smaller share of percent on a long song); for FCs length cuts the other way.

## Is sticking worth it (2026-11-11)
- Without the sticking axis: leaderboard 0.908 to 0.905, tiers 0.932 to 0.934 (inside noise). Without sticking and movement (both come from the hand assignment): leaderboard 0.900, about three times the noise. Alone: sticking 0.801, movement 0.682. Modest but real; keep it, and judge the sticking rework against these numbers.
- Sticking is about 90% of measuring time (190 ms of 216 ms per chart); parsing is 7%, all other features under 5%. Hand assignments are cached per chart (data/cache/strokes), so rebuilds that don't touch sticking run about 20 times faster.

## Tried and dropped
- One hand burst, stamina and syncopation axes: no measurable value (Spearman 0.908 to 0.907, tiers 0.936 to 0.935, both inside noise of about 0.003 and 0.011). Switched off in tuning.AXES_ON, still measured.
- Coordination: the old version was mostly zero. Rebuilt as simultaneous syncopation across limbs (min of kick and hand rates of offbeat and new-rhythm notes); alone it predicts 0.75, but dropping it costs nothing.
- To close the chops gap: a rhythm subdivision-switch axis, contrast, groove measures (novelty chunks, bar similarity, LZ76 phrase complexity), a signed style term. None closed it. Limb-order novelty is the strongest single feature for it but redundant in the full model.
- GBM ceiling: an unconstrained gradient-boosted model gets 0.919 to 0.921 (tiers 0.941); monotone-constrained gets 0.907, the same as ours. So the axis model leaves little on the table with these features; new information has to come from new features, not a fancier fit.

## Measuring bugs found
- Rates divided by near-zero time: John Cage 4'33" (433,433 BPM tempo map, one note) read as density 1,264 and rated near the top. Fixed by flooring density chunks at 0.5 s and run gaps at 15 ms. Notes stacked 1 ms apart had the same flaw in run speed.

## Data facts
- DMBot leaderboard export knows 27,535 charts; 18,558 have drums and at least one score; we have 13,224 of those. Missing: Rock Band Network (849 played), RB3 and RB4 era DLC (about 1,200), and other versions of songs we have (e.g. Rush YYZ, 51 scores).
- Tournament bracket start dates come from data/results (Challonge headers). Icebreakers run at the end of their named year (IB23 started 2023-12-09).
- Drummer's Monthly 1 to 3 and Icebreaker 2022 aren't on the NAS drive; they were extracted from Google Drive zips into data/dmt.
- The NAS has a plocate index (rebuilt nightly about 1:30am). Walking the NAS (find, rglob) is slow over SMB and over bazzite's virtiofs mount; use plocate lists and local copies.

## Infrastructure
- bazzite (VM 122 on nasmox, 8 threads) runs the heavy work: repo at ~/drumchotic, git remote `bazzite` from the Mac, venv, data/charts as a local copy of notes and ini only (2.9 GB). A full feature build of 31,898 charts took about 20 min on the Mac.
