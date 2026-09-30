const viewModels = window.BRUJULA_PUBLIC_VIEW_MODELS;
const staticEngine = window.BRUJULA_STATIC_ENGINE;

const elements = {
  mode: document.querySelector("#result-mode"),
  title: document.querySelector("#result-title"),
  focus: document.querySelector("#result-focus"),
  coordinate: document.querySelector("#result-coordinate"),
  central: document.querySelector("#result-central"),
  question: document.querySelector("#result-question"),
  practice: document.querySelector("#result-practice"),
  note: document.querySelector("#availability-note"),
  grid: document.querySelector("#signal-grid"),
  camino: document.querySelector("#camino-copy"),
  disclaimer: document.querySelector("#result-disclaimer"),
  caminoLink: document.querySelector("#camino-link"),
  confirmFocus: document.querySelector("#confirm-focus"),
  confirmMode: document.querySelector("#confirm-mode"),
  greeting: document.querySelector("#result-greeting"),
  formError: document.querySelector("#form-error"),
  inputName: document.querySelector("#brujula-name"),
  inputFocus: document.querySelector("#brujula-focus"),
  inputBirthDate: document.querySelector("#brujula-birth-date"),
  buttons: Array.from(document.querySelectorAll("[data-state]"))
};

const focusSlugs = {
  "Propósito y dirección": "proposito-direccion",
  "Relaciones y vínculos": "relaciones-vinculos",
  "Trabajo, dinero y vocación": "trabajo-dinero-vocacion",
  "Bienestar y energía": "bienestar-energia",
  "Momento de cambio/transición": "momento-cambio-transicion"
};

function text(node, value) {
  if (node) node.textContent = String(value || "").trim();
}

function makeNode(tag, className, value) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (value) text(node, value);
  return node;
}

function renderSignal(signal) {
  const card = makeNode("article", "signal-card");
  card.appendChild(makeNode("span", "system", signal.system_label));
  card.appendChild(makeNode("h4", "", signal.signal_label));

  if (signal.optional_keyword) {
    card.appendChild(makeNode("span", "keyword", signal.optional_keyword));
  }

  card.appendChild(makeNode("p", "", signal.short_summary));

  if (signal.disclaimer) {
    card.appendChild(makeNode("p", "signal-disclaimer", signal.disclaimer));
  }

  return card;
}

function inputPayload() {
  return {
    name: elements.inputName ? elements.inputName.value : "",
    focus: elements.inputFocus ? elements.inputFocus.value : "",
    birthDate: elements.inputBirthDate ? elements.inputBirthDate.value : ""
  };
}

function applyFocusFromQuery() {
  if (!elements.inputFocus) return;
  const focus = new URLSearchParams(window.location.search).get("focus");
  if (!focus) return;
  const option = Array.from(elements.inputFocus.options).find(item => item.value === focus);
  if (option) {
    elements.inputFocus.value = focus;
    text(elements.confirmFocus, focus);
  }
}

function setError(message) {
  text(elements.formError, message);
  if (elements.formError) elements.formError.hidden = !message;
}

function renderData(data, title) {
  text(elements.mode, data.mode_label);
  text(elements.title, title);
  text(elements.focus, data.current_focus);
  text(elements.coordinate, data.coordinate_label || data.coordinate);
  text(elements.central, data.central_reading || data.central_idea);
  text(elements.question, data.integration_question);
  text(elements.practice, data.brief_practice || data.practice);
  text(elements.camino, data.camino_1_bridge || data.camino_1_invitation);
  text(elements.disclaimer, data.disclaimer);
  text(elements.confirmFocus, data.current_focus);
  text(elements.confirmMode, data.mode_label);
  text(elements.greeting, data.greeting || "");
  if (elements.greeting) elements.greeting.hidden = !data.greeting;

  if (elements.caminoLink) {
    const params = new URLSearchParams();
    const focusSlug = focusSlugs[data.current_focus];
    if (data.life_path && focusSlug) params.set("c", `${data.life_path}-${focusSlug}`);
    elements.caminoLink.href = `../camino-1/index.html${params.toString() ? `?${params.toString()}` : ""}`;
  }

  if (data.availability_note) {
    text(elements.note, data.availability_note);
    if (elements.note) elements.note.hidden = false;
  } else {
    text(elements.note, "");
    if (elements.note) elements.note.hidden = true;
  }

  elements.grid.replaceChildren();
  data.contextual_signals
    .filter(signal => signal && signal.system_label && signal.signal_label && signal.short_summary)
    .forEach(signal => elements.grid.appendChild(renderSignal(signal)));
}

function renderState(stateName) {
  const data = viewModels[stateName] || viewModels.initial;
  const titleByState = {
    initial: "Tu orientación inicial",
    full: "Tu orientación con contexto",
    failclosed: "Tu orientación disponible"
  };
  renderData(data, titleByState[stateName]);

  elements.buttons.forEach(button => {
    button.classList.toggle("is-active", button.dataset.state === stateName);
  });
}

function renderStaticInputResult() {
  if (!staticEngine || !elements.inputFocus || !elements.inputBirthDate) {
    renderState("initial");
    return true;
  }
  try {
    const data = staticEngine.buildPublicViewModel(inputPayload());
    setError("");
    renderData(data, "Esta Brújula no intenta explicarlo todo.");
    return true;
  } catch (error) {
    const message = error && error.message === "INVALID_BIRTH_DATE"
      ? "Revisa la fecha de nacimiento para abrir una Brújula inicial."
      : "No pude abrir una lectura con esos datos. Revisa el foco y la fecha.";
    setError(message);
    return false;
  }
}

function scrollToResult() {
  const target = document.querySelector("#resultado");
  if (!target) return;

  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  target.scrollIntoView({ behavior: reduceMotion ? "auto" : "smooth", block: "start" });
}

document.querySelectorAll("[data-state]").forEach(control => {
  control.addEventListener("click", () => {
    renderState(control.dataset.state);
    if (control.classList.contains("state-button")) return;
    scrollToResult();
  });
});

document.querySelectorAll("[data-jump-result]").forEach(control => {
  control.addEventListener("click", () => {
    if (renderStaticInputResult()) scrollToResult();
  });
});

if (elements.inputFocus) {
  elements.inputFocus.addEventListener("change", () => {
    text(elements.confirmFocus, elements.inputFocus.value);
  });
}

applyFocusFromQuery();

if (staticEngine && elements.inputFocus && elements.inputBirthDate) {
  renderStaticInputResult();
} else {
  renderState("initial");
}
