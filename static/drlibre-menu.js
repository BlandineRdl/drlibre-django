// Closes header dropdowns on an outside click or Escape.
(function () {
  const menus = () => document.querySelectorAll(".site-header details[open]");
  document.addEventListener("click", function (event) {
    menus().forEach((menu) => { if (!menu.contains(event.target)) menu.removeAttribute("open"); });
  });
  document.addEventListener("keydown", function (event) {
    if (event.key !== "Escape") return;
    menus().forEach((menu) => { menu.removeAttribute("open"); menu.querySelector("summary").focus(); });
  });
})();
