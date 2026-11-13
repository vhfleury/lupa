# Conformidade do Lupa

> **MINUTA para revisão de advogado; não é parecer jurídico.** Versão 0.1 · 21 de outubro de 2026 · subetapa 8.2. Trechos marcados "a confirmar pelo advogado" dependem de decisão jurídica.

| Tema | Arquivo de origem |
| --- | --- |
| [Termos de uso e aceite pelo gabinete](#termos-de-uso) | `termos-de-uso.md` |
| [Aviso de tratamento aos usuários e às pessoas citadas nos autos](#aviso-de-tratamento) | `aviso-de-tratamento.md` |
| [Registro das operações de tratamento](#registro-de-operacoes) | `registro-de-operacoes.md` |
| [Resposta a incidentes com dados pessoais](#plano-de-incidentes) | `plano-de-incidentes.md` |
| [Relatório de uso ao tribunal](#relatorio-uso-tribunal) | `relatorio-uso-tribunal.md` |
| [Checklist antes do primeiro processo real](#checklist-piloto) | `checklist-piloto.md` |

[Divergências e diferenças de escopo](#divergencias)

<a id="termos-de-uso"></a>

## Termos de uso do Lupa

### 1. Partes e objeto

- **Fornecedor e responsável técnico:** Victor Hugo Fleury Barreto ("fornecedor"), titular do Lupa e controlador dos dados pessoais tratados no sistema.
- **Usuários:** o desembargador do gabinete e os assessores que ele cadastrar.
- **Tribunal:** não é parte destes termos, não tem acesso ao sistema e não participa do piloto.
- **Objeto:** uso privado do Lupa como ferramenta de apoio à conferência de processos judiciais em 2º grau, na hipótese do art. 19, § 2º, da Resolução CNJ 615/2025 (contratação privada quando o tribunal não oferece solução corporativa), observadas as condições do § 3º do mesmo artigo.

### 2. Finalidade: apoio, nunca decisão

O Lupa organiza os autos, monta a linha do tempo, roda validações objetivas e responde perguntas de localização, sempre apontando a página de origem. Ele **não decide, não opina, não valora prova, não tipifica fatos e não redige atos**. A conclusão jurídica é sempre do assessor ou do magistrado. As finalidades ficam dentro das de baixo risco do Anexo da Resolução (BR1, BR4, BR5 e BR8) e fora das de alto risco (AR1 a AR5), cujo uso com ferramenta privada é vedado (art. 19, § 3º, V).

### 3. O que o sistema faz e o que não faz

| Faz (sempre com citação da página) | Não faz (recusa e explica) |
| --- | --- |
| Localizar peças e atos nos autos | Valorar prova (AR2) |
| Extrair datas, partes (por pseudônimo), dispositivos citados, nomes de peças | Tipificar fatos ou apontar qualificadora (AR3) |
| Resumir peça ou trecho sem juízo de valor | Concluir sobre aplicação de norma, súmula ou precedente (AR4) |
| Relacionar eventos do processo | Opinar sobre o resultado do recurso ou a pena |
| Explicar achados das validações, repetindo os valores calculados | Redigir voto, decisão, ementa ou despacho |
| Rodar as validações determinísticas (tempestividade, prescrição) | Calcular prazo ou prescrição "por conta própria" no chat |

Detalhes técnicos: [seção 2 do contrato do agente](../sistema/agente.md#2-o-que-pode-e-o-que-não-pode), [seção 6](../sistema/agente.md#6-política-de-recusa-57) e [seção 7](../sistema/agente.md#7-limites).

### 4. Responsabilidade do magistrado e dever de conferência

1. O uso é auxiliar e complementar; o magistrado permanece **integralmente responsável** pelas decisões e pelas informações nelas contidas (art. 19, § 3º, II).
2. Todo achado, data, cálculo e citação do Lupa deve ser **conferido pelo usuário na página indicada dos autos** antes de ser usado. O sistema pode errar (leitura de página digitalizada, data mal extraída, calendário desatualizado).
3. O assessor responde perante o desembargador pela conferência do que levar à minuta.
4. Se o Lupa auxiliar a redação de ato judicial, a menção no corpo da decisão fica a critério do magistrado (art. 19, § 6º). Como o registro em sistema interno do tribunal previsto no mesmo parágrafo se aplica a uso privado: a confirmar pelo advogado.
5. O art. 19, § 3º, I, prevê capacitação dos usuários conforme programa de letramento do tribunal; a leitura dos guias do Lupa não substitui essa capacitação (a confirmar pelo advogado como comprovar).

### 5. Processos sigilosos

Na primeira versão é **vedado inserir processo ou peça em segredo de justiça** ou com dados sigilosos (art. 19, § 3º, IV). O sistema bloqueia o que reconhece como sigiloso, mas o bloqueio automático não substitui o cuidado do usuário: na dúvida, não envie.

### 6. Conta, senha e MFA

- Cada usuário tem conta **pessoal e intransferível**; é proibido compartilhar usuário, senha ou o aplicativo autenticador.
- O MFA por aplicativo autenticador (TOTP) é obrigatório.
- Perda de senha ou de MFA: o desembargador (para assessores) ou o fornecedor gera credencial temporária, com troca obrigatória no primeiro acesso. Tudo fica registrado.
- Suspeita de uso da conta por outra pessoa: avise o desembargador e o fornecedor **no mesmo dia**.

### 7. Registro de acesso (auditoria)

Todo acesso e toda ação ficam registrados: quem, quando, **endereço IP, localização aproximada derivada do IP**, processo, ação, resultado e versão do modelo quando há chamada ao agente. Os registros não guardam o conteúdo dos autos nem o texto das perguntas e respostas. O desembargador vê a auditoria do gabinete; o acesso do fornecedor a conteúdo de autos aparece em destaque. Ao aceitar estes termos, o usuário declara ciência desse registro.

### 8. Limites de uso

Há tetos técnicos por pergunta, conversa e processo (tamanho da pergunta, tokens, turnos do agente, páginas por conversa), descritos em [seção 7 do contrato do agente](../sistema/agente.md#7-limites). Ao estourar um teto a conversa é encerrada com aviso. É vedado tentar contornar recusas, testar ataques ou inserir instruções nos autos ou nas perguntas.

<a id="modelo-externo"></a>

### 9. Modelo de linguagem externo

O chat e os resumos usam modelo da Anthropic por API. Vão ao modelo apenas trechos dos autos **pseudonimizados** (sem nome e CPF do réu). O contrato do fornecedor do modelo deve vedar o uso dos dados para treinamento ou outros fins não autorizados (art. 19, § 3º, III); a conferência desses termos é condição do piloto ([item 6 do checklist do piloto](#checklist-6)).

### 10. Suporte e incidentes

- Suporte: diretamente com o fornecedor, pelo canal combinado com o gabinete ([a preencher]). Nunca envie trecho de autos por mensagem ou e-mail.
- Incidentes (acesso estranho, processo "em revisão", suspeita de vazamento): seguir [plano de resposta a incidentes](#plano-de-incidentes).
- Disponibilidade e responsabilidade por indisponibilidade no piloto: a confirmar pelo advogado.
- Remuneração ou gratuidade do piloto: a confirmar pelo advogado.

### 11. Informação ao tribunal

O magistrado deve prestar informações ao tribunal sobre o uso, na forma do regulamento (art. 19, § 7º). O sistema oferece o relatório de uso para isso ([modelo de relatório ao tribunal](#relatorio-uso-tribunal)).

### 12. Encerramento e descarte

- O desembargador desativa imediatamente o assessor que deixar o gabinete. A desativação não apaga o histórico de auditoria.
- Ao fim do piloto ou a pedido do desembargador, os processos são descartados pela destruição da chave de cada processo; cópias em backup cifrado deixam de existir em até 30 dias (retenção padrão do backup).
- Os registros de auditoria são mantidos por prazo maior que o dos dados dos processos (prazo exato: a confirmar pelo advogado).

<a id="aceite-dos-termos"></a>

### 13. Aceite

Declaro que li estes termos, o guia do meu papel ([guia do assessor](../guias/guia-assessor.md) ou [guia do desembargador](../guias/guia-desembargador.md)) e o [aviso de tratamento de dados pessoais](#aviso-de-tratamento), e que concordo com eles.

| Nome | Papel | Usuário no Lupa | Data | Assinatura |
| --- | --- | --- | --- | --- |
| | Desembargador | | | |
| | Assessor | | | |

Forma do aceite (papel, assinatura eletrônica ou tela no sistema): a confirmar pelo advogado.

## Tratamento de dados pessoais

<a id="aviso-de-tratamento"></a>

### Aviso de tratamento de dados pessoais

**Controlador:** Victor Hugo Fleury Barreto, fornecedor do Lupa.

**Encarregado (canal de atendimento):** [a indicar]. A LGPD (art. 41) exige que o controlador indique encarregado e divulgue seu contato; eventual dispensa por porte depende de norma da ANPD: a confirmar pelo advogado. Contato: [a preencher].

O tribunal não é controlador nem operador deste tratamento e não tem acesso ao sistema.

---

#### Parte A. Para os usuários (desembargador e assessores)

| Item | Conteúdo |
| --- | --- |
| Dados | nome de usuário, nome de exibição, papel, gabinete; hash da senha; segredo do autenticador (cifrado); sessões; IP e localização aproximada derivada do IP; registros de uso (o que foi aberto, buscado, perguntado — sem o texto da pergunta —, anotado, corrigido, quando e de onde) |
| Não coletamos | e-mail, CPF, telefone ou documentos pessoais do usuário |
| Finalidade | autenticar, controlar acesso por gabinete e processo, garantir a segurança, permitir auditoria e o relatório de uso que o magistrado entrega ao tribunal |
| Base legal | descrição: execução do acordo de uso firmado com o usuário (LGPD, art. 7º, V) e legítimo interesse do controlador em segurança e prevenção de fraude (art. 7º, IX). Enquadramento final: a confirmar pelo advogado |
| Compartilhamento | nenhum dado de conta vai ao fornecedor do modelo; provedor de hospedagem, se houver, guarda os dados cifrados |
| Retenção | conta: enquanto ativa; após a desativação, mantém-se o registro mínimo para a auditoria. Auditoria: prazo maior que o dos processos (prazo exato a confirmar pelo advogado) |
| Direitos | os do art. 18 da LGPD, pelo canal acima |
| Segurança | MFA obrigatório, bloqueio progressivo de login, auditoria com encadeamento de hash, TLS, cifra em repouso |

<a id="pessoas-citadas-nos-autos"></a>

#### Parte B. Para as pessoas citadas nos autos (réus, vítimas, testemunhas e outros)

Essas pessoas não usam o sistema. Este aviso fica disponível a quem pedir (forma de publicidade: a confirmar pelo advogado).

| Item | Conteúdo |
| --- | --- |
| Dados | os que já constam de processos **públicos** enviados pelo gabinete: nomes, qualificação, CPF e outros identificadores, endereços, datas, fatos narrados. Pode haver dados sensíveis (saúde, por exemplo) e dados sobre infrações penais |
| Origem | autos exportados do sistema do tribunal pelo próprio gabinete |
| Finalidade | apoiar o gabinete na conferência do processo: localizar peças, montar linha do tempo, rodar validações objetivas (tempestividade, prescrição) e responder perguntas de localização com citação de página. Não há perfilamento de pessoas, decisão automatizada nem treino de modelo |
| Base legal | descrição: tratamento ligado ao exercício regular de direitos em processo judicial (LGPD, art. 7º, VI; para dados sensíveis, art. 11, II, "d"). Como o controlador é um particular que apoia o magistrado, a adequação dessa base, a alternativa do legítimo interesse (art. 7º, IX, que não cobre dados sensíveis) e o tratamento de dados de natureza penal são **a confirmar pelo advogado** |
| Pseudonimização | nomes e identificadores do réu são substituídos por pseudônimos na camada analítica, nos logs e no que vai ao modelo; a tabela que liga pseudônimo e identidade fica separada e cifrada, e cada leitura é registrada |
| Compartilhamento | **Fornecedor do modelo (Anthropic, por API).** Vai: trechos dos autos pseudonimizados necessários para responder a pergunta ou gerar o resumo. Não vai: nome e CPF do réu, a tabela de identidades, arquivos inteiros, dados dos usuários. O contrato do fornecedor do modelo deve vedar treinamento com esses dados (conferência pendente, ver [item 6 do checklist do piloto](#checklist-6)). Nomes de vítimas e testemunhas que apareçam no trecho: verificar se a pseudonimização os cobre antes do piloto (a confirmar com o responsável técnico). O processamento pode ocorrer fora do Brasil; a hipótese legal para a transferência internacional é a confirmar pelo advogado. **Provedor de hospedagem**, se houver: guarda só dados cifrados |
| Retenção e descarte | enquanto o gabinete precisar do processo para a finalidade; descarte pela destruição da chave do processo; backups cifrados expiram em 30 dias. No fornecedor do modelo: conforme o contrato (conferir). Registros de auditoria (sem conteúdo dos autos) ficam por mais tempo |
| Direitos | confirmação, acesso, correção, anonimização, bloqueio ou eliminação de dados desnecessários, informação sobre compartilhamento e demais direitos do art. 18 da LGPD, observados os limites próprios de dados em processo judicial (a confirmar pelo advogado). A correção do conteúdo dos autos se faz no próprio processo judicial, não no Lupa |
| Canal | encarregado indicado acima. O pedido não precisa e não deve conter cópia de autos |
| Segurança (LGPD, art. 46) | só processos públicos; arquivo cifrado antes de qualquer leitura; chave por processo derivada da chave do gabinete em cofre próprio (Vault); texto extraído também cifrado; TLS; acesso com MFA e restrito ao gabinete; auditoria append-only; logs sem conteúdo dos autos |

<a id="registro-de-operacoes"></a>

### Registro das operações de tratamento

Bases legais descritas aqui são **a confirmar pelo advogado**.

Atende ao dever de controlador e operador manterem registro das operações de tratamento (LGPD, art. 37). Controlador: [Victor Hugo Fleury Barreto](#aviso-de-tratamento). Operadores: **Anthropic** (fornecedor do modelo, só no fluxo 5) e **provedor de hospedagem** (só se o piloto sair da infraestrutura própria; situação a registrar ao fim da 8.1). O operador trata segundo as instruções do controlador (art. 39); para a Anthropic, as instruções são os termos comerciais da API.

| # | Operação | Dados | Finalidade | Base legal (descrição) | Retenção | Medidas de segurança | Operadores |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Cadastro de usuário | usuário, nome de exibição, papel, gabinete, hash da senha, segredo TOTP | dar acesso pessoal | execução do acordo de uso (art. 7º, V) | enquanto ativo; registro mínimo após desativação | hash forte de senha, TOTP cifrado, reset manual registrado, sem e-mail | hospedagem, se houver |
| 2 | Autenticação e auditoria | IP, localização aproximada, data e hora, ação, processo, objeto (identificadores e hashes), resultado, versões do modelo e do prompt | segurança, prestação de contas, relatório ao tribunal (Res. CNJ 615/2025, art. 19, § 7º) | legítimo interesse em segurança (art. 7º, IX) | maior que a dos processos (prazo a definir) | append-only com encadeamento de hash; sem conteúdo dos autos nem texto de perguntas; rate limit e bloqueio progressivo | hospedagem, se houver |
| 3 | Ingestão dos autos | PDF/ZIP de processo público, com dados de réus, vítimas e testemunhas, inclusive sensíveis e penais | apoio à conferência do processo | exercício regular de direitos em processo judicial (art. 7º, VI; art. 11, II, "d") | até o descarte pedido pelo gabinete ou fim do piloto | bloqueio de sigilo; cifra antes do parser; worker isolado sem rede; temporário 0600 apagado ao fim | hospedagem, se houver |
| 4 | Extração e validações | texto das páginas, datas, partes pseudonimizadas, fatos com evidência, achados | linha do tempo e validações determinísticas | idem 3 | idem 3 | texto, evidências e índices cifrados com chave por processo; pseudonimização; identidades cifradas com chave própria e leitura registrada | hospedagem, se houver |
| 5 | Chat e dossiê (modelo externo) | trechos pseudonimizados, pergunta do usuário, resposta | localizar, resumir, explicar achados | idem 3 | no Lupa: mensagens cifradas até o descarte; no fornecedor do modelo: conforme contrato (conferir) | pseudonimização; TLS; conferência de citação por código; detecção de injeção com processo em revisão; tetos de tokens; contrato sem treino (conferir) | **Anthropic** |
| 6 | Backup | cópia cifrada do banco e do storage | recuperação de desastre | legítimo interesse em continuidade e segurança (art. 7º, IX), acessório a 1-5 | 30 dias (`LUPA_BACKUP_RETENCAO_DIAS`) | cifra `age`; chave mensal destruída quando não há backup vivo; restauração testada por hash | hospedagem, se houver |
| 7 | Descarte | chave do processo (DEK) | eliminar dados ao fim da finalidade | idem 3 | — | destruição da DEK no Vault; evento de auditoria; backups expiram em 30 dias | — |

Transferência internacional (fluxo 5): [hipótese legal a confirmar pelo advogado](#pessoas-citadas-nos-autos). Revisar este registro a cada mudança de fluxo, operador ou versão.

<a id="plano-de-incidentes"></a>

## Plano de resposta a incidentes com dados pessoais

Complementa a [seção 10 do manual de operação](../operacao/operacao.md#10-resposta-a-incidente) (passos técnicos) com papéis, prazos e comunicação.

<a id="fundamentos-incidentes"></a>

### 1. Fundamentos confirmados

- **LGPD, art. 48:** o controlador deve comunicar à autoridade nacional e ao titular o incidente de segurança que possa acarretar risco ou dano relevante aos titulares, em prazo razoável definido pela autoridade, com conteúdo mínimo (natureza dos dados, titulares, medidas de segurança, riscos, motivo da demora, medidas de mitigação). O § 3º manda considerar, na gravidade, se os dados estavam ininteligíveis (cifrados) para terceiros.
- **Resolução CD/ANPD nº 15, de 24 de abril de 2024** (Regulamento de Comunicação de Incidente de Segurança), consultada em 21/10/2026 no [Diário Oficial da União](https://www.in.gov.br/en/web/dou/-/resolucao-cd/anpd-n-15-de-24-de-abril-de-2024-556243024):
  - art. 6º: comunicação à ANPD em **três dias úteis**, contados do conhecimento pelo controlador de que o incidente afetou dados pessoais;
  - art. 9º: comunicação ao titular em **três dias úteis**, contados do mesmo marco;
  - art. 10: registro de todo incidente, **inclusive o não comunicado**, por no mínimo **cinco anos**.
  - Os critérios de "risco ou dano relevante" e a forma do envio (formulário da ANPD) estão na mesma resolução: a confirmar pelo advogado se houve alteração posterior.

### 2. Papéis

| Quem | Faz |
| --- | --- |
| Victor (controlador e responsável técnico) | contém, investiga, decide se há dado pessoal afetado e se há risco relevante, comunica ANPD e titulares, mantém o registro |
| Desembargador (usuário responsável) | avisa Victor de imediato; desativa ou reseta contas do gabinete; decide sobre processo em revisão; avalia se deve informar o tribunal (a confirmar pelo advogado) |
| Assessor | avisa o desembargador e Victor no mesmo dia; não apaga nada |
| Anthropic / hospedagem (operadores) | comunicação ao controlador conforme seus termos (conferir) |

### 3. Classificação

| Nível | Exemplo | Dado pessoal? |
| --- | --- | --- |
| 1 · Evento | processo em revisão por injeção, falso alarme liberado | não |
| 2 · Incidente sem exposição | vazamento só de dado cifrado com Vault e `.env` íntegros; disco cheio | provável não; registrar |
| 3 · Incidente com exposição possível | credencial de usuário comprometida com acesso a autos; `.env` ou `secret_id` vazado junto com dados | sim, avaliar risco |
| 4 · Exposição confirmada | conteúdo de autos ou tabela de identidades lido por terceiro | sim; presume-se risco relevante (a confirmar pelo advogado) |

<a id="prazos-incidentes"></a>

### 4. Prazos internos

| Momento | Ação |
| --- | --- |
| Imediato | conter (manual de operação, [10.1](../operacao/operacao.md#101-vazamento-suspeito-disco-dump-bucket-backup-ou-log), [10.2](../operacao/operacao.md#102-incidente-de-injeção-processo-em-revisão) e [10.3](../operacao/operacao.md#103-comprometimento-de-credencial)); preservar evidência; exportar auditoria |
| Mesmo dia | Victor e desembargador avisados; registro aberto ([modelo abaixo](#modelo-registro-incidente)) |
| Até 1 dia útil | decidir se afetou dados pessoais (marco de contagem) e o nível |
| Até 3 dias úteis do marco | níveis 3-4 com risco relevante: comunicar ANPD e titulares (Res. CD/ANPD 15/2024, arts. 6º e 9º) |
| Até 5 dias úteis | registro completo, causa e correção |

Comunicação aos titulares dos autos: os titulares não têm contato com o sistema; o meio (direto, por intermédio do gabinete ou comunicação pública) é **a confirmar pelo advogado**.

<a id="modelo-registro-incidente"></a>

### 5. Modelo de registro (`docs/incidentes/AAAA-MM-DD-<tipo>.md`)

```
Data e hora de conhecimento:
Quem detectou / como:
Descrição das circunstâncias:
Nível (1-4):
Dados afetados (natureza e categoria):
Número de titulares afetados (crianças, adolescentes, idosos):
Os dados estavam cifrados? Chaves comprometidas?
Avaliação de risco e possíveis danos:
Medidas de contenção e correção (com horários):
Cadeia de auditoria verificada? Resultado:
Comunicado à ANPD? Data / protocolo / motivo de não comunicar:
Comunicado aos titulares? Data / meio:
Desembargador informado em:
Lições e prevenção:
Guardar por no mínimo 5 anos.
```

### Ensaios (Etapa 7.10, 21/10/2026, desenvolvimento, dados sintéticos)

Os dois ensaios constam da [seção 13 do manual de operação](../operacao/operacao.md#13-ensaios-registrados-etapa-710-21102026-ambiente-de-desenvolvimento).

<a id="anexo-a"></a>

#### Anexo A. Ensaio: credencial de assessor comprometida

Rotação da chave do gabinete (v1→v2, 1 DEK reenvelopada) → reset de senha → reset de MFA. Execução das rotas em 0,23 s; as duas sessões do assessor passaram a 401; senha antiga recusada; dossiê seguiu abrindo. Classificação: nível 3 simulado. Detalhes: [ensaio de credencial comprometida da 7.10](../etapas/ETAPAS.md#credencial-7-10).

#### Anexo B. Ensaio: injeção com processo em revisão

Pergunta que provoca resposta com instrução → bloqueio pela conferência → processo em revisão → nova pergunta recusada → liberação pelo desembargador → chat volta. 0,26 s. Auditoria: `chamada_modelo` bloqueado, `processo_em_revisao`, `revisao_liberada`. Classificação: nível 1. Detalhes: [ensaio de injeção da 7.10](../etapas/ETAPAS.md#2-incidente-de-injeção).

<a id="relatorio-uso-tribunal"></a>

## Modelo de relatório de uso de ferramenta privada de IA ao tribunal

Finalidade: permitir ao magistrado prestar ao tribunal as informações sobre o uso de solução de mercado de IA (Res. CNJ 615/2025, art. 19, § 7º, "na forma do regulamento"). O regulamento do tribunal pode exigir outro formulário; nesse caso, use este modelo como fonte dos dados (a confirmar pelo advogado se o TJGO já editou regulamento).

Fonte dos números: Auditoria → Relatório de uso no sistema, ou `GET /api/auditoria/relatorio-uso?usuario=<id>` / `?processo=<id>`; eventos em `GET /api/auditoria/exportar?formato=csv`. Ver [seção 11 do manual de operação](../operacao/operacao.md#11-relatório-de-uso-para-o-tribunal). Nada disso contém conteúdo dos autos.

---

<a id="modelo-relatorio"></a>

### Modelo

**Ao** [órgão indicado no regulamento do tribunal]

**Magistrado:** [nome] · **Gabinete:** [identificação] · **Período:** [dd/mm/aaaa a dd/mm/aaaa]

1. **Ferramenta e fornecedor.** Lupa, versão [x], ferramenta privada de apoio à conferência de processos, fornecida por Victor Hugo Fleury Barreto, contratada na forma do art. 19, § 2º (o tribunal não oferece solução corporativa equivalente: [confirmar]).
2. **Finalidades** (Anexo, baixo risco): BR1 (extração, organização e resumo de documentos com supervisão humana); BR4 (textos de apoio, sob supervisão e versão final do magistrado; o Lupa não redige atos); BR5 (tarefa preparatória: linha do tempo e validações objetivas); BR8 (pseudonimização na exibição e no envio ao modelo).
3. **Vedações observadas.** Sem valoração de prova (AR2), tipificação (AR3), juízo conclusivo sobre norma ou precedente (AR4), perfilamento (AR1) ou biometria (AR5); o sistema recusa essas perguntas. Uso auxiliar, com conferência humana e responsabilidade integral do magistrado (art. 19, § 3º, II).
4. **Modelo de linguagem.** [modelo e versões, do relatório de uso], Anthropic, por API. Termos do fornecedor conferidos em [data]: vedação de treinamento [sim/não, cláusula], retenção [prazo].
5. **Segurança.** Somente processos públicos; cifra em repouso com chave por processo; pseudonimização antes do envio ao modelo; MFA; auditoria append-only com IP e localização aproximada.
6. **Auditoria disponível.** Registro de cada acesso e ação, exportável em CSV/JSON, à disposição do tribunal mediante solicitação.
7. **Volume de uso no período.**

| Indicador | Valor |
| --- | --- |
| Processos inseridos | |
| Usuários ativos | |
| Perguntas ao chat | |
| Chamadas ao modelo | |
| Tokens (entrada / saída) | |
| Custo estimado (tabela de preços versão [x]) | |
| Respostas bloqueadas pela conferência / processos postos em revisão | |

8. **Declaração.** Declaro que nenhum processo ou peça sigilosa ou em segredo de justiça foi inserido no sistema no período, e que todo resultado usado foi conferido nos autos.

[Local, data] · [assinatura]

Anexos: relatório de uso exportado; CSV de eventos (opcional).

---

### Exemplo preenchido (dados sintéticos, nenhum dado real)

**Magistrado:** Desembargador Exemplo Sintético · **Gabinete:** GAB-TESTE-01 · **Período:** 01/11/2026 a 30/11/2026

1. Lupa, versão 1.0.0-piloto, fornecido por Victor Hugo Fleury Barreto, art. 19, § 2º.
2. BR1, BR4, BR5, BR8, conforme o modelo.
3. Vedações conforme o modelo; 4 perguntas recusadas no período por pedirem valoração.
4. Modelo `claude-exemplo-1` (Anthropic). Termos conferidos em 28/10/2026: [cláusula de não treinamento]; retenção [prazo].

5\. e 6. Conforme o modelo.

7. Volume:

| Indicador | Valor |
| --- | --- |
| Processos inseridos | 6 |
| Usuários ativos | 3 (1 desembargador, 2 assessores) |
| Perguntas ao chat | 142 |
| Chamadas ao modelo | 391 |
| Tokens (entrada / saída) | 4.210.000 / 187.000 |
| Custo estimado | R$ 112,40 (tabela de preços v2026-10) |
| Bloqueios / revisões | 1 / 1 (liberada pelo desembargador em 12/11/2026) |

8. Declaração conforme o modelo.

Goiânia, 01/12/2026 · Desembargador Exemplo Sintético

<a id="checklist-piloto"></a>

## Checklist antes do primeiro processo real

Nenhum processo real entra antes de todos os itens marcados, com data e responsável.

| # | Item | Responsável | Feito em |
| --- | --- | --- | --- |
| 1 | [Documentos desta pasta](#conformidade-do-lupa) revisados por advogado e versão final aprovada por Victor | Victor | |
| 2 | Termos de uso aceitos por desembargador e cada assessor ([seção 13 dos termos de uso](#aceite-dos-termos)) | usuários | |
| 3 | Aviso de tratamento entregue ao gabinete; encarregado e canal definidos | Victor | |
| 4 | Decisão do object storage assinada ([assinatura da decisão do object storage](../decisoes/object-storage.md#assinatura)) | Victor | |
| 5 | Chave da API da Anthropic do piloto criada e guardada fora do repositório | Victor | |
| 6 | <a id="checklist-6"></a>Termos da API conferidos: vedação de treinamento, prazo de retenção, local de processamento; cópia e data guardadas | Victor + advogado | |
| 7 | Smoke test com o modelo real (testes `llm`) executado | Victor | |
| 8 | <a id="checklist-8"></a>Vault em produção: TLS, unseal com partes guardadas, reinício testado (manual de operação, [4.1](../operacao/operacao.md#41-inicialização-em-produção) e [4.6](../operacao/operacao.md#46-pendências-e-decisões-para-produção)) | Victor | |
| 9 | Certificado real no proxy; porta direta da API e console do MinIO fechados ([seção 5 do manual de operação](../operacao/operacao.md#5-certificado-e-portas)) | Victor | |
| 10 | Backup agendado, expurgo agendado e uma restauração testada no ambiente do piloto | Victor | |
| 11 | Guias lidos por pelo menos um assessor, com dúvidas respondidas | desembargador | |
| 12 | Dados jurídicos confirmados pelo gabinete: calendários e feriados, prazos, tipos penais, regras de borda das validações | gabinete | |
| 13 | Processo escolhido confirmado como público (sem segredo de justiça em nenhuma peça) | desembargador | |
| 14 | Dados sintéticos removidos do ambiente do piloto, inclusive objetos órfãos | Victor | |
| 15 | Dois administradores nominais ou procedimento de contingência definido | Victor | |
| 16 | Forma de informar o tribunal combinada (art. 19, § 7º) | desembargador | |

Assinaturas: Victor ______ data ___ · Desembargador ______ data ___

<a id="divergencias"></a>

## Divergências e diferenças de escopo

- **Dados no fluxo da Anthropic.** Os termos de uso dizem que vão ao modelo apenas trechos pseudonimizados dos autos. O aviso enumera o que é compartilhado e exclui os dados de conta. O fluxo 5 do registro inclui, entre os dados tratados no chat e no dossiê, a pergunta do usuário e a resposta. A tabela descreve a operação inteira, sem discriminar todos os campos enviados à API. [termos-de-uso.md, cláusula 9](#modelo-externo) · [aviso-de-tratamento.md, Partes A e B](#aviso-de-tratamento) · [registro-de-operacoes.md, fluxo 5](#registro-de-operacoes)

- **Pseudonimização de vítimas e testemunhas.** O modelo de relatório declara pseudonimização na exibição e no envio ao modelo (BR8). Os termos especificam nome e CPF do réu. O aviso deixa a cobertura dos nomes de vítimas e testemunhas para conferência com o responsável técnico antes do piloto. [relatorio-uso-tribunal.md, itens 2 e 5](#modelo-relatorio) · [termos-de-uso.md, cláusula 9](#modelo-externo) · [aviso-de-tratamento.md, Parte B](#pessoas-citadas-nos-autos)

- **Início do prazo de comunicação.** No plano, os fundamentos contam os três dias úteis para comunicar a ANPD e os titulares a partir do conhecimento pelo controlador de que o incidente afetou dados pessoais. A tabela interna dá até um dia útil para decidir se houve esse efeito e chama a decisão de “marco de contagem”. As duas formulações divergem se a decisão ocorrer depois do conhecimento. [plano-de-incidentes.md, seção 1](#fundamentos-incidentes) · [mesma minuta, seção 4](#prazos-incidentes)

- **TLS no Vault.** O item 8 exige TLS no Vault em produção. A seção 4.6 do manual citada nesse item registra a decisão da etapa 8.1 de operar sem TLS entre API/worker e Vault no piloto de host único, com TLS obrigatório se o Vault sair do host da aplicação. O item 8 continua em aberto. [checklist-piloto.md, item 8](#checklist-8) · [operacao.md, seção 4.6](../operacao/operacao.md#46-pendências-e-decisões-para-produção)

- **Rede durante a ingestão.** O fluxo 3 descreve o controle como “worker isolado sem rede”. O relato da etapa 4A.4 informa que o processo filho do parser compartilha a rede interna do worker e que o isolamento de rede pelo kernel ficou fora da entrega. [registro-de-operacoes.md, fluxo 3](#registro-de-operacoes) · [ETAPAS.md, etapa 4A.4](../etapas/ETAPAS.md#etapa-4a-4)

- **Controlador e papel do tribunal.** A arquitetura original identifica o tribunal como controlador e o fornecedor como operador no cenário institucional. Para o piloto privado, os requisitos da primeira versão e as minutas atribuem o controle a Victor Hugo Fleury Barreto. O aviso exclui o tribunal dos papéis de controlador e operador, e os termos registram que ele não participa do piloto. [arquitetura.md, governança institucional](../especificacao/arquitetura.md#governança-lgpd-e-institucional) · [requisitos-v1.md, seção 2](../especificacao/requisitos-v1.md#2-contexto-e-enquadramento) · [aviso-de-tratamento.md](#aviso-de-tratamento) · [termos-de-uso.md, cláusula 1](#termos-de-uso)
