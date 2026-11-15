/* Clone profiles reuse the demo API and Radar; source values stay separate from game results. */
const $ = id => document.getElementById(id);
const percent = value => Number.isFinite(value) ? `${(value * 100).toFixed(1)}%` : '—';
const number = value => Number.isFinite(value) ? value.toLocaleString(undefined, { maximumFractionDigits: 2 }) : '—';

// Weight each known interval by elapsed time, without extrapolating beyond the last sample.
function heatBins(routes, cell = 96) {
  const bins = new Map();
  let seconds = 0;
  for (const route of routes) {
    const path = route.path || [];
    for (let i = 0; i + 1 < path.length; i++) {
      const [t, x, y] = path[i], next = path[i + 1][0], dt = next - t;
      if (![t, x, y, next].every(Number.isFinite) || dt <= 0) continue;
      const cx = Math.floor(x / cell), cy = Math.floor(y / cell), key = `${cx},${cy}`;
      const bin = bins.get(key) || { x: cx * cell, y: cy * cell, seconds: 0 };
      bin.seconds += dt;
      bins.set(key, bin);
      seconds += dt;
    }
  }
  return { bins: [...bins.values()], seconds, cell };
}

function quirkValue(key, value) {
  return key.endsWith('_share') ? percent(value) : number(value);
}

function bars(values) {
  const entries = Object.entries(values || {}).filter(([, v]) => Number.isFinite(v)).sort((a, b) => b[1] - a[1]);
  return entries.map(([name, value]) => `<div class="profile-bar"><span>${esc(name)}</span><div class="bar"><i style="width:${Math.max(0, Math.min(100, value * 100))}%"></i></div><span>${percent(value)}</span></div>`).join('') || '<p class="muted small">No measurements available.</p>';
}

let profile = null, radar = null, heatRoutes = [], sequence = 0, active = null;
const routeCache = new Map();

function renderQuirks() {
  const all = Object.entries(profile.quirks || {});
  const entries = all.filter(([, q]) => !$('distinctive').checked || q.distinctive);
  $('quirks').innerHTML = entries.map(([key, q]) => {
    const control = (profile.quirk_controls || {})[key];
    return `<tr><td>${esc(q.meaning || key)}${q.distinctive ? '<small>Distinctive</small>' : ''}</td><td>${quirkValue(key, q.player)}</td><td>${quirkValue(key, q.population_mean)}</td><td>${number(q.z)} σ</td><td>${esc(control ? control.status : 'Measured only; no separate control')}<small>${esc(control ? control.applied_by : '')}</small></td></tr>`;
  }).join('');
  $('quirk-empty').textContent = !all.length ? 'No quirk measurements in this v1 profile. Select an L clone to inspect measured quirks.' : !entries.length ? 'No distinctive quirks. Uncheck the filter to see all measurements.' : `${entries.length} of ${all.length} measured quirks shown. Rates describe the real player, not a bot match.`;
}

function drawHeat() {
  if (!radar || !profile) return;
  const side = $('side').value;
  const routes = heatRoutes.filter(r => r.side === side);
  radar.draw([]);
  const heat = heatBins(routes), peak = Math.max(0, ...heat.bins.map(b => b.seconds));
  const ctx = radar.ctx, size = heat.cell / radar.view.span * radar.canvas.width;
  for (const b of heat.bins) {
    const [x, y] = radar.px(b.x, b.y + heat.cell);
    const strength = b.seconds / peak;
    ctx.fillStyle = `rgba(${Math.round(130 + strength * 125)},${Math.round(91 + strength * 134)},${Math.round(196 - strength * 36)},${0.3 + strength * 0.7})`;
    ctx.fillRect(x, y, size + 0.5, size + 0.5);
  }
  $('heat-empty').textContent = routes.length ? '' : 'No recorded opening positions for this side.';
  $('heat-caption').textContent = `${routes.length} recorded openings · ${number(heat.seconds)} observed seconds · brighter cells mean more time. Each side uses its own colour scale.`;
  $('heatmap').setAttribute('aria-label', `${profile.display_name}, ${side} opening position heat map from ${routes.length} recorded routes. Most visited areas are listed alongside.`);
}

function renderSide() {
  const side = $('side').value;
  $('heat-side').textContent = `${side} side`;
  $('positions').innerHTML = bars((profile.positions || {})[side]);
  $('routes').innerHTML = bars((profile.route_shares || {})[side]);
  const plans = (profile.buy_plan || {})[side] || {};
  $('buys').innerHTML = ['pistol', 'eco', 'force', 'full'].map(type => {
    const plan = plans[type];
    return `<article class="buy-card"><h3>${type === 'full' ? 'Full buy' : type}</h3><span class="muted small">${plan ? `${number(plan.rounds_of_this_type)} source rounds` : 'No plan available'}</span>${plan ? (plan.items || []).length ? `<ul>${plan.items.map(i => `<li>${esc(i)}</li>`).join('')}</ul>` : '<p class="small muted">No recurring purchases in this plan.</p>' : ''}</article>`;
  }).join('');
  const url = new URL(location.href); url.searchParams.set('side', side); history.replaceState(null, '', url);
  $('replay').href = `replay.html?tab=real&clone=${encodeURIComponent(profile.clone_id)}&side=${side}`;
  drawHeat();
}

async function loadRoutes(id, signal) {
  if (routeCache.has(id)) return routeCache.get(id);
  const meta = await api(`/replay/clones/${encodeURIComponent(id)}/routes`, { signal });
  const result = [];
  let cursor = 0;
  // Bound concurrency so switching profiles cannot flood the local service with reads.
  await Promise.all(Array.from({ length: Math.min(6, meta.length) }, async () => {
    while (cursor < meta.length) {
      const route = meta[cursor++];
      result.push(await api(`/replay/clones/${encodeURIComponent(id)}/routes/${encodeURIComponent(route.recording)}`, { signal }));
    }
  }));
  routeCache.set(id, result);
  return result;
}

async function show(id) {
  const request = ++sequence;
  if (active) active.abort();
  active = new AbortController();
  const signal = active.signal;
  $('error').textContent = ''; $('loading').hidden = false; $('content').hidden = true;
  heatRoutes = []; profile = null;
  try {
    const c = await api(`/replay/clones/${encodeURIComponent(id)}`, { signal });
    if (request !== sequence) return;
    profile = c;
    document.title = `${c.display_name} · Clone profiles`;
    const url = new URL(location.href); url.searchParams.set('clone', id); history.replaceState(null, '', url);
    $('identity').textContent = `${c.clone_id} / ${c.map || 'map unavailable'}`;
    $('player-name').textContent = c.display_name;
    $('summary').textContent = c.learned ? 'Recorded openings and purchases, with measured player quirks. Quirk controls are implemented; their likeness inside CS2 still needs verification.' : 'A clone built from recorded openings and purchase tendencies. Combat passes back to the existing bot AI.';
    const games = c.source_games || [], rounds = c.rounds || {};
    $('metrics').innerHTML = [[games.length, 'Source matches'], [(rounds.T || 0) + (rounds.CT || 0), 'Building rounds'], [Object.values(c.quirks || {}).filter(q => q.distinctive).length, 'Distinctive quirks'], [c.reaction_ms == null ? 'Unmeasured' : `${number(c.reaction_ms)} ms`, 'Reaction time']].map(([value, label]) => `<div><strong>${esc(value)}</strong><span>${label}</span></div>`).join('');
    $('weapons').innerHTML = (c.weapons || []).map((w, i) => `<span class="pill">${i + 1}. ${esc(w)}</span>`).join('') || '<p class="muted">No weapon preferences available.</p>';
    const sim = (c.similarity || {}).player_vs_self || {};
    $('similarity').innerHTML = ['T', 'CT'].map(side => `<tr><td>${side}</td><td>${percent((sim[side] || {}).position_overlap)}</td><td>${percent((sim[side] || {}).route_overlap)}</td><td>${esc(((sim[side] || {}).rounds || []).join(' / ') || 'Unavailable')}</td></tr>`).join('');
    $('holdout').textContent = `Held-back matches: ${((c.similarity || {}).held_back_matches || []).join(', ') || 'unavailable'}. Small samples limit these comparisons. In-game clone similarity has not been measured.`;
    $('provenance').innerHTML = `<p class="muted small">Source match IDs: ${esc(games.map(g => g.match_id).join(', ') || 'unavailable')}. Built: ${esc(c.built_at || 'unavailable')}.</p>`;
    $('replay').href = `replay.html?tab=real&clone=${encodeURIComponent(id)}&side=${$('side').value}`;
    renderQuirks(); renderSide();
    $('content').hidden = false; $('loading').hidden = true;
    $('heat-empty').textContent = 'Loading recorded opening positions…';
    try {
      const routes = await loadRoutes(id, signal);
      if (request !== sequence) return;
      heatRoutes = routes; drawHeat();
    } catch (error) {
      if (request !== sequence || error.name === 'AbortError') return;
      radar.draw([]); $('heat-empty').textContent = 'Opening positions could not be loaded.';
      $('heat-caption').textContent = error.message;
    }
  } catch (error) {
    if (request !== sequence || error.name === 'AbortError') return;
    $('loading').hidden = true; $('content').hidden = true;
    $('error').textContent = `Could not load this profile: ${error.message}`;
  }
}

async function setup() {
  $('side').value = new URLSearchParams(location.search).get('side') === 'CT' ? 'CT' : 'T';
  $('clone').onchange = event => show(event.target.value);
  $('side').onchange = () => profile && renderSide();
  $('distinctive').onchange = () => profile && renderQuirks();
  try {
    const [list, shape] = await Promise.all([api('/replay/clones'), outline()]);
    radar = new Radar($('heatmap'), shape);
    new ResizeObserver(() => { if (!$('content').hidden && heatRoutes.length) drawHeat(); }).observe($('heatmap'));
    if (!list.length) { $('loading').textContent = 'No clone profiles available. Add a data-built profile to the clone catalogue.'; return; }
    $('clone').innerHTML = list.map(c => `<option value="${esc(c.clone_id)}">${esc(c.display_name)} (${esc(c.clone_id)})</option>`).join('');
    $('clone').disabled = false;
    const wanted = new URLSearchParams(location.search).get('clone');
    const first = list.some(c => c.clone_id === wanted) ? wanted : list.some(c => c.clone_id === 'donkL') ? 'donkL' : list[0].clone_id;
    $('clone').value = first;
    await show(first);
  } catch (error) { $('loading').hidden = true; $('error').textContent = `Could not load profiles: ${error.message}`; }
}

if (typeof module !== 'undefined') module.exports = { heatBins, quirkValue };
if (typeof document !== 'undefined') setup();
