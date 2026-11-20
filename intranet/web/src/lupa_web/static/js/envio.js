// Barra de progresso do envio de autos (D8): o HTMX emite htmx:xhr:progress durante o upload.
(function () {
  'use strict';

  function barraDo(evento) {
    var formulario = evento.target.closest ? evento.target.closest('form.form-envio') : null;
    return formulario ? formulario.querySelector('.progresso') : null;
  }

  document.addEventListener('htmx:xhr:progress', function (evento) {
    var barra = barraDo(evento);
    if (!barra || !evento.detail.lengthComputable) return;
    var percentual = Math.floor((evento.detail.loaded / evento.detail.total) * 100);
    barra.hidden = false;
    barra.querySelector('progress').value = percentual;
    barra.querySelector('.percentual').textContent = String(percentual);
  });

  document.addEventListener('htmx:afterRequest', function (evento) {
    var barra = barraDo(evento);
    if (barra) barra.hidden = true;
  });
})();
