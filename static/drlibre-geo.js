// Fills the visitor's position in the search form; the browser only, no external service.
(function () {
  const button = document.getElementById("geo-button");
  const form = document.getElementById("search-form");
  if (!button || !form || !("geolocation" in navigator)) return;
  const status = document.getElementById("geo-status");
  button.hidden = false;
  button.addEventListener("click", function () {
    status.textContent = "Recherche de votre position…";
    navigator.geolocation.getCurrentPosition(
      function (position) {
        form.elements.lat.value = position.coords.latitude.toFixed(4);
        form.elements.lon.value = position.coords.longitude.toFixed(4);
        const sort = form.elements.sort;
        if (!Array.from(sort.options).some((o) => o.value === "distance")) {
          sort.add(new Option("Distance la plus courte", "distance"));
        }
        sort.value = "distance";
        form.requestSubmit();
      },
      function () {
        status.textContent = "Votre position n'est pas disponible.";
      }
    );
  });
})();
