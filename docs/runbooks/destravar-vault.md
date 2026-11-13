# Destravar o Vault depois de um reinício

| Campo | Valor |
| --- | --- |
| Responsável | Victor Hugo Fleury Barreto (responsável técnico) |
| Última validação | 2026-10-21, em desenvolvimento ([ensaios da 7.10](../etapas/ETAPAS.md#ensaios-7-10) e [da 8.1](../etapas/ETAPAS.md#vault-8-1)). Em produção: `{{data da primeira validação em produção}}` |
| Duração medida | 15,9 s do reinício à conferência, em desenvolvimento |

## Quando usar

Qualquer reinício do contêiner `vault` sela o cofre: reboot do host, reinício do Docker ou
atualização de versão. Use este runbook quando aparecer um destes sinais:

- `docker compose ps` mostra `vault` como `unhealthy`;
- `GET /api/saude` responde 503 com `"cofre":"falha"`;
- o alerta `LupaCofreSelado` dispara no Prometheus (2 minutos depois);
- as rotas de processo respondem erro 500 e o login continua funcionando.

Não use para a primeira inicialização (veja [operacao.md, seção 4.1](../operacao/operacao.md)) nem
quando as partes de unseal foram perdidas (seção 4.5 do mesmo manual).

## Pré-condições

- **Ambiente:** host do Lupa, na raiz do repositório, com Docker e `bash` (no Windows, Git Bash).
  Em produção, exporte antes `COMPOSE_FILE=docker-compose.yml:docker-compose.prod.yml`.
- **Parâmetros:** nenhum além de `--so-unseal`.
- **Acessos:** em desenvolvimento, o arquivo `.vault-dev/init.json` (criado na inicialização). Em
  produção, dois dos três portadores das partes presentes: `{{nomes dos três portadores}}`.
- **Execução ativa:** confirme que não há outra pessoa rodando `scripts/vault_inicializar.sh`. Jobs
  de ingestão em andamento não precisam ser cancelados: o worker volta a decifrar sozinho.

## Etapas

1. Confirme que o cofre está selado.

   ```bash
   docker compose exec vault vault status
   ```

   Continue se a linha `Sealed` mostra `true` (código de saída 2). Pare se mostra `false`:
   o problema é outro; vá para "Recuperar uma falha". Pare se o contêiner não responde (código 1):
   suba-o com `docker compose up -d vault` e repita esta etapa.

2. Destrave.

   ```bash
   bash scripts/vault_inicializar.sh --so-unseal
   ```

   Em desenvolvimento, o script usa a chave de `.vault-dev/init.json`. Em produção, dois
   portadores digitam cada um a sua parte, sem eco. Continue se o script termina com código 0.

3. Confirme que o cofre abriu.

   ```bash
   docker compose exec vault vault status
   ```

   Continue se a linha `Sealed` mostra `false` (código de saída 0).

4. Suba o que ficou esperando o cofre.

   ```bash
   docker compose up -d --wait
   ```

   Continue se o comando termina com código 0. Não reinicie `api` nem `worker`: eles refazem o
   login no Vault sozinhos.

## Validar o resultado

Todos os itens abaixo precisam ser verdadeiros.

1. A saúde responde 200 com o cofre em ordem (troque o endereço em produção):

   ```bash
   curl -k https://localhost:8443/api/saude
   ```

   Esperado: `{"api":"ok","db":"ok","minio":"ok","cofre":"ok"}`. O componente `cofre` cifra e
   decifra um valor de teste pela chave `lupa-saude`.

2. `docker compose ps` mostra `vault`, `api`, `worker` e `proxy` como `healthy`.
3. No navegador, um processo abre e uma página aparece no visualizador. Isso prova que a API
   decifra dados reais, não só o valor de teste.
4. Com o perfil `monitoramento` ligado, `lupa_cofre_ok` vale 1 e o alerta `LupaCofreSelado` some de
   `http://127.0.0.1:9090/alerts`.

## Recuperar uma falha

| Sintoma | Ação |
| --- | --- |
| O script recusa uma parte | Peça ao portador para digitar de novo. Vale o limite de tentativas abaixo. |
| `Sealed` em `false`, mas `/api/saude` segue com `"cofre":"falha"` | Leia `docker compose logs api --since 10m` e procure `CofreError`. Em desenvolvimento, rode `bash scripts/vault_inicializar.sh` (sem a opção: gera um `secret_id` novo) e depois `docker compose up -d api worker`. Em produção, gerar `secret_id` exige um token raiz criado pelo quórum (`vault operator generate-root`). |
| `api` ou `proxy` seguem `unhealthy` com o cofre em ordem | `docker compose up -d --wait` de novo e `docker compose logs api worker --since 10m`. |
| O contêiner `vault` não sobe | `docker compose logs vault --since 10m`. Se o volume `vault-dados` estiver danificado, restaure o Vault pelo [manual, seção 4.4](../operacao/operacao.md). |

## Quando parar de tentar

- Pare depois de duas tentativas recusadas da mesma parte. Não tente adivinhar: uma parte errada
  não abre o cofre e nada é recuperável por força bruta.
- Pare se não houver dois portadores disponíveis. O sistema fica indisponível para os autos até
  eles chegarem; o login e a auditoria continuam.
- Pare se não existirem mais duas partes. Siga a [seção 4.5 do manual](../operacao/operacao.md):
  trate como perda total dos dados cifrados, reinstale o Vault, recrie os gabinetes e reenvie os
  autos.

## Quem acionar

- Responsável técnico: Victor Hugo Fleury Barreto, por `{{canal de acionamento do responsável técnico}}`.
- Portadores das partes: `{{nomes e contatos dos portadores}}`.
- Indisponibilidade acima de `{{tempo máximo aceito pelo gabinete}}`: avise o desembargador do gabinete.
- Suspeita de vazamento ou de credencial comprometida: trate como incidente
  ([manual, seção 10](../operacao/operacao.md)).
