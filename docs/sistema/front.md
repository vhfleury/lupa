# Interface da intranet

O front é o pacote Django `lupa_web`, em `intranet/web/src/lupa_web/`, servido por uvicorn no
serviço `front` atrás do Caddy, sob HTTPS ([ADR 0019](../adr/0019-front-django-renderizado-no-servidor.md)).
O Django renderiza todas as telas no servidor e chama a API FastAPI por `httpx` na rede interna,
repassando o cookie de sessão da API e o IP do cliente; o proxy não expõe `/api`. O front não tem
banco, models nem sessão própria; o CSRF é do Django, por cookie. A interatividade usa HTMX, e os
estáticos (CSS, HTMX e os scripts de tema, envio e visualizador) saem pelo WhiteNoise com hash no nome, sem script
inline. O proxy acrescenta os cabeçalhos de segurança e a API valida a sessão e a permissão em
toda rota.

O visual segue o [padrão visual](padrao-visual.md): cores e fontes só em `tokens.css`, botão,
tabela, aviso, badge, selo e demais peças pelos templates de `templates/componentes/`, e o
catálogo na página `/padrao`, aberta só com `LUPA_AMBIENTE=desenvolvimento`.

Quando a API responde 401, a tela leva ao login; se o navegador ainda tinha o cookie de sessão, o
login mostra o aviso de sessão expirada (`/login?motivo=expirada`). Um 403 vira a página "Acesso
negado", e a API fora do ar vira "Serviço indisponível" (502). As ações que salvam e redirecionam
mostram a confirmação pelo parâmetro `?aviso=` (processo criado, anexado, já enviado,
responsáveis, peça reclassificada, consulta liberada).

Os dois papéis podem cadastrar um processo. Em **+ Novo processo**, a pessoa envia um PDF ou ZIP;
a barra mostra o progresso do envio. Se faltar número ou classe, a tela oferece os números
encontrados e pede só o campo necessário; o front guarda o arquivo por até 2 horas no volume
`envios-pendentes` e o reenvia com o complemento, sem novo upload. A tela do processo informa se
houve criação, anexo ou duplicidade e atualiza o estado dos arquivos até o estado final.

O cabeçalho do processo mostra partes, polos e dados da capa com suas fontes. **Corrigir classe**
registra a alteração e recalcula os achados. O processo dá acesso aos arquivos, responsáveis,
dossiê, índice de peças, histórico de fatos e achados e chat. A evidência abre o visualizador na
página do arquivo. No chat, a resposta chega sem recarregar a página; se ela puser o processo em
revisão, o aviso de revisão aparece na hora e o formulário fica bloqueado.

A gestão de assessores e a auditoria ficam no menu do desembargador. Os testes das telas usam
`pytest` com a API simulada por `respx` (`intranet/web/tests/`), e os fluxos pelo navegador e as
capturas dos guias usam `pytest-playwright` (`intranet/web/tests/e2e/`, marcador `e2e`).
[Guia de contribuição](../../CONTRIBUTING.md).
