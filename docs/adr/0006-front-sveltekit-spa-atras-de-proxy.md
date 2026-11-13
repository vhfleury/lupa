# ADR 0006 — Front em SvelteKit como SPA estática atrás de proxy

| Status | Data | Responsável |
| --- | --- | --- |
| Aceito | `{{data exata da decisão}}` (até 2026-10-22, data do primeiro commit) | Executor da Etapa 6; endossada nas revisões 6.1-6.3 e 6.4-6.9 |

## Contexto

A interface precisa de login, upload, dossiê, visualizador de página, chat e auditoria. Toda a autorização está na API.

## Restrições

- Cookie de sessão `Secure` e `SameSite=Strict`.
- CSP sem nada inline.
- Node não existe no host; o build roda em contêiner.

## Alternativas consideradas

| Alternativa | Por que foi descartada |
| --- | --- |
| Next.js | Traria React e um servidor Node para SSR que o sistema não usa. Uma SPA estática não precisa repassar cookie em servidor intermediário. |
| Biblioteca de UI | Dispensada: CSS próprio com tokens; a única dependência de execução é `qrcode`. |
| `root_path` na API | O proxy remove o prefixo `/api`; `api/app.py` fica intocado e não há CORS. |
| pdf.js com o PDF cru no navegador | O PDF chegaria ao navegador e o texto oculto seria desenhado. O servidor renderiza a página como imagem. |

## Decisão

SvelteKit 2 com Svelte 5, `adapter-static`, `ssr = false`. O serviço `front` serve os arquivos por Caddy; o serviço `proxy` (Caddy 2.8.4) entrega `/` ao front e `/api/*` à API, no mesmo origin. A imagem do front só é gerada se lint, typecheck e testes passarem.

## Consequências

- A API roda com `--proxy-headers` restrito à sub-rede `borda`, para a auditoria registrar o IP do cliente.
- Conteúdo visível no PDF aparece como está no visualizador.
- Os lockfiles são gerados em contêiner `node:22.12.0-alpine3.20`.

## Fontes

- [decisoes/registro.md](../decisoes/registro.md), 6.1 e revisões da Etapa 6
- [sistema/front.md](../sistema/front.md)
- [front/README.md](../../front/README.md)
