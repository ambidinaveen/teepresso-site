/* Teepresso — global storefront JS: live search, AJAX add-to-cart, wishlist */
(function () {
  const csrf = (window.TP && TP.csrf) || "";

  // --- Live search ---------------------------------------------------------
  const input = document.getElementById("liveSearch");
  const box = document.getElementById("searchResults");
  if (input && box) {
    let t;
    input.addEventListener("input", function () {
      clearTimeout(t);
      const q = this.value.trim();
      if (q.length < 2) { box.style.display = "none"; return; }
      t = setTimeout(() => {
        fetch(TP.searchUrl + "?q=" + encodeURIComponent(q))
          .then(r => r.json())
          .then(d => {
            if (!d.results.length) { box.style.display = "none"; return; }
            box.innerHTML = d.results.map(p =>
              `<a href="${p.url}"><img src="${p.image || ''}" onerror="this.style.visibility='hidden'">
                 <div><div style="font-weight:600">${p.name}</div>
                 <div class="small text-muted">${p.category} · ₹${Math.round(p.price)}</div></div></a>`
            ).join("");
            box.style.display = "block";
          });
      }, 220);
    });
    document.addEventListener("click", e => { if (!e.target.closest("#searchBox")) box.style.display = "none"; });
  }

  // --- AJAX add to cart ----------------------------------------------------
  document.querySelectorAll("form.js-add-cart").forEach(f => {
    f.addEventListener("submit", function (e) {
      e.preventDefault();
      fetch(this.action, { method: "POST", headers: { "X-Requested-With": "XMLHttpRequest" }, body: new FormData(this) })
        .then(r => r.json())
        .then(d => {
          if (d.ok) {
            const c = document.getElementById("cartCount");
            if (c) { c.textContent = d.count; c.style.display = "inline-block"; c.classList.add("cart-bump"); setTimeout(() => c.classList.remove("cart-bump"), 400); }
            toast(d.message || "Added to cart");
          }
        }).catch(() => this.submit());
    });
  });

  // --- Wishlist toggle -----------------------------------------------------
  document.querySelectorAll(".js-wish").forEach(btn => {
    btn.addEventListener("click", function (e) {
      e.preventDefault();
      const id = this.dataset.id;
      fetch(`/accounts/wishlist/${id}/toggle/`, { method: "POST", headers: { "X-Requested-With": "XMLHttpRequest", "X-CSRFToken": csrf } })
        .then(r => { if (r.status === 302 || r.redirected) { window.location = "/accounts/login/"; return null; } return r.json(); })
        .then(d => {
          if (!d) return;
          this.classList.toggle("active", d.added);
          const ic = this.querySelector("i");
          if (ic) ic.className = d.added ? "bi bi-heart-fill" : "bi bi-heart";
          toast(d.added ? "Added to wishlist ♥" : "Removed from wishlist");
        });
    });
  });

  // --- tiny toast ----------------------------------------------------------
  window.toast = function (msg) {
    let el = document.createElement("div");
    el.textContent = msg;
    el.style.cssText = "position:fixed;bottom:90px;left:50%;transform:translateX(-50%);background:#0f172a;color:#fff;padding:10px 18px;border-radius:999px;z-index:2000;font-size:.9rem;box-shadow:0 10px 30px rgba(0,0,0,.25)";
    document.body.appendChild(el);
    setTimeout(() => el.remove(), 2200);
  };
})();
