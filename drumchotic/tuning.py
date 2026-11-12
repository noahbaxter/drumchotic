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
# Notes inside roll lanes: 'half' keeps every other note (the speed actually needed
# to not miss), 'skip' drops them, 'full' counts every note.
ROLL_MODE = 'half'
# 2x kick notes are opt-in (Expert+). '2x' counts them, as if played on a double pedal;
# '1x' drops them, as if played on Expert with one pedal.
KICK_MODE = '2x'
