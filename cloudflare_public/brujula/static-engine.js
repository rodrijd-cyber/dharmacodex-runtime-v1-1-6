(function () {
  const lookup = window.BRUJULA_STATIC_LOOKUP;
  const MASTER_NUMBERS = new Set([11, 22, 33]);
  const FOCUS_CODES = {
    "Propósito y dirección": "PROPOSITO",
    "Relaciones y vínculos": "RELACIONES",
    "Trabajo, dinero y vocación": "TRABAJO_DINERO",
    "Bienestar y energía": "BIENESTAR",
    "Momento de cambio/transición": "CAMBIO"
  };
  const DISCLAIMER = "Esta lectura es simbólica y no sustituye tu criterio ni acompañamiento profesional.";
  const REQUIRED_READING_FIELDS = [
    "coordinate_label",
    "central_reading",
    "numerology_signal",
    "matrix_signal",
    "astrology_signal",
    "human_design_signal",
    "integration_question",
    "brief_practice",
    "camino_1_bridge"
  ];

  function parseBirthDate(value) {
    const raw = String(value || "").trim();
    const match = raw.match(/^(\d{4})-(\d{2})-(\d{2})$/);
    if (!match) return null;

    const year = Number(match[1]);
    const month = Number(match[2]);
    const day = Number(match[3]);
    const parsed = new Date(Date.UTC(year, month - 1, day));
    if (
      parsed.getUTCFullYear() !== year ||
      parsed.getUTCMonth() !== month - 1 ||
      parsed.getUTCDate() !== day
    ) {
      return null;
    }
    return raw;
  }

  function reducePreservingMaster(value) {
    let current = value;
    while (current > 9 && !MASTER_NUMBERS.has(current)) {
      current = String(current).split("").reduce((sum, digit) => sum + Number(digit), 0);
    }
    return current;
  }

  function lifePathFromDate(value) {
    const parsed = parseBirthDate(value);
    if (!parsed) {
      throw new Error("INVALID_BIRTH_DATE");
    }
    const total = parsed.replaceAll("-", "").split("").reduce((sum, digit) => sum + Number(digit), 0);
    return reducePreservingMaster(total);
  }

  function cleanName(value) {
    return String(value || "").trim();
  }

  function requireReadingFields(entry) {
    const missing = REQUIRED_READING_FIELDS.filter(field => !String(entry[field] || "").trim());
    if (missing.length > 0) {
      throw new Error("STATIC_LOOKUP_ROW_INCOMPLETE");
    }
  }

  function buildPublicViewModel(input) {
    if (!lookup || !lookup.readings) {
      throw new Error("STATIC_LOOKUP_UNAVAILABLE");
    }

    const focus = String(input.focus || "").trim();
    if (!FOCUS_CODES[focus]) {
      throw new Error("INVALID_CURRENT_FOCUS");
    }

    const lifePath = lifePathFromDate(input.birthDate);
    const key = `${lifePath}::${focus}`;
    const entry = lookup.readings[key];
    if (!entry) {
      throw new Error("STATIC_LOOKUP_KEY_MISSING");
    }

    const name = cleanName(input.name);
    requireReadingFields(entry);

    const centralReading = entry.central_reading;
    const numerologySignal = entry.numerology_signal;
    const matrixSignal = entry.matrix_signal;
    const astrologySignal = entry.astrology_signal;
    const humanDesignSignal = entry.human_design_signal;
    const briefPractice = entry.brief_practice;
    const caminoBridge = entry.camino_1_bridge;

    return {
      view_model_version: "0.5.1-static-content-matrix",
      mode_label: "Brújula inicial",
      current_focus: focus,
      life_path: String(lifePath),
      key,
      coordinate: `DCX-${FOCUS_CODES[focus]}-${lifePath}`,
      coordinate_label: entry.coordinate_label,
      central_reading: centralReading,
      central_idea: centralReading,
      numerology_signal: numerologySignal,
      matrix_signal: matrixSignal,
      astrology_signal: astrologySignal,
      human_design_signal: humanDesignSignal,
      integration_question: entry.integration_question,
      brief_practice: briefPractice,
      practice: briefPractice,
      contextual_signals: [
        {
          system_label: "Numerología",
          signal_label: "Coordenada numerológica",
          short_summary: numerologySignal
        },
        {
          system_label: "Matriz del Destino",
          signal_label: "Huella simbólica",
          short_summary: matrixSignal
        },
        {
          system_label: "Astrología",
          signal_label: "Clima simbólico",
          short_summary: astrologySignal
        },
        {
          system_label: "Human Design",
          signal_label: "Pausa y presión",
          short_summary: humanDesignSignal
        }
      ],
      camino_1_bridge: caminoBridge,
      camino_1_invitation: caminoBridge,
      disclaimer: DISCLAIMER,
      greeting: name ? `${name}, esta es tu orientación inicial.` : ""
    };
  }

  window.BRUJULA_STATIC_ENGINE = {
    buildPublicViewModel,
    lifePathFromDate,
    parseBirthDate,
    source: {
      combinations: lookup && lookup.readings ? Object.keys(lookup.readings).length : 0
    }
  };
})();
