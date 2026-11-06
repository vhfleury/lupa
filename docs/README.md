# Documentação do Lupa

Índice da pasta `docs/`. As convenções de código estão no [`CLAUDE.md`](../CLAUDE.md) e a instalação de desenvolvimento no [README da raiz](../README.md).

## Piloto: o que fazer agora

- [piloto/roteiro-piloto.md](piloto/roteiro-piloto.md): o que falta, em ordem, com quem faz e quando termina.
- [piloto/pendencias.md](piloto/pendencias.md): decisões e tarefas em aberto.
- [piloto/calibracao-projudi.md](piloto/calibracao-projudi.md): como rodar o primeiro processo real do Projudi.

## Especificação

- [especificacao/requisitos-v1.md](especificacao/requisitos-v1.md): decisões de produto da primeira versão.
- [especificacao/arquitetura.md](especificacao/arquitetura.md): desenho original do sistema e princípios.
- [especificacao/catalogo-validacoes.md](especificacao/catalogo-validacoes.md): regras jurídicas das validações.
- [especificacao/prompt-injection.md](especificacao/prompt-injection.md): controles contra injeção de instruções nos autos.

## Como o sistema funciona

| Documento | Assunto |
| --- | --- |
| [sistema/modelo-de-dados.md](sistema/modelo-de-dados.md) | diagrama, regras impostas pelo banco, RLS por gabinete |
| [sistema/ingestao.md](sistema/ingestao.md) | pipeline de ingestão: fila, sandbox, OCR, saneamento, fronteiras, eventos |
| [sistema/validacoes.md](sistema/validacoes.md) | as três validações do piloto e o que o gabinete precisa confirmar |
| [sistema/agente.md](sistema/agente.md) | contrato do agente e do chat |
| [sistema/auditoria.md](sistema/auditoria.md) | o que a auditoria registra e como verificar a cadeia |
| [sistema/criptografia.md](sistema/criptografia.md) | cifra em repouso e Vault |
| [sistema/front.md](sistema/front.md) | interface web, proxy e testes E2E |
| [sistema/sinteticos.md](sistema/sinteticos.md) | gerador de autos sintéticos e medição |

## Operação

- [operacao/operacao.md](operacao/operacao.md): manual do responsável técnico (instalação, atualização, Vault, certificado, monitoramento, incidentes).
- [operacao/backup.md](operacao/backup.md): backup cifrado, restauração e expurgo.

## Guias dos usuários

- [guias/guia-assessor.md](guias/guia-assessor.md)
- [guias/guia-desembargador.md](guias/guia-desembargador.md)

As capturas de tela ficam em `imagens/`, gravadas por `front/scripts/capturas.sh`.

## Conformidade (LGPD e Res. CNJ 615/2025)

Minutas para revisão de advogado em [conformidade/](conformidade/): aviso de tratamento, termos de uso, registro de operações, plano de incidentes, relatório de uso ao tribunal e checklist do piloto.

## Histórico da construção

- [etapas/CONFORMIDADE-GERAL.md](etapas/CONFORMIDADE-GERAL.md): estado e métricas ao fim das Etapas 0 a 8.2.
- [decisoes/registro.md](decisoes/registro.md): decisões tomadas em cada etapa e resultado das revisões.
- [decisoes/object-storage.md](decisoes/object-storage.md): decisão do object storage.
- [etapas/FICOU-DE-FORA.md](etapas/FICOU-DE-FORA.md): limitações e itens fora do escopo de cada etapa.
- `etapas/RELATORIO-ETAPA-*.md`: os relatórios de etapa citados pelo código e pelos manuais. Os demais estão no histórico do Git.

## Outros

- `exemplos/fatos.json`: exemplo de entrada do motor de validações, usado pelos testes.
- `contexto/`: relatórios de pesquisa usados no desenho (gabinete do TJGO, dados judiciais, prompt injection).
