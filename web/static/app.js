/* Điều khiển giao diện: Kết nối -> Quyền truy cập -> Dashboard. */
const $ = id => document.getElementById(id);
const STATUS = {
  ok: ['Full read access', 'ok'], partial: ['Partial access', 'partial'], denied: ['No permission', 'denied'],
  error: ['Access error', 'error'], missing: ['Does not exist', 'missing'],
  full: ['Fully available', 'full'], locked: ['Locked', 'locked']
};
const badge = k => h('span', { class: 'badge b-' + STATUS[k][1], text: STATUS[k][0] });
const state = { access: null, catalog: null, dash: null, ctrl: {}, host: '', dbname: '' };

/* Biểu tượng SVG nội tuyến (chuỗi tĩnh). */
const ICONS = {
  refresh: '<path d="M21 12a9 9 0 1 1-2.6-6.4L21 8"/><path d="M21 3v5h-5"/>',
  download: '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><path d="M7 10l5 5 5-5"/><path d="M12 15V3"/>',
  logout: '<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><path d="M16 17l5-5-5-5"/><path d="M21 12H9"/>',
  play: '<path d="M7 4l13 8-13 8z"/>',
  lock: '<rect x="4" y="11" width="16" height="10" rx="2"/><path d="M8 11V7a4 4 0 0 1 8 0v4"/>',
  chevron: '<path d="M9 6l6 6-6 6"/>',
  arrow: '<path d="M5 12h14"/><path d="M13 6l6 6-6 6"/>',
  info: '<circle cx="12" cy="12" r="9"/><path d="M12 11v5"/><path d="M12 8h.01"/>'
};
function ico(name, cls = 'ic') {
  const sp = document.createElement('span'); sp.className = cls;
  sp.innerHTML = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${ICONS[name]}</svg>`;
  return sp;
}
function pageHead(eyebrow, title, sub, ...actions) {
  return h('header', { class: 'page-head' },
    h('div', {}, h('div', { class: 'eyebrow', text: eyebrow }), h('h1', {}, title), sub ? h('p', { class: 'sub' }, sub) : null),
    actions.length ? h('div', { class: 'page-actions' }, actions) : null);
}
const cardHead = (title, sub, ...actions) => h('div', { class: 'card-head' },
  h('div', {}, h('h2', { text: title }), sub ? h('p', { class: 'sub', text: sub }) : null),
  actions.length ? h('div', { class: 'page-actions' }, actions) : null);

async function api(path, body, signal) {
  const opt = body === undefined ? {} : { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) };
  if (signal) opt.signal = signal;
  const r = await fetch(path, opt);
  let j = {};
  try { j = await r.json(); } catch (e) { /* noop */ }
  if (!r.ok) { const e = new Error(j.error || r.statusText); e.status = r.status; e.reasons = j.reasons; throw e; }
  return j;
}

/* Điều hướng */
function show(view) {
  for (const v of ['connect', 'access', 'dash']) $('view-' + v).hidden = v !== view;
  document.querySelectorAll('#steps [data-view]').forEach(b => b.classList.toggle('active', b.dataset.view === view));
  document.querySelectorAll('#dash-nav [data-dash]').forEach(b => b.classList.toggle('active', view === 'dash' && b.dataset.dash === state.dash));
  window.scrollTo(0, 0);
}
document.querySelectorAll('#steps [data-view]').forEach(b => b.addEventListener('click', () => show(b.dataset.view)));

function renderDashNav() {
  const nav = $('dash-nav'); nav.textContent = '';
  if (!state.access) { nav.append(h('div', { class: 'nav-empty', text: 'Connect to unlock dashboards' })); return; }
  nav.append(...state.access.dashboards.map(x => h('button', { class: 'nav-item', 'data-dash': x.id, title: STATUS[x.status][0], onclick: () => openDash(x.id) },
    h('span', { class: 'ic emoji', text: x.icon }), h('span', { class: 'nav-txt', text: x.title }), h('span', { class: 'sd ' + x.status }))));
  document.querySelectorAll('#dash-nav [data-dash]').forEach(b => b.classList.toggle('active', !$('view-dash').hidden && b.dataset.dash === state.dash));
}

function renderWho() {
  const id = state.access.identity, who = $('who');
  who.hidden = false; who.textContent = '';
  who.append(h('div', { class: 'avatar', text: (id.current_user || '?').slice(0, 1).toUpperCase() }),
    h('div', { class: 'who-txt' }, h('b', { text: id.current_user }), h('span', { text: state.dbname || state.host || '' })),
    h('button', { class: 'btn ghost icon', title: 'Disconnect', 'aria-label': 'Disconnect', onclick: disconnect }, ico('logout')));
}

function setConnected(access, host, dbname) {
  state.access = access; state.host = host; state.dbname = dbname;
  document.querySelectorAll('#steps [data-view]').forEach(b => { b.disabled = false; });
  renderDashNav(); renderWho();
}
async function disconnect() {
  resetQueue();
  await api('/api/disconnect', {}).catch(() => { });
  state.access = null; state.catalog = null; state.dash = null;
  $('who').hidden = true;
  document.querySelectorAll('#steps [data-view]').forEach(b => { b.disabled = b.dataset.view !== 'connect'; });
  renderDashNav(); renderConnect(); show('connect');
}

/* 1. Kết nối */
async function renderConnect() {
  const root = $('view-connect'); root.textContent = '';
  let d = {}; try { d = await api('/api/defaults'); } catch (e) { /* noop */ }
  const f = (id, label, val, extra = {}) => h('div', { class: extra.full ? 'full' : '' }, h('label', { for: id, text: label }),
    h('input', { id, value: val ?? '', type: extra.type || 'text', placeholder: extra.ph || '', autocomplete: extra.ac || 'off' }));
  const ssl = h('select', { id: 'f-ssl' }, ['prefer', 'require', 'disable', 'verify-full'].map(o => h('option', { value: o, selected: o === (d.sslmode || 'prefer') }, o)));
  const err = h('div', { class: 'err', hidden: true });
  const btn = h('button', { class: 'btn primary lg', id: 'f-go' }, 'Connect');
  const form = h('form', { class: 'card login' },
    h('h2', { text: 'Connect to PostgreSQL' }), h('p', { class: 'sub', text: 'The session is read-only. The password stays in memory only.' }),
    h('div', { class: 'form' },
      f('f-host', 'Host', d.host), f('f-port', 'Port', d.port || '5432'),
      f('f-db', 'Database', d.dbname, { full: true }),
      f('f-user', 'User', d.user, { full: true }),
      f('f-pw', 'Password', '', { type: 'password', full: true, ac: 'current-password' }),
      h('div', {}, h('label', { for: 'f-ssl', text: 'SSL mode' }), ssl), f('f-schema', 'Schema', d.schema || 'star_schema')),
    h('div', { class: 'form-actions' }, btn), err);
  form.addEventListener('submit', async ev => {
    ev.preventDefault(); err.hidden = true; btn.disabled = true; btn.textContent = 'Connecting…';
    try {
      const a = await api('/api/connect', {
        host: $('f-host').value, port: $('f-port').value, dbname: $('f-db').value, user: $('f-user').value,
        password: $('f-pw').value, sslmode: $('f-ssl').value, schema: $('f-schema').value, role: ''
      });
      $('f-pw').value = '';
      state.catalog = null; state.dash = null; state.ctrl = {};
      setConnected(a, $('f-host').value, $('f-db').value); renderAccess(); show('access');
    } catch (e) { err.textContent = e.message; err.hidden = false; }
    btn.disabled = false; btn.textContent = 'Connect';
  });
  const feat = (icon, t, x) => h('div', { class: 'feat' }, h('span', { class: 'emoji', text: icon }), h('div', {}, h('b', { text: t }), h('p', { text: x })));
  root.append(h('div', { class: 'connect' },
    h('div', { class: 'intro' },
      h('div', { class: 'eyebrow', text: 'H&M E-Commerce Analytics' }),
      h('h1', { text: 'Turn H&M sales data into clear insights' }),
      h('p', { class: 'lead', text: 'Interactive dashboards built on the star_schema data warehouse. Explore revenue, products and customers, all powered by live PostgreSQL queries.' }),
      h('div', { class: 'feats' },
        feat('📈', 'Sales overview', 'Key metrics, monthly and daily trends, Store vs Online share.'),
        feat('🧥', 'Product performance', 'Best-selling product groups, types and individual items.'),
        feat('👥', 'Customer segments', 'Age groups, club membership, purchase frequency, top spenders.'),
        feat('🔎', 'Sales explorer', 'Slice sales by any dimension: time, channel, age, product.')),
      h('p', { class: 'intro-foot' }, ico('lock'), h('span', { text: 'Role-based access: each account only sees the data its PostgreSQL role is granted.' }))),
    form));
}

/* 2. Quyền truy cập */
function renderAccess() {
  const a = state.access, id = a.identity, root = $('view-access'); root.textContent = '';
  const count = k => a.views.filter(v => v.status === k).length;
  const unlocked = a.dashboards.filter(d => d.status !== 'locked').length;

  const recheck = h('button', { class: 'btn', onclick: async ev => {
    const b = ev.currentTarget; b.disabled = true;
    try { state.access = await api('/api/recheck', {}); renderAccess(); renderDashNav(); } catch (e) { alert(e.message); b.disabled = false; }
  } }, ico('refresh'), 'Re-check');
  const head = pageHead('Permissions', id.current_user,
    `${id.superuser ? 'Superuser' : 'Regular user'} · schema ${id.schema} · ${id.server}`, recheck);

  const stat = (l, n, tone) => h('div', { class: 'stat t-' + tone }, h('div', { class: 'l', text: l }), h('div', { class: 'n', text: String(n) }));
  const stats = h('div', { class: 'stats' },
    stat('Views fully readable', `${count('ok')} / ${a.views.length}`, 'ok'),
    stat('Partial access', count('partial'), 'partial'),
    stat('No permission', count('denied') + count('error'), 'denied'),
    count('missing') ? stat('Missing views', count('missing'), 'missing') : null,
    stat('Dashboards unlocked', `${unlocked} / ${a.dashboards.length}`, 'accent'));

  const dcards = h('div', { class: 'dgrid' }, a.dashboards.map(d => h('div', { class: 'dcard s-' + d.status },
    h('div', { class: 'row' }, h('span', { class: 'emoji', text: d.icon }), badge(d.status)),
    h('h3', { text: d.title }),
    h('div', {}, h('div', { class: 'meter' }, h('i', { style: `width:${(100 * d.available) / (d.total || 1)}%` })),
      h('div', { class: 'muted small', style: 'margin-top:6px', text: `${d.available} of ${d.total} widgets available` })),
    d.status !== 'full' ? h('ul', {}, [...new Set(d.widgets.flatMap(w => w.reasons))].slice(0, 3).map(r => h('li', { text: r }))) : null,
    h('div', { class: 'go' }, h('button', { class: 'btn ' + (d.status === 'locked' ? '' : 'primary'), onclick: () => openDash(d.id) },
      d.status === 'locked' ? 'See why' : 'Open dashboard', ico('arrow'))))));
  const dashCard = h('div', { class: 'card' }, cardHead('Dashboards', 'Dashboards this account has enough privileges for are unlocked.'), dcards);

  const rows = [];
  const dn = Object.fromEntries(a.dashboards.map(d => [d.id, d.title]));
  for (const v of a.views) {
    const det = h('tr', { class: 'detail', hidden: true }, h('td', { colspan: 5 },
      v.columns.length ? h('div', {}, v.columns.map(c => h('span', { class: 'chip ' + (c.ok ? 'ok' : 'no'), text: c.name }))) : h('span', { class: 'muted', text: 'No column information (view does not exist).' }),
      v.missing_columns.length ? h('p', { class: 'small', style: 'color:var(--warn)' }, 'Columns the app needs but the view lacks: ' + v.missing_columns.join(', ')) : null,
      v.probe && !v.probe.ok ? h('div', { class: 'err' }, v.probe.error) : null,
      v.status === 'denied' && v.exists ? h('code', { class: 'grant' }, `GRANT SELECT ON ${id.schema}.${v.name} TO ${id.current_user};`) : null));
    const tr = h('tr', { class: 'row', onclick: () => { det.hidden = !det.hidden; tr.classList.toggle('open', !det.hidden); } },
      h('td', {}, h('span', { class: 'vname' }, ico('chevron', 'ic caret'), h('b', { text: v.name }))), h('td', {}, badge(v.status)),
      h('td', { class: 'num' }, v.exists ? [h('span', { class: 'bar-mini' }, h('i', { style: `width:${(100 * v.cols_ok) / (v.cols_total || 1)}%` })), `${v.cols_ok}/${v.cols_total}`] : '–'),
      h('td', {}, v.probe ? h('span', { class: v.probe.ok ? 'txt-ok' : 'txt-bad', text: v.probe.ok ? '✓ Queryable' : '✗ Error' }) : h('span', { class: 'muted', text: '–' })),
      h('td', {}, v.used_by.map(i => h('span', { class: 'chip', text: dn[i] }))));
    rows.push(tr, det);
  }
  const viewsCard = h('div', { class: 'card' }, cardHead(`View permissions · ${id.schema}`, 'Click a row to see each column. “Queryable” means a real SELECT was test-run on the view.'),
    h('div', { class: 'scroll flat' }, h('table', { class: 't' }, h('thead', {}, h('tr', {}, ['View', 'Status', 'Readable columns', 'Test query', 'Used by'].map((t, i) => h('th', { class: i === 2 ? 'num' : '', text: t })))), h('tbody', {}, rows))),
    h('div', { class: 'note' }, ico('info'), h('span', {}, h('b', { text: 'Base tables: ' }), a.tables.map(t => `${t.name} ${t.exists ? (t.select ? '✓' : '✗') : '(missing)'}`).join(' · ') +
      '. Views run with the privileges of the view owner, so SELECT must be granted on each view directly.')));

  const acctCard = h('div', { class: 'card' }, cardHead('Account'),
    h('dl', { class: 'kv wide' },
      kv('Logged in as', id.session_user), kv('Acting as', id.current_user),
      kv('Superuser', id.superuser ? 'Yes (all privileges)' : 'No'), kv('Server', id.server),
      kv(`Schema ${id.schema}`, !id.schema_exists ? 'Does not exist' : id.schema_usage ? 'Has USAGE' : 'No USAGE'),
      h('div', {}, h('dt', { text: 'Member of' }), h('dd', {}, id.member_of.length ? id.member_of.map(r => h('span', { class: 'chip', text: r })) : h('span', { class: 'muted', text: 'none' })))));

  root.append(head, stats, dashCard, viewsCard, acctCard);
}
const kv = (k, v) => h('div', {}, h('dt', { text: k }), h('dd', { text: v }));

/* 3. Dashboard */
async function openDash(id) {
  if (!state.catalog) { try { state.catalog = (await api('/api/catalog')).dashboards; } catch (e) { return alert(e.message); } }
  state.dash = id; show('dash'); renderDash();
}
function renderDash() {
  const root = $('view-dash'); root.textContent = '';
  const d = state.catalog.find(x => x.id === state.dash), acc = state.access.dashboards.find(x => x.id === d.id);
  const vals = state.ctrl[d.id] ||= Object.fromEntries(d.controls.map(c => [c.name, c.default]));
  const inputs = d.controls.map(c => {
    const el = c.type === 'select'
      ? h('select', { onchange: e => { vals[c.name] = e.target.value; } }, c.options.map(o => { const [v, l] = Array.isArray(o) ? o : [o, o]; return h('option', { value: v, selected: String(v) === String(vals[c.name]) }, l); }))
      : h('input', { value: vals[c.name], placeholder: c.placeholder || '', maxlength: c.maxlen || 80, oninput: e => { vals[c.name] = e.target.value; }, onkeydown: e => { if (e.key === 'Enter') apply(); } });
    return h('div', { class: 'ctl' }, h('label', { text: c.label }), el);
  });
  const grid = h('div', { class: 'grid' });
  const pbixHost = h('div');
  const apply = () => { loadAll(d, acc, grid, true); renderPbixSection(pbixHost, d.pbix_page); };
  const controls = d.controls.length ? h('div', { class: 'controls' }, inputs, h('button', { class: 'btn primary', onclick: apply }, 'Apply')) : null;
  root.append(...[pageHead('Dashboard', [h('span', { class: 'emoji', text: d.icon }), h('span', { text: d.title }), badge(acc.status)], d.desc),
    controls, grid, pbixHost].filter(Boolean));
  loadAll(d, acc, grid, false);
  renderPbixSection(pbixHost, d.pbix_page);
}


const VTYPE_LABEL = {
  cardVisual: ['KPI Card', '🔢'],
  lineChart: ['Line Chart', '📈'],
  donutChart: ['Donut Chart', '🍩'],
  clusteredBarChart: ['Bar Chart', '📊'],
  clusteredColumnChart: ['Column Chart', '📊'],
  tableEx: ['Table', '📋'],
  pivotTable: ['Matrix / Pivot', '🧮'],
  slicer: ['Slicer', '🎛️']
};

function renderPbixSection(host, page) {
  host.textContent = '';
  const dlBtn = h('a', { href: '/api/powerbi/download', download: 'hm_sales_report.pbix', class: 'btn' }, ico('download'), 'Download .pbix');
  if (!page) {
    host.append(h('div', { class: 'card pbix-card' }, cardHead('Power BI report', 'The original hm_sales_report.pbix file.', dlBtn)));
    return;
  }
  const signal = loadCtrl.signal;
  const slicerVals = {};
  const nonSlicerLoaders = [];
  const pw = page.width || 1920, ph = page.height || 1080;

  const canvas = h('div', { class: 'pbix-canvas' }, page.visuals.map(v => {
    const [vtName] = VTYPE_LABEL[v.visualType] || [v.visualType, '📊'];
    const left = ((v.x / pw) * 100).toFixed(2) + '%';
    const top = ((v.y / ph) * 100).toFixed(2) + '%';
    const width = ((v.width / pw) * 100).toFixed(2) + '%';
    const height = ((v.height / ph) * 100).toFixed(2) + '%';
    const mainTitle = v.fields.map(f => f.label).join(' · ') || vtName;
    const body = h('div', { class: 'pbix-vbody' });
    const box = h('div', {
      class: 'pbix-visual v-' + v.visualType,
      style: `left:${left};top:${top};width:${width};height:${height}`,
      title: `${vtName}: ${v.fields.map(f => f.queryRef).join(', ')}`
    },
      h('div', { class: 'pbix-vhd' }, h('span', { class: 'pbix-vtitle', text: mainTitle })),
      body);

    const loadVisual = () => {
      if (signal.aborted) return Promise.resolve();
      body.textContent = '';
      body.append(h('div', { class: 'placeholder', style: 'padding:8px;font-size:11px' }, h('span', { class: 'spin' }), 'Loading…'));
      const q = new URLSearchParams();
      if (v.visualType !== 'slicer') {
        for (const [scol, sval] of Object.entries(slicerVals)) {
          if (sval && sval !== 'all') q.set('slicer_' + scol, sval);
        }
      }
      return api(`/api/powerbi/data/${page.id}/${v.name}?${q}`, undefined, signal).then(data => {
        body.textContent = '';
        drawPbixVisual(body, v, data, slicerVals, () => {
          nonSlicerLoaders.forEach(fn => enqueue(fn, signal));
        });
      }).catch(e => {
        if (e.name === 'AbortError' || signal.aborted) return;
        body.textContent = '';
        body.append(h('div', { class: 'small', style: 'color:var(--bad);padding:4px' }, '🔒 ' + e.message));
      });
    };

    if (v.visualType !== 'slicer') nonSlicerLoaders.push(loadVisual);
    enqueue(loadVisual, signal);
    return box;
  }));

  host.append(h('div', { class: 'card pbix-card' },
    cardHead(`Power BI report · ${page.displayName}`, `Page ${page.page_number} of hm_sales_report.pbix · ${page.visuals.length} visuals`, dlBtn),
    canvas));
}

function drawPbixVisual(body, v, data, slicerVals, onSlicerChange) {
  const vt = v.visualType;
  if (vt === 'cardVisual') {
    const val = data.rows[0]?.[0];
    const label = v.fields[0]?.label || '';
    const num = val == null ? '–' : Number(val);
    body.append(h('div', { class: 'pbix-kpi', title: full(num) },
      h('div', { class: 'pbix-kpi-val', text: typeof num === 'number' && !isNaN(num) ? compact(num) : String(val ?? '–') }),
      h('div', { class: 'pbix-kpi-lbl', text: label })));
    return;
  }
  if (vt === 'slicer') {
    const prop = v.fields[0]?.prop || '';
    const cur = slicerVals[prop] || 'all';
    const opts = [['all', 'All'], ...data.rows.map(r => [String(r[0]), String(r[0])])];
    const sel = h('select', {
      style: 'margin-top:4px;height:30px;padding:0 8px;font-size:12px',
      onchange: e => { slicerVals[prop] = e.target.value; onSlicerChange(); }
    }, opts.map(([val, lbl]) => h('option', { value: val, selected: val === cur }, lbl)));
    body.append(sel);
    return;
  }
  if (!data.rows.length) {
    body.append(h('div', { class: 'muted small', style: 'text-align:center;padding:12px' }, 'No data'));
    return;
  }
  const yLabel = v.fields[1]?.label || v.fields[0]?.label || 'Value';
  if (vt === 'lineChart') {
    renderLine(body, data, { x: 'x', series: [{ col: 'y', label: yLabel, fmt: 'dec' }] });
  } else if (vt === 'donutChart') {
    renderDonut(body, data, { label: 'x', series: [{ col: 'y', label: yLabel, fmt: 'dec' }] });
  } else if (vt === 'clusteredBarChart') {
    renderBar(body, data, { x: 'x', horizontal: true, series: [{ col: 'y', label: yLabel, fmt: 'dec' }] });
  } else if (vt === 'clusteredColumnChart') {
    renderBar(body, data, { x: 'x', horizontal: false, series: [{ col: 'y', label: yLabel, fmt: 'dec' }] });
  } else if (vt === 'pivotTable') {
    renderHeat(body, data, { rows: 'r', cols: 'c', value: 'v', fmt: 'dec', row_order: ['Under 20', '20-29', '30-39', '40-49', '50-59', '60+', 'Unknown'] });
  } else if (vt === 'tableEx') {
    const cols = v.fields.map((f, i) => ({ col: 'c' + i, label: f.label, fmt: f.agg == null ? 'text' : 'dec' }));
    renderTable(body, data, { columns: cols });
  }
}

/* Hàng đợi tối đa 3 truy vấn song song. Mỗi lần mở/áp dụng dashboard tạo một "thế hệ" mới:
   hủy (abort) mọi request cũ còn đang chạy để chúng không chiếm chỗ của dashboard mới
   (trước đây request cũ vẫn giữ slot nên quay lại dashboard thì widget đứng im không load). */
const queue = []; let running = 0; let loadCtrl = new AbortController();
function resetQueue() { queue.length = 0; loadCtrl.abort(); loadCtrl = new AbortController(); }
function enqueue(fn, signal) { queue.push({ fn, signal }); pump(); }
function pump() {
  while (running < 3 && queue.length) {
    const job = queue.shift();
    if (job.signal?.aborted) continue;
    running++;
    Promise.resolve().then(job.fn).catch(() => { }).finally(() => { running--; pump(); });
  }
}

function loadAll(d, acc, grid, fromApply) {
  resetQueue(); grid.textContent = '';
  for (const w of d.widgets) {
    const wa = acc.widgets.find(x => x.id === w.id);
    const card = h('div', { class: 'card w' + (wa.available ? '' : ' locked'), style: `--span:${w.span || 12}` });
    grid.append(card);
    renderCard(d, w, wa, card, fromApply);
  }
}

function params(d, w) {
  const vals = state.ctrl[d.id] || {}, q = new URLSearchParams();
  for (const n of w.use_controls || []) q.set(n, vals[n] ?? '');
  return q;
}

function renderCard(d, w, wa, card, auto) {
  card.textContent = '';
  const signal = loadCtrl.signal;
  const acts = h('div', { class: 'acts' });
  const hd = h('div', { class: 'hd' }, h('h3', { text: w.title }), acts);
  const body = h('div'); const ft = h('div', { class: 'ft' });
  card.append(hd, body, ft);
  if (!wa.available) {
    body.append(h('div', { class: 'placeholder locked-msg' }, ico('lock', 'ic big'), h('b', { text: 'This account cannot use this widget yet' }), h('ul', {}, wa.reasons.map(r => h('li', { text: r })))));
    return;
  }
  if (w.note) ft.textContent = w.note;
  const needVals = (w.needs || []).some(n => !(state.ctrl[d.id]?.[n] || '').trim());
  const waiting = () => { body.textContent = ''; body.append(h('div', { class: 'placeholder' }, h('span', { class: 'spin' }), 'Waiting in queue…')); };
  const submit = refresh => { waiting(); enqueue(() => run(refresh), signal); };
  const run = refresh => {
    if (signal.aborted) return Promise.resolve();
    const q = params(d, w); if (refresh) q.set('refresh', '1');
    body.textContent = ''; body.append(h('div', { class: 'placeholder' }, h('span', { class: 'spin' }), 'Querying…'));
    const t0 = Date.now(), tick = setInterval(() => { const p = body.querySelector('.placeholder'); if (p) p.lastChild.textContent = `Querying… ${Math.round((Date.now() - t0) / 1000)}s`; }, 1000);
    return api(`/api/data/${d.id}/${w.id}?${q}`, undefined, signal).then(data => {
      body.textContent = ''; renderWidget(body, data, w);
      const meta = `${data.rows.length} rows · ${data.ms} ms${data.cached ? ` · cached ${Math.max(1, Math.round(data.age / 60))} min ago` : ''}${data.truncated ? ' · truncated' : ''}`;
      acts.textContent = '';
      acts.append(
        h('button', { class: 'btn ghost icon', title: 'Refresh (' + meta + ')', 'aria-label': 'Refresh', onclick: () => submit(true) }, ico('refresh')),
        h('button', { class: 'btn ghost icon', title: 'Download CSV', 'aria-label': 'Download CSV', onclick: () => { const a = h('a', { href: URL.createObjectURL(new Blob([toCsv(data)], { type: 'text/csv' })), download: `${d.id}_${w.id}.csv` }); a.click(); } }, ico('download')));
    }).catch(e => {
      if (e.name === 'AbortError' || signal.aborted) return;
      body.textContent = '';
      if (e.status === 401) { alert('Session expired, please reconnect.'); disconnect(); return; }
      body.append(h('div', { class: 'err' }, e.message), h('button', { class: 'btn sm', style: 'margin-top:8px', onclick: () => submit(false) }, 'Retry'));
    }).finally(() => clearInterval(tick));
  };
  if (w.heavy && auto && w.apply_run && !needVals) { submit(false); return; }
  if (w.heavy) {
    if (needVals) { body.append(h('div', { class: 'placeholder', text: 'Enter a value in the filter bar above, then click “Apply”.' })); return; }
    const go = h('button', { class: 'btn primary', onclick: () => submit(false) }, ico('play'), 'Run query');
    body.append(h('div', { class: 'placeholder' }, h('div', { text: 'Large query, runs on demand.' }), go));
    return;
  }
  if (needVals) { body.append(h('div', { class: 'placeholder', text: 'Enter a value in the filter bar above, then click “Apply”.' })); return; }
  submit(false);
}

/* Khởi động */
(async function init() {
  renderDashNav();
  await renderConnect();
  try {
    const me = await api('/api/me');
    if (me.connected) { setConnected(me.access, me.host, me.dbname); renderAccess(); show('access'); }
  } catch (e) { /* noop */ }
})();
