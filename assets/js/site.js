(function () {
  "use strict";
  var root = document.documentElement;

  // Light/dark toggle. With no saved choice the OS setting applies.
  var themeBtn = document.getElementById("theme-toggle");
  if (themeBtn) {
    themeBtn.addEventListener("click", function () {
      var dark = root.dataset.theme
        ? root.dataset.theme === "dark"
        : window.matchMedia("(prefers-color-scheme: dark)").matches;
      root.dataset.theme = dark ? "light" : "dark";
      try { localStorage.setItem("theme", root.dataset.theme); } catch (e) {}
    });
  }

  // Mobile menu.
  var menuBtn = document.getElementById("menu-toggle");
  var nav = document.getElementById("site-nav");
  if (menuBtn && nav) {
    menuBtn.addEventListener("click", function () {
      var open = nav.classList.toggle("open");
      menuBtn.setAttribute("aria-expanded", String(open));
    });
  }

  // Publications: filter by type, search, and first/senior authorship.
  var controls = document.getElementById("pub-controls");
  if (!controls) return;
  var chips = controls.querySelectorAll(".chip-btn");
  var search = document.getElementById("pub-search");
  var lead = document.getElementById("pub-lead");
  var count = document.getElementById("pub-count");
  var empty = document.getElementById("pub-empty");
  var groups = document.querySelectorAll(".year-group");
  var items = document.querySelectorAll(".pub");
  var type = new URLSearchParams(location.search).get("type") || "all";

  items.forEach(function (li) { li.dataset.text = li.textContent.toLowerCase(); });

  function apply() {
    var q = search.value.trim().toLowerCase();
    var shown = 0;
    items.forEach(function (li) {
      var ok = (type === "all" || li.dataset.type === type) &&
        (!lead.checked || li.hasAttribute("data-lead")) &&
        (!q || li.dataset.text.indexOf(q) !== -1);
      li.hidden = !ok;
      if (ok) shown++;
    });
    groups.forEach(function (g) { g.hidden = !g.querySelector(".pub:not([hidden])"); });
    chips.forEach(function (c) { c.setAttribute("aria-pressed", String(c.dataset.filter === type)); });
    count.textContent = shown === items.length ? "" : "Showing " + shown + " of " + items.length + ".";
    empty.hidden = shown > 0;
  }

  chips.forEach(function (c) {
    c.addEventListener("click", function () {
      type = c.dataset.filter;
      var url = new URL(location.href);
      if (type === "all") url.searchParams.delete("type"); else url.searchParams.set("type", type);
      history.replaceState(null, "", url);
      apply();
    });
  });
  search.addEventListener("input", apply);
  lead.addEventListener("change", apply);
  apply();
})();
