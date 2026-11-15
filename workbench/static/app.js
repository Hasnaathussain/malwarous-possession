"use strict";
(() => {
  const $ = id => document.getElementById(id);
  const colors = {H: "#226a60", A: "#b9683b", D: "#747975", X: "#d1cec5"};
  const stateNames = {H: "Home", A: "Away", D: "Dead ball", X: "Unknown / abstain"};
  let bundle, match, version, t = 0, playing = false, lastTick = 0, viewStart = 0, viewEnd = 0;
  let events = [], visibleEvents = [], chartBackground = null, mediaAvailable = false;
  let mediaFailed = false, mediaWantsPlay = false, sampleIndex = -1;
  const video = $("video");
  const fmt = (seconds, fraction = false) => {
    const raw = Math.max(0, seconds || 0), value = fraction ? Math.round(raw * 1000) / 1000 : Math.floor(raw);
    const mins = Math.floor(value / 60), secs = fraction ? (value % 60).toFixed(3).padStart(6, "0") : Math.floor(value % 60).toString().padStart(2, "0");
    return `${mins.toString().padStart(2, "0")}:${secs}`;
  };
  function viewDuration() {
    if (!match) return 0;
    const selection = $("zoomSelect").value;
    const requested = selection === "full" ? match.duration_s : Number(selection);
    return Math.min(match.duration_s, Number.isFinite(requested) && requested > 0 ? requested : match.duration_s);
  }
  function updateViewLabels() {
    if (!match) return;
    $("axisStart").textContent = fmt(viewStart);
    $("axisMidpoint").textContent = fmt((viewStart + viewEnd) / 2);
    $("axisEnd").textContent = fmt(viewEnd);
    $("visibleRange").textContent = `Visible ${fmt(viewStart, true)}–${fmt(viewEnd, true)} of ${fmt(match.duration_s, true)}`;
  }
  function setWindowAround(time) {
    const span = viewDuration(), latestStart = Math.max(0, match.duration_s - span);
    const start = Math.max(0, Math.min(latestStart, time - span / 2));
    const end = start + span;
    if (Math.abs(start - viewStart) < 1e-8 && Math.abs(end - viewEnd) < 1e-8) return false;
    viewStart = start;
    viewEnd = end;
    renderTimelines();
    prepareEvidenceChart();
    return true;
  }
  function ensureWindowContains(time) {
    return time < viewStart || time > viewEnd ? setWindowAround(time) : false;
  }
  const fps = () => {
    const value = match?.provenance?.fps ?? match?.media?.fps;
    return Number.isFinite(value) && value > 0 ? value : null;
  };
  const lastFrame = rate => rate && match
    ? Math.max(0, Math.ceil(match.duration_s * rate - 1e-7) - 1) : null;
  const frameAt = rate => rate && match
    ? Math.min(lastFrame(rate), Math.max(0, Math.floor(t * rate + 1e-7))) : null;
  function stepFrame(direction) {
    const rate = fps();
    if (!rate) return;
    const current = frameAt(rate);
    const target = Math.max(0, Math.min(lastFrame(rate), current + direction));
    if (target === current) return;
    setTime(target / rate);
  }
  const text = value => typeof value === "object" ? JSON.stringify(value) : String(value ?? "—");
  function element(tag, value, className) {
    const node = document.createElement(tag);
    if (value !== undefined) node.textContent = text(value);
    if (className) node.className = className;
    return node;
  }
  function option(select, value, label) {
    const node = element("option", label);
    node.value = value;
    select.append(node);
  }
  function stateAt(rows, time) {
    if (!rows) return null;
    // End-of-match readout refers to the last instant before its half-open end.
    const when = Math.min(time, match.duration_s - 1e-8);
    let lo = 0, hi = rows.length - 1;
    while (lo <= hi) {
      const mid = (lo + hi) >> 1, row = rows[mid];
      if (when < row.start_s) hi = mid - 1;
      else if (when >= row.end_s) lo = mid + 1;
      else return row.state;
    }
    return null;
  }
  function currentSample() {
    const samples = match.samples || [];
    let lo = 0, hi = samples.length - 1, found = -1;
    while (lo <= hi) {
      const mid = (lo + hi) >> 1;
      if (samples[mid].t <= t) { found = mid; lo = mid + 1; }
      else hi = mid - 1;
    }
    sampleIndex = found;
    return samples[found];
  }
  function selectedSpells() { return match.predictions?.[version]?.spells || []; }
  function mediaTime() { return t + (match.media?.offset_s || 0); }
  function insideMedia() { return mediaAvailable && !mediaFailed && mediaTime() >= 0 && (!Number.isFinite(video.duration) || mediaTime() < video.duration); }
  function syncVideo(force = false) {
    if (!match.media || mediaFailed) return;
    const mapped = mediaTime();
    if (insideMedia()) {
      if (force || Math.abs(video.currentTime - mapped) > 0.35) video.currentTime = mapped;
      if (playing && video.paused && !mediaWantsPlay) {
        mediaWantsPlay = true;
        video.play().catch(() => {
          setPlaying(false);
          $("videoStatus").textContent = "Video playback was blocked. Press Play to retry.";
        }).finally(() => { mediaWantsPlay = false; });
      }
    } else video.pause();
    if (mediaAvailable) $("videoStatus").textContent = insideMedia()
      ? `Synchronized · video ${fmt(mapped, true)} = match time ${match.media.offset_s >= 0 ? "+" : "−"} ${Math.abs(match.media.offset_s || 0).toFixed(3)}s`
      : "Current match time is outside the mapped video range. The match clock remains available.";
  }
  function setTime(value, seek = true) {
    const requested = Number(value);
    if (!Number.isFinite(requested)) return;
    t = Math.max(0, Math.min(match.duration_s, requested));
    lastTick = performance.now();
    if (seek) syncVideo(true);
    ensureWindowContains(t);
    if (t >= match.duration_s) setPlaying(false);
    renderCurrent();
  }
  function setPlaying(value) {
    playing = value;
    lastTick = performance.now();
    $("play").textContent = playing ? "Ⅱ Pause" : "▶ Play";
    $("play").setAttribute("aria-label", playing ? "Pause synchronized sequence" : "Play synchronized sequence");
    if (!playing) video.pause();
    else syncVideo(true);
  }
  function togglePlay() {
    if (t >= match.duration_s) setTime(0);
    setPlaying(!playing);
  }
  function tick(now) {
    if (playing && match) {
      const elapsed = Math.min(0.25, (now - lastTick) / 1000);
      lastTick = now;
      if (insideMedia() && !video.paused) t = Math.max(0, Math.min(match.duration_s, video.currentTime - (match.media.offset_s || 0)));
      else if (!insideMedia()) t = Math.min(match.duration_s, t + elapsed * Number($("speed").value));
      syncVideo();
      ensureWindowContains(t);
      renderCurrent();
      if (t >= match.duration_s) setPlaying(false);
    }
    requestAnimationFrame(tick);
  }
  function renderPitch(sample) {
    const canvas = $("pitch"), ctx = canvas.getContext("2d");
    const w = canvas.width, h = canvas.height, pad = 38;
    const pw = w - pad * 2, ph = h - pad * 2;
    const canvasCssWidth = canvas.getBoundingClientRect().width;
    const displayScale = canvasCssWidth > 0 ? canvasCssWidth / w : 1;
    const screenPx = value => value / displayScale;
    const pitch = match.pitch;
    const x = value => pad + value / pitch.length_m * pw;
    const y = value => pad + (1 - value / pitch.width_m) * ph;
    ctx.fillStyle = "#f0f3e9"; ctx.fillRect(0, 0, w, h);
    for (let stripe = 0; stripe < 10; stripe++) {
      ctx.fillStyle = stripe % 2 ? "#e7eee2" : "#edf2e7";
      ctx.fillRect(pad + pw * stripe / 10, pad, pw / 10, ph);
    }
    ctx.strokeStyle = "#a4b3a1"; ctx.lineWidth = 2;
    ctx.strokeRect(pad, pad, pw, ph);
    ctx.beginPath(); ctx.moveTo(w / 2, pad); ctx.lineTo(w / 2, h - pad); ctx.stroke();
    ctx.beginPath(); ctx.ellipse(w / 2, h / 2, 9.15 / pitch.length_m * pw, 9.15 / pitch.width_m * ph, 0, 0, Math.PI * 2); ctx.stroke();
    for (const side of [0, 1]) {
      const boxW = 16.5 / pitch.length_m * pw, smallW = 5.5 / pitch.length_m * pw;
      ctx.strokeRect(side ? w - pad - boxW : pad, y(pitch.width_m / 2 + 20.16), boxW, 40.32 / pitch.width_m * ph);
      ctx.strokeRect(side ? w - pad - smallW : pad, y(pitch.width_m / 2 + 9.16), smallW, 18.32 / pitch.width_m * ph);
      ctx.strokeRect(side ? w - pad : pad - 8, y(pitch.width_m / 2 + 3.66), 8, 7.32 / pitch.width_m * ph);
    }
    ctx.fillStyle = "#637169"; ctx.font = `${screenPx(10)}px system-ui`;
    ctx.fillText(`0,0`, pad, h - 13);
    ctx.textAlign = "right"; ctx.fillText(`${pitch.length_m} × ${pitch.width_m} m`, w - pad, h - 13); ctx.textAlign = "left";
    if (!sample) {
      ctx.fillStyle = "#536258"; ctx.textAlign = "center"; ctx.font = `${screenPx(18)}px system-ui`;
      ctx.fillText("No tracking sample at this time", w / 2, h / 2 + 50); ctx.textAlign = "left";
      return;
    }
    ctx.save(); ctx.beginPath(); ctx.rect(pad - 12, pad - 12, pw + 24, ph + 24); ctx.clip();
    for (const player of sample.players || []) {
      const px = x(player.x), py = y(player.y);
      ctx.beginPath(); ctx.arc(px, py, screenPx(5.5), 0, Math.PI * 2);
      ctx.fillStyle = colors[player.team]; ctx.fill();
      ctx.strokeStyle = "#fff"; ctx.lineWidth = screenPx(1.5); ctx.stroke();
      if (canvasCssWidth >= 480) {
        ctx.fillStyle = "#fff"; ctx.font = `bold ${screenPx(8)}px system-ui`; ctx.textAlign = "center";
        const id = String(player.id || "").replace(/^[HA]/, "");
        ctx.fillText(id.slice(-3), px, py + screenPx(2.5));
      }
    }
    if (sample.ball) {
      ctx.beginPath(); ctx.arc(x(sample.ball[0]), y(sample.ball[1]), screenPx(5.5), 0, Math.PI * 2);
      ctx.fillStyle = "#fff"; ctx.fill(); ctx.strokeStyle = "#293c2c"; ctx.lineWidth = screenPx(2); ctx.stroke();
      ctx.fillStyle = "#293c2c"; ctx.font = `${screenPx(9)}px system-ui`; ctx.textAlign = "left";
      if (sample.ball.length > 2) ctx.fillText(`z ${sample.ball[2].toFixed(1)}m`, x(sample.ball[0]) + screenPx(7), y(sample.ball[1]) - screenPx(6));
    }
    ctx.restore(); ctx.textAlign = "left";
  }
  function qualityCell(label, value, kind) {
    const cell = element("div", undefined, `quality-cell ${kind || ""}`);
    cell.append(element("span", label), element("strong", value));
    return cell;
  }
  function renderCurrent() {
    const sample = currentSample(), quality = sample?.quality || {};
    $("clock").textContent = fmt(t, true);
    const rate = fps(), frame = frameAt(rate);
    $("frameClock").textContent = frame === null ? "Frame rate not supplied" : `Frame ${frame.toLocaleString()} · ${rate} fps`;
    for (const id of ["backFrame", "forwardFrame", "frameSeek", "goFrame"]) $(id).disabled = rate === null;
    if (rate) $("frameSeek").max = lastFrame(rate);
    $("scrubber").value = t;
    $("scrubber").setAttribute("aria-valuetext", fmt(t, true));
    const windowSpan = Math.max(1e-9, viewEnd - viewStart);
    const playheadPosition = Math.max(0, Math.min(100, (t - viewStart) / windowSpan * 100));
    document.querySelectorAll(".playhead").forEach(head => { head.style.left = `${playheadPosition}%`; });
    $("sampleTime").textContent = sample ? `Sample ${fmt(sample.t, true)}` : "No sample";
    $("positionStatus").textContent = sample ? `${sample.players?.length || 0} player observations` : "No positions supplied";
    const homeCount = sample?.players?.filter(player => player.team === "H").length || 0;
    const awayCount = sample?.players?.filter(player => player.team === "A").length || 0;
    $("pitch").setAttribute("aria-label", sample
      ? `Pitch tracking at ${fmt(t, true)}: ${homeCount} home and ${awayCount} away player positions; ball ${sample.ball ? "position supplied" : "position unavailable"}.`
      : `Pitch at ${fmt(t, true)}: no tracking sample or positions supplied.`);
    renderPitch(sample);
    const observed = quality.ball_observed;
    $("quality").replaceChildren(
      qualityCell("Ball observed", observed === undefined ? "Not supplied" : observed ? "Yes" : "Missing", observed ? "good" : "missing"),
      qualityCell("Player coverage", quality.player_coverage === undefined ? "Not supplied" : `${Math.round(quality.player_coverage * 100)}%`, quality.player_coverage >= 0.9 ? "good" : "missing"));
    const age = sample ? t - sample.t : null;
    $("sampleWarning").textContent = sample
      ? `Latest sample is ${age.toFixed(2)}s old. Positions are not interpolated.${sample.ball === null ? " Ball position unavailable; no synthetic marker is drawn." : ""}`
      : "No observation precedes this timestamp. The pitch remains empty.";
    $("stateSummary").replaceChildren();
    const states = [];
    if ($("showTruth").checked && match.truth?.length) states.push(["Reference", stateAt(match.truth, t)]);
    for (const key of Object.keys(match.predictions || {})) {
      if (key === version || $("compare").checked) states.push([key, stateAt(match.predictions[key].spells, t)]);
    }
    for (const [name, state] of states) {
      const span = element("span", `${name} `); span.append(element("b", state || "∅"));
      span.title = state ? stateNames[state] : "No interval supplied";
      $("stateSummary").append(span);
    }
    if (!states.length) $("stateSummary").append(element("span", "No reference labels or predictions supplied.", "muted"));
    const series = (match.evidence_series || []).find(item => item.key === $("evidenceSelect").value);
    const value = sample?.evidence?.[series?.key];
    $("evidenceValue").textContent = value == null ? "—" : value.toFixed(2);
    $("evidenceUnit").textContent = series ? series.unit : "No evidence supplied";
    renderEvidenceCursor();
    document.querySelectorAll("#eventRows tr[data-start]").forEach(row => {
      const start = Number(row.dataset.start), end = Number(row.dataset.end);
      row.classList.toggle("event-active", t >= start && t < Math.max(start + 0.25, end));
    });
  }
  function renderTimelines() {
    $("timelines").replaceChildren();
    updateViewLabels();
    const rows = [];
    if ($("showTruth").checked && match.truth?.length) rows.push(["Reference", match.truth]);
    for (const key of Object.keys(match.predictions || {})) {
      if (key === version || $("compare").checked) rows.push([key, match.predictions[key].spells]);
    }
    for (const [name, spells] of rows) {
      const row = element("div", undefined, "timeline-row");
      row.append(element("span", name === version ? `${name} •` : name, "timeline-label"));
      const track = element("div", undefined, "timeline-track");
      track.setAttribute("role", "group");
      track.setAttribute("aria-label", `${name} state timeline from ${fmt(viewStart, true)} to ${fmt(viewEnd, true)}`);
      row.append(track);
      $("timelines").append(row);
      const span = Math.max(1e-9, viewEnd - viewStart);
      let visibleCount = 0;
      for (const spell of spells) {
        const clippedStart = Math.max(spell.start_s, viewStart), clippedEnd = Math.min(spell.end_s, viewEnd);
        if (clippedEnd <= clippedStart) continue;
        visibleCount++;
        const left = (clippedStart - viewStart) / span * 100, width = (clippedEnd - clippedStart) / span * 100;
        const visiblePixels = width / 100 * track.clientWidth;
        const button = element("button", visiblePixels >= 24 ? spell.state : "", `spell ${{H:"home", A:"away", D:"dead", X:"unknown"}[spell.state]}`);
        button.style.left = `${left}%`;
        button.style.width = `${width}%`;
        button.title = `${name}: ${stateNames[spell.state]} · ${fmt(spell.start_s, true)}–${fmt(spell.end_s, true)}`;
        button.setAttribute("aria-label", `Jump to ${button.title}`);
        button.addEventListener("click", () => setTime(spell.start_s));
        track.append(button);
      }
      if (!visibleCount) track.append(element("span", "No intervals in this window", "timeline-empty"));
      track.append(element("div", undefined, "playhead"));
    }
    if (!rows.length) {
      const empty = element("p", "No reference labels or predictions supplied for this item.", "timeline-empty-state");
      $("timelines").append(empty);
    }
  }
  function prepareEvidenceChart() {
    const canvas = $("evidenceChart"), offscreen = document.createElement("canvas");
    offscreen.width = canvas.width; offscreen.height = canvas.height;
    const ctx = offscreen.getContext("2d"), w = canvas.width, h = canvas.height;
    const series = (match.evidence_series || []).find(item => item.key === $("evidenceSelect").value);
    $("evidenceDescription").textContent = series ? `${series.description} Gaps indicate missing values. Visible match time ${fmt(viewStart, true)}–${fmt(viewEnd, true)} on x-axis.` : "No measured evidence series supplied. This view does not infer confidence from labels.";
    ctx.fillStyle = "#fff"; ctx.fillRect(0, 0, w, h);
    const samples = match.samples || [], values = samples.map(sample => sample.evidence?.[series?.key]).filter(value => value != null);
    if (!values.length) {
      ctx.fillStyle = "#7b8781"; ctx.font = "17px system-ui"; ctx.fillText("No measured values available", 55, 110);
      ctx.font = "13px ui-monospace,monospace"; ctx.textAlign = "left"; ctx.fillText(fmt(viewStart), 55, h - 7);
      ctx.textAlign = "center"; ctx.fillText(fmt((viewStart + viewEnd) / 2), w / 2 + 19, h - 7);
      ctx.textAlign = "right"; ctx.fillText(fmt(viewEnd), w - 17, h - 7); ctx.textAlign = "left";
      chartBackground = offscreen; return;
    }
    let min = Infinity, max = -Infinity;
    for (const value of values) { min = Math.min(min, value); max = Math.max(max, value); }
    if (max === min) { min -= 1; max += 1; }
    const margin = (max - min) * 0.1; min -= margin; max += margin;
    const left = 55, right = w - 17, top = 20, bottom = h - 30;
    const span = Math.max(1e-9, viewEnd - viewStart);
    const x = time => left + (time - viewStart) / span * (right - left);
    const y = value => bottom - (value - min) / (max - min) * (bottom - top);
    ctx.font = "13px ui-monospace,monospace";
    for (let i = 0; i < 3; i++) {
      const value = min + (max - min) * i / 2, yy = y(value);
      ctx.strokeStyle = "#e6ebe7"; ctx.beginPath(); ctx.moveTo(left, yy); ctx.lineTo(right, yy); ctx.stroke();
      ctx.fillStyle = "#7b8781"; ctx.fillText(value.toFixed(1), 2, yy + 4);
    }
    const middle = (viewStart + viewEnd) / 2;
    ctx.strokeStyle = "#eef1ef"; ctx.beginPath();
    for (const time of [viewStart, middle, viewEnd]) { const xx = x(time); ctx.moveTo(xx, top); ctx.lineTo(xx, bottom); }
    ctx.stroke();
    ctx.fillStyle = "#7b8781"; ctx.textAlign = "left"; ctx.fillText(fmt(viewStart), left, h - 7);
    ctx.textAlign = "center"; ctx.fillText(fmt(middle), (left + right) / 2, h - 7);
    ctx.textAlign = "right"; ctx.fillText(fmt(viewEnd), right, h - 7); ctx.textAlign = "left";
    ctx.strokeStyle = "#226a60"; ctx.lineWidth = 2; ctx.beginPath();
    let open = false;
    ctx.save(); ctx.beginPath(); ctx.rect(left, top, right - left, bottom - top); ctx.clip();
    for (const sample of samples) {
      const value = sample.evidence?.[series?.key];
      if (value == null) { open = false; continue; }
      if (open) ctx.lineTo(x(sample.t), y(value)); else ctx.moveTo(x(sample.t), y(value));
      open = true;
    }
    ctx.stroke(); ctx.restore(); chartBackground = offscreen;
  }
  function renderEvidenceCursor() {
    if (!chartBackground) return;
    const canvas = $("evidenceChart"), ctx = canvas.getContext("2d");
    ctx.drawImage(chartBackground, 0, 0);
    const span = Math.max(1e-9, viewEnd - viewStart);
    const x = 55 + (t - viewStart) / span * (canvas.width - 72);
    ctx.strokeStyle = "#253b31"; ctx.lineWidth = 2; ctx.setLineDash([4, 4]);
    ctx.beginPath(); ctx.moveTo(x, 12); ctx.lineTo(x, canvas.height - 27); ctx.stroke(); ctx.setLineDash([]);
  }
  function deriveEvents() {
    events = [];
    const truth = match.truth || [], pred = selectedSpells();
    const edges = [...new Set([...truth, ...pred].flatMap(row => [row.start_s, row.end_s]))].sort((a,b) => a-b);
    let lastError = null;
    for (let i = 0; i < edges.length - 1; i++) {
      const start = edges[i], end = edges[i+1], mid = (start + end) / 2;
      const reference = stateAt(truth, mid), prediction = stateAt(pred, mid);
      if (reference && reference !== "X" && reference !== prediction) {
        if (lastError && lastError.end === start && lastError.reference === reference && lastError.prediction === prediction) lastError.end = end;
        else { lastError = {start, end, kind:"errors", label:"Label disagreement", reference, prediction}; events.push(lastError); }
      } else lastError = null;
    }
    const transitions = rows => rows.slice(1).flatMap((row, i) => rows[i].end_s === row.start_s && rows[i].state !== row.state ? [{t:row.start_s, from:rows[i].state, to:row.state}] : []);
    const predictedTransitions = transitions(pred);
    for (const boundary of transitions(truth)) {
      let nearest = null;
      for (const candidate of predictedTransitions) {
        if (candidate.from === boundary.from && candidate.to === boundary.to && (!nearest || Math.abs(candidate.t - boundary.t) < Math.abs(nearest.t - boundary.t))) nearest = candidate;
      }
      events.push({start:boundary.t, end:boundary.t, kind:"boundaries", label:`Boundary ${boundary.from} → ${boundary.to}`,
        reference:boundary.to, prediction:stateAt(pred, boundary.t), delta:nearest ? nearest.t - boundary.t : null});
    }
    const samples = match.samples || [];
    let missing = null;
    for (let i = 0; i < samples.length; i++) {
      const sample = samples[i], end = samples[i+1]?.t ?? match.duration_s;
      if (sample.quality?.ball_observed === false) {
        if (missing) missing.end = end;
        else { missing = {start:sample.t, end, kind:"missing", label:"Ball not observed", reference:stateAt(truth,sample.t), prediction:stateAt(pred,sample.t)}; events.push(missing); }
      } else missing = null;
    }
    events.sort((a,b) => a.start - b.start || a.kind.localeCompare(b.kind));
    renderEvents();
  }
  function renderEvents() {
    const filter = $("eventFilter").value, state = $("stateFilter").value;
    visibleEvents = events.filter(event => (filter === "all" || event.kind === filter) && (state === "all" || event.reference === state || event.prediction === state));
    const rows = $("eventRows"); rows.replaceChildren();
    const limit = 300;
    $("eventStatus").textContent = `${visibleEvents.length} events${visibleEvents.length > limit ? ` · displaying first ${limit}; jump buttons visit all filtered events` : ""}${!(match.truth || []).length ? " · no reference labels supplied; error inspection unavailable" : ""}.`;
    for (const event of visibleEvents.slice(0,limit)) {
      const row = element("tr"); row.dataset.start = event.start; row.dataset.end = event.end;
      row.append(element("td", event.end > event.start ? `${fmt(event.start,true)}–${fmt(event.end,true)}` : fmt(event.start,true)),
        element("td", event.label), element("td", event.reference || "∅"), element("td", event.prediction || "∅"),
        element("td", event.kind !== "boundaries" ? "—" : event.delta == null ? "No same-transition match" : `${event.delta >= 0 ? "+" : ""}${event.delta.toFixed(3)}s`));
      const action = element("td"), button = element("button", "Jump ↗");
      button.setAttribute("aria-label", `Jump to ${event.label} at ${fmt(event.start,true)}`);
      button.addEventListener("click", () => setTime(event.start)); action.append(button); row.append(action); rows.append(row);
    }
    if (!visibleEvents.length) {
      const row = element("tr"), cell = element("td", "No inspection events match these filters.", "muted"); cell.colSpan = 6; row.append(cell); rows.append(row);
    }
    $("previousEvent").disabled = $("nextEvent").disabled = !visibleEvents.length;
  }
  function jumpEvent(direction) {
    const epsilon = 0.02;
    let event = direction > 0 ? visibleEvents.find(item => item.start > t + epsilon) : [...visibleEvents].reverse().find(item => item.start < t - epsilon);
    if (!event) event = direction > 0 ? visibleEvents[0] : visibleEvents[visibleEvents.length - 1];
    if (event) setTime(event.start);
  }
  function renderBenchmarks() {
    $("benchmarkRows").replaceChildren();
    const matches = $("allMatches").checked ? bundle.matches : [match];
    const seen = new Set();
    for (const item of matches) for (const benchmark of item.benchmarks || []) {
      const identity = item.provenance?.match || item.id;
      const key = JSON.stringify([identity, benchmark]);
      if (seen.has(key)) continue;
      seen.add(key);
      const row = element("tr"); row.append(element("td", item.provenance?.match || item.title), element("td", benchmark.version));
      const source = element("td");
      source.append(element("span", {official:"Official evaluator",synthetic_demo:"Demo · no accuracy claim",proxy:"Proxy / diagnostic"}[benchmark.metric_source], `tag ${benchmark.metric_source === "synthetic_demo" ? "demo" : benchmark.metric_source === "proxy" ? "proxy" : ""}`)); row.append(source);
      for (const metric of ["spellF1","macroF1"]) row.append(element("td", benchmark[metric] == null ? "—" : benchmark[metric].toFixed(4), "metric"));
      row.append(element("td", benchmark.runtime_s == null ? "—" : `${benchmark.runtime_s.toFixed(3)}s`, "metric"));
      const p = benchmark.provenance, provenance = element("td", p.model_version, "provenance-cell");
      provenance.append(element("small", `Split: ${p.split}`), element("small", `Evaluator: ${p.evaluator}`));
      for (const [key, value] of Object.entries(p)) if (!["model_version","split","evaluator"].includes(key)) {
        if (value && typeof value === "object") {
          const detail = element("details"), heading = element("summary", key.replaceAll("_", " "));
          detail.append(heading, element("pre", JSON.stringify(value, null, 2)));
          provenance.append(detail);
        } else provenance.append(element("small", `${key}: ${text(value)}`));
      }
      row.append(provenance); $("benchmarkRows").append(row);
    }
    if (!$("benchmarkRows").children.length) {
      const row = element("tr"), cell = element("td", "No benchmark results supplied. Missing scores remain blank.", "muted"); cell.colSpan = 7; row.append(cell); $("benchmarkRows").append(row);
    }
  }
  function setVersion() {
    version = $("versionSelect").value;
    renderTimelines(); deriveEvents(); renderProvenance(); renderCurrent();
  }
  function renderProvenance() {
    $("provenance").textContent = JSON.stringify({schema_version:bundle.schema_version, dataset:bundle.dataset,
      match:{id:match.id, provenance:match.provenance || "Not supplied", media:match.media || null},
      selected_prediction:{version, provenance:match.predictions?.[version]?.provenance || null}}, null, 2);
  }
  function selectMatch() {
    setPlaying(false);
    match = bundle.matches.find(item => item.id === $("matchSelect").value);
    $("showTruth").disabled = !match.truth?.length;
    $("showTruth").title = match.truth?.length ? "Display the supplied reference labels" : "No reference labels supplied for this item";
    t = 0; mediaAvailable = false; mediaFailed = false;
    video.pause(); video.removeAttribute("src"); video.load();
    $("noVideo").hidden = false;
    $("noVideoTitle").textContent = match.media ? "Loading video…" : "No video available";
    $("noVideoMessage").textContent = "Video is optional. Pitch, predictions and evidence share the replay clock.";
    $("mediaMapping").textContent = match.media ? `Offset ${(match.media.offset_s || 0).toFixed(3)}s${match.media.fps ? ` · ${match.media.fps} fps` : ""}` : "Optional local file";
    $("videoStatus").textContent = match.media ? "Loading synchronized video…" : "Video is optional.";
    if (match.media) video.src = `/media/${encodeURIComponent(match.media.id)}`;
    $("scrubber").max = match.duration_s;
    $("duration").textContent = `/ ${fmt(match.duration_s,true)}`;
    viewStart = 0; viewEnd = viewDuration();
    $("split").textContent = `Split: ${text(typeof match.provenance?.split === "string" ? match.provenance.split : bundle.dataset.split)}`;
    $("versionSelect").replaceChildren();
    for (const key of Object.keys(match.predictions || {})) option($("versionSelect"), key, key);
    if (!$("versionSelect").options.length) option($("versionSelect"), "", "No predictions supplied");
    if ([...$("versionSelect").options].some(item => item.value === version)) $("versionSelect").value = version;
    else if (match.predictions?.v2) $("versionSelect").value = "v2";
    $("evidenceSelect").replaceChildren();
    for (const series of match.evidence_series || []) option($("evidenceSelect"), series.key, series.label);
    if (!$("evidenceSelect").options.length) option($("evidenceSelect"), "", "No evidence supplied");
    prepareEvidenceChart(); setVersion(); renderBenchmarks();
  }
  video.addEventListener("loadedmetadata", () => {
    mediaAvailable = true; $("noVideo").hidden = true;
    video.playbackRate = Number($("speed").value); syncVideo(true);
  });
  video.addEventListener("error", () => {
    if (!match?.media) return;
    mediaFailed = true; mediaAvailable = false;
    $("noVideo").hidden = false;
    $("noVideoTitle").textContent = "Video unavailable";
    $("noVideoMessage").textContent = "This video could not be played. Pitch, predictions and evidence remain available.";
    $("videoStatus").textContent = "Video could not be played. The replay clock and analysis remain available.";
  });
  video.addEventListener("ended", () => {
    if (match?.media && Number.isFinite(video.duration)) {
      t = Math.min(match.duration_s, video.duration - (match.media.offset_s || 0));
      ensureWindowContains(t);
      renderCurrent();
    }
  });
  $("play").addEventListener("click", togglePlay);
  $("back").addEventListener("click", () => setTime(t - 1));
  $("forward").addEventListener("click", () => setTime(t + 1));
  $("backFrame").addEventListener("click", () => stepFrame(-1));
  $("forwardFrame").addEventListener("click", () => stepFrame(1));
  $("goFrame").addEventListener("click", () => {
    const frame = Number($("frameSeek").value), rate = fps();
    if (rate && Number.isInteger(frame) && frame >= 0 && frame <= Number($("frameSeek").max)) setTime(frame / rate);
  });
  $("scrubber").addEventListener("input", event => setTime(event.target.value));
  $("speed").addEventListener("change", () => { video.playbackRate = Number($("speed").value); });
  $("zoomSelect").addEventListener("change", () => { setWindowAround(t); renderCurrent(); });
  $("centerCursor").addEventListener("click", () => { setWindowAround(t); renderCurrent(); });
  $("versionSelect").addEventListener("change", setVersion);
  $("matchSelect").addEventListener("change", selectMatch);
  $("compare").addEventListener("change", () => { renderTimelines(); renderCurrent(); });
  $("showTruth").addEventListener("change", () => { renderTimelines(); renderCurrent(); });
  $("evidenceSelect").addEventListener("change", () => { prepareEvidenceChart(); renderCurrent(); });
  $("eventFilter").addEventListener("change", () => { renderEvents(); renderCurrent(); });
  $("stateFilter").addEventListener("change", () => { renderEvents(); renderCurrent(); });
  $("allMatches").addEventListener("change", renderBenchmarks);
  $("previousEvent").addEventListener("click", () => jumpEvent(-1));
  $("nextEvent").addEventListener("click", () => jumpEvent(1));
  $("evidenceChart").addEventListener("click", event => {
    const canvas = $("evidenceChart"), rect = canvas.getBoundingClientRect(), style = getComputedStyle(canvas);
    const paddingLeft = parseFloat(style.paddingLeft) || 0, paddingRight = parseFloat(style.paddingRight) || 0;
    const contentWidth = rect.width - paddingLeft - paddingRight;
    if (contentWidth <= 0) return;
    const coordinate = (event.clientX - rect.left - paddingLeft) / contentWidth * canvas.width;
    const left = 55, right = canvas.width - 17;
    const fraction = Math.max(0, Math.min(1, (coordinate - left) / (right - left)));
    setTime(viewStart + fraction * (viewEnd - viewStart));
  });
  document.addEventListener("keydown", event => {
    const active = document.activeElement;
    if (!match || event.altKey || event.ctrlKey || event.metaKey || event.shiftKey || active?.isContentEditable ||
        ["INPUT","SELECT","TEXTAREA","BUTTON","SUMMARY","A"].includes(active?.tagName)) return;
    if (event.code === "Space") {
      event.preventDefault();
      if (event.repeat) return;
      togglePlay();
    }
    if (event.code === "ArrowLeft") { event.preventDefault(); setTime(t - 1); }
    if (event.code === "ArrowRight") { event.preventDefault(); setTime(t + 1); }
  });
  let resizeFrame = 0;
  window.addEventListener("resize", () => {
    if (resizeFrame) return;
    resizeFrame = requestAnimationFrame(() => { resizeFrame = 0; if (match) renderCurrent(); });
  });
  async function loadBundle() {
    $("retryLoad").hidden = true;
    $("retryLoad").disabled = true;
    $("loadingMessage").textContent = "Loading permitted local data…";
    try {
      const response = await fetch("/api/bundle");
      if (!response.ok) throw new Error(`Local data request failed (${response.status})`);
      const data = await response.json();
      if (!data?.dataset || !Array.isArray(data.matches) || !data.matches.length) {
        throw new Error("The local data bundle is missing its dataset or matches");
      }
      bundle = data;
      $("datasetTitle").textContent = data.dataset.title;
      $("datasetProvenance").textContent = text(data.dataset.provenance);
      $("kind").textContent = {synthetic_demo:"Software demo · not accuracy evidence",public_external:"Public external data",private_local:"Private · local only"}[data.dataset.kind] || "Local data";
      $("kind").classList.toggle("demo", data.dataset.kind === "synthetic_demo");
      $("schemaVersion").textContent = data.schema_version;
      $("matchSelect").replaceChildren();
      for (const item of data.matches) option($("matchSelect"), item.id, item.title);
      $("loading").hidden = true; $("application").hidden = false;
      selectMatch(); requestAnimationFrame(tick);
    } catch (error) {
      $("application").hidden = true;
      $("loading").hidden = false;
      $("loadingMessage").textContent = `${error.message}. Check the local server and permitted bundle, then retry.`;
      $("retryLoad").hidden = false;
    } finally {
      $("retryLoad").disabled = false;
    }
  }
  $("retryLoad").addEventListener("click", loadBundle);
  loadBundle();
})();
