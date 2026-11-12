"""A local HTML page for checking the model by eye: model vs players for every scored chart,
each chart's axis profile against the library and against charts of similar difficulty, and
the worst disagreements. Written next to the plots on every render.

python -m drumchotic.page            writes data/plots/<latest>/check.html
"""
import json
import sys

import numpy as np
from scipy.stats import spearmanr

from . import pipeline
from .fit.metrics import tier_accuracy
from .plots import PLOTS_DIR, latest_render
from .rating import PEERS
from .tuning import AXES, MIN_SCORES

FEW_SCORES = 10
LONG_S = 300


def build(r):
    ms = list(r.library) + [m for m in r.anchors if m not in r.library]
    lib = np.array([m in r.library for m in ms])
    axes = list(AXES)
    a = np.array([[r.axes[x][m] for m in ms] for x in axes])                       # [axis, chart]
    lib_sorted = [np.sort(a[i, lib]) for i in range(len(axes))]
    pct = np.array([np.searchsorted(lib_sorted[i], a[i], side='right') / lib.sum() * 100
                    for i in range(len(axes))])
    pred = np.array([r.pred[m] for m in ms])
    by_pred = np.argsort(pred)
    peer = np.zeros_like(pct)
    for pos, c in enumerate(by_pred):
        window = by_pred[max(0, pos - PEERS):pos + PEERS + 1]
        for i in range(len(axes)):
            peer[i, c] = (a[i, window] < a[i, c]).mean() * 100
    sh = r.shares(ms)
    total = np.maximum(sum(sh.values()), 1e-12)
    tier = {m: lab.tier for lab, m in r.labels}
    pool = set(r.pool)
    charts = []
    for j, m in enumerate(ms):
        s = r.songs.get(m)
        charts.append({
            'n': r.name(m),
            'p': round(float(pred[j]), 3),
            'h': round(float(r.held_out[m]), 3) if m in pool else None,
            'l': round(float(r.fit.difficulty[m]), 3) if m in pool else None,
            's': len(s.scores) if s else 0,
            'len': round(r.features[m]['length_s']),
            'rolls': int(r.features[m]['rolls']),
            't': tier.get(m),
            'anchor': m not in r.library,
            'pct': [round(float(v)) for v in pct[:, j]],
            'peer': [round(float(v)) for v in peer[:, j]],
            'sh': [round(float(sh[x][j] / total[j] * 100)) for x in axes],
        })
    sp_sd, tier_sd = r.noise()
    stats = {
        'spearman': round(float(spearmanr(*r.pool_scores())[0]), 3), 'spearman_sd': round(sp_sd, 3),
        'tiers': round(float(tier_accuracy(r.labels, r.tier_pred)), 3), 'tiers_sd': round(tier_sd, 3),
        'pool': len(r.pool), 'library': int(lib.sum()), 'min_scores': MIN_SCORES,
        'few': FEW_SCORES, 'long': LONG_S, 'peers': PEERS,
    }
    return {'axes': axes, 'stats': stats, 'charts': charts}


def write(r, path):
    data = json.dumps(build(r), separators=(',', ':'))
    path.write_text(TEMPLATE.replace('__DATA__', data))
    return path


def main(argv):
    out = latest_render() or PLOTS_DIR
    out.mkdir(parents=True, exist_ok=True)
    print(f'page -> {write(pipeline.run(), out / "check.html")}')


TEMPLATE = r'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Drumchotic model check</title>
<style>
/* layout: scatter and chart inspector side by side, outlier tables below */
:root {
  --bg: #f3f6fb; --panel: #ffffff; --ink: #14213d; --ink-2: #51607d; --line: #dbe3f0;
  --accent: #f0436a; --cool: #0fb5a6; --dot: #7d8db0; --hi: #ffb703;
  --mono: ui-monospace, "SF Mono", Menlo, monospace;
  --sans: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
}
@media (prefers-color-scheme: dark) {
  :root { --bg: #0e1726; --panel: #16223a; --ink: #f1f5fb; --ink-2: #a9b8d4; --line: #263552;
          --accent: #ff5c84; --cool: #2ee6c8; --dot: #8ea3cc; --hi: #ffc93c; color-scheme: dark; }
}
* { box-sizing: border-box; }
body { margin: 0; background: var(--bg); color: var(--ink); font: 14px/1.45 var(--sans);
       padding: 20px max(16px, env(safe-area-inset-left)) 40px max(16px, env(safe-area-inset-right)); }
h1 { font-size: 20px; margin: 0 0 4px; }
h2 { font-size: 15px; margin: 0 0 10px; }
.sub { color: var(--ink-2); margin: 0 0 16px; }
.num { font-family: var(--mono); font-variant-numeric: tabular-nums; }
.row { display: grid; grid-template-columns: minmax(0, 3fr) minmax(0, 2fr); gap: 16px; }
@media (max-width: 900px) { .row { grid-template-columns: minmax(0, 1fr); } }
.panel { background: var(--panel); border: 1px solid var(--line); border-radius: 8px; padding: 14px; min-width: 0; }
.controls { display: flex; flex-wrap: wrap; gap: 12px; align-items: center; margin-bottom: 10px; color: var(--ink-2); }
.controls input[type=search] { flex: 1; min-width: 160px; padding: 6px 8px; border: 1px solid var(--line);
  border-radius: 6px; background: var(--bg); color: var(--ink); font: inherit; }
canvas { width: 100%; height: 620px; display: block; cursor: crosshair; }
@media (max-width: 600px) { canvas { height: 380px; } }
#tip { position: fixed; pointer-events: none; background: var(--ink); color: var(--bg); padding: 4px 8px;
       border-radius: 4px; font-size: 12px; max-width: 420px; display: none; z-index: 5; line-height: 1.5; }
.facts { display: grid; grid-template-columns: repeat(auto-fill, minmax(110px, 1fr)); gap: 8px 12px; margin: 10px 0 14px; }
.fact b { display: block; font: 600 16px var(--mono); }
.fact span { color: var(--ink-2); font-size: 12px; }
.axis { display: grid; grid-template-columns: 96px minmax(0, 1fr) 44px; gap: 8px; align-items: center; margin: 5px 0; }
.axis .name { color: var(--ink-2); font-size: 13px; }
.bar { position: relative; height: 14px; background: var(--bg); border-radius: 3px; }
.bar .lib { position: absolute; left: 0; top: 0; bottom: 0; background: var(--cool); opacity: .55; border-radius: 3px; }
.bar .peer { position: absolute; top: -3px; bottom: -3px; width: 3px; background: var(--accent); border-radius: 2px; }
.axis .share { font: 12px var(--mono); text-align: right; color: var(--ink-2); }
.legend { color: var(--ink-2); font-size: 12px; margin: 8px 0 0; }
.legend i { display: inline-block; width: 10px; height: 10px; vertical-align: -1px; margin-right: 4px; border-radius: 2px; }
.reasons { margin: 12px 0 0; padding-left: 18px; }
.tables { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); gap: 16px; margin-top: 16px; }
@media (max-width: 900px) { .tables { grid-template-columns: minmax(0, 1fr); } }
.scroll { overflow-x: auto; }
table { border-collapse: collapse; width: 100%; font-size: 13px; }
th { text-align: left; color: var(--ink-2); font-weight: 500; border-bottom: 1px solid var(--line); padding: 4px 6px; }
td { padding: 4px 6px; border-bottom: 1px solid var(--line); vertical-align: top; }
td.r, th.r { text-align: right; }
tr.pick { cursor: pointer; } tr.pick:hover { background: var(--bg); }
tr.sel { background: var(--bg); }
.tag { display: inline-block; font-size: 11px; padding: 0 5px; margin: 0 3px 2px 0; border: 1px solid var(--line);
       border-radius: 3px; color: var(--ink-2); white-space: nowrap; }
.empty { color: var(--ink-2); }
</style>
</head>
<body>
<h1>Drumchotic model check</h1>
<p class="sub" id="summary"></p>

<div class="row">
  <div class="panel">
    <h2>Model vs players</h2>
    <div class="controls">
      <label>min scores <input type="range" id="minScores" min="5" max="40" value="5"> <span class="num" id="minScoresVal">5</span></label>
      <input type="search" id="search" placeholder="Find a chart">
    </div>
    <canvas id="scatter"></canvas>
    <p class="legend">x: leaderboard difficulty from player scores. y: model prediction made without seeing that chart.
      Dashed line: agreement. Coloured when they disagree by 0.5 or more:
      <i style="background:var(--accent)"></i>model rates it harder <i style="background:var(--cool)"></i>players find it harder.</p>
  </div>
  <div class="panel" id="inspector"><p class="empty">Click a dot or a table row to inspect a chart.</p></div>
</div>

<div class="tables">
  <div class="panel"><h2>Model rates harder than players find it</h2><div class="scroll"><table id="over"></table></div></div>
  <div class="panel"><h2>Players find harder than the model rates it</h2><div class="scroll"><table id="under"></table></div></div>
</div>
<div id="tip"></div>

<script>
const D = __DATA__;
const S = D.stats, AX = D.axes;
const css = n => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
document.getElementById('summary').innerHTML =
  `Held-out Spearman <b class="num">${S.spearman}</b> (noise ±${S.spearman_sd}) over ${S.pool} scored charts. ` +
  `DMT tiers in order <b class="num">${S.tiers}</b> (noise ±${S.tiers_sd}). Library ${S.library} charts.`;

const scored = D.charts.filter(c => c.l !== null);
let minScores = 5, query = '', selected = null, pts = [];
const DOT_PX = 4;

function tags(c) {
  const t = [];
  if (c.s < S.few) t.push(`${c.s} scores`);
  if (c.len > S.long) t.push(`${Math.round(c.len / 60)} min`);
  if (c.rolls) t.push(`${c.rolls} roll lanes`);
  if (c.t) t.push(`DMT tier ${c.t}`);
  return t.map(x => `<span class="tag">${x}</span>`).join('');
}

const cv = document.getElementById('scatter'), ctx = cv.getContext('2d');
function draw() {
  const dpr = window.devicePixelRatio || 1, w = cv.clientWidth, h = cv.clientHeight;
  cv.width = w * dpr; cv.height = h * dpr; ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, w, h);
  const vis = scored.filter(c => c.s >= minScores);
  const all = vis.flatMap(c => [c.l, c.h]);
  const lo = Math.min(...all), hi = Math.max(...all), pad = 36;
  const sx = v => pad + (v - lo) / (hi - lo) * (w - pad - 8), sy = v => h - pad - (v - lo) / (hi - lo) * (h - pad - 8);
  ctx.strokeStyle = css('--line'); ctx.fillStyle = css('--ink-2'); ctx.font = '11px ' + css('--mono'); ctx.lineWidth = 1;
  for (let v = Math.ceil(lo); v <= hi; v++) {
    ctx.beginPath(); ctx.moveTo(sx(v), h - pad); ctx.lineTo(sx(v), 8); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(pad, sy(v)); ctx.lineTo(w - 8, sy(v)); ctx.stroke();
    ctx.fillText(v, sx(v) - 3, h - pad + 14); ctx.fillText(v, pad - 18, sy(v) + 4);
  }
  ctx.setLineDash([4, 4]); ctx.strokeStyle = css('--ink-2');
  ctx.beginPath(); ctx.moveTo(sx(lo), sy(lo)); ctx.lineTo(sx(hi), sy(hi)); ctx.stroke(); ctx.setLineDash([]);
  const hot = css('--accent'), cool = css('--cool'), dot = css('--dot');
  const q = query.toLowerCase();
  pts = vis.map(c => ({c, x: sx(c.l), y: sy(c.h)}));
  for (const p of pts) {
    const d = p.c.h - p.c.l, strong = Math.min(Math.abs(d) / 1.2, 1);
    ctx.globalAlpha = q && !p.c.n.toLowerCase().includes(q) ? 0.08 : 0.45 + 0.5 * strong;
    ctx.fillStyle = Math.abs(d) < 0.5 ? dot : d > 0 ? hot : cool;
    ctx.beginPath(); ctx.arc(p.x, p.y, DOT_PX, 0, 7); ctx.fill();
  }
  ctx.globalAlpha = 1;
  if (selected && selected.l !== null) {
    ctx.strokeStyle = css('--hi'); ctx.lineWidth = 2.5;
    ctx.beginPath(); ctx.arc(sx(selected.l), sy(selected.h), DOT_PX + 6, 0, 7); ctx.stroke();
  }
  ctx.fillStyle = css('--ink-2');
  ctx.fillText('leaderboard', w - 80, h - pad - 6);
  ctx.save(); ctx.translate(12, 70); ctx.rotate(-Math.PI / 2); ctx.fillText('model', 0, 0); ctx.restore();
}

const HIT_PX = 18, TIP_MAX = 6;
function near(ev) {
  const r = cv.getBoundingClientRect(), x = ev.clientX - r.left, y = ev.clientY - r.top;
  return pts.map(p => ({c: p.c, d: (p.x - x) ** 2 + (p.y - y) ** 2}))
    .filter(p => p.d <= HIT_PX * HIT_PX).sort((a, b) => a.d - b.d).map(p => p.c);
}
const nearest = ev => near(ev)[0] || null;
const tip = document.getElementById('tip');
cv.addEventListener('mousemove', ev => {
  const cs = near(ev);
  if (!cs.length) { tip.style.display = 'none'; return; }
  tip.style.display = 'block'; tip.style.left = ev.clientX + 14 + 'px'; tip.style.top = ev.clientY + 14 + 'px';
  tip.innerHTML = cs.slice(0, TIP_MAX).map((c, i) =>
    `${i ? '' : '<b>'}${c.n}${i ? '' : '</b>'} · model ${c.h.toFixed(2)}, players ${c.l.toFixed(2)}`).join('<br>')
    + (cs.length > TIP_MAX ? `<br>+${cs.length - TIP_MAX} more nearby` : '');
});
cv.addEventListener('mouseleave', () => tip.style.display = 'none');
cv.addEventListener('click', ev => { const c = nearest(ev); if (c) select(c); });

function select(c) {
  selected = c; draw(); renderTables();
  const diff = c.h === null ? '' : `<div class="fact"><b>${(c.h - c.l > 0 ? '+' : '') + (c.h - c.l).toFixed(2)}</b><span>model minus players</span></div>`;
  const order = AX.map((a, i) => i).sort((i, j) => c.sh[j] - c.sh[i]);
  const reasons = AX.map((a, i) => ({a, p: c.peer[i]})).filter(x => x.p >= 85).sort((x, y) => y.p - x.p).slice(0, 3);
  document.getElementById('inspector').innerHTML = `
    <h2>${c.n}</h2>
    <div>${tags(c)}${c.anchor ? '<span class="tag">suggested superhuman</span>' : ''}</div>
    <div class="facts">
      <div class="fact"><b>${c.p.toFixed(2)}</b><span>model score</span></div>
      ${c.l === null ? '' : `<div class="fact"><b>${c.l.toFixed(2)}</b><span>players (leaderboard)</span></div>`}
      ${diff}
      <div class="fact"><b>${c.s}</b><span>scores</span></div>
      <div class="fact"><b>${Math.floor(c.len / 60)}:${String(c.len % 60).padStart(2, '0')}</b><span>length</span></div>
    </div>
    ${order.map(i => `<div class="axis"><span class="name">${AX[i]}</span>
      <div class="bar" title="library percentile ${c.pct[i]}, among similar difficulty ${c.peer[i]}">
        <div class="lib" style="width:${c.pct[i]}%"></div><div class="peer" style="left:calc(${c.peer[i]}% - 1px)"></div></div>
      <span class="share">${c.sh[i]}%</span></div>`).join('')}
    <p class="legend"><i style="background:var(--cool);opacity:.55"></i>percentile in the whole library
      <i style="background:var(--accent)"></i>percentile among the ${S.peers * 2} charts closest in difficulty.
      Right column: share of this chart's score.</p>
    ${reasons.length ? `<p style="margin:12px 0 0"><b>Stands out for its difficulty:</b></p><ul class="reasons">${
      reasons.map(x => `<li>${x.a}: harder than ${x.p}% of charts at this level</li>`).join('')}</ul>`
      : '<p class="legend">Nothing stands out against charts of similar difficulty.</p>'}`;
}

function renderTables() {
  const vis = scored.filter(c => c.s >= minScores && (!query || c.n.toLowerCase().includes(query.toLowerCase())));
  const rows = list => `<tr><th>chart</th><th class="r">model</th><th class="r">players</th><th class="r">gap</th></tr>` +
    list.map((c, k) => `<tr class="pick${c === selected ? ' sel' : ''}" data-k="${k}"><td>${c.n}<br>${tags(c)}</td>
      <td class="r num">${c.h.toFixed(2)}</td><td class="r num">${c.l.toFixed(2)}</td>
      <td class="r num">${(c.h - c.l > 0 ? '+' : '') + (c.h - c.l).toFixed(2)}</td></tr>`).join('');
  const sorted = vis.slice().sort((a, b) => (b.h - b.l) - (a.h - a.l));
  const over = sorted.slice(0, 25), under = sorted.slice(-25).reverse();
  for (const [id, list] of [['over', over], ['under', under]]) {
    const t = document.getElementById(id); t.innerHTML = rows(list);
    t.querySelectorAll('tr.pick').forEach(tr => tr.addEventListener('click', () => select(list[+tr.dataset.k])));
  }
}

document.getElementById('minScores').addEventListener('input', e => {
  minScores = +e.target.value; document.getElementById('minScoresVal').textContent = minScores; draw(); renderTables();
});
document.getElementById('search').addEventListener('input', e => { query = e.target.value; draw(); renderTables(); });
window.addEventListener('resize', draw);
draw(); renderTables();
select(scored.slice().sort((a, b) => (a.h - a.l) - (b.h - b.l))[0]);   // open on the worst underrated chart
</script>
</body>
</html>
'''

if __name__ == '__main__':
    main(sys.argv[1:])
