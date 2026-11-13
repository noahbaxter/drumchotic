"""Every knob that shapes a difficulty score, in one place. After editing, run
    scripts/run.sh
Anything above the COMBINE section changes what gets measured from a chart, so
that run re-measures every chart (~45s); the feature caches key on this file's
text up to the COMBINE marker. COMBINE and PLAYERS knobs only refit (~15s).
"""

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
# "Fastest run of N notes" lengths for kicks, both hands and one hand: up to BURST_MAX is a
# burst, longer is stamina.
RUNS = (4, 8, 16, 32, 64)
BURST_MAX = 8
# Speed: the most notes (chords count each note) in any window this long.
SPEED_WINDOW_S = 1
# Density: notes/s per chunk of this many quarter notes. A fixed tick span, so 3/16 and 13/4
# bars weigh the same; chunks with no notes are silence and skipped.
DENSITY_BEATS = 4
# No rate may come from time spans shorter than anyone could play: a density chunk counts as at
# least MIN_CHUNK_S long (4 beats only get shorter above 480 BPM, so joke tempo maps can't turn one
# note into thousands of notes/s), and each gap in a run as at least MIN_GAP_MS (about 67 notes/s,
# past any limb, so stacked or near-stacked notes can't either).
MIN_CHUNK_S = 0.5
MIN_GAP_MS = 15.0
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

# ---- COMBINE: how axis scores become one difficulty (drumchotic/fit/axes.py)
# How axes add up. 1 = plain sum (being decent at everything adds up).
# Higher = the hardest axis dominates (2 ~ moderate, 4+ ~ close to "only the worst axis counts").
# 2: difficulty is the length of the chart's axis vector, so being hard two ways adds up.
# Powers 1 to 3 all fit the leaderboard equally well; this one is a judgement call.
AXIS_POWER = 2.0
# Manual multiplier on each axis after the fit. 1 = trust the data; raise to make an axis
# matter more than the scores say, 0 to switch it off. Applied before AXIS_POWER.
# Axes not listed stay at 1, e.g. {'kick stamina': 1.5}.
AXIS_SCALE = {}
# Which features feed each axis.
AXES = {
    'speed': ['max_nps'],
    'density': [f'density_p{int(q * 100)}' for q in DENSITY_QUANTILES] + [f'density_w{SUSTAINED_WINDOW_S}'],
    'endurance': [f'endurance_{k}_n{n}' for k in ('share', 'longest') for n in ENDURANCE_NPS],
}
# Kicks, both hands and one hand each get a burst (short runs, densest second), stamina (long
# runs, densest 4s and 16s) and syncopation (off the 8th grid, new rhythms) axis.
for _limb, _label in (('kick', 'kick'), ('hands', 'hand'), ('onehand', 'one hand')):
    AXES[f'{_label} burst'] = ([f'run{n}_{_limb}' for n in RUNS if n <= BURST_MAX]
                               + [f'nps_{_limb}_w{w}' for w in WINDOWS_S if w <= 1])
    AXES[f'{_label} stamina'] = ([f'run{n}_{_limb}' for n in RUNS if n > BURST_MAX]
                                 + [f'nps_{_limb}_w{w}' for w in WINDOWS_S if w > 1])
    AXES[f'{_label} syncopation'] = [f'{_limb}_{k}_w{w}' for k in ('offbeat', 'novel') for w in WINDOWS_S]
AXES['kick syncopation'] += [f'kick_alone_w{w}' for w in WINDOWS_S]
AXES.update({
    # kit distance moved and cymbal/drum switches: they move together, so one axis
    'movement': [f'{k}_w{w}' for k in ('travel', 'cymswitch') for w in WINDOWS_S],
    'sticking': [f'sticking_w{w}' for w in WINDOWS_S],
    'linear': [f'linear_w{w}' for w in WINDOWS_S],
    # feet and hands both syncopated at the same moment
    'coordination': [f'coord_{k}_w{w}' for k in ('offbeat', 'novel') for w in WINDOWS_S],
    # new pad patterns, new limb orders, and new limb orders played one limb at a time
    'variety': [f'{k}_w{w}' for k in ('novel', 'limb_novel', 'limb_novel_single') for w in WINDOWS_S],
})
# Which axes are on. False leaves it out of the model, the reasons and every report; everything
# refits on the next run. One hand is off because it adds nothing measurable: without it
# held-out Spearman 0.908 -> 0.907, tiers 0.936 -> 0.935.
AXES_ON = {
    'speed':                True,
    'density':              True,
    'endurance':            True,
    'kick burst':           True,
    'kick stamina':         True,
    'kick syncopation':     True,
    'hand burst':           True,
    'hand stamina':         True,
    'hand syncopation':     True,
    'one hand burst':       False,
    'one hand stamina':     False,
    'one hand syncopation': False,
    'movement':             True,
    'sticking':             True,
    'linear':               True,
    'coordination':         True,
    'variety':              True,
}
assert set(AXES_ON) == set(AXES), f'AXES_ON must list every axis: {sorted(set(AXES) ^ set(AXES_ON))}'
AXES = {a: ks for a, ks in AXES.items() if AXES_ON[a]}
# Accents and ghosts only add bonus score: a hit with the wrong dynamic still counts, so they
# never change percent. True rates charts for score chasing and adds the dynamics axis.
DYNAMICS = False
if DYNAMICS:
    AXES['dynamics'] = ['dynamics_w1', 'dynamics_w4', 'dynamics_w16']
# Each feature can bend upward above these quantiles (lets the extreme end climb faster).
KNOTS = (0.5, 0.75, 0.9)
# Shrinks axis weights toward 0; keeps near-duplicate features from fighting.
RIDGE = 1e-3
# Charts need this many leaderboard scores to be used as training targets.
MIN_SCORES = 5
# ...and this many notes: on tiny charts one miss swings the percent too far.
MIN_NOTES = 200

# ---- PLAYERS: the leaderboard fit that produces training targets (drumchotic/fit/players.py)
# Pull on chart and player terms toward 0 (bigger = more cautious with few scores).
PRIOR = 1.0
# Scores this many deviations worse than expected get downweighted (bad runs, wrong difficulty).
ROBUST = 1.5
# Scores under this percent are ignored outright: quits, wrong difficulty, single pedal on 2x.
MIN_PERCENT = 70
# Tournament finishes relative to leaderboard scores. A nudge, not ground truth.
T_WEIGHT = 5.0
