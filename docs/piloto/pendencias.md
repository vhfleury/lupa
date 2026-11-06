# Lupa — Pendências

O que ainda falta decidir ou fazer, num lugar só. Junta as pendências do `docs/etapas/CONFORMIDADE-GERAL.md` e das revisões finais (7.10, 8.1 e 8.2), que foram removidas do repositório e continuam no histórico do Git (commit `54219a2`, pasta `docs/etapas/`).

Estado registrado em 22/10/2026. Confira antes de agir: algumas podem já ter sido resolvidas no piloto. A ordem de execução está em [roteiro-piloto.md](roteiro-piloto.md), e os itens formais de segurança em [conformidade/checklist-piloto.md](../conformidade/checklist-piloto.md).

Decisões já tomadas estão em [decisoes/registro.md](../decisoes/registro.md). Limitações e itens fora do escopo de cada etapa, a maioria já resolvida, estão em [etapas/FICOU-DE-FORA.md](../etapas/FICOU-DE-FORA.md).

## Antes do primeiro processo real

1. **Pseudonimização de vítimas e testemunhas.** A pseudonimização da 4F cobre só nome e CPF dos réus (`reu_identidade`); nomes de vítimas e testemunhas vão ao modelo dentro dos trechos. O `requisitos-v1.md` (seção 6) pede pseudonimização de nomes e identificadores sem restringir a réus.
   - Opção A (recomendada pela revisão 8.2): estender a pseudonimização a vítimas e testemunhas identificadas na denúncia, nos termos de depoimento e nas certidões, com uma tabela de identidades por papel; medir recall nos sintéticos; teste de que nenhum nome cadastrado chega ao modelo.
   - Opção B: aceitar a limitação no piloto, só com processos públicos, e registrar no aviso de tratamento que nomes de outras pessoas podem constar dos trechos enviados ao fornecedor do modelo.
2. **Chave da API da Anthropic**, smoke test real do agente (`pytest -m llm`) e leitura dos termos vigentes da API quanto a treinamento, retenção e local de processamento. A aprovação da Etapa 5 ficou condicionada ao smoke test.
3. **Assinatura da decisão do object storage** ([decisoes/object-storage.md](../decisoes/object-storage.md)).
4. **Apagar os 344 objetos sintéticos órfãos** em claro no storage de desenvolvimento. São de processos sintéticos já removidos do banco; o script de descarte não os alcança. Basta um `mc rm` ou um script com lista por prefixo.
5. **Ambiente de produção**: Vault com três pessoas segurando as partes de unseal (sem auto-unseal, pois não há KMS), TLS no Vault, backup frio do volume do Vault, certificado real no proxy, porta direta da API não publicada, perfil de produção num servidor de verdade, `instalar_piloto.sh` ponta a ponta.
6. **Revisão das minutas por advogado** (`docs/conformidade/`) e aceite dos termos pelos usuários.
7. **Confirmação dos dados jurídicos pelo gabinete**: calendários (`feriados`, `suspensoes`), `prazos_recursos`, `prescricao_art109`, `tipos_penais`, `eventos.yaml` e as regras de borda listadas em `docs/sistema/validacoes.md`.
8. **Valores reais das variáveis de produção**: `LUPA_DB_*`, `LUPA_ADMIN_*`, chaves do object storage.

## Itens para o advogado

Registrados pelo executor da 8.2: base legal para dados dos autos tratados por particular e dados de natureza penal; hipótese da transferência internacional ao fornecedor do modelo; encarregado e canal de atendimento; retenção da auditoria; forma do aceite, responsabilidade por indisponibilidade e remuneração; aplicação do registro do § 6º e da capacitação do § 3º, I (Res. CNJ 615/2025, art. 19) ao uso privado; existência de regulamento do TJGO para o § 7º; critério de risco relevante e meio de comunicar titulares que não usam o sistema. Os prazos de comunicação de incidente também ficaram para os documentos de conformidade, porque o `requisitos-v1.md` não os fixa.

## Opcionais ou sem prazo

- **Conta na MaxMind** (GeoLite2) para geolocalização por IP; sem ela a localização fica `desconhecida`.
- **Dimensionamento do worker**: medido 1 worker, 12 CPUs, 4 lotes de 8 páginas, 15 minutos por mil páginas digitalizadas. Recomendação para o piloto: uma réplica com 4 lotes.
- **Canal de notificação dos alertas**: os 4 alertas existem no Prometheus, falta para onde enviá-los.
- **Pasta `.sinteticos` no OneDrive** (4,7 GB sincronizando): excluir da sincronização ou mover com `LUPA_SINTETICOS_DIR`.
- **Arquivo do teste de backup** em `.backups/` (830 KB): apagar com o expurgo ou à mão.
- **Manual de operação**: dizer explicitamente que `conferir_piloto.py` roda no host, porque precisa do CLI do Docker.
