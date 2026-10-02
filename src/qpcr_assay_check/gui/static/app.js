// Light/dark choice (remembered in this browser only; the default follows the system),
// live validation of the YAML editor, a warning before leaving unsaved edits, the live log of a
// run, and measuring the work folder on the Settings page.
(function () {
  "use strict";
  var root = document.documentElement;
  try {
    var saved = localStorage.getItem("qac-theme");
    if (saved === "light" || saved === "dark") root.setAttribute("data-theme", saved);
  } catch (e) { /* storage blocked: follow the system */ }

  function themeToggle() {
    var button = document.querySelector("[data-theme-toggle]");
    if (!button) return;
    button.addEventListener("click", function () {
      var current = root.getAttribute("data-theme") ||
        (window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
      var next = current === "dark" ? "light" : "dark";
      root.setAttribute("data-theme", next);
      try { localStorage.setItem("qac-theme", next); } catch (e) { /* not remembered */ }
    });
  }

  function dirtyGuard() {
    document.querySelectorAll("form[data-dirty-guard]").forEach(function (form) {
      var dirty = false;
      form.addEventListener("input", function () { dirty = true; });
      form.addEventListener("submit", function () { dirty = false; });
      window.addEventListener("beforeunload", function (ev) {
        if (dirty) { ev.preventDefault(); ev.returnValue = ""; }
      });
    });
  }

  function liveValidation() {
    var area = document.querySelector("textarea[data-validate-url]");
    var target = document.querySelector("[data-validation-target]");
    if (!area || !target) return;
    var state = document.querySelector("[data-validate-state]");
    var csrf = area.form.querySelector("input[name=csrf]").value;
    var timer = null;
    var seq = 0;
    var escaped = false;
    area.addEventListener("keydown", function (ev) {
      if (ev.key === "Escape") { escaped = true; return; }
      var leave = escaped;
      escaped = false;
      if (ev.key === "Tab" && !leave && !ev.shiftKey && !ev.ctrlKey && !ev.metaKey) {
        ev.preventDefault();  // two spaces, as YAML needs; Esc then Tab leaves the field
        var s = area.selectionStart;
        area.setRangeText("  ", s, area.selectionEnd, "end");
        area.dispatchEvent(new Event("input", { bubbles: true }));
      }
    });
    area.addEventListener("input", function () {
      if (timer) clearTimeout(timer);
      if (state) state.textContent = "Checking…";
      timer = setTimeout(function () {
        var mine = ++seq;
        var body = new FormData();
        body.append("csrf", csrf);
        body.append("text", area.value);
        fetch(area.getAttribute("data-validate-url"), { method: "POST", body: body, credentials: "same-origin" })
          .then(function (r) { return r.ok && !r.redirected ? r.text() : Promise.reject(r.status); })
          .then(function (html) {
            if (mine !== seq) return;
            target.innerHTML = html;  // rendered and escaped by the server
            if (state) state.textContent = "Checked. Not saved yet.";
          })
          .catch(function () { if (state) state.textContent = "Could not check (signed out?)."; });
      }, 600);
    });
  }

  function runStatus() {
    var box = document.querySelector("[data-run-status]");
    if (!box || box.getAttribute("data-finished") === "1") return;
    var url = box.getAttribute("data-url");
    var offset = parseInt(box.getAttribute("data-offset"), 10) || 0;
    var logEl = box.querySelector("[data-log]");
    var detail = box.querySelector("[data-detail]");
    var bar = box.querySelector("[data-percent]");
    var stages = box.querySelectorAll("[data-stage]");
    function follow() {
      return logEl.scrollHeight - logEl.scrollTop - logEl.clientHeight < 40;
    }
    function poll() {
      fetch(url + "?offset=" + offset, { credentials: "same-origin" })
        .then(function (r) { return r.ok && !r.redirected ? r.json() : Promise.reject(r.status); })
        .then(function (s) {
          if (s.text) {
            var stick = follow();
            logEl.appendChild(document.createTextNode(s.text));
            if (stick) logEl.scrollTop = logEl.scrollHeight;
          }
          offset = s.offset;
          if (detail) detail.textContent = s.detail || "";
          if (bar) {
            if (s.percent === null) { bar.hidden = true; } else { bar.hidden = false; bar.value = s.percent; }
          }
          stages.forEach(function (li) {
            var i = parseInt(li.getAttribute("data-stage"), 10);
            var state = i < s.stage ? "done" : (i === s.stage && s.state === "running" ? "active" : "todo");
            li.className = "stage stage-" + state;
          });
          if (s.finished) { window.location.reload(); return; }
          setTimeout(poll, s.state === "queued" ? 5000 : 2000);
        })
        .catch(function () { setTimeout(poll, 10000); });
    }
    logEl.scrollTop = logEl.scrollHeight;
    setTimeout(poll, 1500);
  }

  function storage() {
    var box = document.querySelector("[data-storage-url]");
    if (!box) return;
    var button = box.querySelector("[data-storage-measure]");
    var target = box.querySelector("[data-storage-target]");
    button.addEventListener("click", function () {
      button.disabled = true;
      target.textContent = "Counting…";
      fetch(box.getAttribute("data-storage-url"), { credentials: "same-origin" })
        .then(function (r) { return r.ok && !r.redirected ? r.text() : Promise.reject(r.status); })
        .then(function (html) { target.innerHTML = html; })  // rendered and escaped by the server
        .catch(function () { target.textContent = "Could not measure (signed out?)."; })
        .then(function () { button.disabled = false; });
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    themeToggle();
    dirtyGuard();
    liveValidation();
    runStatus();
    storage();
  });
})();
