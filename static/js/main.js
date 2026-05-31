/* Версия для слабовидящих — управление параметрами */
(function () {
  var body = document.body;
  var COOKIE = "vi_settings";

  function readCookie() {
    var m = document.cookie.match(/(?:^|; )vi_settings=([^;]*)/);
    if (!m) return null;
    try { return JSON.parse(decodeURIComponent(m[1])); } catch (e) { return null; }
  }
  function saveCookie(s) {
    document.cookie = COOKIE + "=" + encodeURIComponent(JSON.stringify(s)) +
      ";path=/;max-age=" + (60 * 60 * 24 * 180);
  }

  var state = readCookie() || { on: false, scheme: "bw", fs: "fs-1", noimg: false };

  function apply() {
    body.classList.toggle("vi", state.on);
    ["scheme-bw", "scheme-wb", "scheme-bg", "scheme-bb"].forEach(function (c) {
      body.classList.remove(c);
    });
    ["fs-1", "fs-2", "fs-3"].forEach(function (c) { body.classList.remove(c); });
    body.classList.remove("noimg");
    if (state.on) {
      body.classList.add("scheme-" + state.scheme);
      body.classList.add(state.fs);
      if (state.noimg) body.classList.add("noimg");
    }
    var panel = document.getElementById("vi-panel");
    if (panel) panel.classList.toggle("show", state.on);
    syncButtons();
  }

  function syncButtons() {
    document.querySelectorAll("[data-scheme]").forEach(function (b) {
      b.classList.toggle("active", b.dataset.scheme === state.scheme);
    });
    document.querySelectorAll("[data-fs]").forEach(function (b) {
      b.classList.toggle("active", b.dataset.fs === state.fs);
    });
    var ni = document.getElementById("vi-noimg");
    if (ni) ni.classList.toggle("active", state.noimg);
  }

  window.viEnable = function () { state.on = true; saveCookie(state); apply(); };
  window.viDisable = function () { state.on = false; saveCookie(state); apply(); };

  document.addEventListener("click", function (e) {
    var t = e.target.closest("[data-scheme],[data-fs],#vi-noimg,#vi-on,#vi-off");
    if (!t) return;
    e.preventDefault();
    if (t.id === "vi-on") { state.on = true; }
    else if (t.id === "vi-off") { state.on = false; }
    else if (t.dataset.scheme) { state.scheme = t.dataset.scheme; }
    else if (t.dataset.fs) { state.fs = t.dataset.fs; }
    else if (t.id === "vi-noimg") { state.noimg = !state.noimg; }
    saveCookie(state);
    apply();
  });

  apply();

  /* Слайдер баннеров на главной */
  var dots = document.querySelectorAll(".hero-dots span");
  var slides = window.__heroSlides || [];
  if (dots.length && slides.length) {
    var idx = 0;
    var hT = document.querySelector(".hero h1");
    var hP = document.querySelector(".hero p");
    var hA = document.querySelector(".hero .btn");
    function show(i) {
      idx = i;
      dots.forEach(function (d, k) { d.classList.toggle("on", k === i); });
      if (hT) hT.textContent = slides[i].title;
      if (hP) hP.textContent = slides[i].subtitle;
      if (hA) { hA.textContent = slides[i].cta; hA.setAttribute("href", slides[i].link); }
    }
    dots.forEach(function (d, k) { d.addEventListener("click", function () { show(k); }); });
    setInterval(function () { show((idx + 1) % slides.length); }, 5000);
  }
})();
