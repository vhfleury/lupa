// Tema claro, escuro ou do sistema (D8), como o SeletorTema.svelte: a escolha fica só no
// localStorage deste navegador, em "lupa.tema". Carregado sem defer no <head>, aplica o tema salvo
// antes da primeira pintura; depois liga os seletores marcados com data-seletor-tema.
(function () {
  'use strict';

  var CHAVE = 'lupa.tema';
  var VALIDOS = ['claro', 'escuro', 'sistema'];
  var PADRAO = 'escuro';
  var raiz = document.documentElement;

  function lerTema() {
    try {
      var valor = window.localStorage.getItem(CHAVE);
      return VALIDOS.indexOf(valor) >= 0 ? valor : PADRAO;
    } catch (erro) {
      return PADRAO;
    }
  }

  function gravarTema(tema) {
    try {
      window.localStorage.setItem(CHAVE, tema);
    } catch (erro) {
      return;
    }
  }

  function aplicarTema(tema) {
    if (tema === 'sistema') delete raiz.dataset.tema;
    else raiz.dataset.tema = tema;
  }

  function ligarSeletores() {
    var tema = lerTema();
    var seletores = document.querySelectorAll('select[data-seletor-tema]');
    Array.prototype.forEach.call(seletores, function (seletor) {
      seletor.value = tema;
      seletor.addEventListener('change', function () {
        aplicarTema(seletor.value);
        gravarTema(seletor.value);
      });
    });
  }

  aplicarTema(lerTema());
  document.addEventListener('DOMContentLoaded', ligarSeletores);
})();
