# Arquitetura do Lupa

Descreve o sistema como está no código. O desenho original, anterior à implementação, está em
[especificacao/arquitetura.md](especificacao/arquitetura.md); o que os
[requisitos da v1](especificacao/requisitos-v1.md) mudaram nele está registrado nos [ADRs](adr/README.md).

## Limite do sistema

| Lado | Quem | O quê | Como |
| --- | --- | --- | --- |
| Entrada | Assessor do gabinete | PDF ou ZIP dos autos, exportado do Projudi/PJD do TJGO | upload pela interface: `POST /processos/{id}/arquivos?nome=<arquivo>` |
| Entrada | Assessor e desembargador | perguntas ao chat, correções de fato, reclassificação de peça, anotações | interface web |
| Entrada | Gabinete | calendários, prazos e tabelas jurídicas | YAML versionados em `src/lupa/validacoes/dados/` e `src/lupa/ingestao/dados/` |
| Saída | Assessor e desembargador | dossiê, achados, visualizador de página, respostas do chat | interface web, em `/` |
| Saída | Desembargador e administrador | auditoria e relatório de uso para o tribunal | tela Auditoria e exportação CSV |
| Saída | Responsável técnico | métricas e alertas | `GET /metricas/servico`, Prometheus e Grafana |
| Serviço externo | Fornecedor do modelo (API da Anthropic, pelo Claude Agent SDK) | recebe trechos pseudonimizados e a pergunta; devolve a resposta | só a `api` chama; o `worker` não tem saída de rede |

Não há integração com o Projudi nem com o DataJud. O tribunal não acessa o sistema. A primeira
versão aceita só processos públicos: processo sigiloso recebe 403 no upload.

## Componentes

Todos rodam em contêineres do Docker Compose, num único host. As redes `interna` e `ingestao` não
publicam portas; a `ingestao` é `internal: true` (sem rota para fora).

| Componente | Responsabilidade | Onde executa |
| --- | --- | --- |
| `proxy` (Caddy 2.8.4) | HTTPS, cabeçalhos de segurança, front em `/` e API em `/api` | contêiner `proxy`; redes `borda` e `cliente`; única porta publicada em produção |
| `front` (SvelteKit, SPA estática) | telas de login, processos, dossiê, visualizador, chat, auditoria e usuários | contêiner `front`; rede `borda` |
| `api` (FastAPI) | autenticação, autorização por gabinete, recepção e lacre, rotas de leitura, agente e chat, auditoria | contêiner `api`; redes `interna` e `borda` |
| `worker` | validação do arquivo, diagnóstico, extração de páginas, saneamento, peças, eventos, catálogo de validações | contêiner `worker` (`python -m lupa.ingestao.worker`); rede `ingestao` |
| Sandbox de parsing | abre PDF e roda OCR com limites de memória, CPU e tempo | subprocesso `python -I` dentro do `worker` |
| `redis` (7.4) | fila RQ, sem persistência | contêiner `redis`; redes `interna` e `ingestao` |
| `db` (PostgreSQL 16) | dados estruturados, RLS por gabinete, cadeia de auditoria | contêiner `db`; volume `db-dados` |
| `minio` | originais, entradas de ZIP e cache de PNG, já cifrados pela aplicação | contêiner `minio`; volume `minio-dados` |
| `vault` (1.21.3, Transit) | chave de cada gabinete; envelopa a DEK de cada processo | contêiner `vault`; volume `vault-dados` |
| `backup` e `backup-agendado` | backup cifrado com `age`, restauração e expurgo | perfis `backup` e `agendamento` (ligado no perfil de produção) |
| `prometheus` e `grafana` | métricas, painel "Lupa — piloto" e alertas | perfil `monitoramento` |

Detalhes por parte: [modelo de dados](sistema/modelo-de-dados.md), [ingestão](sistema/ingestao.md),
[validações](sistema/validacoes.md), [agente](sistema/agente.md), [auditoria](sistema/auditoria.md),
[criptografia](sistema/criptografia.md), [front](sistema/front.md).

## Uma execução de ponta a ponta

Um arquivo de autos, do upload aos achados.

| Passo | Origem | Destino | Granularidade | Chave |
| --- | --- | --- | --- | --- |
| 1. Recepção e lacre (`api`) | corpo do `POST /processos/{id}/arquivos` | objeto `gabinete/<id>/processo/<id>/<sha256>` no storage; linha em `arquivo`; job `recebido` em `job_ingestao` | um arquivo | `arquivo`: única `(processo_id, sha256)`; `job_ingestao`: única `(arquivo_id)` |
| 2. Fila | `job_id` e `gabinete_id` | fila RQ no Redis | um job | o estado do job fica em `job_ingestao`, não no Redis |
| 3. Validação (`worker`) | objeto do storage | `lote_ingestao`; job em `validado`, `quarentena` ou `falho` | PDF: um lote; ZIP: um lote por entrada | `lote_ingestao`: única `(job_id, numero)` |
| 4. Diagnóstico | PDF | `diagnostico_arquivo` | um por arquivo | única `(arquivo_id)` |
| 5. Extração de páginas | PDF, em lotes de 8 páginas no sandbox | `pagina` (texto, coordenadas, sinais, flags) | uma linha por página | única `(arquivo_id, numero)`, com `versao_extrator` |
| 6. Peças e índice | `pagina` | `peca` | uma linha por peça; só as `vigente` valem | `peca.id`; índice `(arquivo_id, vigente)` |
| 7. Eventos | `pagina` e `peca` | `evidencia`, `fato`, `fato_evidencia`, `reu`, `reu_identidade` | um fato por tipo e valor | `fato.id` derivado de (processo, tipo, valor, evidências) |
| 8. Catálogo | `fato` | `achado` | um achado por validação e réu | `achado.id`; só grava quando difere do último da mesma validação |

`processo` é único por `(gabinete_id, numero_cnj)`. Toda tabela com `gabinete_id` tem RLS forçada
e FK composta `(x_id, gabinete_id)` para o pai.

### Rastrear um achado até a origem

`achado.fatos_usados` → `fato` → `fato_evidencia` → `evidencia` (`pagina_id`, `trecho`, `inicio`,
`fim`, hash) → `pagina` (`arquivo_id`, `numero`) → `arquivo.sha256` → objeto
`gabinete/<id>/processo/<id>/<sha256>`. Um fato sem evidência é recusado por trigger no banco.

### Falha e reexecução

- **Mesmo arquivo enviado de novo ao mesmo processo:** resposta 200 com `duplicado: true`; nenhum
  `arquivo`, objeto ou job novo.
- **Mesmo arquivo em outro processo do gabinete:** o worker copia as páginas já extraídas na versão
  corrente do extrator e pula a extração.
- **Worker morre no meio:** o lease vence; o varredor reenfileira o job. O sucessor recebe um
  `fencing_token` novo e reaproveita os lotes já gravados. O worker antigo recebe
  `LeasePerdidoError` e não grava.
- **Redis reinicia ou perde a mensagem:** o varredor reenfileira jobs `recebido` sem lease há mais
  de 30 s.
- **Parser estoura limite:** `tempo_esgotado` e `erro_parser` voltam a `recebido` até
  `LUPA_MAX_RETENTATIVAS` (2) vezes; `limite_memoria` e `limite_cpu` vão direto a `falho`.
- **Aquisições demais:** depois de `LUPA_MAX_TENTATIVAS` (3) o job vai a `falho` com `erro_interno`.
- **Arquivo inválido:** `quarentena`, estado final, com motivo obrigatório.
- **Extração incompleta:** `parcial`, com a lista das páginas que faltam no relatório do job.
- **Reexecução da extração:** páginas na versão corrente (`VERSAO_EXTRATOR`, hoje `4f.0`) são
  puladas; a gravação é upsert. Mudar a versão refaz todas.
- **Mudança só em `eventos.yaml` ou `tipos_penais.yaml`:** regrava fatos e achados, sem tocar
  páginas e peças. Fatos anotados ou corrigidos por pessoa são preservados.
- **Vault selado:** a `api` responde 503 em `/saude` e erro nas rotas de processo; siga o runbook
  [destravar o Vault](runbooks/destravar-vault.md).

## Decisões e procedimentos

- Decisões de arquitetura: [adr/](adr/README.md). Registro completo por etapa:
  [decisoes/registro.md](decisoes/registro.md).
- Runbooks: [runbooks/](runbooks/README.md). Manual do responsável técnico:
  [operacao/operacao.md](operacao/operacao.md). Backup: [operacao/backup.md](operacao/backup.md).

## Estado das mudanças

Estado registrado nas pendências do piloto (removido; ver histórico do Git) em 22/10/2026. Confira antes de agir.

| Item | Status |
| --- | --- |
| Ingestão, validações, agente, interface, criptografia em repouso, backup e monitoramento | Implementado e verificado em desenvolvimento com autos sintéticos |
| Instalação no servidor do piloto (perfil de produção, Vault com três partes, certificado real) | Planejado; nenhum ambiente de produção registrado no repositório |
| Primeiro processo real | Planejado; depende do [checklist do piloto](conformidade/CONFORMIDADE.md#checklist-piloto) |
| Pseudonimização de vítimas e testemunhas | Em decisão (opções A e B nas pendências do piloto (removido; ver histórico do Git)) |
| Imagem do object storage | Proposto ([ADR 0008](adr/0008-imagem-do-object-storage.md)) |
| Semáforo por gabinete no Redis, para mais de uma réplica do worker | Planejado, sem data |
| Canal de notificação dos alertas (Alertmanager) | Planejado, sem data |
| TLS entre `api`/`worker` e Vault | Planejado; a reavaliar se o Vault sair do host |
| Validações semânticas, catálogo cível, processos em segredo de justiça, integração com o Projudi | Fora do escopo da v1 |
