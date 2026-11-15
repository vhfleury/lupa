# Conformidade do Lupa 0.2

**Minuta para revisão jurídica e institucional, de 14 de novembro de 2026.** O piloto atende um gabinete cível. O cadastro aceita autos sigilosos e o dossiê utiliza os nomes das partes. O recurso de chat pode transmitir trechos identificáveis ao fornecedor externo. A habilitação técnica do cadastro e as condições de uso de dados sigilosos exigem decisões distintas do responsável pelo tratamento.

<a id="termos-de-uso"></a>

## Termos de uso e aceite

O fornecedor identificado nesta minuta é Victor Hugo Fleury Barreto. O serviço auxilia consulta documental, organização de peças e conferência de fatos e regras. O assessor e o desembargador conferem a fonte de cada achado e de cada citação. A elaboração de atos, a avaliação de prova e a decisão jurídica continuam sob responsabilidade humana. A aplicação não integra o sistema processual oficial.

Cada pessoa usa conta própria, senha e autenticador TOTP. O desembargador administra as contas de assessores. Ambos os papéis têm acesso aos processos do gabinete. O usuário comunica pelo canal institucional acordado a perda de credencial, exposição indevida, divergência em fonte ou indício de instrução maliciosa.

<a id="modelo-externo"></a>

**Uso do modelo externo.** Perguntas, trechos e eventualmente páginas originais do processo podem ser processados pelo fornecedor do modelo com os nomes e dados que constem dos autos. O projeto não treina modelos com autos. A vedação de treinamento pelo fornecedor, os termos de retenção e eliminação, a localização do processamento e as salvaguardas contratuais devem ser documentadas para o serviço efetivamente contratado.

O art. 19, § 3º, IV, da Resolução CNJ 615/2025 restringe o uso de modelos privados ou externos com dados sigilosos e prevê exceções condicionadas à anonimização na origem ou a mecanismos técnicos e procedimentais que garantam proteção efetiva. A 0.2 envia trechos com nomes. Cabe ao gabinete e à assessoria jurídica do tribunal documentar se as salvaguardas e a contratação satisfazem a hipótese aplicável antes de usar material sigiloso real. [Resolução CNJ 615/2025, texto vigente](https://atos.cnj.jus.br/atos/detalhar/6001).

<a id="aceite-dos-termos"></a>

**Registro do aceite.** Nome e papel do usuário ______. Versão da minuta ______. Data ______. Declaro que recebi o guia do meu papel, consultei o aviso de tratamento e estou ciente do acesso do gabinete, dos limites do serviço e das condições de envio ao modelo. Assinatura ______. O aceite de uso pelo servidor ou magistrado não substitui a definição da base legal dos dados de terceiros.

<a id="aviso-de-tratamento"></a>

## Aviso de tratamento

A minuta anterior identificou o fornecedor como controlador. A qualificação definitiva de cada agente depende das decisões sobre finalidade e meios e dos instrumentos aplicáveis ao gabinete, tribunal e fornecedores. Registrar a avaliação jurídica, o controlador efetivamente responsável, o encarregado, o canal para exercício de direitos e os contatos para incidentes antes do uso real.

| Titulares e dados | Finalidade | Acesso e retenção |
| --- | --- | --- |
| Usuários, nomes de acesso, papel, credenciais protegidas, sessão e metadados de acesso | Autenticação, segurança, atribuição de trabalho, auditoria e prestação de informações | A aplicação mantém dados de conta e histórico mínimo de atos. Prazos de retenção e canais de atendimento são definidos pelo controlador. |
| Partes, procuradores e demais pessoas citadas em autos, inclusive menores e titulares de dados sensíveis | Organizar documentos, localizar evidências e apoiar a conferência do caso pelo gabinete | Usuários autorizados do gabinete consultam páginas e nomes. O modelo pode receber o contexto necessário à consulta. |
| Perguntas, respostas, fatos corrigidos, anotações e evidências | Instruir a análise e permitir revisão humana | Conteúdo cifrado por processo. O descarte elimina a chave e o conteúdo do banco e remove os objetos. |
| Eventos e metadados do modelo | Verificar integridade, rastrear atos e produzir relatório de uso | Consulta e exportação pelo desembargador. Hubs, vínculos e cadeia de auditoria sobrevivem ao descarte. |

<a id="pessoas-citadas-nos-autos"></a>

O aviso aos titulares deve identificar finalidades, agentes, canal de atendimento, critérios de retenção, transferências e exercício de direitos, preservando eventual segredo de justiça. O controlador registra a hipótese aplicável a dados pessoais e, quando necessário, a dados sensíveis, à luz das atribuições públicas e do caso concreto. Há requisitos próprios para registro das operações, segurança, transferência internacional e comunicação de incidentes. [LGPD, redação atualizada](https://www2.camara.leg.br/legin/fed/lei/2018/lei-13709-14-agosto-2018-787077-normaatualizada-pl.html).

<a id="registro-de-operacoes"></a>

## Registro das operações

Preencher para cada fluxo da tabela anterior: processo de trabalho e finalidade específica, categorias de titulares e dados, responsável pela decisão de tratamento, operadores e destinatários, fundamento jurídico, prazo de retenção, localização e transferência, medidas de segurança e data da revisão. Para o fornecedor do modelo, anexar o contrato e a versão efetiva da política de retenção. Vincular cada decisão à avaliação institucional correspondente.

A instalação em desenvolvimento usa TLS no navegador, controle por papel, trilha encadeada, envelope por processo, armazenamento cifrado e worker em rede interna. Não existe pseudonimização de nomes nem cópia de segurança do acervo de trabalho na implantação 0.2. A perda do host pode atingir correções, anotações, conversas e a própria auditoria. Preservar os documentos originais no repositório institucional definido pelo gabinete.

<a id="plano-de-incidentes"></a>
<a id="fundamentos-incidentes"></a>

## Resposta a incidentes

1. Quem identificar o evento avisa o responsável técnico e o desembargador. Registre horário, identificadores e ações de contenção. Preserve evidências em local autorizado e controle a distribuição das exportações.
2. O responsável técnico verifica contas, sessões, estado do serviço e sequência da auditoria. O desembargador pode desativar uma conta ou manter o chat em revisão enquanto apura a ocorrência. [Manual de operação](../operacao/operacao.md#incidentes).
3. O controlador, com o encarregado e a assessoria jurídica, avalia a natureza dos dados, os titulares, a exposição, as consequências e a necessidade de comunicar à ANPD e aos titulares.
4. Em incidente sujeito à comunicação, o prazo geral é de três dias úteis a partir do conhecimento pelo controlador de que o incidente afetou dados pessoais, observadas as regras e exceções aplicáveis. Registrar a decisão, as datas e os protocolos. [Orientação oficial da ANPD](https://www.gov.br/anpd/pt-br/canais_atendimento/agente-de-tratamento/comunicado-de-incidente-de-seguranca-cis).

<a id="modelo-registro-incidente"></a>

**Registro de incidente.** Identificador ______. Datas de detecção e de conhecimento pelo controlador ______. Responsáveis ______. Categorias de dados e pessoas atingidas ______. Risco e fundamento ______. Contenção, comunicações, decisões e protocolos ______. Medidas de recuperação e revisão ______. Usar referências controladas para evidências que contenham dados pessoais.

<a id="relatorio-uso-tribunal"></a>
<a id="modelo-relatorio"></a>

## Relatório de uso ao tribunal

**Destinatário** ______. **Magistrado e gabinete** ______. **Período** ______. **Versão do Lupa, modelo e prompt** ______.

Descrever as classes processuais e tarefas atendidas, fonte da autorização institucional, forma de supervisão humana e treinamentos. Informar número de processos e consultas no período, recusas, revisões, chamadas ao modelo, tokens e custo estimado conforme a exportação de uso. Relatar incidentes e correções sem expor conteúdo dos autos fora do canal autorizado. Anexar os metadados da auditoria necessários e identificar autor, data e canal de envio.

<a id="checklist-piloto"></a>

## Pontos para o gabinete antes do uso real

Registrar parecer sobre o uso de dados identificáveis e sigilosos, termos do modelo, responsabilidades e canal dos titulares. Formalizar acesso de assessores, supervisão de respostas, retenção, perda do host, procedimento de incidente e informação ao tribunal. Conferir com o gabinete o catálogo cível e suas cinco questões jurídicas pendentes. [Seção 11 da especificação](../especificacao/0.2/especificacao.md).
