const $ = (sel, root = document) => root.querySelector(sel);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const state = { jobs: [], jobId: null, results: [], files: [], errors: [] };
const EDU = { 0: "any", 1: "a diploma", 2: "a bachelor's degree", 3: "a master's degree", 4: "a PhD" };
const WEIGHTS = [["skill_score", "Skills", "s1", 0.45], ["text_score", "Text match", "s2", 0.30], ["experience_score", "Experience", "s3", 0.15], ["education_score", "Education", "s4", 0.10]];

async function api(path, opts = {}) {
  const res = await fetch("/api" + path, opts);
  if (!res.ok) {
    let msg = res.statusText;
    try { const b = await res.json(); msg = typeof b.detail === "string" ? b.detail : (b.detail?.[0]?.msg || msg); } catch {}
    throw new Error(msg);
  }
  return res.status === 204 ? null : res.json();
}
function toast(msg) {
  const t = $("#toast"); t.textContent = msg; t.classList.add("show");
  clearTimeout(toast.id); toast.id = setTimeout(() => t.classList.remove("show"), 3500);
}
const chips = (items, cls = "") => items.length ? `<ul class="chips">${items.map((s) => `<li class="chip ${cls}">${esc(s)}</li>`).join("")}</ul>` : "";

async function loadJobs() { state.jobs = await api("/jobs"); renderJobs(); }
function renderJobs() {
  $("#jobList").innerHTML = state.jobs.map((j) => `<li><button type="button" data-id="${j.id}" ${j.id === state.jobId ? 'aria-current="true"' : ""}>${esc(j.title)}<small>${j.candidate_count} screened</small></button></li>`).join("");
}
$("#jobList").addEventListener("click", (e) => { const b = e.target.closest("button[data-id]"); if (b) openJob(+b.dataset.id); });
$("#newJobBtn").addEventListener("click", showNewJob);

function showNewJob() {
  state.jobId = null; renderJobs();
  $("#main").innerHTML = `
    <h2>New job</h2>
    <p class="sub">Paste the job description. Required skills, experience and education are read from it.</p>
    <form id="jobForm" class="panel">
      <label for="title">Job title</label>
      <input id="title" type="text" required maxlength="200" placeholder="Data Scientist">
      <label for="desc">Job description</label>
      <textarea id="desc" required minlength="20" placeholder="Responsibilities, required skills, years of experience, education…"></textarea>
      <label for="skills">Required skills <span class="hint">Optional. Comma-separated; replaces the skills found in the description.</span></label>
      <input id="skills" type="text" placeholder="python, sql, pandas">
      <p id="formErr" class="err" role="alert"></p>
      <div class="row"><button class="btn primary" type="submit">Create job</button></div>
    </form>`;
  $("#jobForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    const skills = $("#skills").value.split(",").map((s) => s.trim()).filter(Boolean);
    try {
      const job = await api("/jobs", { method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title: $("#title").value, description: $("#desc").value, required_skills: skills.length ? skills : null }) });
      await loadJobs(); openJob(job.id);
    } catch (err) { $("#formErr").textContent = err.message; }
  });
  $("#title").focus();
}

async function openJob(id) {
  state.jobId = id; state.files = []; state.errors = [];
  renderJobs();
  const [job, results] = await Promise.all([api(`/jobs/${id}`), api(`/jobs/${id}/results`)]);
  state.results = results; state.job = job;
  renderJob();
}

function renderJob() {
  const j = state.job;
  const req = [];
  if (j.min_experience_years) req.push(`${j.min_experience_years} years of experience`);
  if (j.min_education_level) req.push(`${EDU[j.min_education_level]} or higher`);
  $("#main").innerHTML = `
    <div class="row" style="justify-content:space-between"><h2>${esc(j.title)}</h2>
      <button id="delJob" class="btn danger" type="button">Delete job</button></div>
    <p class="sub">${req.length ? "Looking for " + esc(req.join(", ")) : "No experience or education requirement found."}</p>
    <section class="panel"><h3>Required skills</h3>
      ${j.required_skills.length ? chips(j.required_skills) : '<p class="sub" style="margin:0">None found. Candidates are ranked by text similarity only. Delete this job and add skills when creating it for stricter matching.</p>'}</section>
    <section class="panel"><h3>Upload resumes</h3>
      <label class="drop" id="drop" for="fileInput">Drop PDF, DOCX or TXT resumes here, or click to choose
        <input id="fileInput" type="file" multiple accept=".pdf,.docx,.txt"></label>
      <ul class="files" id="fileList"></ul>
      <p id="uploadErr" class="err" role="alert"></p>
      <div class="row" style="margin-top:12px"><button id="screenBtn" class="btn primary" type="button" disabled>Screen resumes</button></div>
    </section>
    <section id="results"></section>`;
  $("#delJob").onclick = async () => {
    if (!confirm(`Delete "${j.title}" and its rankings?`)) return;
    await api(`/jobs/${j.id}`, { method: "DELETE" }); state.jobId = null; await loadJobs(); showNewJob();
  };
  const input = $("#fileInput"), drop = $("#drop");
  input.onchange = () => setFiles([...input.files]);
  ["dragenter", "dragover"].forEach((ev) => drop.addEventListener(ev, (e) => { e.preventDefault(); drop.classList.add("over"); }));
  ["dragleave", "drop"].forEach((ev) => drop.addEventListener(ev, (e) => { e.preventDefault(); drop.classList.remove("over"); }));
  drop.addEventListener("drop", (e) => setFiles([...e.dataTransfer.files]));
  $("#screenBtn").onclick = screen;
  renderResults();
}
function setFiles(files) {
  state.files = files;
  $("#fileList").innerHTML = files.map((f) => `<li>${esc(f.name)} (${Math.max(1, Math.round(f.size / 1024))} KB)</li>`).join("");
  $("#screenBtn").disabled = !files.length;
}
async function screen() {
  const btn = $("#screenBtn"); btn.disabled = true; btn.textContent = "Screening…"; $("#uploadErr").textContent = "";
  const fd = new FormData(); state.files.forEach((f) => fd.append("files", f));
  try {
    const out = await api(`/jobs/${state.jobId}/screen`, { method: "POST", body: fd });
    state.results = out.results; state.errors = out.errors;
    toast(`Ranked ${out.results.length} candidate${out.results.length === 1 ? "" : "s"}.`);
    setFiles([]); $("#fileInput").value = ""; loadJobs();
  } catch (err) { $("#uploadErr").textContent = err.message; }
  btn.textContent = "Screen resumes"; btn.disabled = !state.files.length;
  renderResults();
}

function renderResults() {
  const el = $("#results"); if (!el) return;
  const errs = state.errors.map((e) => `<p class="err">${esc(e.filename)}: ${esc(e.error)}</p>`).join("");
  if (!state.results.length) { el.innerHTML = errs + `<div class="empty panel">No candidates yet. Upload resumes to see them ranked here.</div>`; return; }
  el.innerHTML = errs + `
    <div class="row" style="justify-content:space-between"><h3>Ranked candidates</h3>
      <a class="btn" href="/api/jobs/${state.jobId}/results.csv">Export CSV</a></div>
    <p class="legend">${WEIGHTS.map(([, n, c, w]) => `<span><i class="${c}"></i>${n} (${Math.round(w * 100)}%)</span>`).join("")}</p>
    ${state.results.map(candHtml).join("")}`;
  el.querySelectorAll(".cand-head").forEach((b) => b.addEventListener("click", () => {
    const d = b.nextElementSibling; d.hidden = !d.hidden; b.setAttribute("aria-expanded", String(!d.hidden));
  }));
  el.querySelectorAll("[data-del]").forEach((b) => b.addEventListener("click", async () => {
    if (!confirm("Remove this candidate from all jobs?")) return;
    await api(`/candidates/${b.dataset.del}`, { method: "DELETE" });
    state.results = await api(`/jobs/${state.jobId}/results`); loadJobs(); renderResults();
  }));
}
function candHtml(r) {
  const bar = WEIGHTS.map(([k, , c, w]) => `<i class="${c}" style="width:${(r[k] * w).toFixed(1)}%"></i>`).join("");
  return `<article class="cand">
    <button class="cand-head" type="button" aria-expanded="false">
      <span class="rank">${r.rank}</span>
      <span><span class="name">${esc(r.name)}</span><span class="file">${esc(r.filename)}</span>
        <span class="ruler" aria-hidden="true">${bar}</span></span>
      <span class="score">${Math.round(r.score)}<small>/100</small></span>
    </button>
    <div class="detail" hidden>
      <div class="breakdown">${WEIGHTS.map(([k, n]) => `<div>${n}<b>${Math.round(r[k])}%</b></div>`).join("")}</div>
      <div><strong>Matches</strong>${r.matched_skills.length ? chips(r.matched_skills, "ok") : '<p class="sub" style="margin:4px 0 0">No required skills found.</p>'}</div>
      ${r.missing_skills.length ? `<div><strong>Missing</strong>${chips(r.missing_skills, "miss")}</div>` : ""}
      <dl>
        <dt>Contact</dt><dd>${[r.email, r.phone].filter(Boolean).map(esc).join(" · ") || "Not found"}</dd>
        <dt>Experience</dt><dd>${r.experience_years} years</dd>
        <dt>Education</dt><dd>${r.education.length ? `<ul class="plain">${r.education.map((e) => `<li>${esc(e)}</li>`).join("")}</ul>` : esc(r.education_label)}</dd>
        ${r.certifications.length ? `<dt>Certifications</dt><dd><ul class="plain">${r.certifications.map((e) => `<li>${esc(e)}</li>`).join("")}</ul></dd>` : ""}
        ${r.projects.length ? `<dt>Projects</dt><dd><ul class="plain">${r.projects.map((e) => `<li>${esc(e)}</li>`).join("")}</ul></dd>` : ""}
        <dt>All skills</dt><dd>${chips(r.skills) || "None found"}</dd>
      </dl>
      <div><button class="btn danger" type="button" data-del="${r.candidate_id}">Remove candidate</button></div>
    </div></article>`;
}

(async () => {
  await loadJobs();
  state.jobs.length ? openJob(state.jobs[0].id) : showNewJob();
})();
