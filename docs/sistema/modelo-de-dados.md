# Modelo de dados

A revisão Alembic `v0001_data_vault` instala o esquema da 0.2 em uma base nova. O esquema fica no pacote da pipeline e é compartilhado pela intranet. A chave de um hub é o SHA-256 de sua chave de negócio normalizada, guardado em 32 bytes. Nas rotas e no front, o identificador tem 64 dígitos hexadecimais.

| Família | Exemplos | Como ler |
| --- | --- | --- |
| Hubs | processo, arquivo, página, peça, parte, evidência, fato, achado, usuário, conversa | Identidade estável. Um arquivo tem por chave número CNJ e hash dos bytes. A evidência inclui página e offsets. |
| Links | processo–arquivo, arquivo–página, página–evidência, fato–evidência, achado–fato, processo–responsável | Relações entre chaves. O vínculo de responsabilidade tem vigência própria. |
| Satélites | atributos do processo, classificação de peça, texto de página, identidade de parte, valor do fato e resultado do achado | Cada linha representa uma mudança. O `hash_diff` evita repetir valores iguais. Os satélites multiativos distinguem sua subchave. |
| Registros de ocorrência | chamada ao modelo e evento de auditoria | Capturam o ato e seus metadados no momento em que ocorre. |

## Vigência e histórico

O banco gera `load_dts` com seu relógio. Para o mesmo pai e subchave, o trigger garante a ordem crescente mesmo perante recuo do relógio. As views de leitura apresentam a versão atual. `v_fato_historico` e `v_achado_historico` sustentam a consulta de versões anteriores na interface. A correção preserva o identificador do fato e registra a evidência vigente. Um fato só pode ser criado com evidência de origem.

O sujeito de fato ou achado é o hex da chave da parte. O valor vazio designa informação comum ao processo. O nome normalizado da parte identifica o hub por HMAC com a DEK do processo. A identidade e os dados sensíveis residem em satélites cifrados. O banco recusa alterações e remoções diretas nos registros protegidos. O descarte segue a função com privilégios específicos e elimina o conteúdo de um único processo.

## Responsáveis

`link_processo_responsavel` e sua vigência alimentam `v_responsavel`. O desembargador atribui ou remove assessores ativos. O cadastro do gabinete permite a ambas as funções consultar o acervo. A responsabilidade indica a distribuição de trabalho.

## Migração

A partir da raiz, use `make migrate` contra o banco da 0.2. O piloto 0.1 tem esquema e cadeia de revisões próprios. O registro histórico de T1.7 conserva o resultado de seus testes de responsáveis, e T3.6 verifica o vínculo atual. [Histórico das tarefas](../planos/tarefas_0.2.md).
