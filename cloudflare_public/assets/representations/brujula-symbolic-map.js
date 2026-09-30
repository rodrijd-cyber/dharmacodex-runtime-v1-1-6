(function () {
  const SVG_NS = "http://www.w3.org/2000/svg";
  function clean(value) { return String(value || "").trim(); }
  function buildBrujulaSymbolicMap(viewModel) {
    const source = viewModel || {};
    return {
      version: "0.1.2-public-static",
      coordinate: clean(source.coordinate_label || source.coordinate),
      focus: clean(source.current_focus),
      signals: [
        { token: "numerology", name: "Numerología", metaphor: "Ritmo", text: clean(source.numerology_signal) },
        { token: "astrology", name: "Astrología", metaphor: "Clima", text: clean(source.astrology_signal) },
        { token: "humanDesignProtected", name: "Human Design", metaphor: "Pausa", text: clean(source.human_design_signal) },
        { token: "matrix", name: "Matriz del Destino", metaphor: "Huella", text: clean(source.matrix_signal) }
      ]
    };
  }
  function svgElement(tag, attributes) {
    const node = document.createElementNS(SVG_NS, tag);
    Object.entries(attributes || {}).forEach(([key, value]) => node.setAttribute(key, value));
    return node;
  }
  function addGeometry(svg) {
    svg.appendChild(svgElement("circle", { class: "symbolic-map-orbit orbit-outer", cx: "50", cy: "50", r: "37" }));
    svg.appendChild(svgElement("circle", { class: "symbolic-map-orbit orbit-middle", cx: "50", cy: "50", r: "29" }));
    svg.appendChild(svgElement("circle", { class: "symbolic-map-orbit orbit-inner", cx: "50", cy: "50", r: "17" }));
    svg.appendChild(svgElement("path", { class: "symbolic-map-arc arc-one", d: "M 17 38 A 36 36 0 0 1 45 14" }));
    svg.appendChild(svgElement("path", { class: "symbolic-map-arc arc-two", d: "M 55 14 A 36 36 0 0 1 83 38" }));
    svg.appendChild(svgElement("path", { class: "symbolic-map-arc arc-three", d: "M 83 62 A 36 36 0 0 1 55 86" }));
    svg.appendChild(svgElement("path", { class: "symbolic-map-arc arc-four", d: "M 45 86 A 36 36 0 0 1 17 62" }));
    [[50, 13], [87, 50], [50, 87], [13, 50]].forEach(([x, y]) => {
      svg.appendChild(svgElement("line", { class: "symbolic-map-line", x1: String(x), y1: String(y), x2: "50", y2: "50" }));
      svg.appendChild(svgElement("circle", { class: "symbolic-map-node-point", cx: String(x), cy: String(y), r: "2.1" }));
    });
    svg.appendChild(svgElement("circle", { class: "symbolic-map-axis", cx: "50", cy: "50", r: "5.5" }));
    svg.appendChild(svgElement("circle", { class: "symbolic-map-point observation-point", cx: "50", cy: "50", r: "2.3" }));
  }
  function makeLabel(signal, zone) {
    const label = document.createElement("article");
    label.className = `symbolic-map-label symbolic-map-label-${zone}`;
    label.setAttribute("aria-label", `${signal.name}: ${signal.metaphor}`);
    label.appendChild(Object.assign(document.createElement("span"), { className: "symbolic-map-label-index", textContent: `0${zone === "north" ? 1 : zone === "east" ? 2 : zone === "south" ? 3 : 4}` }));
    label.appendChild(Object.assign(document.createElement("span"), { className: "symbolic-map-node-label", textContent: signal.name }));
    label.appendChild(Object.assign(document.createElement("strong"), { className: "symbolic-map-node-text", textContent: signal.metaphor }));
    return label;
  }
  function renderBrujulaSymbolicMap(container, viewModel) {
    if (!container) return;
    const map = buildBrujulaSymbolicMap(viewModel);
    const byToken = Object.fromEntries(map.signals.map(signal => [signal.token, signal]));
    container.replaceChildren();
    const visual = document.createElement("div");
    visual.className = "symbolic-map-visual";
    visual.setAttribute("role", "group");
    visual.setAttribute("aria-label", `Mapa simbólico de ${map.focus}. La coordenada se observa desde cuatro señales.`);
    const north = makeLabel(byToken.numerology, "north");
    const east = makeLabel(byToken.astrology, "east");
    const south = makeLabel(byToken.humanDesignProtected, "south");
    const west = makeLabel(byToken.matrix, "west");
    const geometry = document.createElement("div");
    geometry.className = "symbolic-map-geometry";
    geometry.setAttribute("aria-hidden", "true");
    const svg = svgElement("svg", { viewBox: "0 0 100 100", focusable: "false" });
    addGeometry(svg);
    geometry.appendChild(svg);
    const center = document.createElement("div");
    center.className = "symbolic-map-center";
    center.appendChild(Object.assign(document.createElement("span"), { className: "symbolic-map-kicker", textContent: "Coordenada" }));
    center.appendChild(Object.assign(document.createElement("strong"), { textContent: map.coordinate || "Punto de partida" }));
    center.appendChild(Object.assign(document.createElement("span"), { className: "symbolic-map-focus", textContent: map.focus }));
    const observation = document.createElement("div");
    observation.className = "symbolic-map-observation";
    observation.appendChild(Object.assign(document.createElement("span"), { className: "symbolic-map-kicker", textContent: "Cierre" }));
    observation.appendChild(Object.assign(document.createElement("strong"), { textContent: "Punto de observación" }));
    visual.append(north, west, geometry, center, east, south, observation);
    container.appendChild(visual);
  }
  window.DHARMACODEX_BRUJULA_SYMBOLIC_MAP = { buildBrujulaSymbolicMap, renderBrujulaSymbolicMap };
})();
