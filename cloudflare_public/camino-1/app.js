const lookup = window.BRUJULA_STATIC_LOOKUP;

const elements = {
  reading: document.querySelector("#camino-reading"),
  empty: document.querySelector("#camino-empty"),
  origin: document.querySelector("#camino-origin"),
  focus: document.querySelector("#camino-focus"),
  coordinate: document.querySelector("#camino-coordinate"),
  bridge: document.querySelector("#camino-bridge"),
  question: document.querySelector("#camino-question"),
  practice: document.querySelector("#camino-practice"),
  selector: document.querySelector("#camino-focus-selector"),
  returnLink: document.querySelector("#focus-return-link")
};

const slugToFocus = {
  "proposito-direccion": "Propósito y dirección",
  "relaciones-vinculos": "Relaciones y vínculos",
  "trabajo-dinero-vocacion": "Trabajo, dinero y vocación",
  "bienestar-energia": "Bienestar y energía",
  "momento-cambio-transicion": "Momento de cambio/transición"
};

function text(node, value) {
  if (node) node.textContent = String(value || "").trim();
}

function approvedFocus(value) {
  return lookup && lookup.focuses && lookup.focuses.includes(value);
}

function readingFromParams() {
  if (!lookup || !lookup.readings) return null;

  const params = new URLSearchParams(window.location.search);
  const context = String(params.get("c") || "").trim();
  const match = context.match(/^(1|2|3|4|5|6|7|8|9|11|22|33)-(.+)$/);
  if (!match) return null;

  const lifePath = match[1];
  const focus = slugToFocus[match[2]];
  const key = focus ? `${lifePath}::${focus}` : "";

  if (!key || !lookup.readings[key]) return null;
  const entry = lookup.readings[key];
  if (!approvedFocus(entry.focus)) return null;

  return entry;
}

function updateReturnLink() {
  if (!elements.selector || !elements.returnLink) return;
  const params = new URLSearchParams();
  params.set("focus", elements.selector.value);
  elements.returnLink.href = `../brujula/index.html?${params.toString()}#input-flow`;
}

function renderReading(entry) {
  text(elements.origin, `Vienes de una Brújula sobre ${entry.focus}.`);
  text(elements.focus, entry.focus);
  text(elements.coordinate, entry.coordinate_label);
  text(elements.bridge, entry.camino_1_bridge);
  text(elements.question, entry.integration_question);
  text(elements.practice, entry.brief_practice);
  if (elements.reading) elements.reading.hidden = false;
  if (elements.empty) elements.empty.hidden = true;
}

function renderEmpty() {
  if (elements.reading) elements.reading.hidden = true;
  if (elements.empty) elements.empty.hidden = false;
  updateReturnLink();
}

if (elements.selector) {
  elements.selector.addEventListener("change", updateReturnLink);
}

const entry = readingFromParams();
if (entry) {
  renderReading(entry);
} else {
  renderEmpty();
}
