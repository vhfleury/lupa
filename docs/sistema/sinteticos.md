# Autos sintéticos e medição

O gerador cria autos cíveis reprodutíveis pela semente, em cinco classes. Produz PDF liso, PDF com índice e marcadores ou ZIP com um PDF por peça. A configuração escolhe a mistura de páginas nativas, digitalizadas e híbridas, versos em branco, peças em duas colunas, situação do preparo, representação, tempestividade e vetores de injeção.

Na imagem do worker, este comando gera uma apelação pequena sob o diretório temporário do contêiner:

```sh
python pipeline/scripts/gerar_autos.py --destino /tmp/autos processo --semente 19 --classe apelacao_civel --paginas 25 --cenarios pdf_liso
```

O gabarito ao lado dos autos descreve a classe, a composição e o texto de cada folha, os intervalos das peças e as partes, fatos, sujeitos e resultados esperados. Cada trecho marcado deve coincidir com os offsets no texto visível da página. A numeração física de cada PDF é mapeada à folha de conteúdo, inclusive quando o índice desloca o primeiro documento.

O conjunto de referência contém dez sementes de 200 a 5.000 páginas. O corpus de injeção usa uma variante para cada vetor e uma com todos. Os números CNJ estão na faixa fictícia e o gerador de CPF cria dígitos verificadores inválidos. A medição confronta o índice, os tipos de página e peça, os eventos e as datas com o gabarito. Para os comandos dos verificadores, consulte [CONTRIBUTING.md](../../CONTRIBUTING.md).
