# Registros de decisão de arquitetura (ADR)

Um arquivo por decisão, `NNNN-titulo.md`. O registro completo das decisões de cada etapa continua em
[decisoes/registro.md](../decisoes/registro.md); aqui ficam as que definem a arquitetura.

Status possíveis: Proposto, Aceito, Rejeitado ou Substituído. Quando uma decisão substitui outra,
crie um ADR novo e ligue os dois.

| ADR | Decisão | Status |
| --- | --- | --- |
| [0001](0001-isolamento-por-gabinete-com-rls.md) | Isolamento por gabinete com RLS e `gabinete_id` desnormalizado | Aceito |
| [0002](0002-fila-rq-com-banco-como-fonte-da-verdade.md) | Fila RQ com o banco como fonte da verdade | Aceito |
| [0003](0003-sandbox-de-parsing-por-subprocesso.md) | Sandbox de parsing por subprocesso com limites | Aceito |
| [0004](0004-autenticacao-local-com-totp.md) | Autenticação local com senha e TOTP | Aceito |
| [0005](0005-agente-com-claude-agent-sdk.md) | Agente com o Claude Agent SDK e modelo externo | Aceito |
| [0006](0006-front-sveltekit-spa-atras-de-proxy.md) | Front em SvelteKit como SPA estática atrás de proxy | Aceito |
| [0007](0007-cifra-na-aplicacao-com-dek-por-processo.md) | Cifra na aplicação com DEK por processo | Aceito |
| [0008](0008-imagem-do-object-storage.md) | Imagem do object storage | Proposto |
| [0009](0009-dependencias-com-pip-compile.md) | Dependências com `pip-compile` a partir de `.in` | Substituído por 0010 |
| [0010](0010-dependencias-no-pyproject-com-uv.md) | Dependências só no `pyproject.toml`, travadas com `uv` | Aceito |
| [0011](0011-leitura-de-legado-em-claro.md) | Leitura de dado legado em claro | Substituído por 0012 |
| [0012](0012-recusa-de-dado-em-claro.md) | Dado em claro é recusado na leitura | Aceito |

## Modelo

```markdown
# ADR NNNN — Título

| Status | Data | Responsável |
| --- | --- | --- |
| Proposto | AAAA-MM-DD | nome |

## Contexto
## Restrições
## Alternativas consideradas
## Decisão
## Consequências
## Fontes
```
