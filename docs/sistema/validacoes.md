# Validações cíveis

O motor é determinístico. Recebe fatos vigentes e classe, separa os recorrentes, incorpora fatos comuns e guarda um achado por regra e recorrente. Os valores incluem a base legal, os fatos usados, os identificadores das evidências e das páginas e a versão do catálogo.

| Classe | Regras |
| --- | --- |
| Apelação cível | Tempestividade, preparo e representação |
| Agravo de instrumento | Tempestividade, preparo, representação e cabimento |
| Agravo interno | Tempestividade, preparo e representação |
| Embargos de declaração | Tempestividade e representação |
| Ação originária | Catálogo vazio |

A versão do catálogo é `0.3.0` (`validacoes/versao.py`). Cada regra declara em `PECA_PROCURADA` a peça que a pessoa deve procurar para cada tipo de fato, e a `Coleta` a consulta ao listar o que falta; tipo de fato novo entra no módulo da regra que o usa. O decorador `@regra` converte em achado de conferência a interrupção de uma regra por conflito num fato opcional: `Coleta.unico(..., obrigatorio=False)` com dois valores registra o conflito e levanta `FatoPendenteError`. Em fato obrigatório, a regra segue coletando os demais e devolve `coleta.verificar()` com todas as faltas e divergências. O `ModeloProcesso` memoriza, por instância, o resultado de `fato` e de `recorrentes`, e é o que os chamadores montam diretamente.

As dispensas de preparo e de mandato por qualidade do recorrente ficam em `validacoes/dados/dispensas.yaml`, versão `0.3.0`: cada qualidade tem `rotulo`, `preparo` e `mandato`. As regras de preparo e de representação e a extração das partes (`eventos/partes.py`) leem a mesma tabela (`dispensas_padrao()`). O reprocessamento cita a versão dessa tabela (`dispensas=`) nas versões dos fatos e do catálogo; uma versão nova regrava os fatos e os achados uma vez, com o mesmo resultado e o mesmo texto.

**Tempestividade.** A7 exclui o dia da intimação e conta dias úteis. Os prazos configurados são quinze dias para apelação e agravos e cinco para embargos. A qualidade da parte pode dobrar o prazo. O achado informa vencimento, protocolo, dias úteis de atraso e cada dia desconsiderado com sua fonte. A suspensão do art. 220 vale anualmente de 20 de dezembro a 20 de janeiro, inclusive. O calendário (`Calendario`) indexa cada feriado por data em um `FeriadoCalendario`, com descrição e fonte. `contar_prazo_util` e `dias_uteis_entre(inicio, fim)` percorrem o mesmo gerador de dias (não há contagem em dias corridos); a tempestividade conta o atraso com `dias_uteis_entre`, do termo ao protocolo. As tabelas empacotadas de feriados nacionais e locais cobrem 2026. A conferência de outro ano requer a tabela de feriados correspondente.

**Preparo.** A8 verifica a qualidade da parte, eventual gratuidade e a data do comprovante em relação ao protocolo. Pedido de gratuidade pendente exige conferência. A regra trata a presença e a data da prova e deixa o valor das custas para a pessoa responsável.

**Representação.** A9 verifica o mandato do recorrente ao subscritor, inclusive por cadeia de substabelecimentos. A comparação usa inscrição na OAB quando disponível e nome normalizado como alternativa. O achado liga as páginas dos instrumentos ou indica a falta de mandato ou de identificação.

**Cabimento.** A10 consulta a hipótese da decisão agravada no art. 1.015 do CPC. Retorna conforme quando identifica o inciso ou verificar para exame judicial. O resultado deixa a decisão de admissibilidade ao magistrado.

## Reprodução

Na raiz do repositório, com o worker em execução:

```sh
docker compose exec worker python -m lupa_pipeline.validacoes --fatos pipeline/tests/validacoes/fatos_exemplo.json --classe apelacao_civel --referencia 2026-10-20
```

A lista completa esperada está no gabarito [achados_exemplo.json](../../pipeline/tests/validacoes/achados_exemplo.json). Fato obrigatório ausente ou divergente leva a verificar, com os documentos procurados ou os identificadores conflitantes. As hipóteses de dispensa, o marco eletrônico e o calendário devem passar pela conferência do gabinete descrita na [seção 11 da especificação](../especificacao/0.2/especificacao.md).
