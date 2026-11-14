# Auditoria

A tabela `link_evento_auditoria` mantém uma cadeia única no gabinete. Cada nova ocorrência incorpora o hash anterior e recebe a posição seguinte dentro da transação. Um lock do banco serializa inserções concorrentes. Triggers e permissões protegem a cadeia contra alteração e remoção diretas. O desembargador pode verificar a primeira sequência inconsistente.

Os atos incluem autenticação, abertura de processos e páginas, upload, correção de fato, reclassificação de peça, uso do modelo, liberação de revisão, gestão de assessores, consulta ou exportação de auditoria e descarte. Cada evento traz data, ação, resultado, usuário, processo e referências de localização quando cabíveis. As colunas de auditoria guardam metadados que permitem rastrear o ato. Texto de páginas, perguntas e respostas permanece nos armazenamentos de conteúdo cifrado.

## Consulta e exportação

| Recurso da API sob `/api/auditoria` | Uso |
| --- | --- |
| `GET /` | Filtrar e paginar eventos |
| `GET /verificar` | Recalcular a cadeia e identificar a primeira divergência |
| `GET /exportar` | Exportar os eventos selecionados em CSV ou JSON |
| `GET /relatorio-uso` | Obter totais por processo ou usuário em JSON e exportar o período em CSV |

A tabela de chamadas ao modelo alimenta a contagem, o consumo de tokens e o custo estimado do relatório. A estimativa depende do preço configurado. O relatório é material de apoio à prestação de informações do gabinete. [Guia do desembargador](../guias/guia-desembargador.md).
