/* ============================================================
   Healthcare GraphRAG — frontend controller
   ============================================================ */

const API = "/api";

const state = {
  patients: [],
  meta: null,
  fullGraphNet: null,
  reasoningNet: null,
  graphRenderedFor: null,
};

const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => Array.from(document.querySelectorAll(sel));

/* ---------------- vis-network theme ---------------- */
const VIS_OPTIONS = {
  nodes: {
    font: { color: "#13271f", size: 13, face: "JetBrains Mono", strokeWidth: 3, strokeColor: "#ffffff", multi: false },
    borderWidth: 1.5,
    shadow: { enabled: true, color: "rgba(16,70,50,0.18)", size: 9, x: 0, y: 2 },
  },
  edges: {
    color: { color: "#cdded6", highlight: "#0f9d6b", hover: "#2563eb" },
    font: { color: "#7a8a83", size: 9, strokeWidth: 3, strokeColor: "#ffffff", face: "JetBrains Mono", align: "middle" },
    arrows: { to: { enabled: true, scaleFactor: 0.45 } },
    smooth: { enabled: true, type: "dynamic" },
    width: 1,
  },
  physics: {
    stabilization: { iterations: 180 },
    barnesHut: { gravitationalConstant: -7000, springLength: 150, springConstant: 0.035, damping: 0.5, avoidOverlap: 0.2 },
  },
  interaction: { hover: true, tooltipDelay: 120, navigationButtons: false, keyboard: false },
};

function toVisNodes(nodes) {
  return nodes.map((n) => ({
    id: n.id,
    label: n.label,
    title: n.title,
    shape: n.shape,
    size: n.size,
    color: {
      background: n.color,
      border: "rgba(16,50,38,0.30)",
      highlight: { background: n.color, border: "#13271f" },
      hover: { background: n.color, border: "#13271f" },
    },
  }));
}

function renderGraph(container, data) {
  if (!data.nodes.length) {
    container.innerHTML = '<div class="empty-note">No graph nodes for this view.</div>';
    return null;
  }
  container.innerHTML = "";
  return new vis.Network(
    container,
    { nodes: new vis.DataSet(toVisNodes(data.nodes)), edges: new vis.DataSet(data.edges) },
    VIS_OPTIONS
  );
}

/* ---------------- tiny markdown renderer (escaped, safe) ---------------- */
function renderMarkdown(md) {
  const esc = (s) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  const inline = (s) =>
    esc(s)
      .replace(/`([^`]+)`/g, "<code>$1</code>")
      .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
      .replace(/(^|[^*])\*([^*]+)\*/g, "$1<em>$2</em>");

  let html = "";
  let list = null;
  const closeList = () => {
    if (list) { html += `</${list}>`; list = null; }
  };

  for (const raw of md.split(/\r?\n/)) {
    const line = raw.trimEnd();
    if (!line.trim()) { closeList(); continue; }

    let m;
    if ((m = line.match(/^(#{1,3})\s+(.*)$/))) {
      closeList();
      const lvl = m[1].length;
      html += `<h${lvl}>${inline(m[2])}</h${lvl}>`;
    } else if ((m = line.match(/^\s*[-*]\s+(.*)$/))) {
      if (list !== "ul") { closeList(); list = "ul"; html += "<ul>"; }
      html += `<li>${inline(m[1])}</li>`;
    } else if ((m = line.match(/^\s*(\d+)\.\s+(.*)$/))) {
      if (list !== "ol") { closeList(); list = "ol"; html += "<ol>"; }
      html += `<li value="${m[1]}">${inline(m[2])}</li>`;
    } else {
      closeList();
      html += `<p>${inline(line)}</p>`;
    }
  }
  closeList();
  return html;
}

/* ---------------- API helpers ---------------- */
async function getJSON(path) {
  const res = await fetch(`${API}${path}`);
  if (!res.ok) throw new Error(`${path} → ${res.status}`);
  return res.json();
}
async function postJSON(path, body) {
  const res = await fetch(`${API}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`${path} → ${res.status}`);
  return res.json();
}

function toast(message) {
  let el = $(".toast");
  if (!el) {
    el = document.createElement("div");
    el.className = "toast";
    document.body.appendChild(el);
  }
  el.textContent = message;
  el.classList.add("show");
  setTimeout(() => el.classList.remove("show"), 4200);
}

/* ---------------- selectors / state ---------------- */
const selectedPatient = () => $("#patient-select").value;

function patientById(id) {
  return state.patients.find((p) => p.id === id);
}

function updatePatientContext() {
  const id = selectedPatient();
  const el = $("#patient-context");
  if (id === "all") {
    el.innerHTML = `<b>Whole cohort</b> · ${state.patients.length} patients`;
    return;
  }
  const p = patientById(id);
  if (p) {
    el.innerHTML = `<b>${p.id} · ${p.name}</b><br>${p.diagnosis || "—"} · ${p.residence || "—"}`;
  }
}

/* ---------------- bootstrapping ---------------- */
async function init() {
  bindTabs();
  bindControls();

  try {
    const [meta, patients] = await Promise.all([getJSON("/meta"), getJSON("/patients")]);
    state.meta = meta;
    state.patients = patients;
    applyMeta(meta);
    applyPatients(patients);
    updatePatientContext();
  } catch (err) {
    toast(`Failed to load data: ${err.message}`);
    setEngine(false, "Offline");
  }
}

function applyMeta(meta) {
  $("#tagline").textContent = meta.tagline;
  setEngine(meta.llm_enabled, meta.llm_enabled ? `LLM · ${meta.model}` : "Extractive engine");

  for (const [key, value] of Object.entries(meta.metrics)) {
    const el = document.querySelector(`[data-metric="${key}"]`);
    if (el) animateCount(el, value);
  }

  const sugg = $("#suggestions");
  sugg.innerHTML = "";
  meta.suggested_questions.forEach((q) => {
    const li = document.createElement("li");
    li.textContent = q;
    li.addEventListener("click", () => {
      $("#question").value = q;
      $("#question").focus();
    });
    sugg.appendChild(li);
  });

  const legend = $("#legend");
  legend.innerHTML = "";
  meta.legend.forEach((item) => {
    const li = document.createElement("li");
    li.innerHTML = `<span class="dot" style="background:${item.color}"></span>${item.label}`;
    legend.appendChild(li);
  });

  const tableSel = $("#table-select");
  tableSel.innerHTML = "";
  meta.tables.forEach((name) => {
    const opt = document.createElement("option");
    opt.value = name;
    opt.textContent = name;
    tableSel.appendChild(opt);
  });

  $("#footer-stack").textContent = `FastAPI · networkx · TF-IDF · ${meta.model}`;
}

function applyPatients(patients) {
  const sel = $("#patient-select");
  sel.innerHTML = "";
  const all = document.createElement("option");
  all.value = "all";
  all.textContent = "All patients";
  sel.appendChild(all);
  patients.forEach((p) => {
    const opt = document.createElement("option");
    opt.value = p.id;
    opt.textContent = `${p.id} · ${p.name}`;
    sel.appendChild(opt);
  });
  if (patients.length) sel.value = patients[0].id;
}

function setEngine(enabled, label) {
  $("#engine-label").textContent = label;
  const badge = $("#engine-badge");
  badge.classList.toggle("chip-good", enabled);
  badge.classList.toggle("chip-amber", !enabled);
}

function animateCount(el, target) {
  const duration = 700;
  const start = performance.now();
  const step = (now) => {
    const t = Math.min(1, (now - start) / duration);
    const eased = 1 - Math.pow(1 - t, 3);
    el.textContent = Math.round(target * eased).toLocaleString();
    if (t < 1) requestAnimationFrame(step);
  };
  requestAnimationFrame(step);
}

/* ---------------- controls ---------------- */
function bindControls() {
  const topk = $("#topk");
  const setFill = () => {
    const pct = ((topk.value - topk.min) / (topk.max - topk.min)) * 100;
    topk.style.setProperty("--fill", `${pct}%`);
    $("#topk-value").textContent = topk.value;
  };
  topk.addEventListener("input", setFill);
  setFill();

  $("#patient-select").addEventListener("change", () => {
    updatePatientContext();
    state.graphRenderedFor = null;
    if ($('.tab-panel[data-panel="graph"]').classList.contains("is-active")) {
      loadFullGraph();
    }
  });

  $("#run-btn").addEventListener("click", runAsk);
  $("#question").addEventListener("keydown", (e) => {
    if ((e.metaKey || e.ctrlKey) && e.key === "Enter") runAsk();
  });

  $("#table-select").addEventListener("change", loadTable);
}

/* ---------------- tabs ---------------- */
function bindTabs() {
  const tabs = $$(".tab");
  const moveIndicator = (tab) => {
    const indicator = $("#tab-indicator");
    indicator.style.left = `${tab.offsetLeft}px`;
    indicator.style.width = `${tab.offsetWidth}px`;
  };

  tabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      tabs.forEach((t) => t.classList.remove("is-active"));
      tab.classList.add("is-active");
      moveIndicator(tab);

      const name = tab.dataset.tab;
      $$(".tab-panel").forEach((p) => p.classList.toggle("is-active", p.dataset.panel === name));

      if (name === "graph") loadFullGraph();
      if (name === "tables" && !$("#table-view").childElementCount) loadTable();
    });
  });

  requestAnimationFrame(() => moveIndicator($(".tab.is-active")));
  window.addEventListener("resize", () => moveIndicator($(".tab.is-active")));
}

/* ---------------- Ask flow ---------------- */
async function runAsk() {
  const question = $("#question").value.trim();
  if (!question) {
    toast("Enter a question first.");
    return;
  }

  const btn = $("#run-btn");
  btn.classList.add("is-loading");
  btn.disabled = true;
  btn.querySelector(".btn-label").textContent = "Running…";

  try {
    const data = await postJSON("/ask", {
      question,
      patient_id: selectedPatient(),
      top_k: Number($("#topk").value),
    });
    renderResults(data);
  } catch (err) {
    toast(`Request failed: ${err.message}`);
  } finally {
    btn.classList.remove("is-loading");
    btn.disabled = false;
    btn.querySelector(".btn-label").textContent = "Run GraphRAG";
  }
}

function renderResults(data) {
  $("#ask-placeholder").hidden = true;
  $("#results").hidden = false;

  $("#answer-body").innerHTML = renderMarkdown(data.answer);

  const badge = $("#mode-badge");
  if (data.mode === "llm") {
    badge.innerHTML = `<span class="chip-dot"></span> Generated · ${state.meta.model}`;
    badge.className = "chip chip-good";
  } else {
    badge.innerHTML = `<span class="chip-dot"></span> Extractive engine`;
    badge.className = "chip chip-amber";
    badge.title = data.llm_error || "";
  }

  state.reasoningNet = renderGraph($("#reasoning-graph"), data.reasoning_graph);
  renderEvidence(data.evidence);

  $("#results").scrollIntoView({ behavior: "smooth", block: "nearest" });
}

function renderEvidence(rows) {
  const wrap = $("#evidence");
  $("#evidence-count").textContent = `${rows.length} chunk${rows.length === 1 ? "" : "s"}`;
  if (!rows.length) {
    wrap.innerHTML = '<div class="empty-note">No lexical matches — the answer is grounded in graph facts.</div>';
    return;
  }
  const body = rows
    .map((r) => {
      const sim = Number(r.similarity_score || 0);
      const pct = Math.min(100, Math.round(sim * 100));
      return `<tr>
        <td class="mono">${r.chunk_id ?? ""}</td>
        <td class="mono">${r.patient_id ?? ""}</td>
        <td class="mono">${r.note_date ?? ""}</td>
        <td>${escapeHtml(r.section_name ?? "")}</td>
        <td class="chunk-text">${escapeHtml(r.chunk_text ?? "")}</td>
        <td><div class="sim-bar"><span class="sim-track"><span class="sim-fill" style="width:${pct}%"></span></span><span class="sim-num">${sim.toFixed(2)}</span></div></td>
      </tr>`;
    })
    .join("");
  wrap.innerHTML = `<table class="evidence-table">
    <thead><tr><th>Chunk</th><th>Patient</th><th>Date</th><th>Section</th><th>Text</th><th>Similarity</th></tr></thead>
    <tbody>${body}</tbody></table>`;
}

/* ---------------- Full graph ---------------- */
async function loadFullGraph() {
  const id = selectedPatient();
  if (state.graphRenderedFor === id) return;
  const sub = $("#graph-sub");
  sub.textContent = id === "all" ? "Cohort overview" : id;
  try {
    const data = await getJSON(`/graph?patient_id=${encodeURIComponent(id)}`);
    state.fullGraphNet = renderGraph($("#full-graph"), data);
    sub.textContent = `${data.nodes.length} nodes · ${data.edges.length} edges`;
    state.graphRenderedFor = id;
  } catch (err) {
    toast(`Graph failed: ${err.message}`);
  }
}

/* ---------------- Tables ---------------- */
async function loadTable() {
  const name = $("#table-select").value;
  if (!name) return;
  const view = $("#table-view");
  try {
    const data = await getJSON(`/tables/${encodeURIComponent(name)}`);
    if (!data.rows.length) {
      view.innerHTML = '<div class="empty-note">This table has no rows.</div>';
      return;
    }
    const head = data.columns.map((c) => `<th>${escapeHtml(c)}</th>`).join("");
    const body = data.rows
      .map(
        (row) =>
          `<tr>${data.columns
            .map((c) => `<td title="${escapeHtml(String(row[c] ?? ""))}">${escapeHtml(String(row[c] ?? ""))}</td>`)
            .join("")}</tr>`
      )
      .join("");
    view.innerHTML = `<table class="data-table"><thead><tr>${head}</tr></thead><tbody>${body}</tbody></table>`;
  } catch (err) {
    toast(`Table failed: ${err.message}`);
  }
}

function escapeHtml(s) {
  return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

document.addEventListener("DOMContentLoaded", init);
