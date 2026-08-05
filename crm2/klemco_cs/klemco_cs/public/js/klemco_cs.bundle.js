// Klemco CRM AI Assistant — floating chat bubble.
// Loaded on every desk page (app_include_js) and injectable into the CRM SPA.
// Talks to klemco_cs.ai_assistant.api.{chat,status,confirm_create}.
(function () {
  // Colour the Connections-tab count badges so linked documents stand out. Frappe un-hides a
  // connection's `.count` only when it has linked docs, so `.count:not(.hidden)` == "has documents".
  (function connectionsBadgeCSS() {
    if (document.getElementById("klemco-connections-css")) return;
    const s = document.createElement("style");
    s.id = "klemco-connections-css";
    s.textContent = `
      .document-link-badge .count:not(.hidden){
        background:#1A5276 !important; color:#fff !important;
        border-radius:8px; padding:0 6px; font-weight:600;
      }
      .document-link:has(.count:not(.hidden)) .badge-link{
        color:#1A5276 !important; font-weight:600;
      }`;
    (document.head || document.documentElement).appendChild(s);
  })();

  if (window.__klemcoAIWidget) return;
  window.__klemcoAIWidget = true;

  // ── "Documents" button — list every file attached to this record (separate from Connections) ──
  function klemcoShowDocuments(frm) {
    frappe.call({
      method: "klemco_cs.documents.list_document_files",
      args: { doctype: frm.doctype, name: frm.doc.name },
      callback(r) {
        const files = r.message || [];
        const esc = frappe.utils.escape_html;
        const body = files.length
          ? files.map((f) => {
              const size = f.file_size ? Math.round(f.file_size / 1024) + " KB" : "";
              const lock = f.is_private ? " 🔒" : "";
              const when = f.creation ? frappe.datetime.str_to_user(f.creation) : "";
              return `<tr>
                <td style="padding:4px 8px;">📄 <a href="${esc(f.file_url)}" target="_blank">${esc(f.file_name || f.file_url)}</a>${lock}</td>
                <td style="padding:4px 8px;color:#666;white-space:nowrap;">${size}</td>
                <td style="padding:4px 8px;color:#666;">${esc(f.owner || "")}</td>
                <td style="padding:4px 8px;color:#666;white-space:nowrap;">${esc(when)}</td></tr>`;
            }).join("")
          : `<tr><td colspan="4" style="padding:12px;color:#888;">No files attached to this document.</td></tr>`;
        const html = `<div style="max-height:60vh;overflow:auto;">
          <table style="width:100%;border-collapse:collapse;font-size:13px;">
            <thead><tr style="text-align:left;border-bottom:1px solid #ddd;color:#555;">
              <th style="padding:4px 8px;">File</th><th style="padding:4px 8px;">Size</th>
              <th style="padding:4px 8px;">Uploaded by</th><th style="padding:4px 8px;">When</th></tr></thead>
            <tbody>${body}</tbody></table></div>`;
        const d = new frappe.ui.Dialog({ title: __("Files attached to {0}", [frm.doc.name]), size: "large" });
        d.$body.html(html);
        d.show();
      },
    });
  }

  (function klemcoDocumentsButton() {
    if (!(window.frappe && frappe.ui && frappe.ui.form)) return;
    ["Sales Order", "Quotation", "Sales Invoice", "Delivery Note", "Purchase Order",
     "Purchase Invoice", "Purchase Receipt", "Payment Entry", "KM Order"].forEach((dt) => {
      frappe.ui.form.on(dt, {
        refresh(frm) {
          if (frm.is_new()) return;
          frm.add_custom_button(__("Attached Files"), () => klemcoShowDocuments(frm));
        },
      });
    });
  })();

  const API = "/api/method/klemco_cs.ai_assistant.api.";
  const history = [];

  function csrf() {
    return (window.frappe && frappe.csrf_token) ||
           (window.boot && window.boot.csrf_token) ||
           (window.csrf_token) || "";
  }
  async function call(method, body) {
    const r = await fetch(API + method, {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-Frappe-CSRF-Token": csrf() },
      body: JSON.stringify(body || {}),
    });
    const j = await r.json();
    if (j.exc || j._server_messages) throw new Error("Request failed");
    return j.message;
  }
  function esc(t) { return (t || "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;"); }
  function md(t) {
    return esc(t).replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
                 .replace(/\*(.+?)\*/g, "<em>$1</em>")
                 .replace(/\n/g, "<br>");
  }

  const css = `
  #kai-btn{position:fixed;right:22px;bottom:22px;width:56px;height:56px;border-radius:50%;
    background:#1A5276;color:#fff;border:none;cursor:pointer;box-shadow:0 4px 14px rgba(0,0,0,.25);
    font-size:24px;z-index:99998;display:flex;align-items:center;justify-content:center}
  #kai-panel{position:fixed;right:22px;bottom:88px;width:380px;max-width:92vw;height:540px;max-height:78vh;
    background:#fff;border:1px solid #e5e7eb;border-radius:14px;box-shadow:0 12px 40px rgba(0,0,0,.28);
    z-index:99999;display:none;flex-direction:column;overflow:hidden;font-family:-apple-system,Segoe UI,Roboto,Arial,sans-serif}
  #kai-panel.open{display:flex}
  #kai-hd{background:#1A5276;color:#fff;padding:12px 14px}
  #kai-hd b{font-size:14px}
  #kai-hd .s{font-size:10px;opacity:.85;display:block;margin-top:2px}
  #kai-log{flex:1;overflow-y:auto;padding:14px;display:flex;flex-direction:column;gap:9px;background:#f7f8fa}
  .kai-m{max-width:84%;padding:8px 11px;border-radius:12px;font-size:13px;line-height:1.45;word-wrap:break-word}
  .kai-m.bot{background:#eef2ff;align-self:flex-start;border-bottom-left-radius:3px}
  .kai-m.user{background:#1A5276;color:#fff;align-self:flex-end;border-bottom-right-radius:3px}
  .kai-m.typing{color:#6b7280;font-style:italic}
  .kai-confirm{align-self:flex-start;background:#fff;border:1px solid #f59e0b;border-radius:12px;padding:10px;font-size:13px;max-width:90%}
  .kai-confirm pre{background:#fafafa;border-radius:6px;padding:6px;font-size:11px;white-space:pre-wrap;margin:6px 0}
  .kai-confirm button{font-size:12px;padding:6px 12px;border-radius:8px;border:none;cursor:pointer;margin-right:6px}
  .kai-ok{background:#16a34a;color:#fff}.kai-no{background:#e5e7eb}
  #kai-form{display:flex;gap:6px;padding:10px;border-top:1px solid #e5e7eb;background:#fff}
  #kai-q{flex:1;padding:9px 11px;border:1px solid #d1d5db;border-radius:9px;font-size:13px;outline:none}
  #kai-q:focus{border-color:#1A5276}
  #kai-send{padding:9px 14px;background:#1A5276;color:#fff;border:none;border-radius:9px;cursor:pointer;font-weight:600;font-size:13px}
  #kai-send:disabled{opacity:.5}`;

  function build() {
    if (document.getElementById("kai-btn")) return;
    const st = document.createElement("style"); st.textContent = css; document.head.appendChild(st);
    const btn = document.createElement("button"); btn.id = "kai-btn"; btn.title = "AI Help"; btn.textContent = "💬";
    const panel = document.createElement("div"); panel.id = "kai-panel";
    panel.innerHTML = `
      <div id="kai-hd"><b>Klemco CRM Assistant</b><span class="s" id="kai-status">connecting…</span></div>
      <div id="kai-log"></div>
      <form id="kai-form"><input id="kai-q" autocomplete="off" placeholder="Ask about your CRM…"/>
        <button id="kai-send" type="submit">Send</button></form>`;
    document.body.appendChild(btn); document.body.appendChild(panel);

    const log = panel.querySelector("#kai-log");
    function add(role, html) {
      const d = document.createElement("div"); d.className = "kai-m " + role; d.innerHTML = html;
      log.appendChild(d); log.scrollTop = log.scrollHeight; return d;
    }
    function confirmCard(pa) {
      const card = document.createElement("div"); card.className = "kai-confirm";
      card.innerHTML = `<div>Create <b>${esc(pa.doctype)}</b>?</div>
        <pre>${esc(JSON.stringify(pa.values, null, 2))}</pre>
        <button class="kai-ok">Confirm</button><button class="kai-no">Cancel</button>`;
      log.appendChild(card); log.scrollTop = log.scrollHeight;
      card.querySelector(".kai-ok").onclick = async () => {
        card.innerHTML = "Creating…";
        try {
          const res = await call("confirm_create", { doctype: pa.doctype, values: JSON.stringify(pa.values) });
          card.outerHTML = `<div class="kai-m bot">✅ Created <b>${esc(res.doctype)}</b> <b>${esc(res.name)}</b>.</div>`;
        } catch (e) { card.innerHTML = "⚠️ " + esc(e.message || "could not create"); }
        log.scrollTop = log.scrollHeight;
      };
      card.querySelector(".kai-no").onclick = () => { card.outerHTML = `<div class="kai-m bot">Cancelled — nothing was saved.</div>`; };
    }
    async function send(text) {
      if (!text.trim()) return;
      add("user", md(text)); history.push({ role: "user", content: text });
      const t = add("bot typing", "thinking…");
      panel.querySelector("#kai-send").disabled = true;
      try {
        const res = await call("chat", { message: text, history: JSON.stringify(history.slice(0, -1)) });
        t.className = "kai-m bot"; t.innerHTML = md(res.reply);
        history.push({ role: "assistant", content: res.reply });
        if (res.pending_action) confirmCard(res.pending_action);
      } catch (e) { t.className = "kai-m bot"; t.innerHTML = "⚠️ " + esc(e.message || "request failed"); }
      panel.querySelector("#kai-send").disabled = false; panel.querySelector("#kai-q").focus();
    }
    panel.querySelector("#kai-form").addEventListener("submit", (e) => {
      e.preventDefault(); const q = panel.querySelector("#kai-q"); const v = q.value; q.value = ""; send(v);
    });
    btn.onclick = async () => {
      panel.classList.toggle("open");
      if (panel.classList.contains("open")) {
        panel.querySelector("#kai-q").focus();
        if (!log.dataset.init) {
          log.dataset.init = "1";
          add("bot", "Hi! Ask me how to use the CRM, or about your data — e.g. <em>how many open complaints?</em> or <em>log a complaint about a leaking valve</em>.");
          try { const s = await call("status", {});
            panel.querySelector("#kai-status").textContent = s.configured ? ("live · " + s.model) : "demo mode (no API key)";
          } catch (e) { panel.querySelector("#kai-status").textContent = "offline"; }
        }
      }
    };
  }

  if (document.body) build();
  else document.addEventListener("DOMContentLoaded", build);
})();
