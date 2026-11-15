# Cifra e chaves

Cada processo tem uma chave de dados (DEK). O Vault Transit envolve essa DEK com a chave `lupa`. O satélite `sat_processo_chave` guarda o envelope. A API e o worker autenticam-se no Vault com AppRole. O conteúdo de uma DEK ativa fica em memória durante as operações autorizadas sobre o processo.

O envelope binário dos objetos tem o cabeçalho `LUPAOBJ`. Os campos de banco protegidos usam o prefixo `lupa1:` e seus dados associados incluem o identificador do processo. A aplicação cifra originais e conteúdo sensível antes de entregá-los a PostgreSQL ou MinIO. A tentativa de ler um campo ou objeto em claro gera erro de integridade. Identificadores públicos, relações, contagens e registros operacionais têm tratamento próprio.

Nomes de partes são cifrados em repouso e aparecem no dossiê, nas evidências e nos trechos enviados ao modelo. O HMAC do nome serve à identificação interna. A cifra em repouso termina na abertura autorizada do conteúdo pela aplicação.

## Descarte

O desembargador aciona o descarte de um processo. A função do banco apaga os satélites de conteúdo e o envelope do processo e registra a situação final com o evento de auditoria na mesma transação. A aplicação invalida a chave em cache e apaga originais e imagens em cache no bucket. Uma falha nessa última etapa gera evento de limpeza pendente e pode ser retomada pelo mesmo endpoint. Hubs, vínculos estruturais e auditoria continuam consultáveis como registro técnico. [Operação](../operacao/operacao.md).
