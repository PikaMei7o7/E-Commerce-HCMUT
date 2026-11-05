/* Biểu đồ SVG thuần (không phụ thuộc thư viện ngoài). */
const SVGNS = 'http://www.w3.org/2000/svg';
const PALETTE = ['var(--c1)', 'var(--c2)', 'var(--c3)', 'var(--c4)', 'var(--c5)', 'var(--c6)'];

function h(tag, attrs, ...kids) {
  const e = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (v == null || v === false) continue;
    if (k === 'class') e.className = v;
    else if (k === 'text') e.textContent = v;
    else if (k.startsWith('on')) e.addEventListener(k.slice(2), v);
    else e.setAttribute(k, v === true ? '' : v);
  }
  for (const c of kids.flat()) if (c != null && c !== false) e.append(c.nodeType ? c : document.createTextNode(c));
  return e;
}
function s(tag, attrs, ...kids) {
  const e = document.createElementNS(SVGNS, tag);
  for (const [k, v] of Object.entries(attrs || {})) if (v != null) e.setAttribute(k, v);
  for (const c of kids.flat()) if (c != null) e.append(c.nodeType ? c : document.createTextNode(c));
  return e;
}

function compact(v) {
  if (v == null || isNaN(v)) return '–';
  if (v === 0) return '0';
  const a = Math.abs(v), sg = v < 0 ? '-' : '';
  if (a >= 1e9) return sg + (a / 1e9).toFixed(2) + 'B';
  if (a >= 1e6) return sg + (a / 1e6).toFixed(2) + 'M';
  if (a >= 1e4) return sg + (a / 1e3).toFixed(1) + 'K';
  if (a >= 100) return sg + a.toFixed(0);
  if (a >= 1) return sg + a.toFixed(2);
  return sg + a.toFixed(4);
}
const full = v => v == null ? '–' : Number(v).toLocaleString('en-US', { maximumFractionDigits: 6 });
function fmtVal(kind, v) {
  if (v == null) return '–';
  if (kind === 'text') return String(v);
  if (typeof v !== 'number') return String(v);
  if (kind === 'int') return Math.round(v).toLocaleString('en-US');
  if (kind === 'dec') return Math.abs(v) >= 1000 ? compact(v) : v.toLocaleString('en-US', { maximumFractionDigits: 4 });
  return compact(v); // money
}

const tipEl = () => document.getElementById('tip');
function showTip(ev, html) {
  const t = tipEl(); t.textContent = ''; t.append(...html); t.hidden = false;
  const r = t.getBoundingClientRect();
  let x = ev.clientX + 14, y = ev.clientY + 14;
  if (x + r.width > innerWidth - 8) x = ev.clientX - r.width - 14;
  if (y + r.height > innerHeight - 8) y = ev.clientY - r.height - 14;
  t.style.left = x + 'px'; t.style.top = y + 'px';
}
const hideTip = () => { tipEl().hidden = true; };

function niceMax(m) {
  if (!(m > 0)) return 1;
  const p = Math.pow(10, Math.floor(Math.log10(m))), f = m / p;
  return (f <= 1 ? 1 : f <= 2 ? 2 : f <= 2.5 ? 2.5 : f <= 5 ? 5 : 10) * p;
}
const colIdx = (cols, name) => cols.indexOf(name);

function seriesChips(series, cur, onPick) {
  if (series.length < 2) return null;
  return h('div', { class: 'chips' }, series.map((m, i) =>
    h('button', { class: i === cur ? 'on' : '', onclick: () => onPick(i) }, m.label)));
}

/* KPI */
function renderKpis(host, data, cfg) {
  const row = data.rows[0] || [];
  host.append(h('div', { class: 'kpis' }, cfg.items.map(it => {
    const v = row[colIdx(data.columns, it.col)];
    return h('div', { class: 'kpi', title: full(v) }, h('div', { class: 'l', text: it.label }),
      h('div', { class: 'n', text: fmtVal(it.fmt === 'money' ? 'money' : it.fmt, v) }));
  })));
}

/* Line */
function renderLine(host, data, cfg) {
  let cur = 0;
  const box = h('div'); host.append(box);
  const xi = colIdx(data.columns, cfg.x);
  const xs = data.rows.map(r => String(r[xi] ?? ''));
  const monthly = xs.length && xs.every(x => /-01/.test(x.slice(7, 10)) || x.length <= 7);
  const xl = x => (monthly ? x.slice(0, 7) : x.slice(0, 10));
  function draw() {
    box.textContent = '';
    const m = cfg.series[cur], yi = colIdx(data.columns, m.col);
    const ys = data.rows.map(r => (r[yi] == null ? null : Number(r[yi])));
    const W = Math.max(320, host.clientWidth || 900), H = 300, L = 62, R = 14, T = 12, B = 28;
    const mx = niceMax(Math.max(0, ...ys.filter(v => v != null)));
    const px = i => L + (xs.length < 2 ? (W - L - R) / 2 : (i * (W - L - R)) / (xs.length - 1));
    const py = v => T + (1 - v / mx) * (H - T - B);
    const svg = s('svg', { class: 'ch', viewBox: `0 0 ${W} ${H}` });
    for (let i = 0; i <= 4; i++) {
      const v = (mx * i) / 4, y = py(v);
      svg.append(s('line', { class: 'grid', x1: L, x2: W - R, y1: y, y2: y }),
        s('text', { x: L - 8, y: y + 4, 'text-anchor': 'end' }, compact(v)));
    }
    const nt = Math.min(7, xs.length);
    for (let k = 0; k < nt; k++) {
      const i = nt < 2 ? 0 : Math.round((k * (xs.length - 1)) / (nt - 1));
      svg.append(s('text', { x: px(i), y: H - 8, 'text-anchor': k === 0 ? 'start' : k === nt - 1 ? 'end' : 'middle' }, xl(xs[i])));
    }
    let d = '', started = false;
    ys.forEach((v, i) => { if (v == null) { started = false; return; } d += (started ? 'L' : 'M') + px(i).toFixed(1) + ' ' + py(v).toFixed(1); started = true; });
    if (xs.length > 1) svg.append(s('path', { d: d + `L${px(xs.length - 1)} ${py(0)}L${px(0)} ${py(0)}Z`, fill: 'var(--c1)', opacity: .1 }));
    svg.append(s('path', { d, fill: 'none', stroke: 'var(--c1)', 'stroke-width': 2, 'stroke-linejoin': 'round' }));
    if (xs.length <= 40) ys.forEach((v, i) => v != null && svg.append(s('circle', { cx: px(i), cy: py(v), r: 3, fill: 'var(--c1)' })));
    const cross = s('line', { y1: T, y2: H - B, stroke: 'var(--muted)', 'stroke-dasharray': '3 3', visibility: 'hidden' });
    const dot = s('circle', { r: 5, fill: 'var(--c1)', stroke: 'var(--card)', 'stroke-width': 2, visibility: 'hidden' });
    const ov = s('rect', { x: L, y: T, width: W - L - R, height: H - T - B, fill: 'transparent' });
    ov.addEventListener('pointermove', ev => {
      const b = svg.getBoundingClientRect(), fx = ((ev.clientX - b.left) / b.width) * W;
      let i = xs.length < 2 ? 0 : Math.round(((fx - L) / (W - L - R)) * (xs.length - 1));
      i = Math.max(0, Math.min(xs.length - 1, i));
      cross.setAttribute('x1', px(i)); cross.setAttribute('x2', px(i)); cross.setAttribute('visibility', 'visible');
      if (ys[i] != null) { dot.setAttribute('cx', px(i)); dot.setAttribute('cy', py(ys[i])); dot.setAttribute('visibility', 'visible'); }
      showTip(ev, [h('b', { text: xs[i].slice(0, 10) }), h('br'), `${m.label}: ${full(ys[i])}`]);
    });
    ov.addEventListener('pointerleave', () => { hideTip(); cross.setAttribute('visibility', 'hidden'); dot.setAttribute('visibility', 'hidden'); });
    svg.append(cross, dot, ov);
    box.append(seriesChips(cfg.series, cur, i => { cur = i; draw(); }), svg);
  }
  draw();
}

/* Bar (dọc hoặc ngang) + bảng tùy chọn */
function renderBar(host, data, cfg) {
  let cur = 0;
  const box = h('div'); host.append(box);
  const xi = colIdx(data.columns, cfg.x);
  const labels = data.rows.map(r => String(r[xi] ?? '–'));
  function draw() {
    box.textContent = '';
    const m = cfg.series[cur], yi = colIdx(data.columns, m.col);
    const vals = data.rows.map(r => (r[yi] == null ? 0 : Number(r[yi])));
    const mx = niceMax(Math.max(0, ...vals));
    let svg;
    if (cfg.horizontal) {
      const rowH = 26, L = 190, R = 70, W = Math.max(420, host.clientWidth || 900), H = vals.length * rowH + 8;
      svg = s('svg', { class: 'ch', viewBox: `0 0 ${W} ${H}` });
      vals.forEach((v, i) => {
        const y = 4 + i * rowH, w = Math.max(1, (v / mx) * (W - L - R));
        const lab = labels[i].length > 30 ? labels[i].slice(0, 29) + '…' : labels[i];
        const g = s('g'); const t = s('text', { x: L - 8, y: y + 16, 'text-anchor': 'end' }, lab);
        const rect = s('rect', { x: L, y: y + 3, width: w, height: rowH - 8, rx: 4, fill: 'var(--c1)' });
        g.append(t, rect, s('text', { x: L + w + 6, y: y + 16 }, compact(v)));
        const hit = s('rect', { x: 0, y, width: W, height: rowH, fill: 'transparent' });
        hit.addEventListener('pointermove', ev => showTip(ev, [h('b', { text: labels[i] }), h('br'), `${m.label}: ${full(v)}`]));
        hit.addEventListener('pointerleave', hideTip);
        g.append(hit); svg.append(g);
      });
    } else {
      const W = Math.max(320, host.clientWidth || 900), H = 300, L = 62, R = 10, T = 12, B = 44, n = vals.length || 1;
      svg = s('svg', { class: 'ch', viewBox: `0 0 ${W} ${H}` });
      for (let i = 0; i <= 4; i++) {
        const v = (mx * i) / 4, y = T + (1 - v / mx) * (H - T - B);
        svg.append(s('line', { class: 'grid', x1: L, x2: W - R, y1: y, y2: y }), s('text', { x: L - 8, y: y + 4, 'text-anchor': 'end' }, compact(v)));
      }
      const bw = (W - L - R) / n;
      vals.forEach((v, i) => {
        const hgt = (v / mx) * (H - T - B), x = L + i * bw, y = H - B - hgt;
        const rect = s('rect', { x: x + bw * 0.15, y, width: bw * 0.7, height: Math.max(1, hgt), rx: 4, fill: 'var(--c1)' });
        rect.addEventListener('pointermove', ev => showTip(ev, [h('b', { text: labels[i] }), h('br'), `${m.label}: ${full(v)}`]));
        rect.addEventListener('pointerleave', hideTip);
        const mc = Math.max(3, Math.floor(bw / 7)), lab = labels[i].length > mc ? labels[i].slice(0, mc - 1) + '…' : labels[i];
        svg.append(rect, s('text', { x: x + bw / 2, y: H - B + 16, 'text-anchor': 'middle' }, lab));
        if (n <= 14) svg.append(s('text', { x: x + bw / 2, y: y - 4, 'text-anchor': 'middle' }, compact(v)));
      });
    }
    box.append(seriesChips(cfg.series, cur, i => { cur = i; draw(); }), svg);
    if (cfg.table) {
      const cols = [{ col: cfg.x, label: 'Dimension', fmt: 'text' }, ...cfg.series];
      box.append(h('div', { class: 'scroll' }, tableEl(data, cols)));
    }
  }
  draw();
}

/* Donut */
function renderDonut(host, data, cfg) {
  let cur = 0;
  const box = h('div'); host.append(box);
  const li = colIdx(data.columns, cfg.label);
  function draw() {
    box.textContent = '';
    const m = cfg.series[cur], vi = colIdx(data.columns, m.col);
    const items = data.rows.map(r => ({ l: String(r[li] ?? '–'), v: Number(r[vi] || 0) }));
    const tot = items.reduce((a, b) => a + b.v, 0) || 1;
    const svg = s('svg', { class: 'ch', viewBox: '-100 -100 200 200' });
    let a0 = -Math.PI / 2;
    const R = 90, r = 56;
    items.forEach((it, i) => {
      const frac = it.v / tot, a1 = a0 + frac * Math.PI * 2 - (frac >= 0.9999 ? 0.0001 : 0);
      const big = a1 - a0 > Math.PI ? 1 : 0;
      const P = (rad, a) => `${(rad * Math.cos(a)).toFixed(2)} ${(rad * Math.sin(a)).toFixed(2)}`;
      const path = s('path', { d: `M${P(R, a0)}A${R} ${R} 0 ${big} 1 ${P(R, a1)}L${P(r, a1)}A${r} ${r} 0 ${big} 0 ${P(r, a0)}Z`, fill: PALETTE[i % 6], stroke: 'var(--card)', 'stroke-width': 1.5 });
      path.addEventListener('pointermove', ev => showTip(ev, [h('b', { text: it.l }), h('br'), `${m.label}: ${full(it.v)} (${(frac * 100).toFixed(1)}%)`]));
      path.addEventListener('pointerleave', hideTip);
      svg.append(path); a0 = a1;
    });
    svg.append(s('text', { x: 0, y: -2, 'text-anchor': 'middle', style: 'font-size:16px;font-weight:700;fill:var(--ink)' }, compact(tot)),
      s('text', { x: 0, y: 14, 'text-anchor': 'middle' }, 'total'));
    const legend = h('div', { class: 'legend' }, items.map((it, i) => h('div', {}, h('i', { style: `background:${PALETTE[i % 6]}` }),
      h('span', { text: it.l }), h('span', { text: `${fmtVal(m.fmt, it.v)} · ${((it.v / tot) * 100).toFixed(1)}%` }))));
    box.append(seriesChips(cfg.series, cur, i => { cur = i; draw(); }), h('div', { class: 'donutwrap' }, svg, legend));
  }
  draw();
}

/* Heatmap */
function renderHeat(host, data, cfg) {
  const ri = colIdx(data.columns, cfg.rows), ci = colIdx(data.columns, cfg.cols), vi = colIdx(data.columns, cfg.value);
  const rows = [...new Set(data.rows.map(r => r[ri]))].sort((a, b) => {
    const o = cfg.row_order || []; const x = o.indexOf(a), y = o.indexOf(b);
    return (x < 0 ? 99 : x) - (y < 0 ? 99 : y);
  });
  const cols = [...new Set(data.rows.map(r => r[ci]))].sort();
  const map = new Map(data.rows.map(r => [r[ri] + '|' + r[ci], r[vi]]));
  const mx = Math.max(...data.rows.map(r => Number(r[vi]) || 0), 1e-9);
  const tbl = h('table', { class: 'heat' }, h('tr', {}, h('th'), cols.map(c => h('th', { text: c }))),
    rows.map(rw => h('tr', {}, h('th', { text: rw }), cols.map(c => {
      const v = map.get(rw + '|' + c);
      return h('td', { title: full(v), style: v == null ? '' : `background:color-mix(in srgb,var(--accent) ${Math.round(8 + 72 * (Number(v) / mx))}%,transparent)` }, fmtVal(cfg.fmt, v == null ? null : Number(v)));
    }))));
  host.append(h('div', { class: 'scroll' }, tbl));
}

/* Table (sắp xếp bằng cách bấm tiêu đề) */
function tableEl(data, cols) {
  let sortCol = -1, dir = -1;
  const idx = cols.map(c => colIdx(data.columns, c.col));
  const tbl = h('table', { class: 't' });
  function draw() {
    tbl.textContent = '';
    let rows = data.rows.slice();
    if (sortCol >= 0) rows.sort((a, b) => {
      const x = a[idx[sortCol]], y = b[idx[sortCol]];
      return (x == null) - (y == null) || (typeof x === 'number' ? x - y : String(x).localeCompare(String(y))) * dir;
    });
    tbl.append(h('thead', {}, h('tr', {}, cols.map((c, i) => h('th', {
      class: c.fmt === 'text' ? '' : 'num', style: 'cursor:pointer',
      onclick: () => { dir = sortCol === i ? -dir : -1; sortCol = i; draw(); }
    }, c.label + (sortCol === i ? (dir < 0 ? ' ↓' : ' ↑') : ''))))),
      h('tbody', {}, rows.map(r => h('tr', {}, cols.map((c, i) => h('td', { class: c.fmt === 'text' ? '' : 'num', title: c.fmt === 'text' ? '' : full(r[idx[i]]) }, fmtVal(c.fmt, r[idx[i]])))))));
  }
  draw();
  return tbl;
}
function renderTable(host, data, cfg) { host.append(h('div', { class: 'scroll' }, tableEl(data, cfg.columns))); }

function renderWidget(host, data, cfg) {
  if (cfg.kind === 'kpis') return renderKpis(host, data, cfg);
  if (!data.rows.length) return host.append(h('div', { class: 'placeholder', text: 'No data for this filter.' }));
  ({ line: renderLine, bar: renderBar, donut: renderDonut, heat: renderHeat, table: renderTable })[cfg.kind](host, data, cfg);
}

function toCsv(data) {
  const q = v => { const t = v == null ? '' : String(v); return /[",\n]/.test(t) ? '"' + t.replace(/"/g, '""') + '"' : t; };
  return '﻿' + [data.columns, ...data.rows].map(r => r.map(q).join(',')).join('\n');
}
