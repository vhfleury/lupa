# Documentação do Lupa

Índice da pasta `docs/`. As convenções de código estão no [`CLAUDE.md`](../CLAUDE.md) e a instalação de desenvolvimento no [README da raiz](../README.md).

## Visão geral

- [arquitetura.md](arquitetura.md): limite do sistema, componentes, uma execução de ponta a ponta e o estado das mudanças.
- [adr/](adr/README.md): registros de decisão de arquitetura, um arquivo por decisão.
- [runbooks/](runbooks/README.md): procedimentos operacionais com resultado observável.
- Na raiz: [CONTRIBUTING.md](../CONTRIBUTING.md), [CHANGELOG.md](../CHANGELOG.md) e [CODE_OF_CONDUCT.md](../CODE_OF_CONDUCT.md).

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

As minutas para revisão de advogado estão em [Conformidade do Lupa](conformidade/CONFORMIDADE.md).

- [Termos de uso do Lupa](conformidade/CONFORMIDADE.md#termos-de-uso) e [aceite pelo gabinete](conformidade/CONFORMIDADE.md#aceite-dos-termos)
- [Aviso de tratamento de dados pessoais](conformidade/CONFORMIDADE.md#aviso-de-tratamento) e [registro das operações de tratamento](conformidade/CONFORMIDADE.md#registro-de-operacoes)
- [Plano de resposta a incidentes](conformidade/CONFORMIDADE.md#plano-de-incidentes)
- [Modelo de relatório de uso ao tribunal](conformidade/CONFORMIDADE.md#relatorio-uso-tribunal)
- [Checklist antes do primeiro processo real](conformidade/CONFORMIDADE.md#checklist-piloto)

## Histórico da construção

- [Relatórios, limitações e pendências por etapa](etapas/ETAPAS.md#etapas-e-pendencias). Os demais relatórios de execução estão no histórico do Git.
- [Conformidade geral](etapas/ETAPAS.md#conformidade-geral) reúne o estado e as métricas até a 8.2.
- [decisoes/registro.md](decisoes/registro.md): decisões tomadas em cada etapa e resultado das revisões. As que definem a arquitetura têm registro próprio em [adr/](adr/README.md).
- [decisoes/object-storage.md](decisoes/object-storage.md): decisão do object storage.

## Outros

- `contexto/`: relatórios de pesquisa usados no desenho (gabinete do TJGO, dados judiciais, prompt injection).
