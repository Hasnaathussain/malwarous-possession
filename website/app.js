const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];

const els = {
  matchSelect: $("#matchSelect"),
  halfSelect: $("#halfSelect"),
  sequenceTitle: $("#sequenceTitle"),
  dataState: $("#dataState"),
  replayWorkbench: $("#replayWorkbench"),
  pitchCanvas: $("#pitchCanvas"),
  pitchEmpty: $("#pitchEmpty"),
  fieldCaption: $("#fieldCaption"),
  resetView: $("#resetView"),
  numbersToggle: $("#numbersToggle"),
  gridToggle: $("#gridToggle"),
  trailsToggle: $("#trailsToggle"),
  regionsToggle: $("#regionsToggle"),
  homeColor: $("#homeColor"),
  awayColor: $("#awayColor"),
  referenceToggle: $("#referenceToggle"),
  referenceLane: $("#referenceLane"),
  referenceCaption: $("#referenceCaption"),
  referenceReading: $("#referenceReading"),
  referenceState: $("#referenceState"),
  trackV1: $("#trackV1"),
  trackV2: $("#trackV2"),
  trackReference: $("#trackReference"),
  rulerMid: $("#rulerMid"),
  rulerEnd: $("#rulerEnd"),
  stateDisplay: $("#stateDisplay"),
  stateLetter: $("#stateLetter"),
  stateWord: $("#stateWord"),
  stateContext: $("#stateContext"),
  v1State: $("#v1State"),
  v2State: $("#v2State"),
  observationAge: $("#observationAge"),
  observationStatus: $("#observationStatus"),
  observationDetail: $("#observationDetail"),
  measurementList: $("#measurementList"),
  provenanceText: $("#provenanceText"),
  stepBack: $("#stepBack"),
  playButton: $("#playButton"),
  playText: $("#playText"),
  stepForward: $("#stepForward"),
  speedSelect: $("#speedSelect"),
  previousChange: $("#previousChange"),
  nextChange: $("#nextChange"),
  frameRange: $("#frameRange"),
  elapsedTime: $("#elapsedTime"),
  frameReadout: $("#frameReadout"),
  durationTime: $("#durationTime"),
  frameInput: $("#frameInput"),
  timeInput: $("#timeInput"),
  seekFrameButton: $("#seekFrameButton"),
  seekTimeButton: $("#seekTimeButton"),
  shareButton: $("#shareButton"),
  shareLinkRow: $("#shareLinkRow"),
  shareLink: $("#shareLink"),
  shareStatus: $("#shareStatus"),
  exportButton: $("#exportButton"),
  replayScope: $("#replayScope"),
  videoPanel: $("#videoPanel"),
  syntheticVideo: $("#syntheticVideo"),
  scenarioFilter: $("#scenarioFilter"),
  benchmarkRows: $("#benchmarkRows"),
  benchmarkCount: $("#benchmarkCount"),
  benchmarkInterpretation: $("#benchmarkInterpretation"),
};

const controlIds = [
  "#numbersToggle", "#gridToggle", "#trailsToggle", "#regionsToggle", "#homeColor", "#awayColor",
  "#referenceToggle", "#resetView", "#stepBack", "#playButton", "#stepForward", "#speedSelect",
  "#previousChange", "#nextChange", "#frameRange", "#frameInput", "#timeInput", "#seekFrameButton",
  "#seekTimeButton", "#shareButton", "#exportButton",
];

const stateNames = { H: "Home", A: "Away", D: "Dead ball", X: "Unlabelled" };
const defaults = { home: "#d6e79d", away: "#ee946d", numbers: true, grid: false, trails: false, regions: false, reference: false };
const pitchCtx = els.pitchCanvas.getContext("2d", { alpha: false });

let indexData = null;
let sequences = [];
let sequenceById = new Map();
let currentMeta = null;
let currentData = null;
let currentFrame = 0;
let currentSampleIndex = 0;
let playbackPosition = 0;
let playbackRaf = 0;
let playing = false;
let previousTick = 0;
let lastAnnouncedState = "";
let resizeObserver = null;
let benchmarkData = null;
let labMounted = false;
let loadSequenceToken = 0;
let lastMeasuredSampleIndex = -1;
let measurementRows = new Map();

function setTone(message, tone = "") {
  els.dataState.textContent = message;
  if (tone) els.dataState.dataset.tone = tone;
  else delete els.dataState.dataset.tone;
}

function setReplayControls(enabled) {
  for (const selector of controlIds) {
    const element = $(selector);
    if (element) element.disabled = !enabled;
  }
  els.matchSelect.disabled = !indexData;
  els.halfSelect.disabled = !indexData || !els.halfSelect.options.length;
}

function safeNum(value, fallback = 0) {
  if (value === null || value === undefined || value === "") return fallback;
  const n = Number(value);
  return Number.isFinite(n) ? n : fallback;
}

function formatTime(seconds, digits = 1) {
  if (!Number.isFinite(seconds) || seconds < 0) return "—";
  const scale = 10 ** digits;
  const rounded = Math.round(seconds * scale) / scale;
  const mins = Math.floor(rounded / 60);
  const secs = rounded - mins * 60;
  return `${mins}:${secs.toFixed(digits).padStart(digits ? 4 : 2, "0")}`;
}

function formatFrameTime(frame, fps = currentData?.fps || 1) {
  return formatTime(frame / fps, 1);
}

function parseTime(value) {
  const raw = String(value).trim();
  if (!raw) return null;
  if (raw.includes(":")) {
    const parts = raw.split(":");
    if (parts.length !== 2 || parts.some((part) => !part.trim())) return null;
    const mins = Number(parts[0]);
    const secs = Number(parts[1]);
    if (!Number.isFinite(mins) || !Number.isFinite(secs) || mins < 0 || secs < 0 || secs >= 60) return null;
    return mins * 60 + secs;
  }
  const seconds = Number(raw);
  return Number.isFinite(seconds) && seconds >= 0 ? seconds : null;
}

function sequenceLabel(sequence) {
  if (sequence.kind === "synthetic_demo") return "Synthetic demo · software fixture";
  const half = sequence.half === 1 ? "1st half" : sequence.half === 2 ? "2nd half" : `Half ${sequence.half}`;
  return `${sequence.match_id} · ${half}`;
}

function populateMatches(preferredId) {
  const groups = new Map();
  for (const sequence of sequences) {
    if (!groups.has(sequence.match_id)) groups.set(sequence.match_id, []);
    groups.get(sequence.match_id).push(sequence);
  }

  els.matchSelect.replaceChildren();
  const fragment = document.createDocumentFragment();
  for (const [matchId, entries] of groups) {
    const option = document.createElement("option");
    option.value = matchId;
    option.textContent = entries.some((entry) => entry.kind === "synthetic_demo") ? "Synthetic demo" : matchId;
    fragment.append(option);
  }
  els.matchSelect.append(fragment);
  els.matchSelect.disabled = false;

  const initial = sequenceById.get(preferredId) || sequenceById.get(indexData.default_sequence) || sequences[0];
  if (!initial) return;
  els.matchSelect.value = initial.match_id;
  populateHalves(initial.match_id, initial.id);
}

function populateHalves(matchId, preferredId) {
  const entries = sequences.filter((sequence) => sequence.match_id === matchId);
  els.halfSelect.replaceChildren();
  for (const sequence of entries) {
    const option = document.createElement("option");
    option.value = sequence.id;
    option.textContent = sequence.kind === "synthetic_demo"
      ? "Demo fixture"
      : sequence.half === 1 ? "First half" : sequence.half === 2 ? "Second half" : `Half ${sequence.half}`;
    els.halfSelect.append(option);
  }
  els.halfSelect.disabled = !entries.length;
  const selected = entries.find((entry) => entry.id === preferredId) || entries[0];
  if (selected) els.halfSelect.value = selected.id;
}

function getSequenceFromControls() {
  return sequenceById.get(els.halfSelect.value) || null;
}

function binarySampleIndex(frame) {
  const samples = currentData?.samples || [];
  if (!samples.length) return 0;
  let low = 0;
  let high = samples.length;
  while (low < high) {
    const mid = (low + high) >> 1;
    if (safeNum(samples[mid].f) <= frame) low = mid + 1;
    else high = mid;
  }
  return Math.max(0, low - 1);
}

function intervalState(intervals, frame) {
  if (!Array.isArray(intervals) || !intervals.length) return "X";
  let low = 0;
  let high = intervals.length;
  while (low < high) {
    const mid = (low + high) >> 1;
    if (safeNum(intervals[mid]?.[0]) <= frame) low = mid + 1;
    else high = mid;
  }
  const interval = intervals[Math.max(0, low - 1)];
  if (!interval) return "X";
  return frame >= safeNum(interval[0]) && frame < safeNum(interval[1]) ? normalizeState(interval[2]) : "X";
}

function normalizeState(value) {
  const code = String(value ?? "X").toUpperCase();
  return ["H", "A", "D", "X"].includes(code) ? code : "X";
}

function stateAt(version, frame) {
  return intervalState(currentData?.predictions?.[version], frame);
}

function hasBall(sample) {
  if (!sample?.b || sample.b.length < 2) return false;
  if (sample.q && sample.q.ball_observed === false) return false;
  return typeof sample.b[0] === "number" && Number.isFinite(sample.b[0]) && typeof sample.b[1] === "number" && Number.isFinite(sample.b[1]);
}

function stateLabel(code) {
  return `${code} · ${stateNames[code] || "Unlabelled"}`;
}

function updateStateReadout() {
  const v1 = stateAt("v1", currentFrame);
  const v2 = stateAt("v2", currentFrame);
  const ref = intervalState(currentData?.truth, currentFrame);
  els.v1State.textContent = stateLabel(v1);
  els.v2State.textContent = stateLabel(v2);
  els.referenceState.textContent = stateLabel(ref);
  els.stateDisplay.dataset.state = v2;
  els.stateLetter.textContent = v2;
  els.stateWord.textContent = stateNames[v2] || "Unlabelled";
  const live = currentData?.samples?.[currentSampleIndex];
  const sampleAge = live ? Math.max(0, (currentFrame - safeNum(live.f)) / safeNum(currentData.fps, 1)) : null;
  els.stateContext.textContent = currentData
    ? `${formatFrameTime(currentFrame)} · frame ${currentFrame.toLocaleString()} · ${sampleAge === null ? "no sample" : `sample ${sampleAge.toFixed(2)}s old`}`
    : "No replay loaded.";
  const announcement = `${v2} ${stateNames[v2] || "Unlabelled"}`;
  if (announcement !== lastAnnouncedState) lastAnnouncedState = announcement;
}

function updateObservationReadout() {
  const sample = currentData?.samples?.[currentSampleIndex];
  if (!sample) {
    els.observationAge.textContent = "—";
    els.observationStatus.textContent = "awaiting replay";
    els.observationDetail.textContent = "Ball and player coordinates are read from the nearest preceding published sample.";
    updateMeasurementValue("ball", "—");
    updateMeasurementValue("coverage", "—");
    return;
  }
  const fps = safeNum(currentData.fps, 1);
  const age = Math.max(0, (currentFrame - safeNum(sample.f)) / fps);
  const ballPresent = hasBall(sample);
  const q = sample.q || {};
  const e = sample.e || {};
  els.observationAge.textContent = `${age.toFixed(2)}s`;
  els.observationStatus.textContent = ballPresent ? "sample support age" : "ball absent at sample";
  els.observationDetail.textContent = `Latest sample at frame ${safeNum(sample.f).toLocaleString()} (${formatFrameTime(safeNum(sample.f), fps)}); positions are held from that observation.`;
  if (lastMeasuredSampleIndex !== currentSampleIndex) {
    const coverage = q.player_coverage;
    const coverageText = typeof coverage === "number" && Number.isFinite(coverage)
      ? `${(coverage <= 1 ? coverage * 100 : coverage).toFixed(0)}%`
      : "—";
    const ballText = ballPresent ? "Observed" : q.ball_observed === false || sample.b === null ? "Not observed" : "Unavailable";
    updateMeasurementValue("ball", ballText);
    updateMeasurementValue("coverage", coverageText);
    for (const definition of Array.isArray(currentData.evidence_series) ? currentData.evidence_series : []) {
      const key = definition?.key;
      if (!key) continue;
      updateMeasurementValue(key, formatEvidenceValue(e[key], definition.unit || ""));
    }
    lastMeasuredSampleIndex = currentSampleIndex;
  }
}

function formatEvidenceValue(value, unit = "") {
  if (value === null || value === undefined || value === "") return "—";
  if (typeof value === "number") {
    if (!Number.isFinite(value)) return "—";
    const formatted = new Intl.NumberFormat(undefined, { maximumFractionDigits: 3 }).format(value);
    return unit ? `${formatted} ${unit}` : formatted;
  }
  if (typeof value === "boolean") return value ? "Yes" : "No";
  if (Array.isArray(value)) return value.map((item) => String(item)).join(", ");
  return unit ? `${String(value)} ${unit}` : String(value);
}

function createMeasurementRow(label, description = "", evidenceKey = "") {
  const row = document.createElement("div");
  if (evidenceKey) row.dataset.evidenceKey = evidenceKey;
  if (description) row.title = description;
  const term = document.createElement("dt");
  term.textContent = label;
  if (description) term.title = description;
  const detail = document.createElement("dd");
  detail.textContent = "—";
  if (description) detail.title = description;
  row.append(term, detail);
  return { row, detail };
}

function prepareMeasurementRows() {
  measurementRows = new Map();
  const fragment = document.createDocumentFragment();
  const basics = [
    ["ball", "Ball observed", "Published observation flag."],
    ["coverage", "Player coverage", "Published player coverage at this sample."],
  ];
  for (const [key, label, description] of basics) {
    const nodes = createMeasurementRow(label, description);
    measurementRows.set(key, nodes);
    fragment.append(nodes.row);
  }
  for (const definition of Array.isArray(currentData?.evidence_series) ? currentData.evidence_series : []) {
    const key = definition?.key;
    if (!key) continue;
    const nodes = createMeasurementRow(definition.label || key, definition.description || "Published evidence value.", key);
    measurementRows.set(key, nodes);
    fragment.append(nodes.row);
  }
  els.measurementList.replaceChildren(fragment);
  lastMeasuredSampleIndex = -1;
}

function updateMeasurementValue(key, value) {
  const nodes = measurementRows.get(key);
  if (nodes && nodes.detail.textContent !== String(value)) nodes.detail.textContent = String(value);
}

function createTimeline(track, intervals, totalFrames) {
  const marker = track.querySelector(".lane-marker");
  track.replaceChildren();
  for (const interval of Array.isArray(intervals) ? intervals : []) {
    const start = Math.max(0, safeNum(interval?.[0]));
    const end = Math.min(totalFrames, safeNum(interval?.[1]));
    if (end <= start) continue;
    const segment = document.createElement("span");
    segment.className = "lane-segment";
    segment.dataset.state = normalizeState(interval[2]);
    segment.style.left = `${(start / totalFrames) * 100}%`;
    segment.style.width = `${((end - start) / totalFrames) * 100}%`;
    segment.title = `${normalizeState(interval[2])} · ${formatFrameTime(start)}–${formatFrameTime(end)}`;
    track.append(segment);
  }
  const newMarker = document.createElement("span");
  newMarker.className = "lane-marker";
  newMarker.setAttribute("aria-hidden", "true");
  track.append(newMarker);
}

function updateTimelineMarkers() {
  const duration = Math.max(1, safeNum(currentData?.duration_frames, 1));
  const left = `${Math.min(100, Math.max(0, (currentFrame / duration) * 100))}%`;
  for (const track of [els.trackV1, els.trackV2, els.trackReference]) {
    const marker = track.querySelector(".lane-marker");
    if (marker) marker.style.left = left;
  }
}

function buildTimeline() {
  const total = Math.max(1, safeNum(currentData?.duration_frames, 1));
  createTimeline(els.trackV1, currentData?.predictions?.v1, total);
  createTimeline(els.trackV2, currentData?.predictions?.v2, total);
  createTimeline(els.trackReference, currentData?.truth, total);
  const totalSeconds = total / safeNum(currentData?.fps, 1);
  els.rulerMid.textContent = formatTime(totalSeconds / 2, 0);
  els.rulerEnd.textContent = formatTime(totalSeconds, 0);
  els.referenceCaption.textContent = currentMeta?.kind === "synthetic_demo" ? "authored fixture" : "provider labels";
  els.referenceLane.hidden = !els.referenceToggle.checked;
  els.referenceReading.hidden = !els.referenceToggle.checked;
  els.referenceToggle.disabled = !Array.isArray(currentData?.truth);
  updateTimelineMarkers();
}

function hexRgba(hex, alpha) {
  const raw = String(hex).replace("#", "");
  const normalized = raw.length === 3 ? raw.split("").map((c) => c + c).join("") : raw;
  const number = Number.parseInt(normalized, 16);
  if (!Number.isFinite(number)) return `rgba(207,223,130,${alpha})`;
  return `rgba(${(number >> 16) & 255},${(number >> 8) & 255},${number & 255},${alpha})`;
}

function pitchDimensions(width, height, length, breadth) {
  const padX = Math.max(24, width * 0.055);
  const padY = Math.max(24, height * 0.07);
  const scale = Math.min((width - padX * 2) / length, (height - padY * 2) / breadth);
  const fieldWidth = length * scale;
  const fieldHeight = breadth * scale;
  return {
    x: (width - fieldWidth) / 2,
    y: (height - fieldHeight) / 2,
    w: fieldWidth,
    h: fieldHeight,
    scale,
  };
}

function pitchPoint(xM, yM, pitch, length, breadth) {
  return [pitch.x + (xM / length) * pitch.w, pitch.y + (yM / breadth) * pitch.h];
}

function drawPitchLines(ctx, width, height, pitch, length, breadth, options) {
  ctx.fillStyle = "#103229";
  ctx.fillRect(0, 0, width, height);
  ctx.fillStyle = "#174237";
  ctx.fillRect(pitch.x, pitch.y, pitch.w, pitch.h);
  ctx.strokeStyle = "rgba(239,239,219,.73)";
  ctx.lineWidth = Math.max(1, Math.min(width, height) * 0.0024);
  ctx.strokeRect(pitch.x, pitch.y, pitch.w, pitch.h);
  const line = (x1, y1, x2, y2, dashed = false) => {
    const a = pitchPoint(x1, y1, pitch, length, breadth);
    const b = pitchPoint(x2, y2, pitch, length, breadth);
    ctx.beginPath();
    ctx.setLineDash(dashed ? [4, 4] : []);
    ctx.moveTo(...a);
    ctx.lineTo(...b);
    ctx.stroke();
    ctx.setLineDash([]);
  };
  line(length / 2, 0, length / 2, breadth);
  const [cx, cy] = pitchPoint(length / 2, breadth / 2, pitch, length, breadth);
  ctx.beginPath();
  ctx.arc(cx, cy, 9.15 * pitch.scale, 0, Math.PI * 2);
  ctx.stroke();
  ctx.fillStyle = "rgba(239,239,219,.73)";
  ctx.beginPath();
  ctx.arc(cx, cy, Math.max(1.5, pitch.scale * .18), 0, Math.PI * 2);
  ctx.fill();
  const boxDepth = Math.min(16.5, length / 4);
  const boxHalf = Math.min(20.16, breadth / 2);
  const goalDepth = Math.min(5.5, length / 10);
  const goalHalf = Math.min(9.16, breadth / 2);
  ctx.strokeRect(pitch.x, cy - boxHalf * pitch.scale, boxDepth * pitch.scale, boxHalf * 2 * pitch.scale);
  ctx.strokeRect(pitch.x + pitch.w - boxDepth * pitch.scale, cy - boxHalf * pitch.scale, boxDepth * pitch.scale, boxHalf * 2 * pitch.scale);
  ctx.strokeRect(pitch.x, cy - goalHalf * pitch.scale, goalDepth * pitch.scale, goalHalf * 2 * pitch.scale);
  ctx.strokeRect(pitch.x + pitch.w - goalDepth * pitch.scale, cy - goalHalf * pitch.scale, goalDepth * pitch.scale, goalHalf * 2 * pitch.scale);
  const spotX1 = pitchPoint(11, breadth / 2, pitch, length, breadth);
  const spotX2 = pitchPoint(length - 11, breadth / 2, pitch, length, breadth);
  ctx.fillStyle = "rgba(239,239,219,.78)";
  for (const [sx, sy] of [spotX1, spotX2]) {
    ctx.beginPath();
    ctx.arc(sx, sy, Math.max(1.2, pitch.scale * .15), 0, Math.PI * 2);
    ctx.fill();
  }

  if (options.grid) {
    ctx.strokeStyle = "rgba(225,233,201,.12)";
    ctx.lineWidth = 1;
    for (let x = 10; x < length; x += 10) line(x, 0, x, breadth);
    for (let y = 10; y < breadth; y += 10) line(0, y, length, y);
  }
  if (options.regions) {
    const bx = options.ball ? options.ball[0] / options.coordinateScale : null;
    const by = options.ball ? options.ball[1] / options.coordinateScale : null;
    if (bx !== null && by !== null) {
      const col = Math.min(2, Math.max(0, Math.floor((bx / length) * 3)));
      const row = Math.min(2, Math.max(0, Math.floor((by / breadth) * 3)));
      ctx.fillStyle = "rgba(207,223,130,.17)";
      ctx.fillRect(pitch.x + col * pitch.w / 3, pitch.y + row * pitch.h / 3, pitch.w / 3, pitch.h / 3);
    }
    ctx.strokeStyle = "rgba(241,233,170,.5)";
    ctx.lineWidth = 1;
    for (let part = 1; part < 3; part++) {
      const x = pitch.x + pitch.w * part / 3;
      const y = pitch.y + pitch.h * part / 3;
      ctx.beginPath(); ctx.moveTo(x, pitch.y); ctx.lineTo(x, pitch.y + pitch.h); ctx.stroke();
      ctx.beginPath(); ctx.moveTo(pitch.x, y); ctx.lineTo(pitch.x + pitch.w, y); ctx.stroke();
    }
  }
}

function drawTrails(ctx, data, sampleIndex, pitch, length, breadth, colors) {
  const samples = data.samples;
  const roster = data.roster || [];
  const fps = safeNum(data.fps, 1);
  const currentSample = samples[sampleIndex];
  const maxAgeFrames = Math.max(1, Math.round(fps * 4));
  const startIndex = Math.max(0, sampleIndex - Math.ceil(safeNum(data.sample_hz, 1) * 4));
  const trails = new Map();
  for (let index = startIndex; index <= sampleIndex; index++) {
    const sample = samples[index];
    if (currentSample && safeNum(currentSample.f) - safeNum(sample.f) > maxAgeFrames) continue;
    const present = new Set();
    for (const player of sample.p || []) {
      if (!Array.isArray(player) || player.length < 3) continue;
      const rosterIndex = safeNum(player[0], -1);
      if (rosterIndex < 0) continue;
      present.add(rosterIndex);
      if (!trails.has(rosterIndex)) trails.set(rosterIndex, []);
      trails.get(rosterIndex).push([safeNum(player[1]) / safeNum(data.coordinate_scale, 100), safeNum(player[2]) / safeNum(data.coordinate_scale, 100)]);
    }
    for (const [rosterIndex, points] of trails) {
      if (!present.has(rosterIndex)) trails.set(rosterIndex, []);
    }
  }
  for (const [rosterIndex, points] of trails) {
    if (points.length < 2) continue;
    const player = roster[rosterIndex];
    const color = player?.team === "H" ? colors.home : colors.away;
    ctx.beginPath();
    points.forEach(([x, y], index) => {
      const [px, py] = pitchPoint(x, y, pitch, length, breadth);
      if (!index) ctx.moveTo(px, py);
      else ctx.lineTo(px, py);
    });
    ctx.strokeStyle = hexRgba(color, .28);
    ctx.lineWidth = Math.max(1.4, Math.min(4.5, pitch.scale * .75));
    ctx.lineCap = "round";
    ctx.lineJoin = "round";
    ctx.stroke();
  }
}

function drawPitch(ctx, width, height, options = {}) {
  const data = options.data || currentData;
  if (!data) {
    ctx.fillStyle = "#103229";
    ctx.fillRect(0, 0, width, height);
    return;
  }
  const length = safeNum(data.pitch?.length_m, 105);
  const breadth = safeNum(data.pitch?.width_m, 68);
  const scale = safeNum(data.coordinate_scale, 100);
  const pitch = pitchDimensions(width, height, length, breadth);
  const sampleIndex = options.sampleIndex ?? currentSampleIndex;
  const sample = data.samples?.[sampleIndex];
  const ballAvailable = hasBall(sample);
  const colors = options.colors || { home: els.homeColor.value, away: els.awayColor.value };
  drawPitchLines(ctx, width, height, pitch, length, breadth, {
    grid: options.grid ?? els.gridToggle.checked,
    regions: options.regions ?? els.regionsToggle.checked,
    ball: ballAvailable ? sample.b : null,
    coordinateScale: scale,
  });

  if ((options.trails ?? els.trailsToggle.checked) && !options.exportSimple) {
    drawTrails(ctx, data, sampleIndex, pitch, length, breadth, colors);
  }

  const roster = data.roster || [];
  const playerRadius = Math.max(4.2, Math.min(8.1, width * .0095));
  for (const player of sample?.p || []) {
    if (!Array.isArray(player) || player.length < 3) continue;
    const rosterIndex = safeNum(player[0], -1);
    if (rosterIndex < 0) continue;
    const entry = roster[rosterIndex];
    const teamColor = entry?.team === "H" ? colors.home : colors.away;
    const [px, py] = pitchPoint(safeNum(player[1]) / scale, safeNum(player[2]) / scale, pitch, length, breadth);
    ctx.beginPath();
    ctx.arc(px, py, playerRadius, 0, Math.PI * 2);
    ctx.fillStyle = teamColor;
    ctx.fill();
    ctx.lineWidth = Math.max(1.4, width * .0023);
    ctx.strokeStyle = "rgba(8,34,28,.9)";
    ctx.stroke();
    if ((options.numbers ?? els.numbersToggle.checked) && entry && entry.number !== undefined && entry.number !== null) {
      ctx.fillStyle = "#132c27";
      ctx.font = `700 ${Math.max(7, playerRadius * 1.4)}px ${getComputedStyle(document.body).fontFamily}`;
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      ctx.fillText(String(entry.number), px, py + .2);
    }
  }

  if (ballAvailable) {
    const [bx, by] = pitchPoint(safeNum(sample.b[0]) / scale, safeNum(sample.b[1]) / scale, pitch, length, breadth);
    const r = Math.max(5.3, Math.min(9, width * .011));
    ctx.beginPath(); ctx.arc(bx, by, r + 2.3, 0, Math.PI * 2);
    ctx.fillStyle = "rgba(10,35,29,.65)"; ctx.fill();
    ctx.beginPath(); ctx.arc(bx, by, r, 0, Math.PI * 2);
    ctx.fillStyle = "#f1e9aa"; ctx.fill();
    ctx.lineWidth = 1.2; ctx.strokeStyle = "#102f27"; ctx.stroke();
    ctx.beginPath(); ctx.moveTo(bx - r * .48, by); ctx.lineTo(bx + r * .48, by); ctx.moveTo(bx, by - r * .48); ctx.lineTo(bx, by + r * .48);
    ctx.strokeStyle = "rgba(16,47,39,.58)"; ctx.stroke();
  }

  if (options.exportMeta) {
    const footerHeight = options.footerHeight || 52;
    ctx.fillStyle = "#103229";
    ctx.fillRect(0, height, width, footerHeight);
    ctx.fillStyle = "#f7f5ec";
    ctx.textAlign = "left";
    ctx.textBaseline = "middle";
    ctx.font = "600 14px Segoe UI, Arial, sans-serif";
    ctx.fillText(options.exportMeta.identity, 18, height + footerHeight / 2 - 8);
    ctx.fillStyle = "rgba(247,245,236,.77)";
    ctx.font = "11px Segoe UI, Arial, sans-serif";
    ctx.fillText(options.exportMeta.credit, 18, height + footerHeight / 2 + 10);
  }
}

function resizeCanvas() {
  if (!els.pitchCanvas || !pitchCtx) return;
  const rect = els.pitchCanvas.getBoundingClientRect();
  const width = Math.max(1, Math.floor(rect.width));
  const height = Math.max(1, Math.floor(rect.height));
  const dpr = Math.min(3, Math.max(1, window.devicePixelRatio || 1));
  const backingWidth = Math.floor(width * dpr);
  const backingHeight = Math.floor(height * dpr);
  if (els.pitchCanvas.width !== backingWidth || els.pitchCanvas.height !== backingHeight) {
    els.pitchCanvas.width = backingWidth;
    els.pitchCanvas.height = backingHeight;
  }
  pitchCtx.setTransform(dpr, 0, 0, dpr, 0, 0);
  document.documentElement.style.setProperty("--active-home", els.homeColor.value);
  document.documentElement.style.setProperty("--active-away", els.awayColor.value);
  drawPitch(pitchCtx, width, height);
}

function updateFrameReadouts(syncVideo = false) {
  if (!currentData) return;
  const total = Math.max(1, safeNum(currentData.duration_frames, 1));
  currentFrame = Math.max(0, Math.min(total - 1, Math.round(currentFrame)));
  currentSampleIndex = binarySampleIndex(currentFrame);
  const fps = safeNum(currentData.fps, 1);
  els.frameRange.value = String(currentFrame);
  els.frameInput.value = String(currentFrame);
  els.timeInput.value = formatFrameTime(currentFrame, fps);
  els.elapsedTime.textContent = formatFrameTime(currentFrame, fps);
  els.frameReadout.textContent = currentFrame.toLocaleString();
  updateStateReadout();
  updateObservationReadout();
  updateTimelineMarkers();
  resizeCanvas();
  if (syncVideo) seekSyntheticVideo();
}

function updateFrame(frame, syncVideo = true) {
  if (!currentData) return;
  currentFrame = frame;
  playbackPosition = Math.round(safeNum(frame));
  updateFrameReadouts(syncVideo);
}

function seekSyntheticVideo() {
  if (!currentData?.media?.url) return;
  const expectedUrl = new URL(currentData.media.url, document.baseURI).href;
  if (els.syntheticVideo.dataset.sourceUrl && els.syntheticVideo.dataset.sourceUrl !== expectedUrl) return;
  if (els.syntheticVideo.currentSrc && els.syntheticVideo.currentSrc !== expectedUrl) return;
  if (els.syntheticVideo.readyState < 1 || !Number.isFinite(els.syntheticVideo.duration) || els.syntheticVideo.duration <= 0) return;
  const offset = safeNum(currentData.media.offset_s);
  const target = Math.max(0, offset + currentFrame / safeNum(currentData.fps, 1));
  const videoTime = Math.min(target, Math.max(0, els.syntheticVideo.duration - .02));
  if (Math.abs(els.syntheticVideo.currentTime - videoTime) > .025) {
    try { els.syntheticVideo.currentTime = videoTime; } catch { /* A browser may defer seeking until media data is ready. */ }
  }
}

function drawFrame() {
  resizeCanvas();
}

function stopPlayback() {
  playing = false;
  if (playbackRaf) cancelAnimationFrame(playbackRaf);
  playbackRaf = 0;
  previousTick = 0;
  els.playButton.classList.remove("is-playing");
  els.playButton.setAttribute("aria-label", "Play replay");
  els.playText.textContent = "Play";
  els.syntheticVideo.pause();
}

function playbackTick(now) {
  if (!playing || !currentData) return;
  if (!previousTick) previousTick = now;
  const delta = now - previousTick;
  previousTick = now;
  const speed = Math.max(.1, safeNum(els.speedSelect.value, 1));
  let nextFrame;
  if (currentData.media?.url && !els.syntheticVideo.paused && els.syntheticVideo.readyState >= 2 && Number.isFinite(els.syntheticVideo.currentTime)) {
    playbackPosition = Math.max(0, (els.syntheticVideo.currentTime - safeNum(currentData.media.offset_s)) * safeNum(currentData.fps, 1));
    nextFrame = Math.floor(playbackPosition);
  } else {
    playbackPosition += (delta / 1000) * safeNum(currentData.fps, 1) * speed;
    nextFrame = Math.floor(playbackPosition);
  }
  if (nextFrame >= safeNum(currentData.duration_frames) - 1) {
    currentFrame = Math.max(0, safeNum(currentData.duration_frames) - 1);
    playbackPosition = currentFrame;
    updateFrameReadouts(false);
    stopPlayback();
    return;
  }
  if (nextFrame !== currentFrame) {
    currentFrame = nextFrame;
    updateFrameReadouts(false);
  }
  playbackRaf = requestAnimationFrame(playbackTick);
}

function startPlayback() {
  if (!currentData) return;
  if (currentFrame >= safeNum(currentData.duration_frames) - 1) updateFrame(0);
  playing = true;
  previousTick = 0;
  playbackPosition = currentFrame;
  els.playButton.classList.add("is-playing");
  els.playButton.setAttribute("aria-label", "Pause replay");
  els.playText.textContent = "Pause";
  if (currentData.media?.url) {
    els.syntheticVideo.playbackRate = Math.max(.1, safeNum(els.speedSelect.value, 1));
    seekSyntheticVideo();
    els.syntheticVideo.play().catch(() => {});
  }
  playbackRaf = requestAnimationFrame(playbackTick);
}

function togglePlayback() {
  if (playing) stopPlayback();
  else startPlayback();
}

function changeStateTransitions() {
  const intervals = currentData?.predictions?.v2 || [];
  const transitions = [];
  let previousTeam = null;
  for (const interval of intervals) {
    const state = normalizeState(interval?.[2]);
    const frame = safeNum(interval?.[0]);
    if (state !== "H" && state !== "A") continue;
    if (previousTeam !== null && state !== previousTeam) transitions.push(frame);
    previousTeam = state;
  }
  return transitions;
}

function seekChange(direction) {
  const transitions = changeStateTransitions();
  if (direction < 0) {
    const target = [...transitions].reverse().find((frame) => frame < currentFrame);
    if (target !== undefined) updateFrame(target);
  } else {
    const target = transitions.find((frame) => frame > currentFrame);
    if (target !== undefined) updateFrame(target);
  }
}

function resetDisplay() {
  els.homeColor.value = defaults.home;
  els.awayColor.value = defaults.away;
  els.numbersToggle.checked = defaults.numbers;
  els.gridToggle.checked = defaults.grid;
  els.trailsToggle.checked = defaults.trails;
  els.regionsToggle.checked = defaults.regions;
  els.referenceToggle.checked = defaults.reference;
  applyReferenceToggle();
  resizeCanvas();
}

function applyReferenceToggle() {
  const visible = Boolean(els.referenceToggle.checked && currentData?.truth);
  els.referenceLane.hidden = !visible;
  els.referenceReading.hidden = !visible;
  updateFrameReadouts(false);
}

function updateSequenceCopy() {
  if (!currentMeta || !currentData) return;
  els.sequenceTitle.textContent = currentMeta.title || currentData.title || sequenceLabel(currentMeta);
  const sourceHz = safeNum(currentData.source_sample_hz, safeNum(currentData.sample_hz));
  const displayHz = safeNum(currentData.sample_hz, sourceHz);
  const cadence = Number.isFinite(displayHz) && displayHz > 0
    ? `Display cadence ${displayHz.toFixed(2)} Hz${sourceHz > displayHz + .01 ? ` · source ${sourceHz.toFixed(2)} Hz` : ""}.`
    : "Display cadence reported in the replay record.";
  els.fieldCaption.textContent = `${sequenceLabel(currentMeta)} · ${cadence}`;
  if (currentMeta.kind === "synthetic_demo") {
    els.replayScope.textContent = "Synthetic software fixture. Labels are authored test values, not outputs from the trained model; benchmark cells remain null.";
    els.provenanceText.textContent = "Synthetic positions and labels are software fixtures. They do not represent a match or a trained-model result.";
    els.videoPanel.hidden = !currentData.media?.url;
  } else {
    els.replayScope.textContent = "Public CC BY 4.0 tracking observations; labels are from the published source. Source observations are thinned for display, while label and benchmark intervals remain unchanged.";
    els.provenanceText.textContent = "The displayed coordinates are a thinned, rounded view. Full-rate labels and evaluation rows are unchanged.";
    els.videoPanel.hidden = true;
  }
  els.referenceCaption.textContent = currentMeta.kind === "synthetic_demo" ? "authored fixture" : "provider labels";
}

async function loadSequence(sequence) {
  if (!sequence) return;
  const loadToken = ++loadSequenceToken;
  stopPlayback();
  setReplayControls(false);
  currentMeta = sequence;
  currentData = null;
  els.videoPanel.hidden = sequence.kind !== "synthetic_demo";
  els.replayWorkbench.setAttribute("aria-busy", "true");
  els.pitchEmpty.hidden = false;
  els.pitchEmpty.textContent = "Loading approved replay observations…";
  els.sequenceTitle.textContent = sequence.title || sequenceLabel(sequence);
  setTone(`Loading ${sequenceLabel(sequence)}…`);
  resizeCanvas();
  try {
    const response = await fetch(sequence.url);
    if (loadToken !== loadSequenceToken) return;
    if (!response.ok) throw new Error(`Replay file returned ${response.status}`);
    const data = await response.json();
    if (loadToken !== loadSequenceToken) return;
    if (!data || !Array.isArray(data.samples) || !Array.isArray(data.roster)) throw new Error("Replay file does not match the public schema");
    currentData = data;
    currentFrame = 0;
    currentSampleIndex = 0;
    prepareMeasurementRows();
    els.frameRange.min = "0";
    els.frameRange.max = String(Math.max(0, safeNum(data.duration_frames) - 1));
    els.frameRange.value = "0";
    els.frameInput.min = "0";
    els.frameInput.max = String(Math.max(0, safeNum(data.duration_frames) - 1));
    els.durationTime.textContent = formatTime(safeNum(data.duration_frames) / safeNum(data.fps, 1));
    els.referenceToggle.checked = false;
    updateSequenceCopy();
    buildTimeline();
    els.pitchEmpty.hidden = true;
    els.replayWorkbench.setAttribute("aria-busy", "false");
    setReplayControls(true);
    els.referenceToggle.disabled = !Array.isArray(data.truth);
    els.referenceLane.hidden = true;
    els.referenceReading.hidden = true;
    els.exportButton.disabled = false;
    els.shareButton.disabled = false;
    setTone(`${data.samples.length.toLocaleString()} display observations · ${formatTime(safeNum(data.duration_frames) / safeNum(data.fps, 1))} total`, "ok");
    updateFrame(0, true);
    if (data.media?.url) {
      const mediaUrl = new URL(data.media.url, document.baseURI).href;
      els.syntheticVideo.dataset.sourceUrl = mediaUrl;
      els.syntheticVideo.src = mediaUrl;
      els.syntheticVideo.load();
      seekSyntheticVideo();
    } else {
      els.syntheticVideo.pause();
      delete els.syntheticVideo.dataset.sourceUrl;
      els.syntheticVideo.removeAttribute("src");
      els.syntheticVideo.load();
    }
  } catch (error) {
    if (loadToken !== loadSequenceToken) return;
    currentData = null;
    els.replayWorkbench.setAttribute("aria-busy", "false");
    els.pitchEmpty.hidden = false;
    els.pitchEmpty.textContent = "This approved replay could not be loaded.";
    els.sequenceTitle.textContent = sequence.title || sequenceLabel(sequence);
    setReplayControls(false);
    setTone(`Could not load ${sequenceLabel(sequence)}. Check that the public replay files are present.`, "error");
    console.error("Replay load failed", error);
    resizeCanvas();
  }
}

function formatMetric(value, digits = 4) {
  return typeof value === "number" && Number.isFinite(value) ? value.toFixed(digits) : "—";
}

function renderBenchmarks() {
  if (!benchmarkData) return;
  const rows = Array.isArray(benchmarkData.rows) ? benchmarkData.rows : [];
  const filter = els.scenarioFilter.value || "all";
  const visibleRows = filter === "all" ? rows : rows.filter((row) => row.scenario === filter);
  els.benchmarkRows.replaceChildren();
  if (!visibleRows.length) {
    const tr = document.createElement("tr");
    const td = document.createElement("td");
    td.colSpan = 8;
    td.className = "table-placeholder";
    td.textContent = "No published rows for this scenario.";
    tr.append(td);
    els.benchmarkRows.append(tr);
  } else {
    const fragment = document.createDocumentFragment();
    for (const row of visibleRows) {
      const tr = document.createElement("tr");
      const values = [
        row.match_id ?? "—", row.scenario ?? "—",
        formatMetric(row.v1?.spellF1), formatMetric(row.v2?.spellF1),
        formatMetric(row.v1?.macroF1), formatMetric(row.v2?.macroF1),
        formatMetric(row.v1?.inference_s, 2), formatMetric(row.v2?.inference_s, 2),
      ];
      for (const value of values) {
        const td = document.createElement("td");
        td.textContent = String(value);
        tr.append(td);
      }
      fragment.append(tr);
    }
    els.benchmarkRows.append(fragment);
  }
  els.benchmarkCount.textContent = `${visibleRows.length} of ${rows.length} whole-match rows · both halves`;
  const summary = benchmarkData.summary || {};
  $("#spellV1").textContent = formatMetric(summary.v1?.spellF1, 5);
  $("#spellV2").textContent = formatMetric(summary.v2?.spellF1, 5);
  $("#macroV1").textContent = formatMetric(summary.v1?.macroF1, 5);
  $("#macroV2").textContent = formatMetric(summary.v2?.macroF1, 5);
  els.benchmarkInterpretation.textContent = benchmarkData.interpretation || "Reused-source grouped development, not independent or target.";
}

async function loadBenchmarks() {
  try {
    const response = await fetch(indexData.benchmarks_url);
    if (!response.ok) throw new Error(`Benchmark file returned ${response.status}`);
    benchmarkData = await response.json();
    const scenarios = [...new Set((benchmarkData.rows || []).map((row) => row.scenario).filter(Boolean))].sort();
    els.scenarioFilter.replaceChildren();
    const allOption = document.createElement("option");
    allOption.value = "all";
    allOption.textContent = "All source scenarios";
    els.scenarioFilter.append(allOption);
    for (const scenario of scenarios) {
      const option = document.createElement("option");
      option.value = scenario;
      option.textContent = scenario;
      els.scenarioFilter.append(option);
    }
    els.scenarioFilter.disabled = false;
    renderBenchmarks();
  } catch (error) {
    els.benchmarkCount.textContent = "Published benchmark table unavailable.";
    els.benchmarkRows.innerHTML = "<tr><td colspan=\"8\" class=\"table-placeholder\">Development measurements could not be loaded from the published public files.</td></tr>";
    console.error("Benchmark load failed", error);
  }
}

async function loadPublicIndex() {
  try {
    const response = await fetch("./replays/index.json");
    if (!response.ok) throw new Error(`Replay index returned ${response.status}`);
    indexData = await response.json();
    if (!Array.isArray(indexData.sequences) || !indexData.sequences.length) throw new Error("Replay index is empty");
    sequences = indexData.sequences;
    sequenceById = new Map(sequences.map((sequence) => [sequence.id, sequence]));
    const requested = new URLSearchParams(location.search).get("replay");
    const requestedFrame = new URLSearchParams(location.search).get("frame");
    populateMatches(requested || indexData.default_sequence);
    els.scenarioFilter.disabled = true;
    const sequence = getSequenceFromControls();
    await Promise.all([loadSequence(sequence), loadBenchmarks()]);
    if (requested && sequence?.id === requested && requestedFrame !== null && Number.isFinite(Number(requestedFrame))) {
      updateFrame(Number(requestedFrame), true);
    }
  } catch (error) {
    els.replayWorkbench.setAttribute("aria-busy", "false");
    els.pitchEmpty.hidden = false;
    els.pitchEmpty.textContent = "Approved public replay files are not available.";
    els.matchSelect.replaceChildren(new Option("Replay files unavailable", ""));
    els.matchSelect.disabled = true;
    els.halfSelect.disabled = true;
    setTone("Could not load the approved public replay index. Serve the website folder with its replay files.", "error");
    console.error("Public replay index failed", error);
    resizeCanvas();
  }
}

function currentShareUrl() {
  const url = new URL(window.location.href);
  url.searchParams.set("replay", currentMeta.id);
  url.searchParams.set("frame", String(Math.round(currentFrame)));
  return url.toString();
}

async function shareCurrentView() {
  if (!currentMeta) return;
  const url = currentShareUrl();
  els.shareLinkRow.hidden = false;
  els.shareLink.value = url;
  try {
    await navigator.clipboard.writeText(url);
    els.shareStatus.textContent = "Link copied.";
  } catch {
    els.shareStatus.textContent = "Link ready. Select the field and copy.";
    els.shareLink.focus();
    els.shareLink.select();
  }
}

function sanitizeFilename(value) {
  return String(value || "replay").replace(/[^a-z0-9_-]+/gi, "-").replace(/^-+|-+$/g, "").toLowerCase() || "replay";
}

function exportCurrentField() {
  if (!currentMeta || !currentData) return;
  // Use a readable export size even when the field is viewed on a phone.
  const logicalWidth = Math.max(960, els.pitchCanvas.clientWidth);
  const logicalHeight = Math.round(logicalWidth * els.pitchCanvas.clientHeight / Math.max(1, els.pitchCanvas.clientWidth));
  const footerHeight = 64;
  const image = document.createElement("canvas");
  image.width = logicalWidth * 2;
  image.height = (logicalHeight + footerHeight) * 2;
  const ctx = image.getContext("2d");
  ctx.setTransform(2, 0, 0, 2, 0, 0);
  const credit = currentMeta.kind === "synthetic_demo"
    ? "Synthetic software fixture · authored test labels, not trained-model results"
    : `${currentData.license?.credit || "Bassek, Rein, Weber and Memmert"} · CC BY 4.0 · doi.org/10.6084/m9.figshare.28196177.v1`;
  drawPitch(ctx, logicalWidth, logicalHeight, {
    data: currentData,
    sampleIndex: currentSampleIndex,
    numbers: els.numbersToggle.checked,
    grid: els.gridToggle.checked,
    regions: els.regionsToggle.checked,
    trails: els.trailsToggle.checked,
    colors: { home: els.homeColor.value, away: els.awayColor.value },
    exportMeta: {
      identity: `${currentMeta.title || currentMeta.id} · ${formatFrameTime(currentFrame)} · frame ${Math.round(currentFrame)}`,
      credit,
    },
    footerHeight,
  });
  const link = document.createElement("a");
  link.download = `possession-atlas-${sanitizeFilename(currentMeta.id)}-${String(Math.round(currentFrame)).padStart(6, "0")}.png`;
  link.href = image.toDataURL("image/png");
  link.click();
}

function bindEvents() {
  els.matchSelect.addEventListener("change", () => {
    populateHalves(els.matchSelect.value);
    loadSequence(getSequenceFromControls());
  });
  els.halfSelect.addEventListener("change", () => loadSequence(getSequenceFromControls()));
  els.playButton.addEventListener("click", togglePlayback);
  els.stepBack.addEventListener("click", () => updateFrame(currentFrame - 1));
  els.stepForward.addEventListener("click", () => updateFrame(currentFrame + 1));
  els.frameRange.addEventListener("input", () => updateFrame(Number(els.frameRange.value)));
  els.frameInput.addEventListener("keydown", (event) => {
    if (event.key === "Enter") { event.preventDefault(); updateFrame(Number(els.frameInput.value)); }
  });
  els.seekFrameButton.addEventListener("click", () => updateFrame(Number(els.frameInput.value)));
  els.timeInput.addEventListener("keydown", (event) => {
    if (event.key === "Enter") { event.preventDefault(); const seconds = parseTime(els.timeInput.value); if (seconds !== null) updateFrame(seconds * safeNum(currentData?.fps, 1)); }
  });
  els.seekTimeButton.addEventListener("click", () => {
    const seconds = parseTime(els.timeInput.value);
    if (seconds !== null) updateFrame(seconds * safeNum(currentData?.fps, 1));
    else { els.timeInput.setCustomValidity("Enter seconds or minutes:seconds, such as 93.4 or 1:33.4."); els.timeInput.reportValidity(); }
  });
  els.timeInput.addEventListener("input", () => els.timeInput.setCustomValidity(""));
  els.speedSelect.addEventListener("change", () => {
    if (currentData?.media?.url) els.syntheticVideo.playbackRate = safeNum(els.speedSelect.value, 1);
  });
  els.syntheticVideo.addEventListener("loadedmetadata", () => {
    if (!currentData?.media?.url) return;
    const expectedUrl = new URL(currentData.media.url, document.baseURI).href;
    if (els.syntheticVideo.dataset.sourceUrl !== expectedUrl || els.syntheticVideo.currentSrc !== expectedUrl) return;
    seekSyntheticVideo();
  });
  els.previousChange.addEventListener("click", () => seekChange(-1));
  els.nextChange.addEventListener("click", () => seekChange(1));
  els.referenceToggle.addEventListener("change", applyReferenceToggle);
  for (const input of [els.numbersToggle, els.gridToggle, els.trailsToggle, els.regionsToggle, els.homeColor, els.awayColor]) {
    input.addEventListener("input", resizeCanvas);
    input.addEventListener("change", resizeCanvas);
  }
  els.resetView.addEventListener("click", resetDisplay);
  els.shareButton.addEventListener("click", shareCurrentView);
  els.exportButton.addEventListener("click", exportCurrentField);
  els.scenarioFilter.addEventListener("change", renderBenchmarks);
  window.addEventListener("resize", resizeCanvas, { passive: true });
  if ("ResizeObserver" in window) {
    resizeObserver = new ResizeObserver(resizeCanvas);
    resizeObserver.observe(els.pitchCanvas);
  }

  const menuToggle = $("#menuToggle");
  const mobileNav = $("#mobileNav");
  menuToggle.addEventListener("click", () => {
    const expanded = menuToggle.getAttribute("aria-expanded") === "true";
    menuToggle.setAttribute("aria-expanded", String(!expanded));
    menuToggle.setAttribute("aria-label", expanded ? "Open navigation" : "Close navigation");
    mobileNav.hidden = expanded;
  });
  mobileNav.addEventListener("click", (event) => {
    if (event.target.closest("a")) {
      mobileNav.hidden = true;
      menuToggle.setAttribute("aria-expanded", "false");
      menuToggle.setAttribute("aria-label", "Open navigation");
    }
  });
}

async function mountSandboxOnce() {
  if (labMounted) return;
  labMounted = true;
  try {
    const { mountSandbox } = await import("./sandbox.js");
    mountSandbox($("#sandboxRoot"));
  } catch (error) {
    const root = $("#sandboxRoot");
    root.textContent = "The synthetic decoder lab could not be loaded.";
    console.error("Decoder lab failed to mount", error);
  }
}

bindEvents();
resizeCanvas();
mountSandboxOnce();
loadPublicIndex();
