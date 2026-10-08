/* Teepresso — products page helpers (wishlist toggle is wired in main.js).
   This file is a hook for product-list specific behaviour (kept lightweight). */
(function () {
  // re-bind wishlist on dynamically inserted cards, if any
  document.querySelectorAll(".js-wish:not([data-bound])").forEach(b => b.setAttribute("data-bound", "1"));
})();
