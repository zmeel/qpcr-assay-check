// Light/dark choice, remembered in this browser only (the default follows the system).
(function () {
  "use strict";
  var root = document.documentElement;
  try {
    var saved = localStorage.getItem("qac-theme");
    if (saved === "light" || saved === "dark") root.setAttribute("data-theme", saved);
  } catch (e) { /* storage blocked: follow the system */ }
  document.addEventListener("DOMContentLoaded", function () {
    var button = document.querySelector("[data-theme-toggle]");
    if (!button) return;
    button.addEventListener("click", function () {
      var current = root.getAttribute("data-theme") ||
        (window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
      var next = current === "dark" ? "light" : "dark";
      root.setAttribute("data-theme", next);
      try { localStorage.setItem("qac-theme", next); } catch (e) { /* not remembered */ }
    });
  });
})();
