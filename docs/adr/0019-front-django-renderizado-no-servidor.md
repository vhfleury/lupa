# ADR 0019 — Front Django renderizado no servidor

| Status | Data | Responsável |
| --- | --- | --- |
| Proposto | 2026-11-19 | Projeto Lupa |

Substitui o ADR [0006](0006-front-sveltekit-spa-atras-de-proxy.md) e, quanto aos pacotes, o
[0016](0016-dois-pacotes.md).

## Contexto

A intranet usava uma SPA SvelteKit servida pelo Caddy, que chamava a API FastAPI em `/api` pela
mesma origem. O front tinha lint, tipos, testes e build próprios em Node, e a CSP precisava de
exceção para um estilo gerado pelo framework.

## Restrições

A especificação da 0.2 (seção 4.12, decisões 46 a 53) fixa: front Django com templates, API sem
alteração, sessão só na API, sem banco no front, HTMX para a interatividade, pacote `lupa_web`
separado, `lupa_intranet` renomeado para `lupa_api`, troca de uma vez, suíte de navegador em
`pytest-playwright` e o mesmo visual.

## Alternativas consideradas

Manter o SvelteKit. Django substituindo também a API. Django sem HTMX, com recarga de página. Um
módulo Django dentro do pacote da API.

## Decisão

O serviço `front` passa a rodar o pacote `lupa_web` (Django em ASGI sob uvicorn), que renderiza
todas as telas e chama a API por `httpx` na rede interna, repassando o cookie de sessão e o IP do
cliente. O proxy deixa de expor `/api`. O front não tem banco, models nem sessão própria; CSRF é
do Django. HTMX e os estáticos são servidos pelo WhiteNoise, sem script inline, e a CSP perde
`unsafe-hashes`. O pacote da API passa a se chamar `lupa_api`, e o `record_source` das linhas
novas usa o prefixo `api.`.

## Consequências

O projeto deixa de depender de Node. Toda tela passa a ser testável com `pytest`. Cada tela custa
uma chamada a mais (navegador → Django → API). As linhas de auditoria antigas mantêm o prefixo
`intranet.`. As capturas dos guias são regeradas.

## Fontes

- [Especificação da 0.2, seção 4.12 e decisões 46 a 53](../especificacao/0.2/especificacao.md)
- [Plano do front em Django](../planos/plano_front_django.md)
- [Registro de decisões](../decisoes/registro.md)
