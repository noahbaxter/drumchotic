import re
from pathlib import Path

LINE = re.compile(r'^\s*([^=;#\[]+?)\s*=\s*(.*?)\s*$')
TRUE = {'1', 'true', 'yes'}
BOOL_KEYS = {'pro_drums', 'five_lane_drums'}
INT_KEYS = {'diff_drums', 'diff_drums_real'}


def read(path):
    """song.ini -> dict with lowercased keys. Bool/int keys used by drumchotic are converted."""
    try:
        raw = Path(path).read_bytes()
    except FileNotFoundError:
        return {}
    try:
        text = raw.decode('utf-8-sig')
    except UnicodeDecodeError:
        text = raw.decode('cp1252', errors='replace')    # older charting tools save Windows-1252
    out = {}
    for line in text.splitlines():
        m = LINE.match(line)
        if not m:
            continue
        key, value = m.group(1).strip().lower(), m.group(2)
        if key in BOOL_KEYS:
            out[key] = value.strip().lower() in TRUE
        elif key in INT_KEYS:
            try:
                out[key] = int(value)
            except ValueError:
                pass
        else:
            out[key] = value
    return out
