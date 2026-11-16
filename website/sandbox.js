const STATE_NAMES = Object.freeze(["H", "A", "D"]);
const STATE_COLORS = Object.freeze({ H: "#9d90ff", A: "#f2a93b", D: "#8b8a93" });
const PRESETS = Object.freeze(["short-regain", "occlusion", "stoppage"]);
const BIN_COUNT = 36;
const BIN_SECONDS = 0.5;

let nextInstanceId = 0;

const LAB_STYLES = `
.lab-shell {
  --lab-paper: #111116;
  --lab-paper-deep: #19191f;
  --lab-ink: #e7e5df;
  --lab-muted: #aaa6b5;
  --lab-rule: #34313f;
  --lab-pine: #9d90ff;
  --lab-copper: #f2a93b;
  --lab-chartreuse: #9d90ff;
  --lab-dead: #8b8a93;
  color: var(--lab-ink);
  background: var(--lab-paper);
  border: 1px solid var(--lab-rule);
  padding: clamp(1.15rem, 3vw, 2.4rem);
  font-family: "IBM Plex Sans", system-ui, sans-serif;
  line-height: 1.5;
  isolation: isolate;
}
.lab-shell *, .lab-shell *::before, .lab-shell *::after { box-sizing: border-box; }
.lab-shell .lab-kicker {
  margin: 0 0 .65rem;
  color: var(--lab-copper);
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: .73rem;
  font-weight: 750;
  letter-spacing: .13em;
  text-transform: uppercase;
}
.lab-shell .lab-heading {
  max-width: 16ch;
  margin: 0;
  font-family: "Archivo", "Arial Black", sans-serif;
  font-size: clamp(2rem, 4.6vw, 3.4rem);
  font-weight: 800;
  letter-spacing: -.045em;
  line-height: .98;
}
.lab-shell .lab-lede { max-width: 64ch; margin: 1rem 0 0; color: var(--lab-muted); }
.lab-shell .lab-disclaimer {
  margin: 1.25rem 0 0;
  padding: .8rem 1rem;
  border-left: 3px solid var(--lab-chartreuse);
  background: var(--lab-paper-deep);
  font-size: .9rem;
  font-weight: 650;
}
.lab-shell .lab-layout {
  display: grid;
  grid-template-columns: minmax(15rem, .86fr) minmax(0, 1.14fr);
  gap: clamp(1.5rem, 4vw, 3.4rem);
  margin-top: 2rem;
  padding-top: 1.5rem;
  border-top: 1px solid var(--lab-rule);
}
.lab-shell .lab-controls { min-width: 0; }
.lab-shell .lab-section-label {
  margin: 0 0 .7rem;
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: .72rem;
  font-weight: 750;
  letter-spacing: .1em;
  text-transform: uppercase;
}
.lab-shell .lab-presets {
  display: flex;
  flex-wrap: wrap;
  gap: .45rem;
  margin: 0 0 1.35rem;
  padding: 0;
  border: 0;
}
.lab-shell .lab-presets legend { margin-bottom: .65rem; padding: 0; }
.lab-shell .lab-button {
  min-height: 2.6rem;
  padding: .55rem .8rem;
  border: 1px solid var(--lab-rule);
  border-radius: 0;
  background: transparent;
  color: var(--lab-ink);
  font: inherit;
  font-size: .87rem;
  cursor: pointer;
}
.lab-shell .lab-button:hover { background: var(--lab-paper-deep); }
.lab-shell .lab-button[aria-pressed="true"] {
  border-color: var(--lab-ink);
  background: var(--lab-ink);
  color: var(--lab-paper);
}
.lab-shell .lab-range-control { margin: 1.15rem 0 1.25rem; }
.lab-shell .lab-range-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 1rem;
  margin-bottom: .45rem;
  font-size: .9rem;
  font-weight: 650;
}
.lab-shell .lab-range-head output {
  color: var(--lab-copper);
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: .86rem;
  font-variant-numeric: tabular-nums;
}
.lab-shell .lab-range {
  display: block;
  width: 100%;
  min-height: 1.25rem;
  margin: 0;
  accent-color: var(--lab-pine);
  cursor: pointer;
}
.lab-shell .lab-help { margin: .25rem 0 0; color: var(--lab-muted); font-size: .8rem; }
.lab-shell .lab-button-reset { margin-top: .15rem; text-decoration: underline; text-underline-offset: .2em; }
.lab-shell .lab-results { min-width: 0; }
.lab-shell .lab-status {
  min-height: 1.5em;
  margin: 0 0 .8rem;
  color: var(--lab-muted);
  font-size: .82rem;
}
.lab-shell .lab-metric-strip {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  border-top: 1px solid var(--lab-rule);
  border-bottom: 1px solid var(--lab-rule);
}
.lab-shell .lab-metric { min-width: 0; padding: .7rem .6rem .75rem 0; }
.lab-shell .lab-metric + .lab-metric { padding-left: .75rem; border-left: 1px solid var(--lab-rule); }
.lab-shell .lab-metric-label { display: block; color: var(--lab-muted); font-size: .73rem; }
.lab-shell .lab-metric-value {
  display: block;
  margin-top: .15rem;
  font-family: "Archivo", "Arial Black", sans-serif;
  font-size: clamp(1.25rem, 2.4vw, 1.7rem);
  font-variant-numeric: tabular-nums;
  line-height: 1.1;
}
.lab-shell .lab-objective { margin-top: 1.1rem; }
.lab-shell .lab-subheading {
  margin: 0;
  font-family: "Archivo", "Arial Black", sans-serif;
  font-size: 1.3rem;
  font-weight: 800;
}
.lab-shell .lab-formula { margin: .35rem 0 .7rem; color: var(--lab-muted); font-size: .82rem; }
.lab-shell .lab-objective-table,
.lab-shell .lab-evidence-table { width: 100%; border-collapse: collapse; font-size: .82rem; }
.lab-shell .lab-objective-table th,
.lab-shell .lab-objective-table td,
.lab-shell .lab-evidence-table th,
.lab-shell .lab-evidence-table td {
  padding: .48rem .5rem .48rem 0;
  border-bottom: 1px solid var(--lab-rule);
  text-align: left;
  vertical-align: top;
}
.lab-shell .lab-objective-table th,
.lab-shell .lab-evidence-table th { color: var(--lab-muted); font-size: .72rem; font-weight: 700; }
.lab-shell .lab-objective-table td:nth-child(2),
.lab-shell .lab-objective-table td:nth-child(3),
.lab-shell .lab-objective-table th:nth-child(2),
.lab-shell .lab-objective-table th:nth-child(3) {
  text-align: right;
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-variant-numeric: tabular-nums;
}
.lab-shell .lab-timeline { margin-top: 1.65rem; padding-top: 1.2rem; border-top: 1px solid var(--lab-rule); }
.lab-shell .lab-track { display: grid; grid-template-columns: 7.2rem minmax(0, 1fr); align-items: center; gap: .7rem; margin: .85rem 0; }
.lab-shell .lab-track-label { font-size: .82rem; font-weight: 700; }
.lab-shell .lab-track svg { display: block; width: 100%; height: auto; overflow: visible; }
.lab-shell .lab-track-caption { grid-column: 2; margin: -.55rem 0 0; color: var(--lab-muted); font-size: .72rem; }
.lab-shell .lab-state-legend { display: flex; flex-wrap: wrap; gap: .5rem 1rem; margin: .8rem 0 0 7.9rem; color: var(--lab-muted); font-size: .77rem; }
.lab-shell .lab-legend-item { display: inline-flex; align-items: center; gap: .4rem; }
.lab-shell .lab-swatch { display: inline-block; width: .7rem; height: .7rem; border: 1px solid rgba(231,229,223,.3); }
.lab-shell .lab-explanation {
  max-width: 75ch;
  margin: 1rem 0 0;
  padding: .8rem 1rem;
  background: rgba(157, 144, 255, .18);
  color: var(--lab-ink);
  font-size: .86rem;
}
.lab-shell .lab-chart-wrap { margin-top: 1.8rem; padding-top: 1.2rem; border-top: 1px solid var(--lab-rule); }
.lab-shell .lab-chart-head { display: flex; align-items: baseline; justify-content: space-between; gap: 1rem; }
.lab-shell .lab-chart-note { margin: .25rem 0 .65rem; color: var(--lab-muted); font-size: .78rem; }
.lab-shell .lab-chart { display: block; width: 100%; height: auto; }
.lab-shell .lab-evidence-details { margin-top: .75rem; font-size: .82rem; }
.lab-shell .lab-evidence-details summary { width: fit-content; cursor: pointer; font-weight: 650; text-decoration: underline; text-underline-offset: .2em; }
.lab-shell .lab-evidence-scroll { max-height: 18rem; margin-top: .6rem; overflow: auto; border-top: 1px solid var(--lab-rule); }
.lab-shell .lab-evidence-table th:not(:first-child),
.lab-shell .lab-evidence-table td:not(:first-child) { text-align: right; font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; font-variant-numeric: tabular-nums; }
.lab-shell .lab-visually-hidden {
  position: absolute !important;
  width: 1px !important;
  height: 1px !important;
  padding: 0 !important;
  margin: -1px !important;
  overflow: hidden !important;
  clip: rect(0, 0, 0, 0) !important;
  white-space: nowrap !important;
  border: 0 !important;
}
.lab-shell :focus-visible { outline: 3px solid var(--lab-copper); outline-offset: 3px; }
@media (max-width: 760px) {
  .lab-shell .lab-layout { grid-template-columns: minmax(0, 1fr); gap: 1.5rem; }
  .lab-shell .lab-track { grid-template-columns: 5.6rem minmax(0, 1fr); gap: .45rem; }
  .lab-shell .lab-track-caption { grid-column: 2; }
  .lab-shell .lab-state-legend { margin-left: 6.05rem; }
}
@media (max-width: 420px) {
  .lab-shell .lab-metric-strip { grid-template-columns: 1fr 1fr; }
  .lab-shell .lab-metric:last-child { grid-column: 1 / -1; padding-left: 0; border-top: 1px solid var(--lab-rule); border-left: 0; }
  .lab-shell .lab-track { grid-template-columns: minmax(0, 1fr); gap: .25rem; }
  .lab-shell .lab-track-caption { grid-column: 1; }
  .lab-shell .lab-state-legend { margin-left: 0; }
  .lab-shell .lab-chart-head { display: block; }
}
@media (prefers-reduced-motion: reduce) {
  .lab-shell *, .lab-shell *::before, .lab-shell *::after { scroll-behavior: auto !important; transition-duration: .01ms !important; animation-duration: .01ms !important; }
}
`;

function clamp(value, min, max, fallback) {
  const number = Number(value);
  return Number.isFinite(number) ? Math.min(max, Math.max(min, number)) : fallback;
}

function validateEvidence(evidence) {
  if (!Array.isArray(evidence)) throw new TypeError("Evidence must be an array of H/A/D score rows.");
  return evidence.map((row, index) => {
    if (!Array.isArray(row) || row.length !== 3 || !row.every(Number.isFinite)) {
      throw new TypeError(`Evidence row ${index} must contain three finite scores in H/A/D order.`);
    }
    return row;
  });
}

/** Centered mean for illustrative log scores, with truncated edges. */
export function smoothEvidence(evidence, radius = 0) {
  const rows = validateEvidence(evidence);
  if (!Number.isInteger(radius) || radius < 0 || radius > 12) throw new RangeError('Radius must be an integer from 0 to 12 bins.');
  return rows.map((_, i) => {
    const window = rows.slice(Math.max(0, i-radius), Math.min(rows.length, i+radius+1));
    return [0,1,2].map(k => window.reduce((sum, row) => sum+row[k],0)/window.length);
  });
}

function validatePenalty(penalty) {
  if (!Number.isFinite(penalty) || penalty < 0) throw new RangeError("The transition penalty must be a finite, non-negative number.");
  return penalty;
}

/** Create a deterministic 36-bin H/A/D synthetic fixture in illustrative log-evidence units. */
export function generateEvidence({ preset = "short-regain", regainLength = 3, noise = 15 } = {}) {
  const safePreset = PRESETS.includes(preset) ? preset : "short-regain";
  const safeLength = Math.round(clamp(regainLength, 1, 8, 3));
  const safeNoise = clamp(noise, 0, 100, 15);
  const rows = Array.from({ length: BIN_COUNT }, () => [0, 0, 0]);

  if (safePreset === "short-regain") {
    for (let i = 0; i < BIN_COUNT; i += 1) rows[i] = [-8, 5, -6];
    rows[7] = [6.5, 5, -5]; // A deliberately weak, one-bin raw-argmax twitch.
    for (let i = 13; i < 13 + safeLength; i += 1) rows[i] = [16.5, 5, -6];
  } else if (safePreset === "occlusion") {
    for (let i = 0; i < 12; i += 1) rows[i] = [9, -6, -5];
    for (let i = 12; i < 23; i += 1) rows[i] = [0, 0.1, -0.2];
    for (let i = 23; i < BIN_COUNT; i += 1) rows[i] = [-6, 9, -5];
  } else {
    for (let i = 0; i < 12; i += 1) rows[i] = [9, -5, -6];
    for (let i = 12; i < 21; i += 1) rows[i] = [-5, -5, 9];
    for (let i = 21; i < BIN_COUNT; i += 1) rows[i] = [-5, 9, -6];
  }

  const amplitude = (safeNoise / 100) * 3.8;
  return rows.map((row, bin) => row.map((score, state) => {
    const phase = (bin + 1) * (state + 1) * 0.91 + state * 0.73;
    const wobble = Math.sin(phase) * 0.65 + Math.cos((bin + 3) * 0.47 + state * 1.31) * 0.35;
    return score + amplitude * wobble;
  }));
}

/** Exact max-sum Viterbi decode with a fixed cost for every adjacent state change. */
export function decodeViterbi(evidence, penalty = 10) {
  const rows = validateEvidence(evidence);
  const transitionCost = validatePenalty(penalty);
  if (rows.length === 0) return { path: [], objective: 0 };

  const backpointers = Array.from({ length: rows.length }, () => [0, 0, 0]);
  let scores = [...rows[0]];
  for (let t = 1; t < rows.length; t += 1) {
    const nextScores = [0, 0, 0];
    for (let state = 0; state < 3; state += 1) {
      let bestPrevious = 0;
      let bestScore = Number.NEGATIVE_INFINITY;
      for (let previous = 0; previous < 3; previous += 1) {
        const candidate = scores[previous] - (previous === state ? 0 : transitionCost);
        if (candidate > bestScore) {
          bestScore = candidate;
          bestPrevious = previous;
        }
      }
      nextScores[state] = bestScore + rows[t][state];
      backpointers[t][state] = bestPrevious;
    }
    scores = nextScores;
  }

  let finalState = 0;
  for (let state = 1; state < 3; state += 1) {
    if (scores[state] > scores[finalState]) finalState = state;
  }
  const pathIndexes = Array(rows.length);
  pathIndexes[rows.length - 1] = finalState;
  for (let t = rows.length - 1; t > 0; t -= 1) {
    pathIndexes[t - 1] = backpointers[t][pathIndexes[t]];
  }
  const path = pathIndexes.map((index) => STATE_NAMES[index]);
  return { path, objective: scorePath(rows, path, transitionCost) };
}

/** Per-bin maximum evidence state, before transition costs are applied. */
export function argmaxPath(evidence) {
  return validateEvidence(evidence).map((row) => {
    let best = 0;
    for (let state = 1; state < 3; state += 1) if (row[state] > row[best]) best = state;
    return STATE_NAMES[best];
  });
}

/** Weighted objective: summed evidence minus penalty times the number of transitions. */
export function scorePath(evidence, path, penalty = 10) {
  const rows = validateEvidence(evidence);
  const transitionCost = validatePenalty(penalty);
  if (!Array.isArray(path) || path.length !== rows.length || path.some((state) => !STATE_NAMES.includes(state))) {
    throw new TypeError("The path must contain one H, A, or D state for each evidence row.");
  }
  let objective = 0;
  for (let t = 0; t < rows.length; t += 1) {
    objective += rows[t][STATE_NAMES.indexOf(path[t])];
    if (t > 0 && path[t] !== path[t - 1]) objective -= transitionCost;
  }
  return objective;
}

function makeElement(tag, className = "", text = undefined) {
  const element = document.createElement(tag);
  if (className) element.className = className;
  if (text !== undefined) element.textContent = text;
  return element;
}

function makeSvgElement(tag, attributes = {}) {
  const element = document.createElementNS("http://www.w3.org/2000/svg", tag);
  for (const [key, value] of Object.entries(attributes)) element.setAttribute(key, String(value));
  return element;
}

function transitionsFor(path) {
  const changes = [];
  for (let i = 1; i < path.length; i += 1) {
    if (path[i] !== path[i - 1]) changes.push({ bin: i + 1, from: path[i - 1], to: path[i] });
  }
  return changes;
}

function describeRuns(path) {
  if (path.length === 0) return "No observations.";
  const runs = [];
  let start = 0;
  for (let i = 1; i <= path.length; i += 1) {
    if (i === path.length || path[i] !== path[start]) {
      const first = start + 1;
      const last = i;
      runs.push(`${path[start]} ${first === last ? `bin ${first}` : `bins ${first}–${last}`}`);
      start = i;
    }
  }
  return runs.join("; ");
}

function formatTransitions(changes) {
  return changes.length
    ? changes.map(({ bin, from, to }) => `bin ${bin}: ${from} → ${to}`).join(" · ")
    : "No state changes";
}

function formatNumber(value) {
  const rounded = Math.abs(value) < 0.05 ? 0 : value;
  return rounded.toFixed(1);
}

function eventWindow(preset, regainLength) {
  if (preset === "short-regain") return { start: 13, end: 13 + regainLength, label: "regain" };
  if (preset === "occlusion") return { start: 12, end: 23, label: "low evidence" };
  return { start: 12, end: 21, label: "stoppage" };
}

function presetExplanation(preset) {
  if (preset === "short-regain") {
    return "A short regain pays for both the transition into it and the transition out. It survives when its accumulated evidence gain exceeds that combined cost; a weaker one-bin twitch often disappears.";
  }
  if (preset === "occlusion") {
    return "The shaded interval has nearly tied synthetic evidence. The decoder can carry the previous state through that uncertainty, then change when stronger evidence returns.";
  }
  return "This fixture gives the dead-ball state a sustained evidence lead, then a restart to the away state. The penalty smooths brief noise without preventing supported changes.";
}

function buildTimeline(path, label) {
  const svg = makeSvgElement("svg", {
    viewBox: `0 0 ${BIN_COUNT * 26} 32`,
    role: "img",
    "aria-label": `${label} timeline: ${describeRuns(path)}. One bin represents half a synthetic second.`,
    focusable: "false",
  });
  const title = makeSvgElement("title");
  title.textContent = `${label}: ${describeRuns(path)}`;
  svg.appendChild(title);
  for (let i = 0; i < path.length; i += 1) {
    svg.appendChild(makeSvgElement("rect", {
      x: i * 26 + 0.5,
      y: 1,
      width: 25,
      height: 30,
      rx: 1,
      fill: STATE_COLORS[path[i]],
      stroke: "#111116",
      "stroke-width": 1,
    }));
  }
  let runStart = 0;
  for (let i = 1; i <= path.length; i += 1) {
    if (i === path.length || path[i] !== path[runStart]) {
      const runWidth = (i - runStart) * 26;
      if (runWidth >= 42) {
        const text = makeSvgElement("text", {
          x: runStart * 26 + runWidth / 2,
          y: 16,
          fill: "#0e0e11",
          "font-family": "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace",
          "font-size": 11,
          "font-weight": 700,
          "text-anchor": "middle",
          "dominant-baseline": "middle",
          "pointer-events": "none",
        });
        text.textContent = path[runStart];
        svg.appendChild(text);
      }
      runStart = i;
    }
  }
  return svg;
}

function buildEvidenceChart(evidence, preset, regainLength) {
  const width = 936;
  const height = 224;
  const left = 42;
  const right = width - 8;
  const top = 14;
  const bottom = height - 26;
  const minValue = -16;
  const maxValue = 24;
  const plotWidth = right - left;
  const plotHeight = bottom - top;
  const xFor = (index) => left + (index / (evidence.length - 1)) * plotWidth;
  const yFor = (value) => top + ((maxValue - value) / (maxValue - minValue)) * plotHeight;
  const svg = makeSvgElement("svg", {
    viewBox: `0 0 ${width} ${height}`,
    class: "lab-chart",
    role: "img",
    "aria-label": "Synthetic H, A, and D log evidence by observation bin. Higher values are stronger. Exact values are available in the evidence table below.",
  });
  svg.appendChild(makeSvgElement("title")).textContent = "Synthetic log evidence by bin";
  const window = eventWindow(preset, regainLength);
  const x1 = left + ((window.start - 1) / evidence.length) * plotWidth;
  const x2 = left + ((window.end - 1) / evidence.length) * plotWidth;
  svg.appendChild(makeSvgElement("rect", {
    x: x1, y: top, width: Math.max(1, x2 - x1), height: plotHeight,
    fill: "#9d90ff", opacity: 0.28,
  }));
  for (const tick of [-16, -8, 0, 8, 16, 24]) {
    const y = yFor(tick);
    svg.appendChild(makeSvgElement("line", { x1: left, x2: right, y1: y, y2: y, stroke: "#34313f", "stroke-width": 1 }));
    const label = makeSvgElement("text", {
      x: left - 8, y: y + 3,
      fill: "#aaa6b5", "font-size": 10, "text-anchor": "end",
      "font-family": "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace",
    });
    label.textContent = String(tick);
    svg.appendChild(label);
  }
  for (const [stateIndex, state] of STATE_NAMES.entries()) {
    const d = evidence.map((row, i) => `${i === 0 ? "M" : "L"}${xFor(i).toFixed(2)},${yFor(row[stateIndex]).toFixed(2)}`).join(" ");
    svg.appendChild(makeSvgElement("path", {
      d, fill: "none", stroke: STATE_COLORS[state], "stroke-width": 2.5,
      "stroke-linejoin": "round", "stroke-linecap": "round",
    }));
  }
  const firstLabel = makeSvgElement("text", { x: left, y: height - 5, fill: "#aaa6b5", "font-size": 10 });
  firstLabel.textContent = "bin 1";
  svg.appendChild(firstLabel);
  const finalLabel = makeSvgElement("text", {
    x: right, y: height - 5, fill: "#aaa6b5", "font-size": 10, "text-anchor": "end",
  });
  finalLabel.textContent = `bin ${evidence.length}`;
  svg.appendChild(finalLabel);
  return svg;
}

function makeRangeControl({ id, label, min, max, value, help }) {
  const wrapper = makeElement("div", "lab-range-control");
  const head = makeElement("div", "lab-range-head");
  const labelElement = makeElement("label", "", label);
  labelElement.htmlFor = id;
  const output = makeElement("output", "", String(value));
  output.htmlFor = id;
  head.append(labelElement, output);
  const input = makeElement("input", "lab-range");
  input.type = "range";
  input.id = id;
  input.min = String(min);
  input.max = String(max);
  input.step = "1";
  input.value = String(value);
  const helpText = makeElement("p", "lab-help", help);
  wrapper.append(head, input, helpText);
  return { wrapper, input, output };
}

function renderEvidenceTable(tbody, evidence) {
  const fragment = document.createDocumentFragment();
  evidence.forEach((row, index) => {
    const tr = makeElement("tr");
    tr.append(
      makeElement("th", "", String(index + 1)),
      makeElement("td", "", row[0].toFixed(2)),
      makeElement("td", "", row[1].toFixed(2)),
      makeElement("td", "", row[2].toFixed(2)),
    );
    fragment.appendChild(tr);
  });
  tbody.replaceChildren(fragment);
}

/** Mount a self-contained synthetic decoder lab into the provided root element. */
export function mountSandbox(rootElement) {
  if (!rootElement || typeof rootElement.append !== "function") {
    throw new TypeError("mountSandbox needs a DOM root element.");
  }

  const instanceId = ++nextInstanceId;
  let state = { preset: "short-regain", penalty: 10, regainLength: 3, noise: 15, radius: 0 };
  let renderTimer = null;
  const style = makeElement("style");
  style.textContent = LAB_STYLES;
  const shell = makeElement("section", "lab-shell");
  shell.setAttribute("aria-labelledby", `lab-heading-${instanceId}`);

  const header = makeElement("header", "lab-header");
  header.append(
    makeElement("p", "lab-kicker", "Decoder lab / synthetic fixture"),
  );
  const heading = makeElement("h2", "lab-heading", "When should a state change count?");
  heading.id = `lab-heading-${instanceId}`;
  header.appendChild(heading);
  header.appendChild(makeElement(
    "p", "lab-lede",
    "A small, deterministic H/A/D example makes the transition penalty visible. Compare each bin’s strongest emission with the globally optimal path, then change the evidence or switching cost.",
  ));
  header.appendChild(makeElement(
    "p", "lab-disclaimer",
    "Illustrative decoder, not the fitted model. Changing these controls does not modify frozen submission model or provide accuracy scores.",
  ));

  const layout = makeElement("div", "lab-layout");
  const controls = makeElement("div", "lab-controls");
  controls.appendChild(makeElement("p", "lab-section-label", "Set the fixture"));
  const presetFieldset = makeElement("fieldset", "lab-presets");
  presetFieldset.appendChild(makeElement("legend", "lab-section-label", "Choose a scenario"));
  const presetButtons = new Map();
  const presetLabels = new Map([
    ["short-regain", "Short regain"],
    ["occlusion", "Occlusion"],
    ["stoppage", "Stoppage"],
  ]);
  for (const preset of PRESETS) {
    const button = makeElement("button", "lab-button", presetLabels.get(preset));
    button.type = "button";
    button.setAttribute("aria-pressed", preset === state.preset ? "true" : "false");
    button.addEventListener("click", () => {
      state.preset = preset;
      presetButtons.forEach((item, key) => item.setAttribute("aria-pressed", key === state.preset ? "true" : "false"));
      regainInput.disabled = state.preset !== "short-regain";
      render();
      status.textContent = `${presetLabels.get(state.preset)} fixture updated.`;
    });
    presetButtons.set(preset, button);
    presetFieldset.appendChild(button);
  }
  controls.appendChild(presetFieldset);

  const penaltyControl = makeRangeControl({
    id: `lab-penalty-${instanceId}`,
    label: "Transition penalty",
    min: 0, max: 50, value: state.penalty,
    help: "Cost for each adjacent state change. V2’s submitted setting is 10.",
  });
  const radiusControl = makeRangeControl({id: `lab-radius-${instanceId}`, label: "Emission radius", min: 0, max: 6, value: state.radius, help: "Centered averaging radius in half-second fixture bins. Zero preserves raw evidence; this is not a model setting change."});
  const regainControl = makeRangeControl({
    id: `lab-regain-${instanceId}`,
    label: "Short regain length",
    min: 1, max: 8, value: state.regainLength,
    help: "Bins in the strong regain; used by the Short regain preset.",
  });
  const noiseControl = makeRangeControl({
    id: `lab-noise-${instanceId}`,
    label: "Noisy observations",
    min: 0, max: 100, value: state.noise,
    help: "Deterministic wobble added to each synthetic H/A/D score.",
  });
  const penaltyInput = penaltyControl.input;
  const regainInput = regainControl.input;
  const noiseInput = noiseControl.input;
  const penaltyOutput = penaltyControl.output;
  const regainOutput = regainControl.output;
  const noiseOutput = noiseControl.output;
  regainInput.disabled = false;
  controls.append(penaltyControl.wrapper, radiusControl.wrapper, regainControl.wrapper, noiseControl.wrapper);
  const resetButton = makeElement("button", "lab-button lab-button-reset", "Reset lab");
  resetButton.type = "button";
  controls.appendChild(resetButton);

  const results = makeElement("div", "lab-results");
  const status = makeElement("p", "lab-status");
  status.setAttribute("role", "status");
  status.setAttribute("aria-live", "polite");
  status.setAttribute("aria-atomic", "true");
  status.textContent = "Synthetic fixture ready.";
  results.appendChild(status);
  const metricStrip = makeElement("div", "lab-metric-strip");
  const metricBins = makeElement("div", "lab-metric");
  metricBins.append(makeElement("span", "lab-metric-label", "Observations"));
  metricBins.append(makeElement("strong", "lab-metric-value", `${BIN_COUNT} × ${BIN_SECONDS.toFixed(1)} s`));
  const metricRaw = makeElement("div", "lab-metric");
  metricRaw.append(makeElement("span", "lab-metric-label", "Raw changes"));
  const rawCount = makeElement("strong", "lab-metric-value", "0");
  metricRaw.appendChild(rawCount);
  const metricDecoded = makeElement("div", "lab-metric");
  metricDecoded.append(makeElement("span", "lab-metric-label", "Viterbi changes"));
  const decodedCount = makeElement("strong", "lab-metric-value", "0");
  metricDecoded.appendChild(decodedCount);
  metricStrip.append(metricBins, metricRaw, metricDecoded);
  results.appendChild(metricStrip);

  const objectiveSection = makeElement("section", "lab-objective");
  const objectiveHeading = makeElement("h3", "lab-subheading", "Weighted path objective");
  objectiveSection.appendChild(objectiveHeading);
  objectiveSection.appendChild(makeElement(
    "p", "lab-formula",
    "Σ log evidence − penalty × state changes · higher is better for this fixture",
  ));
  const objectiveTable = makeElement("table", "lab-objective-table");
  const objectiveCaption = makeElement("caption", "lab-visually-hidden", "Synthetic path objective at the selected transition penalty");
  objectiveTable.appendChild(objectiveCaption);
  const objectiveHead = makeElement("thead");
  const objectiveHeaderRow = makeElement("tr");
  for (const name of ["Path", "Changes", "Objective"]) objectiveHeaderRow.appendChild(makeElement("th", "", name));
  objectiveHead.appendChild(objectiveHeaderRow);
  objectiveTable.appendChild(objectiveHead);
  const objectiveBody = makeElement("tbody");
  const rawObjectiveRow = makeElement("tr");
  const decodedObjectiveRow = makeElement("tr");
  const rawObjectiveCell = makeElement("td", "", "Raw argmax");
  const rawTransitionCell = makeElement("td", "", "0");
  const rawScoreCell = makeElement("td", "", "0.0");
  rawObjectiveRow.append(rawObjectiveCell, rawTransitionCell, rawScoreCell);
  const decodedObjectiveCell = makeElement("td", "", "Viterbi");
  const decodedTransitionCell = makeElement("td", "", "0");
  const decodedScoreCell = makeElement("td", "", "0.0");
  decodedObjectiveRow.append(decodedObjectiveCell, decodedTransitionCell, decodedScoreCell);
  objectiveBody.append(rawObjectiveRow, decodedObjectiveRow);
  objectiveTable.appendChild(objectiveBody);
  objectiveSection.appendChild(objectiveTable);
  results.appendChild(objectiveSection);

  const timelineSection = makeElement("section", "lab-timeline");
  timelineSection.appendChild(makeElement("h3", "lab-subheading", "Two ways through the same evidence"));
  const rawTrack = makeElement("div", "lab-track");
  rawTrack.appendChild(makeElement("span", "lab-track-label", "Raw argmax"));
  const rawTrackSvg = makeElement("div", "lab-track-svg");
  rawTrack.appendChild(rawTrackSvg);
  const rawTrackCaption = makeElement("p", "lab-track-caption");
  rawTrack.appendChild(rawTrackCaption);
  const decodedTrack = makeElement("div", "lab-track");
  decodedTrack.appendChild(makeElement("span", "lab-track-label", "Viterbi path"));
  const decodedTrackSvg = makeElement("div", "lab-track-svg");
  decodedTrack.appendChild(decodedTrackSvg);
  const decodedTrackCaption = makeElement("p", "lab-track-caption");
  decodedTrack.appendChild(decodedTrackCaption);
  timelineSection.append(rawTrack, decodedTrack);
  const legend = makeElement("div", "lab-state-legend");
  for (const [stateName, stateLabel] of [["H", "Home possession"], ["A", "Away possession"], ["D", "Dead ball"]]) {
    const item = makeElement("span", "lab-legend-item");
    const swatch = makeElement("span", "lab-swatch");
    swatch.style.backgroundColor = STATE_COLORS[stateName];
    swatch.setAttribute("aria-hidden", "true");
    item.append(swatch, makeElement("span", "", `${stateName} · ${stateLabel}`));
    legend.appendChild(item);
  }
  timelineSection.appendChild(legend);
  const explanation = makeElement("p", "lab-explanation");
  timelineSection.appendChild(explanation);
  results.appendChild(timelineSection);

  const chartSection = makeElement("section", "lab-chart-wrap");
  const chartHead = makeElement("div", "lab-chart-head");
  chartHead.appendChild(makeElement("h3", "lab-subheading", "Emission log evidence"));
  const chartLegend = makeElement("div", "lab-legend-item");
  chartLegend.appendChild(makeElement("span", "", "H / A / D score"));
  chartHead.appendChild(chartLegend);
  chartSection.append(chartHead, makeElement("p", "lab-chart-note", "Illustrative log-evidence units by synthetic half-second bin. Higher is stronger; the highlighted interval is the preset event."));
  const chartContainer = makeElement("div", "lab-chart-container");
  chartSection.appendChild(chartContainer);
  const evidenceDetails = makeElement("details", "lab-evidence-details");
  evidenceDetails.appendChild(makeElement("summary", "", "Inspect exact evidence values"));
  const evidenceScroll = makeElement("div", "lab-evidence-scroll");
  const evidenceTable = makeElement("table", "lab-evidence-table");
  evidenceTable.appendChild(makeElement("caption", "lab-visually-hidden", "Synthetic evidence values for each observation bin"));
  const evidenceHeader = makeElement("thead");
  const evidenceHeaderRow = makeElement("tr");
  for (const name of ["Bin", "H", "A", "D"]) evidenceHeaderRow.appendChild(makeElement("th", "", name));
  evidenceHeader.appendChild(evidenceHeaderRow);
  evidenceTable.appendChild(evidenceHeader);
  const evidenceBody = makeElement("tbody");
  evidenceTable.appendChild(evidenceBody);
  evidenceScroll.appendChild(evidenceTable);
  evidenceDetails.appendChild(evidenceScroll);
  chartSection.appendChild(evidenceDetails);
  results.appendChild(chartSection);

  layout.append(controls, results);
  shell.append(header, layout);
  rootElement.append(style, shell);

  function render() {
    const evidence = smoothEvidence(generateEvidence(state), state.radius);
    const rawPath = argmaxPath(evidence);
    const decoded = decodeViterbi(evidence, state.penalty);
    const rawChanges = transitionsFor(rawPath);
    const decodedChanges = transitionsFor(decoded.path);
    const rawObjective = scorePath(evidence, rawPath, state.penalty);
    const decodedObjective = decoded.objective;

    rawCount.textContent = String(rawChanges.length);
    decodedCount.textContent = String(decodedChanges.length);
    rawTransitionCell.textContent = String(rawChanges.length);
    decodedTransitionCell.textContent = String(decodedChanges.length);
    rawScoreCell.textContent = formatNumber(rawObjective);
    decodedScoreCell.textContent = formatNumber(decodedObjective);
    rawScoreCell.setAttribute("aria-label", `Raw objective ${formatNumber(rawObjective)}`);
    decodedScoreCell.setAttribute("aria-label", `Viterbi objective ${formatNumber(decodedObjective)}`);

    rawTrackSvg.replaceChildren(buildTimeline(rawPath, "Raw argmax"));
    decodedTrackSvg.replaceChildren(buildTimeline(decoded.path, "Viterbi"));
    rawTrackCaption.textContent = `Transitions: ${formatTransitions(rawChanges)}. Objective ${formatNumber(rawObjective)}.`;
    decodedTrackCaption.textContent = `Transitions: ${formatTransitions(decodedChanges)}. Objective ${formatNumber(decodedObjective)}.`;
    explanation.textContent = presetExplanation(state.preset);
    chartContainer.replaceChildren(buildEvidenceChart(evidence, state.preset, state.regainLength));
    renderEvidenceTable(evidenceBody, evidence);
  }

  function scheduleRender() {
    if (renderTimer !== null) clearTimeout(renderTimer);
    renderTimer = setTimeout(() => {
      renderTimer = null;
      render();
      status.textContent = `Results updated. Raw path: ${transitionsFor(argmaxPath(smoothEvidence(generateEvidence(state), state.radius))).length} changes; Viterbi path: ${transitionsFor(decodeViterbi(smoothEvidence(generateEvidence(state), state.radius), state.penalty).path).length} changes.`;
    }, 110);
  }

  radiusControl.input.addEventListener("input", () => { state.radius = Number(radiusControl.input.value); radiusControl.output.textContent = String(state.radius); scheduleRender(); });
  penaltyInput.addEventListener("input", () => {
    state.penalty = Number(penaltyInput.value);
    penaltyOutput.textContent = String(state.penalty);
    scheduleRender();
  });
  regainInput.addEventListener("input", () => {
    state.regainLength = Number(regainInput.value);
    regainOutput.textContent = String(state.regainLength);
    scheduleRender();
  });
  noiseInput.addEventListener("input", () => {
    state.noise = Number(noiseInput.value);
    noiseOutput.textContent = `${state.noise}%`;
    scheduleRender();
  });
  noiseOutput.textContent = `${state.noise}%`;
  resetButton.addEventListener("click", () => {
    if (renderTimer !== null) clearTimeout(renderTimer);
    renderTimer = null;
    state = { preset: "short-regain", penalty: 10, regainLength: 3, noise: 15, radius: 0 };
    radiusControl.input.value = "0"; radiusControl.output.textContent = "0";
    penaltyInput.value = String(state.penalty);
    regainInput.value = String(state.regainLength);
    noiseInput.value = String(state.noise);
    penaltyOutput.textContent = String(state.penalty);
    regainOutput.textContent = String(state.regainLength);
    noiseOutput.textContent = `${state.noise}%`;
    regainInput.disabled = false;
    presetButtons.forEach((button, preset) => button.setAttribute("aria-pressed", preset === state.preset ? "true" : "false"));
    render();
    status.textContent = "Lab reset to the illustrative V2 reference penalty of 10.";
  });

  render();
  return () => {
    if (renderTimer !== null) clearTimeout(renderTimer);
    style.remove();
    shell.remove();
  };
}
