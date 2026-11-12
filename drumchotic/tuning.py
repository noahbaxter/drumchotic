"""Every knob that shapes a difficulty score, in one place."""

# ---- STICKING: how hands get assigned (drumchotic/measure/sticking.py) ------
# One hand hitting this often (ms apart) costs 1; cost grows with the cube of speed. A hand's
# speed is averaged over its last two gaps, so a double played on the rebound costs like alternating.
HAND_SPEED_MS = 110.0
# A hand moving across the kit with this long to get there costs about 1 per unit of distance.
HAND_TRAVEL_MS = 150.0
# Left hand pays this much more than the right for the same speed.
LEFT_WEAKNESS = 1.15
# Speed cost multiplier by position in a run of same-hand strokes: 1st, 2nd, 3rd, 4th onward.
# Doubles are as easy as singles; three in a row is where it gets hard.
RUN_FACTOR = (1.0, 1.0, 3.0, 8.0)
# The run multiplier applies in full at HAND_SPEED_MS and faster; slower, it fades with the
# hand's speed to this power, so a one-hand ride pattern at moderate tempo stays cheap.
RUN_FADE = 4.0
# Crossing: cost per kit unit the left hand sits right of the right hand...
CROSS_COST = 1.0
# ...doubled when the crossing stroke comes this soon after that hand's last hit (ms).
CROSS_MS = 150.0
# Share of the crossing cost left when one hand is on a cymbal and the other on a drum: the
# arms pass at different heights. The right hand on the hi-hat is the normal grip and counts
# as if it sat at the snare.
CROSS_CLEARED = 0.5
# Left hand reaching right of this x (kit units, mid tom) pays this much per unit, per stroke,
# crossed or not: the left hand doesn't live on the floor tom or the ride.
LEFT_REACH_X = 1.0
REACH_COST = 3.0
# Cymbals sit this far above the drums (kit units), so reaching one is that much further.
CYMBAL_HEIGHT = 0.5
# Yellow cymbals may go to a left crash instead of the hi-hat, whichever plays easier.
LEFT_CRASH = True

# ---- FEATURES: what gets measured from a chart (drumchotic/measure/features.py)
# Sliding windows (seconds): 1 = burst, 4 = section, 16 = sustained.
WINDOWS_S = (1, 4, 16)
# "Fastest run of N notes" lengths for kicks, both hands and one hand.
RUNS = (4, 8, 16, 32, 64)
# Speed: the most notes (chords count each note) in any window this long.
SPEED_WINDOW_S = 1
# Density: notes/s per chunk of this many quarter notes. A fixed tick span, so 3/16 and 13/4
# bars weigh the same; chunks with no notes are silence and skipped.
DENSITY_BEATS = 4
# Density at these quantiles of the chart's playing time (chunks weighted by duration):
# p50 = half the time you're playing, it's at least this dense.
DENSITY_QUANTILES = (0.5, 0.75, 0.9)
# Density also takes the densest stretch this long (s): what you have to get through at its worst.
SUSTAINED_WINDOW_S = 30
# Endurance: share of playing time, and longest unbroken stretch, at or above each of these
# notes/s (same chunks as density). Neither grows just because a chart is long.
ENDURANCE_NPS = (8, 10, 12)
# A hand move counts fully as travel when the gap is shorter than this (ms).
TRAVEL_CLOSE_MS = 250.0
# Kick-only and drum-only onsets alternating faster than this (ms) count as linear playing.
LINEAR_MS = 100
# How many onsets back a pattern has to be seen before it stops counting as new (variety).
NOVEL_HISTORY = 32
# Variety also counts new limb orders (kick / left / right, from the sticking): this many
# onsets make up one pattern of limbs.
LIMB_GRAM = 6
# How much a note inside a repeating pattern counts toward density, travel and cymbal
# switching (1 = same as a new pattern). Grooves you lock into are easier to sustain than
# the same density of changing material. Raw speed (fastest runs) is never discounted.
REPEAT_WEIGHT = 0.7
# Notes inside roll lanes: 'half' keeps every other note (the speed actually needed
# to not miss), 'skip' drops them, 'full' counts every note.
ROLL_MODE = 'half'
# 2x kick notes are opt-in (Expert+). '2x' counts them, as if played on a double pedal;
# '1x' drops them, as if played on Expert with one pedal.
KICK_MODE = '2x'

# ---- PLAYERS: the leaderboard fit that produces training targets (drumchotic/fit/players.py)
# Pull on chart and player terms toward 0 (bigger = more cautious with few scores).
PRIOR = 1.0
# Scores this many deviations worse than expected get downweighted (bad runs, wrong difficulty).
ROBUST = 1.5
# Scores under this percent are ignored outright: quits, wrong difficulty, single pedal on 2x.
MIN_PERCENT = 70
# Tournament finishes relative to leaderboard scores. A nudge, not ground truth.
T_WEIGHT = 5.0
