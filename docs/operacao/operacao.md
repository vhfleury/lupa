# Operação do Lupa 0.2

Os comandos abaixo rodam na raiz do repositório, em host com Docker Compose v2, Bash e Python 3. No Windows, os scripts de shell rodam em Git Bash. A implantação versionada é de desenvolvimento e usa TLS interno. Os serviços e volumes devem pertencer à instalação que se pretende operar.

## Primeira instalação

1. Copie `.env.example` para `.env` em uma instalação nova. Defina as credenciais do PostgreSQL, do bucket e do papel de conexão da aplicação, além dos dados de bootstrap do desembargador. As URLs de conexão precisam usar os mesmos usuários e senhas definidos para os serviços. Os segredos ficam fora do Git.
2. Inicialize os serviços internos:

   ```sh
   docker compose build api worker front
   docker compose up -d db minio minio-init
   ```

3. Aplique a revisão do Data Vault ao banco novo. Configure o usuário da aplicação e a primeira conta do desembargador antes de iniciar a API e o worker.

   ```sh
   docker compose run --rm -T api alembic -c pipeline/src/lupa_pipeline/migrations/alembic.ini upgrade head
   docker compose run --rm -T api python intranet/api/scripts/criar_usuario_banco.py
   docker compose run --rm -T api python intranet/api/scripts/criar_desembargador.py
   docker compose up -d --wait
   ```

4. Abra `https://localhost:8443` ou a porta de `PROXY_PORTA_HOST`, confirme a origem do certificado interno e faça o primeiro login com MFA. Acesse `/api/saude` e confira `api`, `db` e `minio`. Para o cliente real do modelo, forneça a credencial de API pelo ambiente reservado da intranet. A verificação normal usa clientes roteirizados.

O esquema anterior tem outra cadeia de migrações. Mantenha os volumes da 0.1 separados da implantação 0.2. A aplicação não oferece migração do acervo da 0.1 nem backup e restauração da 0.2.

## Atualização de versão

Em uma instalação 0.2, obtenha a revisão do código e confira os manifestos e as notas de versão. Reconstrua as imagens com `docker compose up -d --build --wait`, aplique a revisão prevista com `make migrate` e confirme a saúde da instalação e a abertura de um caso sintético.

A atualização que remove o Vault e a cifra da aplicação (revisão `v0003`) não converte os dados gravados com cifra. Pare os serviços e apague os volumes do banco, do MinIO e `vault-dados` (`docker compose down -v` apaga todos os volumes do projeto). Refaça a [primeira instalação](#primeira-instalação) e reenvie os processos.

## Operação diária

- `docker compose ps` mostra estado e saúde dos serviços. `docker compose logs --since 10m worker api` permite examinar falhas pelo identificador do processo, do arquivo e pelo tipo do erro. A implantação depende dessas verificações e das telas de estado para detectar incidentes.
- O PostgreSQL precisa de espaço para páginas e histórico. O MinIO guarda originais e imagens. Confira o espaço do host e a saúde do banco e do storage quando uma recepção, extração ou página falhar.
- A fila está no banco. O worker controla tentativas em uma única conexão e retoma arquivos pendentes após reinício. Veja o relatório e o motivo de quarentena ou falha antes de reenviar os mesmos bytes, pois a recepção reconhece duplicatas.
- Para encerrar os serviços e conservar os volumes, use `docker compose down`. Para iniciar após uma parada, use `docker compose up -d --wait`. O comando `docker compose down -v` apaga os dados dos volumes.

## Credenciais

Os segredos da instalação ficam no `.env`, fora do Git. Autos, nomes de partes e mensagens ficam em claro no PostgreSQL e no MinIO; restrinja o acesso ao host e aos volumes.

As contas de assessores podem ser desativadas ou ter a senha e o MFA redefinidos pelo desembargador. O procedimento de bootstrap usa variáveis de ambiente e mantém a senha fora dos logs. O worker trabalha com `lupa_app`. A conexão do dono serve à instalação do esquema e procedimentos administrativos documentados.

## Descarte

O desembargador aciona `POST /api/processos/{id}/descartar`. O ato apaga os satélites de conteúdo e registra o estado e a auditoria; o evento `processo_descartado` tem `objeto_tipo` `processo` e `objeto_id` igual ao identificador do processo. A limpeza remove originais e renderizações no bucket. Se o endpoint informar objetos pendentes, regularize o storage e repita a chamada para concluir essa etapa. Mantenha a referência do evento para o histórico.

## Incidentes

| Sinal | Procedimento |
| --- | --- |
| Saúde 503 | Identifique o componente em `/api/saude` (`db` ou `minio`). Verifique o status do contêiner e as credenciais do `.env`. |
| Arquivo permanece pendente | Verifique saúde do worker e do banco, o diagnóstico e o contador de tentativas. A retomada continua a partir do que já foi gravado. |
| Resposta ou trecho suspeito | Preserve a referência e consulte o evento e a página. O desembargador avalia a liberação do chat em revisão. |
| Possível comprometimento de conta | Desative ou redefina as credenciais da conta, preserve os registros filtrados e comunique aos responsáveis. |
| Integridade de auditoria divergente | Registre a primeira posição inconsistente e preserve a exportação e os metadados para investigação. |

Qualquer incidente envolvendo dados pessoais segue o [procedimento da minuta de conformidade](../conformidade/CONFORMIDADE.md#plano-de-incidentes). O relatório de uso para o tribunal fica em **Auditoria**, com exportação do período. As rotas e os parâmetros constam no [documento de auditoria](../sistema/auditoria.md).
