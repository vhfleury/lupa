# Operação do Lupa 0.2

Os comandos abaixo rodam na raiz do repositório, em host com Docker Compose v2, Bash e Python 3. No Windows, os scripts de shell rodam em Git Bash. A implantação versionada é de desenvolvimento e usa TLS interno. Os serviços e volumes devem pertencer à instalação que se pretende operar.

## Primeira instalação

1. Copie `.env.example` para `.env` em uma instalação nova. Defina as credenciais do PostgreSQL, do bucket e do papel de conexão da aplicação, além dos dados de bootstrap do desembargador. As URLs de conexão precisam usar os mesmos usuários e senhas definidos para os serviços. Os segredos ficam fora do Git.
2. Inicialize os serviços internos e configure o Vault:

   ```sh
   docker compose build api worker front
   docker compose up -d db minio minio-init vault
   bash scripts/vault_inicializar.sh
   ```

3. Aplique a revisão do Data Vault ao banco novo. Configure o usuário da aplicação e a primeira conta do desembargador antes de iniciar a API e o worker.

   ```sh
   docker compose run --rm -T api alembic -c pipeline/src/lupa_pipeline/migrations/alembic.ini upgrade head
   docker compose run --rm -T api python intranet/api/scripts/criar_usuario_banco.py
   docker compose run --rm -T api python intranet/api/scripts/criar_desembargador.py
   docker compose up -d --wait
   ```

4. Abra `https://localhost:8443` ou a porta de `PROXY_PORTA_HOST`, confirme a origem do certificado interno e faça o primeiro login com MFA. Acesse `/api/saude` e confira banco, storage e cofre. Para o cliente real do modelo, forneça a credencial de API pelo ambiente reservado da intranet. A verificação normal usa clientes roteirizados.

O esquema anterior tem outra cadeia de migrações. Mantenha os volumes da 0.1 separados da implantação 0.2. A aplicação não oferece migração do acervo da 0.1 nem backup e restauração da 0.2.

## Atualização de versão

Em uma instalação 0.2, obtenha a revisão do código e confira os manifestos e as notas de versão. Reconstrua as imagens com `docker compose up -d --build --wait`, aplique a revisão prevista com `make migrate` e confirme a saúde da instalação e a abertura de um caso sintético. Se o cofre estiver selado, siga o procedimento de destravamento antes de aguardar os serviços dependentes.

## Operação diária

- `docker compose ps` mostra estado e saúde dos serviços. `docker compose logs --since 10m worker api` permite examinar falhas pelo identificador do processo, do arquivo e pelo tipo do erro. A implantação depende dessas verificações e das telas de estado para detectar incidentes.
- O PostgreSQL precisa de espaço para páginas e histórico. O MinIO guarda originais e imagens. Confira o espaço do host e a saúde do cofre quando uma recepção, extração ou página falhar.
- A fila está no banco. O worker controla tentativas em uma única conexão e retoma arquivos pendentes após reinício. Veja o relatório e o motivo de quarentena ou falha antes de reenviar os mesmos bytes, pois a recepção reconhece duplicatas.
- Para encerrar os serviços e conservar os volumes, use `docker compose down`. Para iniciar após uma parada, suba o Vault, destrave-o e suba os demais serviços. O comando `docker compose down -v` apaga os dados dos volumes.

## Cofre e credenciais

Após reiniciar o Vault, execute `bash scripts/vault_inicializar.sh --so-unseal` no host da instalação de desenvolvimento e confira a saúde novamente. O script exige o material de inicialização daquela instalação. A chave Transit `lupa` envolve as DEKs e `lupa-saude` atende à prova do healthcheck. O papel AppRole usado pela aplicação tem as permissões de cifra definidas em `vault/politicas/lupa.hcl`. [Procedimento de destravamento](../runbooks/destravar-vault.md).

As contas de assessores podem ser desativadas ou ter a senha e o MFA redefinidos pelo desembargador. O procedimento de bootstrap usa variáveis de ambiente e mantém a senha fora dos logs. O worker trabalha com `lupa_app`. A conexão do dono serve à instalação do esquema e procedimentos administrativos documentados.

## Descarte

O desembargador aciona `POST /api/processos/{id}/descartar`. O ato apaga o envelope da DEK e os satélites de conteúdo, registra o estado e a auditoria e invalida a chave em cache. A limpeza remove originais e renderizações no bucket. Se o endpoint informar objetos pendentes, regularize o storage e repita a chamada para concluir essa etapa. Mantenha a referência do evento para o histórico.

## Incidentes

| Sinal | Procedimento |
| --- | --- |
| Saúde 503 ou cofre selado | Identifique o componente em `/api/saude`. Verifique o status do contêiner, o material local da instalação e o AppRole. |
| Arquivo permanece pendente | Verifique saúde do worker e do banco, o diagnóstico e o contador de tentativas. A retomada continua a partir do que já foi gravado. |
| Resposta ou trecho suspeito | Preserve a referência e consulte o evento e a página. O desembargador avalia a liberação do chat em revisão. |
| Possível comprometimento de conta | Desative ou redefina as credenciais da conta, preserve os registros filtrados e comunique aos responsáveis. |
| Integridade de auditoria divergente | Registre a primeira posição inconsistente e preserve a exportação e os metadados para investigação. |

Qualquer incidente envolvendo dados pessoais segue o [procedimento da minuta de conformidade](../conformidade/CONFORMIDADE.md#plano-de-incidentes). O relatório de uso para o tribunal fica em **Auditoria**, com exportação do período. As rotas e os parâmetros constam no [documento de auditoria](../sistema/auditoria.md).
