# Ingestão de autos

A API recebe o corpo de `POST /api/processos/arquivos?nome=...` em um temporário e calcula o SHA-256 durante o envio. O sandbox inspeciona o PDF e extrai as primeiras páginas. Em ZIP, inventaria as entradas e lê o primeiro PDF. A janela padrão é de três páginas e o limite de tempo é de 30 segundos (`LUPA_IDENTIFICACAO_PAGINAS` e `LUPA_IDENTIFICACAO_TEMPO_SEGUNDOS`).

Na primeira página, um número CNJ válido após um rótulo tem precedência. Se a página inicial não tiver rótulo de número, um único CNJ válido distinto nas páginas lidas identifica o processo. Um rótulo com número inválido exige complemento, mesmo que haja um CNJ válido em uma referência a outro processo. A classe vem da linha rotulada na capa. Uma identificação incompleta devolve HTTP 422 com o que foi lido, os campos faltantes e os números encontrados. O cliente reenvia os bytes com o complemento na query. O temporário é removido ao fim de cada tentativa. A recusa estrutural também devolve 422, inclusive quando o cliente forneceu os dois campos.

A API serializa o cadastro pelo número. Cria o processo ou anexa o arquivo ao processo existente, preservando a classe corrente. Um processo descartado devolve 409. Para enviar diretamente ao processo aberto, use `POST /api/processos/{id}/arquivos`. Em ambos os fluxos, o arquivo novo recebe HTTP 201 e o reenvio dos mesmos bytes no mesmo processo, HTTP 200 com o identificador existente. O limite de envio vem de `LUPA_UPLOAD_LIMITE_BYTES`. O storage guarda o original e a view `v_fila_ingestao` seleciona as pendências.

## Processamento e retomada

O worker usa a mesma conexão física do PostgreSQL para obter um advisory lock de sessão, consultar a fila e processar o trabalho. Um segundo worker sai quando o primeiro mantém o lock. A perda dessa conexão invalida o consumidor. Cada tentativa começa por uma transação curta que registra o contador e verifica o estado corrente do processo. O intervalo de consulta e o máximo de tentativas são configuráveis.

O inventário distingue ZIP por peça, PDF com marcadores ou índice e PDF liso. O subprocesso de parsing verifica a estrutura e limita bytes descomprimidos, número de entradas, razão de expansão, memória, CPU e tempo de execução. Tipo recusado ou arquivo perigoso terminam em quarentena. Uma falha de recursos registra o motivo no relatório.

Cada página tem texto normalizado, origem da extração, blocos, coordenadas e sinalizações. O roteador seleciona texto nativo, OCR ou combinação para páginas híbridas. O saneamento identifica, entre outros sinais, texto fora da página, instrução em metadado e texto com baixa visibilidade. A revisão humana pode abrir o original. Os lotes já concluídos e suas páginas são recuperados após interrupção.

## Peças, partes e fatos

Nas primeiras páginas de cada arquivo o worker procura relator, órgão julgador, assunto, valor da causa, juízo de origem e distribuição. Cada fato é comum ao processo e tem evidência no intervalo do valor. O valor da causa é decimal em texto e a distribuição é data ISO. A ficha pode mostrar valores divergentes com suas respectivas fontes. A versão `civel-0.3.0` dos padrões aciona a reextração dos arquivos já processados.

O índice reúne as páginas de cada peça. A classificação combina títulos, fórmulas e assinaturas das peças cíveis. Uma reclassificação manual fica no histórico e orienta o reprocessamento. Os extratores usam qualificações da petição, da decisão e do recurso para reconhecer as partes. Cada fato contém o tipo, o valor, o sujeito, a confiança e a origem. Antes de armazenar o fato, o extrator confere a igualdade entre o trecho e o intervalo do texto normalizado.

Ao iniciar, o worker compara as versões das páginas, das regras de peças, dos extratores de fatos e do catálogo com o relatório de cada arquivo pronto. Uma alteração de catálogo recalcula os achados a partir dos fatos vigentes. Alterações nas peças ou nos fatos também refazem as etapas que dependem deles. A troca de extrator processa as páginas na nova versão. As anotações e as correções humanas conservam a autoria e a evidência.

O relatório do arquivo expõe o diagnóstico e as páginas pendentes. O processo pode ficar parcial se faltarem páginas. Com os fatos vigentes, o worker avalia as validações cabíveis e disponibiliza o dossiê. [Regras cíveis](validacoes.md).
