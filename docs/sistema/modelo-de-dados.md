# Modelo de dados

A revisão Alembic `v0001_data_vault` instala o esquema da 0.2 em uma base nova. O esquema fica no pacote da pipeline e é compartilhado pela intranet. A chave de um hub é o SHA-256 de sua chave de negócio normalizada, guardado em 32 bytes. Nas rotas e no front, o identificador tem 64 dígitos hexadecimais.

| Família | Exemplos | Como ler |
| --- | --- | --- |
| Hubs | processo, arquivo, página, peça, parte, evidência, fato, achado, usuário, conversa | Identidade estável. Um arquivo tem por chave número CNJ e hash dos bytes. A evidência inclui página e offsets. |
| Links | processo–arquivo, arquivo–página, página–evidência, fato–evidência, achado–fato, processo–responsável | Relações entre chaves. O vínculo de responsabilidade tem vigência própria. |
| Satélites | atributos do processo, classificação de peça, texto de página, identidade de parte, valor do fato e resultado do achado | Cada linha representa uma mudança. O `hash_diff` evita repetir valores iguais. Os satélites multiativos distinguem sua subchave. |
| Registros de ocorrência | chamada ao modelo e evento de auditoria | Capturam o ato e seus metadados no momento em que ocorre. |

## Vigência e histórico

A revisão `0002` amplia o CHECK de `hub_fato.tipo` com os seis dados da capa. Em `sat_processo_dados`, cada linha guarda a classe e o usuário que a registrou. A view `v_processo` lê o criador da primeira linha e a classe da última. Quando há correção, expõe a classe penúltima, a chave e o identificador de quem corrigiu e o instante da alteração.

O banco gera `load_dts` com seu relógio. Para o mesmo pai e subchave, o trigger garante a ordem crescente mesmo perante recuo do relógio. As views de leitura apresentam a versão atual. `v_fato_historico` e `v_achado_historico` sustentam a consulta de versões anteriores na interface. A correção preserva o identificador do fato e registra a evidência vigente. Um fato só pode ser criado com evidência de origem.

O sujeito de fato ou achado é o hex da chave da parte. O valor vazio designa informação comum ao processo. A chave de negócio da parte, `hub_parte.chave_nome`, é o SHA-256 do nome normalizado, sem chave secreta. O `hash_diff` dos satélites é sempre SHA-256. Autos, nomes de partes e mensagens do chat ficam em claro no PostgreSQL e no MinIO; a proteção em repouso cabe ao host e aos volumes. O banco recusa alterações e remoções diretas nos registros protegidos. O descarte segue a função com privilégios específicos e elimina o conteúdo de um único processo.

## Descarte

O desembargador aciona o descarte de um processo. A função do banco apaga os satélites de conteúdo do processo e registra a situação final com o evento de auditoria `processo_descartado` na mesma transação; o evento tem `objeto_tipo` `processo` e `objeto_id` igual ao identificador hexadecimal do processo. A aplicação apaga originais e imagens em cache no bucket. Uma falha nessa última etapa gera evento de limpeza pendente e pode ser retomada pelo mesmo endpoint. Hubs, vínculos estruturais e auditoria continuam consultáveis como registro técnico. [Operação](../operacao/operacao.md).

## Responsáveis

`link_processo_responsavel` e sua vigência alimentam `v_responsavel`. O desembargador atribui ou remove assessores ativos. O cadastro do gabinete permite a ambas as funções consultar o acervo. A responsabilidade indica a distribuição de trabalho.

## Migração

A revisão `v0003` remove `sat_processo_chave` e a coluna `chave_dados_cifrada` de `v_processo`. Ela não converte dados gravados com cifra: a instalação recria banco e MinIO e reenvia os processos.

O downgrade para `0001` restaura a definição anterior da view e do CHECK. Se houver fatos de um dos seis tipos novos, o PostgreSQL recusa o CHECK anterior e desfaz a transação, preservando os dados.

A partir da raiz, use `make migrate` contra o banco da 0.2. O piloto 0.1 tem esquema e cadeia de revisões próprios. O registro histórico de T1.7 conserva o resultado de seus testes de responsáveis, e T3.6 verifica o vínculo atual. [Histórico das tarefas](../planos/tarefas_0.2.md).
