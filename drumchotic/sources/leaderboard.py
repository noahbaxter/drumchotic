"""DMBot leaderboard export: one row per song, scores as a JSON column."""
import csv
import json
from dataclasses import dataclass
from pathlib import Path

csv.field_size_limit(1 << 30)


@dataclass(frozen=True)
class Score:
    md5: str
    user: str           # Discord user id
    username: str
    percent: int
    fc: bool
    play_count: int


@dataclass(frozen=True)
class Song:
    md5: str
    name: str
    artist: str
    notes: int          # expert drum note count, 0 if unknown
    diff_drums: int     # charter's rating, -1 if unknown
    scores: tuple


def _expert_drum_notes(raw):
    for nc in json.loads(raw or '[]'):
        if nc.get('instrument') == 'drums' and nc.get('difficulty') == 'expert':
            return nc['count']
    return 0


def load(path, min_scores=1):
    songs = {}
    with Path(path).open(newline='') as f:
        for r in csv.DictReader(f):
            if int(r['scores_count'] or 0) < min_scores:
                continue
            scores = tuple(
                Score(r['md5'], s['user_id'], s['username'], s['percent'], bool(s['is_fc']), s.get('play_count') or 0)
                for s in json.loads(r['leaderboard'] or '[]')
                if s.get('speed') == 100
            )
            diff = json.loads(r['difficulties'] or '{}').get('drums', -1)
            songs[r['md5']] = Song(r['md5'], r['name'], r['artist'],
                                   _expert_drum_notes(r['note_counts']), diff, scores)
    return songs
