// Display-only tools. No fitted model, target inputs or scoring live here.
const $ = id => document.getElementById(id);
const make = (tag, text, cls) => { const e = document.createElement(tag); if (text) e.textContent = text; if (cls) e.className = cls; return e; };
const clock = s => `${Math.floor(s / 60)}:${Math.floor(s % 60).toString().padStart(2, '0')}`;
const stateAt = (xs, f) => xs?.find(x => x[0] <= f && f < x[1])?.[2] || 'X';

export function mountMatchday(api) {
  let start = 0, differences = [], data;
  const chart = make('figure', '', 'evidence-plot');
  chart.id = 'evidencePlot';
  chart.append(make('figcaption', 'Evidence at observation times · uncalibrated scores'));
  const canvas = make('canvas'); canvas.id = 'evidenceCanvas'; canvas.width = 1000; canvas.height = 300;
  canvas.setAttribute('aria-label', 'Home-versus-away evidence, dead evidence and ball support. Exact values available in the sample inspector.');
  const tip = make('p', 'Hover to inspect a published sample. Missing values break the traces.', 'evidence-tooltip');
  tip.id = 'evidenceTooltip'; chart.append(canvas, tip);
  document.querySelector('.timeline-block').after(chart);
  const badge = make('p', '', 'comparison-badge'); badge.hidden = true; document.querySelector('.pitch-shell').append(badge);
  const pan = $('timelinePan'), zoom = $('timelineZoom');
  function windowRange() {
    const duration = data?.duration_frames || 1, span = Math.ceil(duration / Number(zoom.value));
    start = Math.max(0, Math.min(start, duration - span));
    return [start, Math.min(duration, start + span)];
  }
  function lane(track, intervals, range, marker = true) {
    track.replaceChildren();
    for (const [a, b, state] of intervals || []) {
      if (b <= range[0] || a >= range[1]) continue;
      const el = make('span', '', 'lane-segment'); el.dataset.state = state;
      el.style.left = `${100 * (Math.max(a, range[0]) - range[0]) / (range[1] - range[0])}%`;
      el.style.width = `${100 * (Math.min(b, range[1]) - Math.max(a, range[0])) / (range[1] - range[0])}%`;
      el.title = `${state} · frames ${a}–${b - 1} · ${clock(a / data.fps)}–${clock(b / data.fps)}`;
      track.append(el);
    }
    if (marker) track.append(make('span', '', 'lane-marker'));
  }
  function paintEvidence(range) {
    const ctx = canvas.getContext('2d'), width = canvas.width, fps = data.fps;
    ctx.fillStyle = '#10232a'; ctx.fillRect(0, 0, width, 300);
    const specs = [['team_log_evidence', 'Home − away · log ratio', '#d6e79d'], ['dead_log_evidence', 'Dead · log score', '#ee946d'], ['ball_support_4s', 'Ball support · fraction', '#b6cbd5']];
    const samples = data.samples.filter(s => range[0] <= s.f && s.f < range[1]);
    specs.forEach(([key, label, color], row) => {
      const top = row * 100, finite = samples.map(s => s.e?.[key]).filter(v => typeof v === 'number' && Number.isFinite(v));
      const lo = key === 'ball_support_4s' ? 0 : Math.min(0, ...finite), hi = key === 'ball_support_4s' ? 1 : Math.max(1, ...finite);
      ctx.font = '14px Arial'; ctx.fillStyle = '#d4dfd7'; ctx.fillText(label, 12, top + 18);
      ctx.font = '11px monospace'; ctx.fillStyle = '#a5b4b9'; ctx.fillText(`${lo.toFixed(1)} … ${hi.toFixed(1)}`, 12, top + 38);
      ctx.strokeStyle = '#32464b'; ctx.beginPath(); ctx.moveTo(180, top + 85); ctx.lineTo(width - 12, top + 85); ctx.stroke();
      ctx.strokeStyle = color; ctx.lineWidth = 2; ctx.beginPath(); let pen = false;
      for (const s of samples) {
        const v = s.e?.[key];
        if (typeof v !== 'number' || !Number.isFinite(v)) { pen = false; continue; }
        const x = 180 + (width - 192) * (s.f - range[0]) / (range[1] - range[0]), y = top + 82 - 55 * (v - lo) / (hi - lo);
        if (pen) ctx.lineTo(x, y); else ctx.moveTo(x, y); pen = true;
      }
      ctx.stroke();
      if (!finite.length) { ctx.fillStyle = '#a5b4b9'; ctx.fillText('No declared values in this window', 200, top + 55); }
    });
    chart.dataset.fps = String(fps);
  }
  canvas.addEventListener('pointermove', e => {
    if (!data) return;
    const r = canvas.getBoundingClientRect(), range = windowRange();
    const fraction = Math.max(0, Math.min(1, ((e.clientX - r.left) / r.width * 1000 - 180) / 808));
    const f = range[0] + fraction * (range[1] - range[0]);
    let lo = 0, hi = data.samples.length - 1;
    while (lo < hi) { const m = Math.ceil((lo + hi) / 2); if (data.samples[m].f <= f) lo = m; else hi = m - 1; }
    const s = data.samples[lo], fmt = v => typeof v === 'number' && Number.isFinite(v) ? v.toFixed(3) : 'missing';
    tip.textContent = `Sample frame ${s.f} · ${clock(s.f / data.fps)} · H−A ${fmt(s.e?.team_log_evidence)} log ratio · D ${fmt(s.e?.dead_log_evidence)} log score · support ${fmt(s.e?.ball_support_4s)}. ${data.kind === 'synthetic_demo' ? 'Synthetic fixture.' : 'Licensed external: Bassek et al., CC BY 4.0.'}`;
  });
  function render() {
    if (!data) return;
    const range = windowRange();
    lane($('trackV2'), data.predictions.v2, range); lane($('trackV1'), data.predictions.v1, range);
    lane($('trackReference'), data.truth, range); lane($('trackDifference'), differences, range);
    const mini = $('timelineMinimap'); lane(mini, data.predictions.v2, [0, data.duration_frames], false);
    const box = make('span'); box.id = 'minimapWindow'; box.style.left = `${100 * range[0] / data.duration_frames}%`; box.style.width = `${100 * (range[1] - range[0]) / data.duration_frames}%`; mini.append(box);
    for (const t of [$('trackV1'), $('trackV2'), $('trackReference')]) t.dataset.filter = $('stateFilter').value;
    pan.max = String(Math.max(0, data.duration_frames - (range[1] - range[0]))); pan.value = String(start); pan.disabled = zoom.value === '1';
    $('rulerStart').textContent = clock(range[0] / data.fps); $('rulerMid').textContent = clock((range[0] + range[1]) / 2 / data.fps); $('rulerEnd').textContent = clock(range[1] / data.fps);
    $('zoomWindow').textContent = `${clock(range[0] / data.fps)}–${clock(range[1] / data.fps)}`;
    for (const marker of document.querySelectorAll('.timeline-lane .lane-marker')) {
      const f = api.getFrame(); marker.style.left = `${100*(f-range[0])/(range[1]-range[0])}%`;
      marker.hidden = f < range[0] || f >= range[1];
    }
    paintEvidence(range);
  }
  function frame() {
    if (!data) return;
    let range = windowRange(); const f = api.getFrame();
    if (f < range[0] || f >= range[1]) { start = f - (range[1] - range[0]) / 2; render(); range = windowRange(); }
    for (const el of document.querySelectorAll('.timeline-lane .lane-marker')) {
      el.hidden = false; el.style.left = `${100 * (f - range[0]) / (range[1] - range[0])}%`;
      el.parentElement.setAttribute('aria-valuemin', String(range[0])); el.parentElement.setAttribute('aria-valuemax', String(range[1]-1)); el.parentElement.setAttribute('aria-valuenow', String(f));
    }
    badge.hidden = !$('differenceToggle').checked;
    badge.textContent = `Same observed geometry · V1 ${stateAt(data.predictions.v1, f)} / V2 ${stateAt(data.predictions.v2, f)}`;
  }
  function sequence() {
    data = api.getData(); if (!data) return;
    start = 0; differences = [];
    const boundaries = [...new Set([0, data.duration_frames, ...data.predictions.v1.flatMap(s => s.slice(0, 2)), ...data.predictions.v2.flatMap(s => s.slice(0, 2))])].sort((a,b) => a-b);
    for (let i = 0; i < boundaries.length - 1; i++) if (stateAt(data.predictions.v1, boundaries[i]) !== stateAt(data.predictions.v2, boundaries[i])) differences.push([boundaries[i], boundaries[i+1], 'X']);
    render(); frame();
  }
  zoom.addEventListener('change', () => { const d = api.getData(); if (!d) return; start = api.getFrame() - d.duration_frames / Number(zoom.value) / 2; render(); frame(); });
  pan.addEventListener('input', () => { start = Number(pan.value); render(); });
  $('stateFilter').addEventListener('change', render);
  $('differenceToggle').addEventListener('change', () => { $('differenceLane').hidden = !$('differenceToggle').checked; frame(); });
  for (const id of ['trackV1', 'trackV2', 'trackReference', 'trackDifference']) {
    const track = $(id); track.removeAttribute('aria-hidden'); track.tabIndex = 0; track.setAttribute('role', 'slider'); track.setAttribute('aria-label', 'Seek in '+id);
    track.addEventListener('click', e => {
      if (!data) return; const r = track.getBoundingClientRect(), range = windowRange();
      const f = Math.floor(range[0] + Math.max(0, Math.min(1, (e.clientX - r.left) / r.width)) * (range[1] - range[0] - 1));
      api.setFrame(f); const intervals = id === 'trackReference' ? data.truth : id === 'trackV1' ? data.predictions.v1 : data.predictions.v2;
      const spell = intervals.find(s => s[0] <= f && f < s[1]);
      $('spellInspect').textContent = spell ? `${spell[2]} · frames ${spell[0]}–${spell[1]-1} · ${((spell[1]-spell[0])/data.fps).toFixed(2)}s. Selected frame ${f}; sample support and evidence are shown alongside and below.` : 'Unlabelled frame.';
    });
  }
  document.addEventListener('keydown', e => {
    if (e.target.closest('input,select,textarea,button,a,[contenteditable=true]')) return;
    if (e.code === 'Space') { e.preventDefault(); api.play(); }
    if (e.key === '?') $('shortcutsButton').click();
    if (e.key === 'ArrowRight' || e.key === 'ArrowLeft') { e.preventDefault(); const d = e.key === 'ArrowRight' ? 1 : -1; if (e.shiftKey) api.seekChange(d); else api.setFrame(api.getFrame()+d); }
  });
  $('retryLoad').addEventListener('click', api.retry);
  $('shortcutsButton').addEventListener('click', () => { const open = $('shortcutsHelp').hidden; $('shortcutsHelp').hidden = !open; $('shortcutsButton').setAttribute('aria-expanded', String(open)); });
  $('fullscreenButton').addEventListener('click', async () => {
    try { if (document.fullscreenElement) await document.exitFullscreen(); else await $('replay').requestFullscreen(); }
    catch { $('spellInspect').textContent = 'Fullscreen is unavailable in this browser. The replay remains available below.'; }
  });
  document.addEventListener('fullscreenchange', () => { $('fullscreenButton').textContent = document.fullscreenElement ? 'Exit fullscreen' : '⛶ Fullscreen'; });
  const video = $('heroVideo'), motion = $('heroMotion'), reduce = matchMedia('(prefers-reduced-motion: reduce)');
  function hero(playing) { if (playing) { if (!video.getAttribute('src')) video.src = './media/synthetic-demo.mp4'; video.play().then(() => { motion.textContent = 'Pause synthetic preview'; motion.setAttribute('aria-pressed','true'); }).catch(() => { motion.textContent = 'Play synthetic preview'; }); } else { video.pause(); motion.textContent = 'Play synthetic preview'; motion.setAttribute('aria-pressed','false'); } }
  motion.addEventListener('click', () => hero(video.paused));
  if (!reduce.matches) hero(true);
  reduce.addEventListener('change', () => { if (reduce.matches) hero(false); });
  const observer = new IntersectionObserver(entries => { for (const e of entries) if (e.isIntersecting) { e.target.classList.add('is-visible'); document.querySelectorAll('.primary-nav a[href^="#"]').forEach(a => { if (a.hash === '#'+e.target.id) a.setAttribute('aria-current','location'); else a.removeAttribute('aria-current'); }); } }, {threshold:.12});
  for (const section of document.querySelectorAll('main > section')) { if (!reduce.matches && section.id !== 'top') section.classList.add('reveal-ready'); observer.observe(section); }
  return {sequence, frame};
}

export function renderBenchmarkChart(rows) {
  const root = $('benchmarkChart'); root.replaceChildren();
  for (const row of rows) {
    const el = make('div', '', 'chart-row'); el.tabIndex = 0;
    el.title = `${row.match_id} ${row.scenario}: V1 ${row.v1.spellF1.toFixed(5)}; V2 ${row.v2.spellF1.toFixed(5)}. Reused external development.`;
    el.setAttribute('aria-label', el.title); el.append(make('span', `${row.match_id} / ${row.scenario}`));
    const axis = make('div', '', 'chart-axis'), line = make('span', '', 'chart-connector');
    line.style.left = `${100*Math.min(row.v1.spellF1,row.v2.spellF1)}%`; line.style.width = `${100*Math.abs(row.v2.spellF1-row.v1.spellF1)}%`; axis.append(line);
    for (const version of ['v1','v2']) { const point = make('span', '', 'chart-point '+version); point.style.left = `${100*row[version].spellF1}%`; axis.append(point); } el.append(axis); root.append(el);
  }
}
