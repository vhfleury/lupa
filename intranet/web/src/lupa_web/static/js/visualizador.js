// Atalhos de teclado do visualizador (D8): com o foco na moldura da pagina, as setas trocam de
// pagina e + e - mudam o zoom, seguindo os mesmos links da barra (data-atalho). O destino volta
// com #moldura, e a moldura recebe o foco de novo para o proximo atalho.
(function () {
  'use strict';

  var TECLAS = {
    ArrowLeft: 'anterior',
    ArrowRight: 'proxima',
    '-': 'menos-zoom',
    '+': 'mais-zoom',
    '=': 'mais-zoom'
  };

  function seguir(atalho) {
    var link = document.querySelector('a[data-atalho="' + atalho + '"]');
    if (!link) return false;
    window.location.assign(link.getAttribute('href') + '#moldura');
    return true;
  }

  document.addEventListener('DOMContentLoaded', function () {
    var moldura = document.getElementById('moldura');
    if (!moldura) return;
    if (window.location.hash === '#moldura') moldura.focus();
    moldura.addEventListener('keydown', function (evento) {
      var atalho = TECLAS[evento.key];
      if (atalho && seguir(atalho)) evento.preventDefault();
    });
  });
})();
