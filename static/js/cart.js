/* Teepresso — cart page AJAX (qty update + remove, live totals) */
(function () {
  const csrf = (window.TP && TP.csrf) || "";
  const fmt = n => "₹" + Math.round(n).toLocaleString("en-IN");

  function refreshTotals(d) {
    const set = (id, val) => { const el = document.getElementById(id); if (el) el.textContent = val; };
    set("sum-sub", fmt(d.subtotal));
    set("sum-gst", fmt(d.gst));
    set("sum-total", fmt(d.total));
    const ship = document.getElementById("sum-ship");
    if (ship) ship.innerHTML = d.shipping ? fmt(d.shipping) : '<span class="text-success">FREE</span>';
    const cc = document.getElementById("cartCount");
    if (cc) { cc.textContent = d.count; cc.style.display = d.count ? "inline-block" : "none"; }
  }

  document.querySelectorAll(".js-qty").forEach(inp => {
    inp.addEventListener("change", function () {
      const id = this.dataset.item;
      const fd = new FormData(); fd.append("qty", this.value); fd.append("csrfmiddlewaretoken", csrf);
      fetch(`/cart/update/${id}/`, { method: "POST", headers: { "X-Requested-With": "XMLHttpRequest" }, body: fd })
        .then(r => r.json()).then(d => {
          const row = document.querySelector(`tr[data-item='${id}'] .js-line`);
          if (row) row.textContent = fmt(d.line_total);
          if (+this.value <= 0) document.querySelector(`tr[data-item='${id}']`).remove();
          refreshTotals(d);
        });
    });
  });

  document.querySelectorAll(".js-remove").forEach(btn => {
    btn.addEventListener("click", function () {
      const id = this.dataset.item;
      fetch(`/cart/remove/${id}/`, { method: "POST", headers: { "X-Requested-With": "XMLHttpRequest", "X-CSRFToken": csrf } })
        .then(r => r.json()).then(d => {
          const row = document.querySelector(`tr[data-item='${id}']`);
          if (row) row.remove();
          refreshTotals(d);
          if (!d.count) location.reload();
        });
    });
  });
})();
