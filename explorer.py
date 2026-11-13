"""Network board: final plan view and guided replay of the selected augmenting paths.

Presentation only; it never changes state. Builds a self-contained HTML page
from optimizer.trace_restock_plan. Integers travel as strings and are handled as
BigInt in the page, so exact large values survive. The replay shows the paths
the optimizer chose, not the shortest-path search that found them.
"""
import json
from optimizer import trace_restock_plan
from theme import css_variables, font_face_css
from ui_model import labels

MAX_LOCATIONS = 12   # per side; beyond this the board is unreadable
MAX_PATHS = 60       # replay length cap across all items


def build_payload(state, *, autoplay=False):
    """Return (payload dict, reason). reason is user-facing text when the board cannot show."""
    if len(state.warehouses) > MAX_LOCATIONS or len(state.stores) > MAX_LOCATIONS:
        return None, (f'The network board supports up to {MAX_LOCATIONS} warehouses and '
                      f'{MAX_LOCATIONS} stores. Reduce the network to explore it.')
    trace = trace_restock_plan(state)
    if not trace:
        return None, 'There is nothing to ship, so there is no plan to draw.'
    warehouses, stores = tuple(state.warehouses), tuple(state.stores)
    nw, ns = len(warehouses), len(stores)
    items, total_paths, shown = [], sum(len(t['paths']) for t in trace), 0
    for record in trace:
        paths = []
        for path in record['paths']:
            if shown >= MAX_PATHS:
                break
            middle = path['vertices'][1:-1]  # drop source and sink
            steps = []
            for u, v in zip(middle, middle[1:]):
                if u < nw:   # warehouse → store: new or extra allocation
                    steps.append({'w': u, 's': v - nw, 'reverse': False})
                else:        # store → warehouse: undo part of an earlier allocation
                    steps.append({'w': v, 's': u - nw, 'reverse': True})
            paths.append({'steps': steps, 'amount': str(path['amount']),
                          'cost': str(path['path_cost']),
                          'potentials': None if path['potentials'] is None
                          else [str(p) for p in path['potentials'][:nw + ns]]})
            shown += 1
        items.append({'name': labels(state.items)[record['item_id']],
                      'stock': [str(x) for x in record['stock']],
                      'need': [str(x) for x in record['need']], 'paths': paths,
                      'complete': len(paths) == len(record['paths'])})
        if shown >= MAX_PATHS:
            break
    payload = {
        'warehouses': [labels(state.warehouses)[w] for w in warehouses],
        'stores': [labels(state.stores)[s] for s in stores],
        'rates': [[str(state.shipping_costs_cents[w][s]) for s in stores] for w in warehouses],
        'items': items, 'shownPaths': shown, 'totalPaths': total_paths, 'autoplay': bool(autoplay),
    }
    return payload, None


def render_html(payload):
    data = json.dumps(payload, ensure_ascii=False).replace('</', '<\\/')
    return (_TEMPLATE.replace('__FONTS__', font_face_css())
            .replace('__TOKENS__', css_variables()).replace('__PAYLOAD__', data))


_TEMPLATE = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
__FONTS__
__TOKENS__
*{box-sizing:border-box}
html,body{margin:0;background:transparent;color:var(--mist);font-family:var(--body);
  font-variant-numeric:tabular-nums;-webkit-font-smoothing:antialiased}
.board{background:var(--harbor);border-radius:10px;padding:16px 18px 14px;
  background-image:radial-gradient(rgba(147,169,185,.13) 1px,transparent 1.2px);background-size:22px 22px}
.top{display:flex;align-items:flex-start;justify-content:space-between;gap:10px;flex-wrap:wrap}
.item{font:700 28px/1 var(--display);letter-spacing:-.01em;margin:0}
.where{color:var(--fog);font-size:15px;margin-top:5px}
.controls{display:flex;gap:6px;flex-wrap:wrap;margin-left:auto}
.title{display:grid;grid-template-columns:auto 1fr;align-items:center;column-gap:12px}
.title .where{grid-column:1/-1}
.chips{display:flex;gap:6px;flex-wrap:wrap}
.chips button{padding:3px 11px;min-height:28px;font-size:13.5px}
.chips[hidden]{display:none}
button{font:500 14px var(--body);color:var(--mist);background:transparent;border:1px solid var(--lane);
  border-radius:999px;padding:5px 12px;cursor:pointer;min-height:32px}
button:hover{border-color:var(--fog)}
button:disabled{opacity:.45;cursor:default}
button:focus-visible{outline:2px solid var(--glow);outline-offset:2px}
button[aria-pressed="true"]{background:var(--deck);border-color:var(--fog)}
button[hidden]{display:none}
svg{display:block;width:100%;overflow:visible;margin-top:6px}
.name{fill:var(--mist);font:600 17px var(--display)}
.sub{fill:var(--fog);font-size:13.5px}
.col{fill:var(--fog);font-size:13.5px}
.lane{fill:none;stroke:var(--lane);stroke-width:1.5}
.lane.used{stroke:var(--used)}
.flowlabel{fill:var(--mist);font-size:13px;font-weight:600;paint-order:stroke;stroke:var(--harbor);stroke-width:4px}
.rate{fill:var(--fog);font-size:12px;paint-order:stroke;stroke:var(--harbor);stroke-width:4px;display:none}
.rate.on{display:block}
.gbg{fill:var(--gauge)}
.gfill{fill:var(--gauge-fill);transition:width .6s ease}
.gfill.store{fill:var(--glow)}
.pulse{fill:none;stroke-linecap:round}
.caption{margin-top:4px;min-height:52px;font-size:19px;line-height:1.35;max-width:62ch}
.caption.undo{color:var(--undo-text)}
.tally{display:flex;gap:28px;margin-top:8px;align-items:baseline;flex-wrap:wrap}
.tally b{font:700 24px/1.1 var(--display);display:block}
.tally span{color:var(--fog);font-size:13.5px}
.ticks{display:flex;gap:4px;margin-left:auto;align-self:center;flex-wrap:wrap;max-width:50%}
.tick{width:14px;height:4px;border-radius:2px;background:var(--lane)}
.tick.done{background:var(--used)}.tick.now{background:var(--glow)}
.note{color:var(--fog);font-size:13px;margin-top:10px}
.details{border-top:1px solid var(--lane);margin-top:14px;padding-top:12px;
  display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:4px 28px}
.details[hidden]{display:none}
.details h3{font:600 18px var(--display);margin:0 0 4px}
.details p{color:var(--fog);font-size:13.5px;margin:4px 0 10px;line-height:1.4}
.details table{width:100%;border-collapse:collapse;font-size:14px;margin-bottom:10px}
.details td,.details th{text-align:left;padding:4px 0;border-bottom:1px solid var(--lane);font-weight:400}
.details th{color:var(--fog)}
.details .num{text-align:right}
.details .undo{color:var(--undo)}
@media (prefers-reduced-motion:reduce){.gfill{transition:none}}
</style></head><body>
<div class="board" id="board">
  <div class="top">
    <div class="title"><h2 class="item" id="item"></h2><div class="chips" id="chips" role="group" aria-label="Item"></div>
      <div class="where" id="where"></div></div>
    <div class="controls">
      <button id="prev" type="button" aria-label="Previous path" hidden>Previous</button>
      <button id="play" type="button" hidden>Pause</button>
      <button id="next" type="button" aria-label="Next path" hidden>Next</button>
      <button id="replay" type="button" hidden>Replay</button>
      <button id="inspect" type="button" aria-pressed="false" aria-controls="details">Details</button>
    </div>
  </div>
  <svg id="svg" role="img" aria-label="Warehouses on the left, stores on the right, routes between them"></svg>
  <div class="caption" id="caption" aria-live="polite"></div>
  <div class="tally">
    <div><b id="units">0</b><span id="unitsLabel">units planned</span></div>
    <div><b id="cost">$0.00</b><span id="costLabel">shipping cost</span></div>
    <div class="ticks" id="ticks" aria-hidden="true"></div>
  </div>
  <div class="note" id="note"></div>
  <section class="details" id="details" hidden aria-label="Algorithm details"></section>
</div>
<script>
const D = __PAYLOAD__;
const B = s => BigInt(s);
const NS = 'http://www.w3.org/2000/svg';
const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;
const $ = id => document.getElementById(id);
const esc = t => String(t).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const H_W = D.warehouses.map(esc), H_S = D.stores.map(esc);
const nw = D.warehouses.length, ns = D.stores.length, NI = D.items.length;

function money(c){ const neg = c < 0n; if (neg) c = -c;
  const d = (c/100n).toString().replace(/\B(?=(\d{3})+(?!\d))/g, ','); const r = (c%100n).toString().padStart(2,'0');
  return (neg ? '−$' : '$') + d + '.' + r; }
function count(n){ return n.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ','); }
function ratio(a,b){ return b === 0n ? 0 : Number(a*1000n/b)/1000; }

// ---------- pausable clock ----------
let paused = false, token = 0, running = false, animating = false;
class Stop extends Error {}
const frame = () => new Promise(r => requestAnimationFrame(r));
async function tween(ms, fn, t){
  let spent = 0, last = performance.now();
  if (reduce) ms = 0;
  while (true){
    if (t !== token) throw new Stop();
    const now = performance.now(); if (!paused) spent += now - last; last = now;
    const p = ms ? Math.min(1, spent/ms) : 1; fn(p);
    if (p >= 1) return; await frame();
  }
}
async function hold(ms, t){   // reading time is kept even with reduced motion
  let spent = 0, last = performance.now();
  while (spent < ms){ if (t !== token) throw new Stop(); await frame();
    const now = performance.now(); if (!paused) spent += now - last; last = now; }
  if (t !== token) throw new Stop();
}
const ease = p => p<.5 ? 4*p*p*p : 1 - Math.pow(-2*p+2,3)/2;

// ---------- model: position = (item k, paths applied j) ----------
let S, pos = {k:0, j:0}, mode = D.autoplay ? 'replay' : 'final', curPath = null;
function apply(st, P){ const amt = B(P.amount), first = P.steps[0], last = P.steps[P.steps.length-1];
  for (const x of P.steps) st.flow[x.w][x.s] += x.reverse ? -amt : amt;
  st.left[first.w] -= amt; st.got[last.s] += amt; st.units += amt; st.cost += amt * B(P.cost); }
function setPosition(k, j){
  const it = D.items[k];
  S = { k, it, stock: it.stock.map(B), left: it.stock.map(B), need: it.need.map(B), got: it.need.map(()=>0n),
        flow: D.warehouses.map(()=>D.stores.map(()=>0n)), units: 0n, cost: 0n, before: {units:0n, cost:0n} };
  for (let i=0; i<k; i++) for (const P of D.items[i].paths){ S.before.units += B(P.amount); S.before.cost += B(P.amount)*B(P.cost); }
  for (let p=0; p<j; p++) apply(S, it.paths[p]);
  pos = {k, j};
}

// ---------- layout + drawing ----------
let L = {};
function el(tag, attrs, parent){ const e = document.createElementNS(NS, tag);
  for (const k in attrs) e.setAttribute(k, attrs[k]); if (parent) parent.appendChild(e); return e; }
function laneD(w, s){ const a = L.w[w], b = L.s[s], m = (a.x + b.x)/2;
  return `M${a.x},${a.y} C${m},${a.y} ${m},${b.y} ${b.x},${b.y}`; }

function draw(){
  const svg = $('svg'); svg.innerHTML = '';
  const W = svg.clientWidth || 600, narrow = W < 520;
  const block = narrow ? Math.max(110, W*.3) : Math.min(200, W*.28), rowH = 70, top = 28;
  const rows = Math.max(nw, ns), H = top + rows*rowH;
  svg.setAttribute('viewBox', `0 0 ${W} ${H}`); svg.setAttribute('height', H);
  const yOf = (i, n) => top + (rows - n)*rowH/2 + i*rowH + rowH/2;
  L = { w: D.warehouses.map((_,i)=>({x:block+14, y:yOf(i,nw)})), s: D.stores.map((_,i)=>({x:W-block-14, y:yOf(i,ns)})) };
  el('text',{x:0,y:12,class:'col'},svg).textContent = 'Warehouses';
  el('text',{x:W,y:12,class:'col','text-anchor':'end'},svg).textContent = 'Stores';
  const lanes = el('g',{},svg); L.pulse = el('g',{},svg); const labelsG = el('g',{},svg);
  L.lane = []; L.flowText = []; L.rateText = [];
  for (let w=0; w<nw; w++){ L.lane[w]=[]; L.flowText[w]=[]; L.rateText[w]=[];
    for (let s=0; s<ns; s++){
      const lane = L.lane[w][s] = el('path',{d:laneD(w,s),class:'lane'},lanes);
      // Crossing lanes share a midpoint, so unit labels sit past it, where lanes have separated.
      const f = lane.getPointAtLength(lane.getTotalLength()*.64);
      L.flowText[w][s] = el('text',{x:f.x,y:f.y+4,class:'flowlabel','text-anchor':'middle'},labelsG);
      const q = lane.getPointAtLength(lane.getTotalLength()*.36);
      L.rateText[w][s] = el('text',{x:q.x,y:q.y-7,class:'rate','text-anchor':'middle'},labelsG);
      L.rateText[w][s].textContent = money(B(D.rates[w][s])) + '/unit';
    } }
  const fit = n => { const max = Math.floor(block/8.2); return n.length > max ? n.slice(0, max-1) + '…' : n; };
  const node = (side, i, name) => {
    const p = side==='w' ? L.w[i] : L.s[i], g = el('g',{},svg), left = side==='w';
    const x0 = left ? 0 : W - block, gw = block - 4;
    el('circle',{cx:p.x, cy:p.y, r:4.5, fill: left ? 'var(--gauge-fill)' : 'var(--glow)'}, g);
    el('text',{x: left? 0 : W, y:p.y-12, class:'name','text-anchor': left?'start':'end'}, g).textContent = fit(name);
    el('rect',{x:x0, y:p.y-3, width:gw, height:6, rx:3, class:'gbg'}, g);
    const f = el('rect',{x: left ? x0 : x0+4, y:p.y-3, width:0, height:6, rx:3, class:'gfill'+(left?'':' store')}, g);
    const t = el('text',{x: left? 0 : W, y:p.y+21, class:'sub','text-anchor': left?'start':'end'}, g);
    return {f, t, gw: left ? gw : gw-4};
  };
  L.wn = D.warehouses.map((n,i)=>node('w',i,n));
  L.sn = D.stores.map((n,i)=>node('s',i,n));
  paint(); showMarks(); markRates();
}

function paint(){
  if (!S || !L.wn) return;
  for (let w=0; w<nw; w++){ const n = L.wn[w];
    n.f.setAttribute('width', Math.max(0, n.gw*ratio(S.left[w], S.stock[w])));
    n.t.textContent = S.stock[w] === 0n ? 'none of this item' : `${count(S.left[w])} of ${count(S.stock[w])} left`; }
  for (let s=0; s<ns; s++){ const n = L.sn[s];
    n.f.setAttribute('width', Math.max(0, n.gw*ratio(S.got[s], S.need[s])));
    n.t.textContent = S.need[s] === 0n ? 'needs none' : `${count(S.got[s])} of ${count(S.need[s])} delivered`; }
  let max = 1n; S.flow.forEach(r=>r.forEach(f=>{ if (f>max) max=f; }));
  for (let w=0; w<nw; w++) for (let s=0; s<ns; s++){
    const f = S.flow[w][s], lane = L.lane[w][s];
    lane.classList.toggle('used', f>0n);
    lane.style.strokeWidth = f>0n ? (2 + 4*ratio(f,max)) : '';
    L.flowText[w][s].textContent = f>0n ? count(f) : '';
  }
  const n = S.it.paths.length;
  $('item').textContent = S.it.name;
  if (mode === 'final'){
    $('where').textContent = `Final plan, found in ${n} ${n === 1 ? 'path' : 'paths'}`;
    $('units').textContent = count(S.units); $('cost').textContent = money(S.cost);
    $('unitsLabel').textContent = 'units of this item'; $('costLabel').textContent = 'cost for this item';
  } else {
    $('where').textContent = pos.j >= n ? `All ${n} ${n === 1 ? 'path' : 'paths'} replayed` : `Path ${pos.j+1} of ${n}`;
    $('units').textContent = count(S.before.units + S.units); $('cost').textContent = money(S.before.cost + S.cost);
    $('unitsLabel').textContent = 'units planned so far'; $('costLabel').textContent = 'shipping cost so far';
  }
  chips(); ticks(); buttons();
}
function chips(){
  const box = $('chips'); if (NI < 2){ box.hidden = true; return; }
  box.innerHTML = '';
  D.items.forEach((it, k) => { const b = document.createElement('button'); b.type = 'button';
    b.textContent = it.name; b.setAttribute('aria-pressed', k === pos.k); b.onclick = () => showFinal(k); box.appendChild(b); });
}
function ticks(){
  const box = $('ticks'); box.innerHTML = ''; if (mode === 'final') return;
  D.items.forEach((it,k)=>it.paths.forEach((_,j)=>{ const t = document.createElement('i'); t.className='tick';
    if (k<pos.k || (k===pos.k && j<pos.j)) t.classList.add('done'); else if (k===pos.k && j===pos.j && animating) t.classList.add('now');
    box.appendChild(t); }));
}
function buttons(){
  const replay = mode === 'replay';
  ['prev','play','next','replay'].forEach(id => $(id).hidden = !replay);
  $('play').textContent = running ? (paused ? 'Resume' : 'Pause') : 'Play';
  $('prev').disabled = pos.k === 0 && pos.j === 0 && !animating;
}
function say(text, undo){ const c = $('caption'); c.textContent = text; c.classList.toggle('undo', !!undo); }

// ---------- glow marks (survive redraws) ----------
let marks = [];
function showMarks(){ marks.forEach(m => { m.els = null; applyMark(m); }); }
function applyMark(m){
  const lane = L.lane[m.w][m.s], d = lane.getAttribute('d'), len = lane.getTotalLength(), seg = Math.min(70, len*.35);
  const color = m.reverse ? 'var(--undo)' : 'var(--glow)';
  if (!m.els || !m.els[0].isConnected){
    if (m.reverse){ lane.style.strokeDasharray = '6 6'; lane.style.stroke = 'var(--undo)'; }
    m.els = [el('path',{d,class:'pulse',stroke:color,'stroke-width':2.5,opacity:.55},L.pulse),
             el('path',{d,class:'pulse',stroke:color,'stroke-width':7,opacity:.25},L.pulse),
             el('path',{d,class:'pulse',stroke:color,'stroke-width':3},L.pulse)];
  }
  const [trail, halo, head] = m.els, p = ease(m.p);
  if (reduce){ trail.setAttribute('stroke-dasharray', m.reverse ? '6 6' : 'none'); halo.setAttribute('stroke-dasharray','none'); head.remove(); return; }
  if (m.reverse){ const at = len - p*len;               // store end → warehouse end
    trail.setAttribute('stroke-dasharray','6 6');
    [halo,head].forEach(e=>{ e.setAttribute('stroke-dasharray', `${seg} ${len+seg}`); e.setAttribute('stroke-dashoffset', -at); }); }
  else { const at = p*len;
    trail.setAttribute('stroke-dasharray', `${len} ${len}`); trail.setAttribute('stroke-dashoffset', len - at);
    [halo,head].forEach(e=>{ e.setAttribute('stroke-dasharray', `${seg} ${len+seg}`); e.setAttribute('stroke-dashoffset', seg - at); }); }
}
function clearMarks(){ marks.forEach(m => { (m.els||[]).forEach(e=>e.remove());
  const lane = L.lane && L.lane[m.w] && L.lane[m.w][m.s]; if (lane){ lane.style.strokeDasharray=''; lane.style.stroke=''; } }); marks = []; }
async function travel(w, s, reverse, t){ const m = {w, s, reverse, p: 0}; marks.push(m);
  await tween(1100, raw => { m.p = raw; applyMark(m); }, t); }
function markRates(){ if (!L.rateText) return;
  for (let w=0; w<nw; w++) for (let s=0; s<ns; s++)
    L.rateText[w][s].classList.toggle('on', detailsOpen && (curPath ? curPath.steps.some(x=>x.w===w&&x.s===s) : (S && S.flow[w][s] > 0n))); }

// ---------- captions ----------
const itemWord = () => S.it.name.toLowerCase();
const capStart = P => `Cheapest remaining route for ${count(B(P.amount))} ${itemWord()}, starting from ${D.warehouses[P.steps[0].w]}'s stock.`;
const capStep = (x, amt) => x.reverse
  ? `Reassigning an earlier allocation: ${D.warehouses[x.w]} sends ${count(amt)} fewer to ${D.stores[x.s]}, so those units can go elsewhere.`
  : `Send ${count(amt)} from ${D.warehouses[x.w]} to ${D.stores[x.s]}.`;
const capDone = P => { const amt = B(P.amount), c = B(P.cost), last = P.steps[P.steps.length-1];
  return `${D.stores[last.s]} gets ${count(amt)} more. This path costs ${money(c)} per unit, ${money(amt*c)} in total.`; };

// ---------- the guided sequence ----------
async function animatePath(P, t){
  curPath = P; animating = true; detail(); markRates(); paint();
  say(capStart(P)); await hold(1500, t);
  for (const x of P.steps){ say(capStep(x, B(P.amount)), x.reverse); await travel(x.w, x.s, x.reverse, t); await hold(x.reverse ? 1700 : 700, t); }
  apply(S, P); pos.j++; animating = false; clearMarks(); paint(); say(capDone(P)); await hold(2200, t);
}
async function run(k0, j0, single){
  const t = ++token; clearMarks(); mode = 'replay'; running = true; paused = false; animating = false;
  try {
    setPosition(k0, j0); draw();
    for (let k = k0; k < NI; k++){
      if (k !== k0){ setPosition(k, 0); draw(); }
      curPath = null; detail();
      if (pos.j === 0 && !single){ say(`Planning ${itemWord()}. Each step finds the cheapest way to move more units from a warehouse to a store that still needs them.`); await hold(2600, t); }
      while (pos.j < S.it.paths.length){ await animatePath(S.it.paths[pos.j], t); if (single) return; }
      if (!single){ curPath = null; detail(); markRates();
        say(S.it.complete ? `${S.it.name} planned. No cheaper rearrangement is left, so this allocation is optimal.`
                          : `${S.it.name}: replay stops at the path limit.`);
        await hold(2400, t); }
    }
    say(D.shownPaths < D.totalPaths
      ? `Replay ends here. These were the first ${D.shownPaths} of ${D.totalPaths} paths; the tables have the full plan.`
      : `Done. ${count(S.before.units + S.units)} units for ${money(S.before.cost + S.cost)}, the same totals as the plan.`);
  } catch (e) { if (!(e instanceof Stop)) throw e; }
  finally { if (t === token){ running = false; animating = false; paint(); } }
}
function stop(){ token++; running = false; paused = false; animating = false; clearMarks(); }
function showFinal(k){ stop(); mode = D.autoplay ? 'replay' : 'final'; setPosition(k, D.items[k].paths.length);
  animating = false; curPath = null; draw(); detail();
  say(mode === 'final' ? `Final plan for ${itemWord()}: ${count(S.units)} units for ${money(S.cost)}. Choose Explore algorithm to watch how it was found.`
                       : `${S.it.name} after all ${S.it.paths.length} paths. Use Previous path to step back through them.`); }
function stepBack(){
  const wasMid = animating; stop(); animating = false;
  let {k, j} = pos;
  if (!wasMid){ if (j > 0) j--; else if (k > 0){ k--; j = Math.max(0, D.items[k].paths.length - 1); } }
  setPosition(k, j); curPath = S.it.paths[j] || null; draw(); detail();
  say(curPath ? `Next up: ${capStart(curPath)}` : `${S.it.name}: no paths.`);
}
function stepForward(){
  if (running && animating){ const P = S.it.paths[pos.j]; stop(); setPosition(pos.k, pos.j + 1); curPath = null; draw(); detail(); say(capDone(P)); return; }
  stop(); let {k, j} = pos;
  while (k < NI && j >= D.items[k].paths.length){ k++; j = 0; }
  if (k >= NI){ say('That was the last path. Choose Replay to start again.'); paint(); return; }
  run(k, j, true);
}

// ---------- details ----------
let detailsOpen = false;
function detail(){
  const d = $('details'); if (!detailsOpen || !S) return;
  const P = curPath;
  if (!P){
    const rows = [];
    for (let w=0; w<nw; w++) for (let s=0; s<ns; s++){ const f = S.flow[w][s]; if (f > 0n){ const r = B(D.rates[w][s]);
      rows.push(`<tr><td>${H_W[w]} → ${H_S[s]}</td><td class="num">${count(f)}</td><td class="num">${money(r)}</td><td class="num">${money(f*r)}</td></tr>`); } }
    d.innerHTML = `<div><h3>Routes used</h3><table><tr><th>Route</th><th class="num">Units</th><th class="num">Rate</th><th class="num">Subtotal</th></tr>${rows.join('') || '<tr><td colspan="4">No routes used yet.</td></tr>'}
      <tr><td><b>Total</b></td><td class="num"><b>${count(S.units)}</b></td><td></td><td class="num"><b>${money(S.cost)}</b></td></tr></table></div>
      <div><h3>Reading the board</h3><p>Lane thickness and the number on it show units on that route. Gauges show stock left at each warehouse and units delivered to each store.</p></div>`;
    return;
  }
  const amt = B(P.amount);
  const rows = P.steps.map(x => { const rate = B(D.rates[x.w][x.s]), f = S.flow[x.w][x.s];
    const room = x.reverse ? f : (S.stock[x.w] < S.need[x.s] ? S.stock[x.w] : S.need[x.s]) - f;
    return `<tr${x.reverse?' class="undo"':''}><td>${x.reverse ? H_S[x.s]+' ⟵ '+H_W[x.w] : H_W[x.w]+' → '+H_S[x.s]}</td>
      <td class="num">${x.reverse ? '−' : ''}${money(rate)}</td><td class="num">${count(room)}</td></tr>`; }).join('');
  let pot = '';
  if (P.potentials){ const names = [...H_W, ...H_S];
    pot = '<div><h3>Potentials</h3><p>Dijkstra labels after this search. They keep adjusted route costs non-negative, so reassignment steps with negative cost are safe to search.</p><table>' +
      names.map((n,i)=>`<tr><td>${n}</td><td class="num">${money(B(P.potentials[i]))}</td></tr>`).join('') + '</table></div>'; }
  d.innerHTML = `<div><h3>This path</h3><p>${count(amt)} units. A reassignment refunds its rate, so it counts as a negative cost.</p>
    <table><tr><th>Route</th><th class="num">Rate</th><th class="num">Room</th></tr>${rows}
    <tr><td><b>Per unit</b></td><td class="num"><b>${money(B(P.cost))}</b></td><td></td></tr></table>
    <p>Room is how many more units the route could take before this path, or for a reassignment, how many can be undone.</p></div>${pot}`;
}

$('play').onclick = () => {
  if (running){ paused = !paused; buttons(); return; }
  let {k, j} = pos; while (k < NI && j >= D.items[k].paths.length){ k++; j = 0; }
  k >= NI ? run(0, 0, false) : run(k, j, false);
};
$('prev').onclick = stepBack;
$('next').onclick = stepForward;
$('replay').onclick = () => run(0, 0, false);
$('inspect').onclick = () => { detailsOpen = !detailsOpen; $('inspect').setAttribute('aria-pressed', detailsOpen);
  $('details').hidden = !detailsOpen; detail(); markRates(); };
let rt; addEventListener('resize', () => { clearTimeout(rt); rt = setTimeout(draw, 120); });
$('note').textContent = 'Replays the augmenting paths the planner selected, one route at a time. It does not show the search that found each path.';
if (D.autoplay) run(0, 0, false); else showFinal(0);
</script></body></html>
"""
