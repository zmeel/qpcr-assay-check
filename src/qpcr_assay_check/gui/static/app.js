// Light/dark choice (remembered in this browser only; the default follows the system),
// live validation of the YAML editor, and a warning before leaving unsaved edits.
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

  document.addEventListener("DOMContentLoaded", function () {
    themeToggle();
    dirtyGuard();
    liveValidation();
  });
})();
