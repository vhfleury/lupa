# Ingestão de autos

A API recebe `POST /api/processos/{id}/arquivos`. O arquivo novo recebe um identificador e HTTP 201. O reenvio dos mesmos bytes no mesmo processo devolve o identificador existente e HTTP 200. O limite de upload vem de `LUPA_UPLOAD_LIMITE_BYTES`. O storage guarda o original cifrado. A view `v_fila_ingestao` seleciona as pendências.

## Processamento e retomada

O worker usa a mesma conexão física do PostgreSQL para obter um advisory lock de sessão, consultar a fila e processar o trabalho. Um segundo worker sai quando o primeiro mantém o lock. A perda dessa conexão invalida o consumidor. Cada tentativa começa por uma transação curta que registra o contador e verifica o estado corrente do processo. O intervalo de consulta e o máximo de tentativas são configuráveis.

O inventário distingue ZIP por peça, PDF com marcadores ou índice e PDF liso. O subprocesso de parsing verifica a estrutura e limita bytes descomprimidos, número de entradas, razão de expansão, memória, CPU e tempo de execução. Tipo recusado ou arquivo perigoso terminam em quarentena. Uma falha de recursos registra o motivo no relatório.

Cada página tem texto normalizado, origem da extração, blocos, coordenadas e sinalizações. O roteador seleciona texto nativo, OCR ou combinação para páginas híbridas. O saneamento identifica, entre outros sinais, texto fora da página, instrução em metadado e texto com baixa visibilidade. A revisão humana pode abrir o original. Os lotes já concluídos e suas páginas são recuperados após interrupção.

## Peças, partes e fatos

O índice reúne as páginas de cada peça. A classificação combina títulos, fórmulas e assinaturas das peças cíveis. Uma reclassificação manual fica no histórico e orienta o reprocessamento. Os extratores usam qualificações da petição, da decisão e do recurso para reconhecer as partes. Cada fato contém o tipo, o valor, o sujeito, a confiança e a origem. Antes de armazenar o fato, o extrator confere a igualdade entre o trecho e o intervalo do texto normalizado.

O relatório do arquivo expõe o diagnóstico e as páginas pendentes. O processo pode ficar parcial se faltarem páginas. Com os fatos vigentes, o worker avalia as validações cabíveis e disponibiliza o dossiê. [Regras cíveis](validacoes.md).
