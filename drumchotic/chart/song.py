import hashlib
from pathlib import Path

from . import ini, parse_chart, parse_mid

NOTE_FILES = ('notes.mid', 'notes.chart')   # notes.mid wins when both exist


def notes_file(folder):
    folder = Path(folder)
    return next((folder / n for n in NOTE_FILES if (folder / n).exists()), None)


def load(folder):
    """Song folder -> (DrumChart or None, song.ini dict)."""
    meta = ini.read(Path(folder) / 'song.ini')
    path = notes_file(folder)
    if path is None:
        return None, meta
    parser = parse_mid if path.suffix == '.mid' else parse_chart
    return parser.load(path, meta), meta


def title(meta, folder):
    """'Artist - Name' from song.ini, the folder name when both are blank."""
    return f"{meta.get('artist', '').strip()} - {meta.get('name', '').strip()}".strip(' -') or Path(folder).name


def md5(folder):
    """MD5 of the notes file, the key leaderboards use for a chart."""
    path = notes_file(folder)
    return hashlib.md5(path.read_bytes()).hexdigest() if path else None
