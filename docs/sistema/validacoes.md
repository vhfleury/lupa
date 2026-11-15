# Validações cíveis

O motor é determinístico. Recebe fatos vigentes e classe, separa os recorrentes, incorpora fatos comuns e guarda um achado por regra e recorrente. Os valores incluem a base legal, os fatos usados, os identificadores das evidências e das páginas e a versão do catálogo.

| Classe | Regras |
| --- | --- |
| Apelação cível | Tempestividade, preparo e representação |
| Agravo de instrumento | Tempestividade, preparo, representação e cabimento |
| Agravo interno | Tempestividade, preparo e representação |
| Embargos de declaração | Tempestividade e representação |
| Ação originária | Catálogo vazio |

**Tempestividade.** A7 exclui o dia da intimação e conta dias úteis. Os prazos configurados são quinze dias para apelação e agravos e cinco para embargos. A qualidade da parte pode dobrar o prazo. O achado informa vencimento, protocolo, dias úteis de atraso e cada dia desconsiderado com sua fonte. A suspensão do art. 220 vale anualmente de 20 de dezembro a 20 de janeiro, inclusive. As tabelas empacotadas de feriados nacionais e locais cobrem 2026. A conferência de outro ano requer a tabela de feriados correspondente.

**Preparo.** A8 verifica a qualidade da parte, eventual gratuidade e a data do comprovante em relação ao protocolo. Pedido de gratuidade pendente exige conferência. A regra trata a presença e a data da prova e deixa o valor das custas para a pessoa responsável.

**Representação.** A9 verifica o mandato do recorrente ao subscritor, inclusive por cadeia de substabelecimentos. A comparação usa inscrição na OAB quando disponível e nome normalizado como alternativa. O achado liga as páginas dos instrumentos ou indica a falta de mandato ou de identificação.

**Cabimento.** A10 consulta a hipótese da decisão agravada no art. 1.015 do CPC. Retorna conforme quando identifica o inciso ou verificar para exame judicial. O resultado deixa a decisão de admissibilidade ao magistrado.

## Reprodução

Na raiz do repositório, com o worker em execução:

```sh
docker compose exec worker python -m lupa_pipeline.validacoes --fatos pipeline/tests/validacoes/fatos_exemplo.json --classe apelacao_civel --referencia 2026-10-20
```

A lista completa esperada está no gabarito [achados_exemplo.json](../../pipeline/tests/validacoes/achados_exemplo.json). Fato obrigatório ausente ou divergente leva a verificar, com os documentos procurados ou os identificadores conflitantes. As hipóteses de dispensa, o marco eletrônico e o calendário devem passar pela conferência do gabinete descrita na [seção 11 da especificação](../especificacao/0.2/especificacao.md).
