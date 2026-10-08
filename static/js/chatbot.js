/* Teepresso — Teebot rule-based support chatbot widget */
(function () {
  const toggle = document.getElementById("botToggle");
  const boxEl = document.getElementById("chatbox");
  const closeBtn = document.getElementById("botClose");
  const body = document.getElementById("chatBody");
  const form = document.getElementById("chatForm");
  const inp = document.getElementById("chatInput");
  if (!toggle || !boxEl) return;

  function add(text, who) {
    const m = document.createElement("div");
    m.className = "chat-msg " + who;
    m.innerHTML = text;
    body.appendChild(m);
    body.scrollTop = body.scrollHeight;
  }
  let greeted = false;
  function open() {
    boxEl.classList.add("open");
    if (!greeted) { add("Hi! I'm <b>Teebot</b> 🤖 — ask me about products, delivery, bulk orders or tracking.", "bot"); greeted = true; }
  }
  toggle.addEventListener("click", () => boxEl.classList.contains("open") ? boxEl.classList.remove("open") : open());
  closeBtn.addEventListener("click", () => boxEl.classList.remove("open"));

  form.addEventListener("submit", function (e) {
    e.preventDefault();
    const q = inp.value.trim();
    if (!q) return;
    add(q, "me"); inp.value = "";
    add('<span class="spin"><i class="bi bi-arrow-repeat"></i></span>', "bot");
    fetch(TP.chatUrl + "?q=" + encodeURIComponent(q))
      .then(r => r.json())
      .then(d => { body.lastChild.remove(); add(d.reply, "bot"); })
      .catch(() => { body.lastChild.remove(); add("Sorry, I'm having trouble right now.", "bot"); });
  });
})();
