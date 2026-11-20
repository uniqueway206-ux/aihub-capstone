(() => {
  "use strict";
  const $ = (s) => document.querySelector(s);
  let sid = crypto.randomUUID ? crypto.randomUUID() : String(Date.now());
  let docNames = [];

  // ---------- helpers ----------
  const esc = (s) => s.replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const inline = (t) => t.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>").replace(/`(.+?)`/g, "<code>$1</code>");
  function md(text) {
    const out = []; let list = false;
    for (const line of esc(text).split("\n")) {
      const m = line.match(/^\s*[-*]\s+(.*)/);
      if (m) { if (!list) { out.push("<ul>"); list = true; } out.push("<li>" + inline(m[1]) + "</li>"); }
      else { if (list) { out.push("</ul>"); list = false; } if (line.trim()) out.push("<p>" + inline(line) + "</p>"); }
    }
    if (list) out.push("</ul>");
    return out.join("");
  }
  function el(tag, cls, text) {
    const e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text !== undefined) e.textContent = text;
    return e;
  }

  async function api(path, opts = {}) {
    const headers = { ...(opts.headers || {}) };
    if (!(opts.body instanceof FormData) && opts.body) headers["Content-Type"] = "application/json";
    const key = sessionStorage.getItem("aihub_key");
    if (key) headers["X-API-Key"] = key;
    let res;
    try { res = await fetch(path, { ...opts, headers }); }
    catch (e) { throw new Error("Cannot reach the API. Is the server running?"); }
    if (res.status === 401) {
      const k = prompt("This server needs an API key:");
      if (k) { sessionStorage.setItem("aihub_key", k); return api(path, opts); }
    }
    let data = {};
    try { data = await res.json(); } catch (e) { /* no body */ }
    if (!res.ok) throw new Error(data.error || "Request failed (" + res.status + ")");
    return data;
  }

  // ---------- tabs ----------
  document.querySelectorAll(".tab").forEach((b) => b.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach((t) => t.classList.toggle("active", t === b));
    ["chat", "sum", "sql"].forEach((n) => { $("#tab-" + n).hidden = n !== b.dataset.tab; });
  }));

  // ---------- health ----------
  async function health() {
    try {
      const r = await fetch("/health"); const d = await r.json();
      $("#dot").className = "dot on"; $("#healthText").textContent = "API online (v" + d.version + ")";
    } catch (e) { $("#dot").className = "dot off"; $("#healthText").textContent = "API offline"; }
  }

  // ---------- documents ----------
  async function loadDocs() {
    try {
      const d = await api("/api/documents");
      const ul = $("#docs"); ul.replaceChildren(); docNames = Object.keys(d.documents);
      docNames.forEach((n) => {
        const li = el("li"); li.append(el("span", "", n), el("span", "", d.documents[n] + " chunks")); ul.append(li);
      });
    } catch (e) { setStatus(e.message, true); }
  }
  function setStatus(t, err) { const s = $("#uploadStatus"); s.textContent = t; s.className = "note" + (err ? " err" : ""); }

  async function upload(file) {
    if (!file) return;
    if (!file.name.toLowerCase().endsWith(".pdf")) return setStatus("Only PDF files are supported.", true);
    if (docNames.includes(file.name)) return setStatus(file.name + " is already indexed. Clear documents first to index it again.", true);
    setStatus("Indexing " + file.name + "... the first time can take a minute.");
    const fd = new FormData(); fd.append("file", file);
    try {
      const r = await api("/api/documents", { method: "POST", body: fd });
      setStatus("Indexed " + r.file + " (" + r.chunks + " chunks)");
      await loadDocs();
    } catch (e) { setStatus(e.message, true); }
    $("#file").value = "";
  }
  $("#file").addEventListener("change", (e) => upload(e.target.files[0]));
  const drop = $("#drop");
  ["dragenter", "dragover"].forEach((ev) => drop.addEventListener(ev, (e) => { e.preventDefault(); drop.classList.add("over"); }));
  ["dragleave", "drop"].forEach((ev) => drop.addEventListener(ev, (e) => { e.preventDefault(); drop.classList.remove("over"); }));
  drop.addEventListener("drop", (e) => upload(e.dataTransfer.files[0]));

  $("#clearDocs").addEventListener("click", async () => {
    if (!confirm("Remove all indexed documents?")) return;
    try { await api("/api/documents", { method: "DELETE" }); setStatus("All documents cleared."); await loadDocs(); }
    catch (e) { setStatus(e.message, true); }
  });

  // ---------- chat ----------
  const box = $("#messages");
  function addMsg(kind, text, extra) {
    const empty = $("#empty"); if (empty) empty.remove();
    const m = el("div", "msg " + kind);
    if (kind === "user" || kind === "error") m.textContent = text; else m.innerHTML = md(text);
    if (extra) m.append(extra);
    box.append(m); box.scrollTop = box.scrollHeight; return m;
  }
  function metaOf(res) {
    const wrap = el("div", "meta");
    if (res.route) wrap.append(el("span", "badge", res.route));
    (res.sources || []).forEach((s) => wrap.append(el("span", "src", s.source + (s.page ? " p." + s.page : ""))));
    const frag = document.createDocumentFragment(); frag.append(wrap);
    if (res.details && res.details.sql) frag.append(el("pre", "sql", res.details.sql));
    return frag;
  }
  async function send(text) {
    text = text.trim(); if (!text) return;
    addMsg("user", text); $("#msg").value = ""; autosize();
    const wait = addMsg("bot", ""); wait.innerHTML = '<span class="typing"><i></i><i></i><i></i></span>';
    $("#send").disabled = true;
    try {
      const res = await api("/api/chat", { method: "POST", body: JSON.stringify({ session_id: sid, message: text }) });
      wait.remove(); addMsg("bot", res.answer, metaOf(res));
    } catch (e) { wait.remove(); addMsg("error", e.message); }
    $("#send").disabled = false; $("#msg").focus();
  }
  function autosize() { const t = $("#msg"); t.style.height = "auto"; t.style.height = Math.min(t.scrollHeight, 140) + "px"; }
  $("#chatForm").addEventListener("submit", (e) => { e.preventDefault(); send($("#msg").value); });
  $("#msg").addEventListener("input", autosize);
  $("#msg").addEventListener("keydown", (e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send($("#msg").value); } });
  document.querySelectorAll(".chip").forEach((c) => c.addEventListener("click", () => send(c.textContent)));
  $("#newChat").addEventListener("click", async () => {
    try { await api("/api/chat/" + sid, { method: "DELETE" }); } catch (e) { /* ignore */ }
    sid = crypto.randomUUID ? crypto.randomUUID() : String(Date.now());
    box.replaceChildren(); addMsg("bot", "New conversation started. What would you like to know?");
  });

  // ---------- summarizer ----------
  $("#sumForm").addEventListener("submit", async (e) => {
    e.preventDefault(); const out = $("#sumOut"); out.replaceChildren(el("p", "note", "Fetching and summarizing..."));
    const btn = e.submitter; btn.disabled = true;
    try {
      const r = await api("/api/summarize", { method: "POST", body: JSON.stringify({ url: $("#url").value.trim() }) });
      const card = el("div", "card"); card.append(el("span", "badge", r.type)); const body = el("div"); body.innerHTML = md(r.summary);
      card.append(body); out.replaceChildren(card);
    } catch (err) { out.replaceChildren(el("div", "msg error", err.message)); }
    btn.disabled = false;
  });

  // ---------- sql ----------
  $("#sqlForm").addEventListener("submit", async (e) => {
    e.preventDefault(); const out = $("#sqlOut"); out.replaceChildren(el("p", "note", "Generating SQL..."));
    const btn = e.submitter; btn.disabled = true;
    try {
      const r = await api("/api/sql", { method: "POST", body: JSON.stringify({ question: $("#q").value.trim() }) });
      const card = el("div", "card"); const a = el("div"); a.innerHTML = md(r.answer); card.append(a, el("pre", "sql", r.sql));
      const table = el("table"); const head = el("tr");
      r.columns.forEach((c) => head.append(el("th", "", c))); table.append(head);
      r.rows.forEach((row) => { const tr = el("tr"); row.forEach((v) => tr.append(el("td", "", v === null ? "" : String(v)))); table.append(tr); });
      const wrap = el("div", "tablewrap"); wrap.append(table); card.append(wrap); out.replaceChildren(card);
    } catch (err) { out.replaceChildren(el("div", "msg error", err.message)); }
    btn.disabled = false;
  });

  health(); loadDocs();
})();
