"use strict";

const state = {
  lemmas: [], lemmaByKey: new Map(), ann: {}, tags: [], tokensTotal: 0,
  lemma: null, occurrence: 0, doc: null, tokenDetails: new Map(),
  form: { lemma: "", pos: "", ligre_lemma: "", note: "" }, ligre: [], busy: false,
};
const STORAGE_KEY = "missing-lemma-viewer:last-lemma";

// ---------- helpers ----------
function h(tag, attributes = {}, ...children) {
  const element = document.createElement(tag);
  for (const [name, value] of Object.entries(attributes)) {
    if (value === null || value === undefined || value === false) continue;
    if (name === "class") element.className = value;
    else if (name.startsWith("on")) element.addEventListener(name.slice(2), value);
    else if (name === "dataset") Object.assign(element.dataset, value);
    else element.setAttribute(name, value === true ? "" : value);
  }
  for (const child of children.flat()) {
    if (child === null || child === undefined || child === false) continue;
    element.append(child instanceof Node ? child : String(child));
  }
  return element;
}

function fill(element, ...children) {
  element.replaceChildren(...children.flat().filter((child) => child !== null && child !== undefined && child !== false));
}

async function api(path, body) {
  const options = body === undefined ? {} : {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
  };
  const response = await fetch(path, options);
  const payload = await response.json();
  if (!response.ok) throw new Error(payload.error || response.statusText);
  return payload;
}

let toastTimer = null;
function toast(message, isError = false) {
  const element = document.getElementById("toast");
  element.textContent = message;
  element.className = isError ? "toast error" : "toast";
  element.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { element.hidden = true; }, isError ? 6000 : 2200);
}

function remember(key) {
  try { localStorage.setItem(STORAGE_KEY, key); } catch (error) { /* storage unavailable */ }
}
function recall() {
  try { return localStorage.getItem(STORAGE_KEY); } catch (error) { return null; }
}

const fold = (text) => text.normalize("NFD").replace(/\p{M}/gu, "").normalize("NFC").toLowerCase().replace(/ς/g, "σ");
const stripHomograph = (lemma) => lemma.replace(/(\D)\d+$/, "$1");
const formatYear = (value) => {
  const year = parseInt(value, 10);
  if (Number.isNaN(year)) return "";
  return year < 0 ? `${-year} BCE` : `${year} CE`;
};
const NOT_A_WORD = "not-a-word";
const decision = (row) => (row.status === NOT_A_WORD ? "not a word" : `${row.lemma} · ${row.pos}`);
const link = (href, text) => h("a", { href, target: "_blank", rel: "noopener" }, text);

// ---------- overview, progress, lemma list ----------
function applyOverview(overview) {
  state.ann = overview.annotations;
  state.tags = overview.tags;
  state.tokensTotal = overview.tokens_total;
  if (!state.lemmas.length) {
    state.lemmas = overview.lemmas;
    state.lemmas.forEach((lemma) => { lemma.folded = fold(lemma.lemma); state.lemmaByKey.set(lemma.key, lemma); });
  }
  const doneKeys = Object.keys(state.ann);
  const doneTokens = doneKeys.reduce((sum, key) => sum + (state.lemmaByKey.get(key)?.tokens || 0), 0);
  const unsure = Object.values(state.ann).filter((row) => row.status === "unsure").length;
  const percent = state.lemmas.length ? (100 * doneKeys.length) / state.lemmas.length : 0;
  const progress = document.getElementById("progress");
  fill(progress, 
    h("span", {}, `${doneKeys.length} / ${state.lemmas.length} lemmas`),
    h("div", { class: "bar", title: `${percent.toFixed(1)}%` }, h("span", { style: `width:${percent}%` })),
    h("span", {}, `${doneTokens} / ${state.tokensTotal} tokens covered`),
    unsure ? h("span", {}, `${unsure} unsure`) : null,
    h("span", { title: overview.not_a_word.markers.map((item) => `${item.marker}: ${item.tokens} token${item.tokens === 1 ? "" : "s"}${item.lemmas ? ` (${item.lemmas} lemmas)` : ""} — ${item.description}`).join("\n") },
      `${overview.not_a_word.tokens} tokens not a word ⓘ`),
    overview.stale_annotations
      ? h("span", { title: "Annotated lemmas that are no longer missing from LiGre" }, `${overview.stale_annotations} obsolete`)
      : null,
  );
  progress.title = `Saved in ${overview.annotations_file}`;
  renderSidebar();
}

function filteredLemmas() {
  const query = fold(document.getElementById("lemma-search").value.trim());
  const filter = document.getElementById("lemma-filter").value;
  return state.lemmas.filter((lemma) => {
    if (query && !lemma.folded.includes(query)) return false;
    const row = state.ann[lemma.key];
    switch (filter) {
      case "open": return !row;
      case "flagged": return !row && lemma.flags.length > 0;
      case "near": return lemma.flags.includes("near LiGre match");
      case "unsure": return row?.status === "unsure";
      case "notaword": return row?.status === NOT_A_WORD;
      case "done": return Boolean(row);
      default: return true;
    }
  });
}

const MAX_LISTED = 400;
function renderSidebar() {
  const lemmas = filteredLemmas();
  const activeKey = state.lemma?.key;
  const shown = lemmas.slice(0, MAX_LISTED);
  if (activeKey && !shown.some((lemma) => lemma.key === activeKey)) {
    const active = state.lemmaByKey.get(activeKey);
    if (active) shown.unshift(active);
  }
  document.getElementById("sidebar-count").textContent =
    lemmas.length > MAX_LISTED ? `${lemmas.length} lemmas (first ${MAX_LISTED} shown; search to narrow)` : `${lemmas.length} lemmas`;
  fill(document.getElementById("lemma-list"), ...shown.map((lemma) => {
    const row = state.ann[lemma.key];
    return h("li", { class: lemma.key === activeKey ? "active" : "" },
      h("button", { onclick: () => openLemma(lemma.key), title: lemma.flags.join(", ") },
        h("span", { class: `dot ${row?.status || ""}` }),
        h("span", { class: "w" }, lemma.lemma, lemma.flags.length ? h("span", { class: "flag" }, " ⚑") : null),
        h("span", { class: "count" }, lemma.tokens),
        h("span", { class: "sub" }, lemma.pos, row ? ` → ${decision(row)}` : "")));
  }));
  const active = document.querySelector(".lemma-list li.active");
  if (active) active.scrollIntoView({ block: "nearest" });
}

function nextUnannotated() {
  const order = filteredLemmas();
  const lists = [order, state.lemmas];
  for (const list of lists) {
    const start = list.findIndex((lemma) => lemma.key === state.lemma?.key) + 1;
    for (let offset = 0; offset < list.length; offset += 1) {
      const lemma = list[(start + offset) % list.length];
      if (!state.ann[lemma.key]) return lemma.key;
    }
  }
  return null;
}

// ---------- loading ----------
async function openLemma(key) {
  if (!key) return;
  try {
    const payload = await api(`/api/lemma?key=${encodeURIComponent(key)}`);
    state.lemma = payload;
    state.occurrence = 0;
    state.doc = null;
    remember(key);
    history.replaceState(null, "", `#${encodeURIComponent(key)}`);
    const row = state.ann[key];
    state.form = row
      ? { lemma: row.lemma, pos: row.pos, ligre_lemma: row.ligre_lemma, note: row.note }
      : { lemma: payload.lemma, pos: "", ligre_lemma: "", note: "" };
    renderSidebar();
    await selectOccurrence(0);
    renderPanel();
    lookupLigre(state.form.lemma);
  } catch (error) {
    toast(error.message, true);
  }
}

async function selectOccurrence(index) {
  const occurrences = state.lemma.occurrences;
  if (index < 0 || index >= occurrences.length) return;
  state.occurrence = index;
  const occurrence = occurrences[index];
  if (!state.doc || state.doc.id !== occurrence.document) {
    const query = `id=${encodeURIComponent(occurrence.document)}&lemma=${encodeURIComponent(state.lemma.key)}`;
    state.doc = await api(`/api/document?${query}`);
    state.tokenDetails = new Map();
    for (const line of [...state.doc.lines, { tokens: state.doc.unplaced }]) {
      for (const token of line.tokens) if (token.key) state.tokenDetails.set(token.key, token.details);
    }
    renderDocument();
  } else {
    renderOccurrences();
  }
  markTokens();
  renderOccurrenceDetails();
  const current = document.querySelector(".greek .tok.current");
  if (current) current.scrollIntoView({ block: "center", behavior: "smooth" });
}

// ---------- document view ----------
function tokenElement(token) {
  const attributes = {
    class: token.key ? "tok target" : "tok",
    title: `${token.lemma || "?"} — ${token.info}`,
    dataset: { sentence: token.sentence, word: token.word },
  };
  if (token.key) {
    attributes.dataset.key = token.key;
    attributes.onclick = () => selectOccurrence(state.lemma.occurrences.findIndex((item) => item.key === token.key));
  }
  return h("span", attributes, token.form);
}

function renderOccurrences() {
  const list = document.getElementById("occurrence-list");
  if (!list) return;
  fill(list, ...state.lemma.occurrences.map((item, index) => h("li", {
    class: index === state.occurrence ? "self" : "", onclick: () => selectOccurrence(index),
  },
    h("span", {}, `${index + 1}`),
    h("span", {}, h("span", { class: "src" }, `${item.document}, line ${item.line || "–"} · ${item.info}`),
      item.before ? `${item.before} ` : "", h("mark", {}, item.form), item.after ? ` ${item.after}` : ""))));
  const self = list.querySelector("li.self");
  if (self) self.scrollIntoView({ block: "nearest" });
}

function renderDocument() {
  const doc = state.doc;
  const meta = doc.meta;
  const dates = [formatYear(meta.date_not_before), formatYear(meta.date_not_after)].filter(Boolean);
  const links = [
    ...doc.hgv_ids.map((id) => link(`https://papyri.info/hgv/${encodeURIComponent(id)}`, `papyri.info HGV ${id}`)),
    ...doc.tm_ids.map((id) => link(`https://www.trismegistos.org/text/${encodeURIComponent(id)}`, `TM ${id}`)),
  ];

  const greek = [];
  let previousPart = null;
  const addLine = (number, tokens) => {
    const children = [];
    tokens.forEach((token, index) => { if (index) children.push(" "); children.push(tokenElement(token)); });
    greek.push(h("div", { class: "line" }, h("span", { class: "line-number" }, number), h("span", {}, children)));
  };
  for (const line of doc.lines) {
    if (previousPart !== null && line.part !== previousPart) greek.push(h("div", { class: "part-break" }, `part ${line.part}`));
    previousPart = line.part;
    addLine(line.line, line.tokens);
  }
  if (doc.unplaced.length) {
    greek.push(h("div", { class: "part-break" }, "without line number"));
    addLine("–", doc.unplaced);
  }

  let translation;
  if (doc.translations.length) {
    translation = doc.translations.map((item) => h("div", {},
      h("div", { class: "translation-source" }, `papyri.info translation (HGV ${item.hgv_id}${item.language ? `, ${item.language}` : ""})`),
      h("div", { class: "translation-text" }, item.text)));
  } else if (doc.translations_probed) {
    translation = [h("p", { class: "empty" }, "papyri.info has no translation for this text. The edition linked above may have one.")];
  } else {
    translation = [h("p", { class: "empty" }, "Translations were not downloaded yet. Restart with ",
      h("code", {}, "--fetch-translations"), " (one small request per text).")];
  }

  fill(document.getElementById("document"), 
    h("div", { class: "pane occ-pane" },
      h("h3", {}, `Occurrences of ${state.lemma.lemma} (${state.lemma.tokens}) — click one to see its papyrus`),
      h("ul", { class: "occurrences", id: "occurrence-list" })),
    h("div", { class: "doc-header" },
      h("h2", {}, doc.id),
      h("div", { class: "doc-meta" },
        dates.length ? h("span", {}, dates.join(" – ")) : null,
        meta.place ? h("span", {}, meta.place) : null,
        ...meta.text_types.map((type) => h("span", {}, type)),
        ...links),
      meta.people.length ? h("div", { class: "people" }, meta.people.map((person) => h("span", { class: "chip" },
        person.tm_id ? link(`https://www.trismegistos.org/person/${encodeURIComponent(person.tm_id)}`, person.name) : person.name,
        person.role ? h("span", { class: "role" }, ` · ${person.role}`) : null))) : null),
    h("div", { class: "columns" },
      h("div", { class: "pane" }, h("h3", {}, "Greek text (PapyGreek)"), h("div", { class: "greek" }, greek),
        h("div", { class: "legend" },
          h("span", { class: "tok current" }, "this occurrence"), h("span", { class: "tok target" }, "same lemma"),
          h("span", { class: "tok head" }, "head word"), h("span", {}, "hover any word for its lemma and grammar"))),
      h("div", { class: "pane translation-pane" }, h("h3", {}, "Translation"), translation)),
  );
  renderOccurrences();
}

function markTokens() {
  const key = state.lemma.occurrences[state.occurrence]?.key;
  document.querySelectorAll(".greek .tok").forEach((element) => {
    element.classList.toggle("current", element.dataset.key === key);
    element.classList.remove("head");
  });
  const head = state.tokenDetails.get(key)?.head;
  if (head) {
    const element = document.querySelector(`.greek .tok[data-sentence="${head.sentence}"][data-word="${head.word}"]`);
    if (element) element.classList.add("head");
  }
}

// ---------- annotation panel ----------
let ligreTimer = null;
function lookupLigre(lemma) {
  clearTimeout(ligreTimer);
  const query = stripHomograph(lemma.trim());
  if (!query) { state.ligre = []; renderLigre(); return; }
  ligreTimer = setTimeout(async () => {
    try {
      state.ligre = (await api(`/api/ligre?q=${encodeURIComponent(query)}`)).results;
      renderLigre();
    } catch (error) {
      toast(error.message, true);
    }
  }, 150);
}

function chooseLigre(result) {
  state.form.lemma = result.written;
  state.form.ligre_lemma = result.id;
  if (result.tags.length === 1) state.form.pos = result.tags[0];
  renderPanel();
  lookupLigre(state.form.lemma);
}

function renderLigre() {
  const list = document.getElementById("ligre-results");
  const note = document.getElementById("ligre-note");
  if (!list) return;
  const query = stripHomograph(state.form.lemma.trim()).normalize("NFC");
  fill(list, ...state.ligre.map((result) => h("li", {
    class: result.written === query ? "exact" : "", title: "Link to this LiGre lemma", onclick: () => chooseLigre(result),
  }, h("span", { class: "w" }, result.written), h("span", { class: "t" }, `${result.tags.join("/") || "?"} · ${result.id}`))));
  const exact = state.ligre.filter((result) => result.written === query);
  note.textContent = !query ? ""
    : exact.length ? `This spelling is in LiGre: ${exact.map((result) => `${result.tags.join("/")} (${result.id})`).join(", ")}. Click it to link.`
      : "No LiGre lemma with exactly this spelling.";
}

function annotationState(row) {
  if (!row) return h("div", { class: "state todo" }, "Not annotated yet.");
  return h("div", { class: `state ${row.status}` },
    row.status === NOT_A_WORD ? "Not a word: left out of the linking." : `${row.status === "checked" ? "Checked" : "Unsure"}: ${decision(row)}`,
    row.ligre_lemma ? ` · LiGre ${row.ligre_lemma}` : "",
    row.note ? h("div", {}, `Note: ${row.note}`) : null);
}

function renderOccurrenceDetails() {
  const container = document.getElementById("occurrence-details");
  if (!container) return;
  const occurrence = state.lemma.occurrences[state.occurrence];
  const details = state.tokenDetails.get(occurrence?.key);
  if (!details) { fill(container); return; }
  fill(container, h("dl", {},
    h("dt", {}, "form"), h("dd", { class: "greek-value" }, details.form),
    details.regularized_form && details.regularized_form !== details.form
      ? [h("dt", {}, "regularized"), h("dd", { class: "greek-value" }, details.regularized_form)] : null,
    details.original_lemma && details.original_lemma !== state.lemma.lemma
      ? [h("dt", {}, "lemma (orig.)"), h("dd", { class: "greek-value" }, details.original_lemma)] : null,
    h("dt", {}, "grammar"), h("dd", {}, details.info),
    h("dt", {}, "tag"), h("dd", {}, h("code", {}, details.postag || "–")),
    details.relation ? [h("dt", {}, "role"), h("dd", {}, `${details.relation_info} (${details.relation})`)] : null,
    details.head ? [h("dt", {}, "depends on"), h("dd", { class: "greek-value" }, `${details.head.form} (${details.head.lemma})`)] : null));
}

function renderPanel() {
  const panel = document.getElementById("panel");
  const lemma = state.lemma;
  if (!lemma) { fill(panel, h("p", { class: "empty" }, "Select a lemma.")); return; }
  const row = state.ann[lemma.key];
  const genders = Object.entries(lemma.genders);
  const saveOnEnter = (event) => {
    if (event.key === "Enter") { event.preventDefault(); save(event.shiftKey ? "unsure" : "checked"); }
  };

  fill(panel, 
    h("div", { class: "where" }, h("span", {}, `${lemma.tokens} token${lemma.tokens === 1 ? "" : "s"} · PapyGreek ${lemma.pos}`)),
    h("h2", {}, lemma.lemma),
    lemma.flags.length ? h("div", { class: "flags" }, lemma.flags.map((flag) => h("span", { class: "chip" }, `⚑ ${flag}`))) : null,
    annotationState(row),

    lemma.near_ligre.length ? h("section", {},
      h("h3", {}, "Almost the same in LiGre (accents, breathings or capitals differ)"),
      h("div", { class: "near" }, h("ul", {}, lemma.near_ligre.map((result) => h("li", {},
        h("span", {}, h("span", { class: "w" }, result.written), " ", h("span", { class: "t" }, `${result.tags.join("/") || "?"} · ${result.id}`)),
        h("button", { onclick: () => chooseLigre(result) }, "link to this")))))) : null,

    lemma.variants.length ? h("section", {},
      h("h3", {}, "Other PapyGreek lemmas spelled alike (also missing from LiGre)"),
      h("ul", { class: "occurrences variants" }, lemma.variants.map((variant) => h("li", { onclick: () => openLemma(variant.key) },
        h("span", { class: `dot ${state.ann[variant.key]?.status || ""}` }),
        h("span", {}, `${variant.lemma} `, h("span", { class: "src" }, `${variant.lemma === lemma.lemma ? "same spelling, other part of speech" : "differs in accent, breathing or capital"} · ${variant.pos} · ${variant.tokens} token${variant.tokens === 1 ? "" : "s"}`
          + (state.ann[variant.key] ? ` · annotated ${decision(state.ann[variant.key])}` : ""))))))) : null,

    h("section", {},
      h("h3", {}, "PapyGreek says"),
      h("div", { class: "suggestion" },
        h("dl", {},
          h("dt", {}, "lemma"), h("dd", { class: "greek-value" }, lemma.lemma),
          h("dt", {}, "part of speech"), h("dd", {}, lemma.pos),
          genders.length ? [h("dt", {}, "gender"), h("dd", {}, genders.map(([gender, count]) => `${gender} ${count}×`).join(", "))] : null),
        h("h3", { style: "margin-top:8px" }, `Occurrence ${state.occurrence + 1} of ${lemma.tokens}`,
          " ", h("button", { title: "Previous occurrence ( [ )", onclick: () => selectOccurrence(state.occurrence - 1) }, "←"),
          " ", h("button", { title: "Next occurrence ( ] )", onclick: () => selectOccurrence(state.occurrence + 1) }, "→")),
        h("div", { id: "occurrence-details" }))),

    h("section", {},
      h("h3", {}, "Your lemma"),
      h("div", { class: "lemma-row" },
        h("input", {
          type: "text", id: "lemma-input", value: state.form.lemma, lang: "grc", autocomplete: "off", spellcheck: "false",
          oninput: (event) => {
            state.form.lemma = event.target.value;
            state.form.ligre_lemma = "";
            updateDiff();
            lookupLigre(state.form.lemma);
          },
          onkeydown: saveOnEnter,
        }),
        h("button", { title: "Reset to PapyGreek's lemma", onclick: () => {
          state.form.lemma = lemma.lemma; state.form.ligre_lemma = ""; renderPanel(); lookupLigre(lemma.lemma);
        } }, "↺")),
      h("div", { id: "linked-chip" }),
      h("div", { class: "diff", id: "lemma-diff" }),
      h("ul", { class: "ligre", id: "ligre-results" }),
      h("div", { class: "ligre-note", id: "ligre-note" })),

    h("section", {},
      h("h3", {}, "Your part of speech"),
      h("div", { class: "pos-grid" }, state.tags.map(({ tag, ligre }, index) => h("button", {
        class: [lemma.suggested_tags.includes(tag) ? "suggested" : "", state.form.pos === tag ? "selected" : ""].join(" "),
        title: `${ligre} LiGre lemmas have this tag${lemma.suggested_tags.includes(tag) ? "; compatible with PapyGreek's part of speech" : ""}`,
        onclick: () => { state.form.pos = tag; renderPanel(); },
      }, index < 9 ? h("kbd", {}, index + 1) : null, " ", tag, h("span", { class: "n" }, ligre ? `${ligre} in LiGre` : "none in LiGre")))),
      h("div", { class: "hint" }, `Framed tags are compatible with PapyGreek's ${lemma.pos}; none is preselected.`)),

    h("section", {},
      h("h3", {}, "Note (optional)"),
      h("input", { type: "text", value: state.form.note, oninput: (event) => { state.form.note = event.target.value; }, onkeydown: saveOnEnter })),

    h("section", {},
      h("div", { class: "actions" },
        h("button", { class: "primary", onclick: () => save("checked") }, "✓ Save ", h("kbd", {}, "Enter")),
        h("button", { onclick: () => save("unsure") }, "? Unsure ", h("kbd", {}, "U")),
        h("button", { title: "A gap, blank space or placeholder: no word to link", onclick: () => save(NOT_A_WORD) }, "✗ Not a word ", h("kbd", {}, "X")),
        row ? h("button", { onclick: clearAnnotation }, "Clear") : null),
      h("div", { class: "hint" }, "Keys outside the text fields: 1–9 part of speech, X not a word, [ ] previous/next occurrence, N next unannotated lemma. Shift+Enter in a field saves as unsure.")),
  );
  renderOccurrenceDetails();
  updateDiff();
  renderLigre();
}

function updateDiff() {
  const diff = document.getElementById("lemma-diff");
  const chip = document.getElementById("linked-chip");
  if (!diff || !state.lemma) return;
  diff.textContent = state.form.lemma.trim() && state.form.lemma.trim() !== state.lemma.lemma
    ? `Differs from PapyGreek's lemma (${state.lemma.lemma}).` : "";
  fill(chip, state.form.ligre_lemma
    ? h("span", { class: "linked" }, `linked to LiGre lemma ${state.form.ligre_lemma}`,
      h("button", { title: "Remove the link", onclick: () => { state.form.ligre_lemma = ""; updateDiff(); } }, "✕"))
    : "");
}

async function save(status) {
  if (state.busy || !state.lemma) return;
  if (status !== NOT_A_WORD && !state.form.lemma.trim()) { toast("Enter a lemma first.", true); return; }
  if (status !== NOT_A_WORD && !state.form.pos) { toast("Choose a part of speech first.", true); return; }
  state.busy = true;
  try {
    applyOverview(await api("/api/annotate", { key: state.lemma.key, status, ...state.form, lemma: state.form.lemma.trim() }));
    toast(`Saved ${state.lemma.lemma}.`);
    const next = nextUnannotated();
    if (next) await openLemma(next);
    else { renderPanel(); toast("Every lemma is annotated."); }
  } catch (error) {
    toast(error.message, true);
  } finally {
    state.busy = false;
  }
}

async function clearAnnotation() {
  try {
    applyOverview(await api("/api/remove", { key: state.lemma.key }));
    await openLemma(state.lemma.key);
  } catch (error) {
    toast(error.message, true);
  }
}

// ---------- keyboard & start ----------
document.addEventListener("keydown", (event) => {
  const typing = ["INPUT", "TEXTAREA", "SELECT"].includes(document.activeElement?.tagName);
  if (event.key === "Escape") { document.activeElement?.blur(); return; }
  if (typing || event.ctrlKey || event.metaKey || event.altKey || !state.lemma) return;
  if (event.key === "Enter") { event.preventDefault(); save("checked"); }
  else if (event.key === "u" || event.key === "U") save("unsure");
  else if (event.key === "x" || event.key === "X") save(NOT_A_WORD);
  else if (event.key === "]") selectOccurrence(state.occurrence + 1);
  else if (event.key === "[") selectOccurrence(state.occurrence - 1);
  else if (event.key === "n" || event.key === "N") openLemma(nextUnannotated());
  else if (/^[1-9]$/.test(event.key) && state.tags[Number(event.key) - 1]) {
    state.form.pos = state.tags[Number(event.key) - 1].tag;
    renderPanel();
  }
});

document.getElementById("lemma-search").addEventListener("input", renderSidebar);
document.getElementById("lemma-filter").addEventListener("change", renderSidebar);
document.getElementById("next-todo").addEventListener("click", () => openLemma(nextUnannotated()));

(async function start() {
  try {
    applyOverview(await api("/api/overview"));
    const fromUrl = decodeURIComponent(location.hash.slice(1));
    const last = state.lemmaByKey.has(fromUrl) ? fromUrl : recall();
    const key = last && state.lemmaByKey.has(last) ? last : (nextUnannotated() || state.lemmas[0]?.key);
    await openLemma(key);
  } catch (error) {
    fill(document.getElementById("document"), h("p", { class: "empty" }, `Could not load: ${error.message}`));
  }
})();
