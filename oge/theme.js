// Тема и роль — те же ключи localStorage, что и в основном кабинете (startum_theme, startum_role).
(function () {
  var d = document.documentElement;
  try {
    var t = localStorage.getItem('startum_theme');
    if (t === 'light' || t === 'dark') d.dataset.theme = t;
    var r = localStorage.getItem('startum_role');
    if (r) d.dataset.role = r === 's' ? 's' : 't';
  } catch (e) {}
})();
