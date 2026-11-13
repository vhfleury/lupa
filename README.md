# Lupa

O gabinete de um desembargador recebe autos de até cerca de 10 mil páginas e confere à mão
prazos, prescrição e revisões de prisão. O Lupa recebe o PDF ou o ZIP do processo, separa as
peças, extrai os fatos datados com a página de origem e roda validações determinísticas.

- **Quem usa:** assessores e desembargador de um gabinete, pela interface web. O responsável
  técnico instala e opera.
- **O que produz:** dossiê do processo (peças, linha do tempo, réus pseudonimizados), achados das
  três validações do piloto (tempestividade do recurso, prescrição pela pena em abstrato, revisão
  da preventiva em 90 dias) e respostas de chat com citações conferidas contra a página.
- **O que não faz:** não decide, não valora prova, não tipifica e não redige atos.

Etapas 0 a 7 concluídas (ingestão, validações, agente, interface, criptografia em repouso, backup,
guias e operação); a Etapa 8 é o piloto.

## Primeira execução

Pré-requisitos na máquina. O restante roda em contêiner.

| Ferramenta | Versão | Para quê |
| --- | --- | --- |
| Docker Engine com Compose v2 | não fixada no repositório (no Windows, Docker Desktop com WSL 2) | toda a stack |
| `bash` | no Windows, Git Bash | scripts de `scripts/` e `front/scripts/` |
| Python 3 | qualquer 3.x no host | só os scripts do Vault e do backup |

Versões dentro dos contêineres, fixadas no repositório: Python 3.12 (`python:3.12-slim`),
PostgreSQL 16, Redis 7.4, Vault 1.21.3, Caddy 2.8.4, Node 22.12.0 (build do front), Tesseract 5.5.0.
As dependências Python vêm de `requirements*.txt` com hashes; as do front, de
`front/package-lock.json`. Nada é instalado no host.

Rode na raiz do repositório:

```bash
cp .env.example .env        # troque os valores fictícios
docker compose up -d vault           # o vault so fica healthy destravado (Etapa 8.1)
bash scripts/vault_inicializar.sh   # init/unseal de dev, Transit, AppRole e chave lupa-saude
docker compose up -d --build --wait   # ou: make up
docker compose exec api alembic -c src/lupa/migrations/alembic.ini upgrade head
```

### Conferir o resultado

1. Confira a saúde dos serviços:

   ```bash
   curl -k https://localhost:8443/api/saude
   ```

   Saída esperada: `{"api":"ok","db":"ok","minio":"ok","cofre":"ok"}`.

2. Rode as validações sobre a entrada de exemplo
   [`tests/validacoes/fatos_exemplo.json`](tests/validacoes/fatos_exemplo.json) (processo sintético):

   ```bash
   docker compose exec api python -m lupa.validacoes --fatos tests/validacoes/fatos_exemplo.json --materia criminal --referencia 2026-10-20
   ```

   Saída esperada: uma lista JSON com três achados, todos com `"resultado": "conforme"`.

   | `validacao` | Valores que devem aparecer na `explicacao` |
   | --- | --- |
   | `tempestividade_recurso` | prazo de 5 dias contado de 03/09/2026, vencimento em 08/09/2026 |
   | `prescricao_abstrata` | pena máxima de 48 meses, prazo de 8 anos |
   | `revisao_preventiva` | maior intervalo de 87 dias |

   Se o comando terminar sem erro com outra contagem ou outro resultado, a instalação está errada.

Para usar a interface, crie o usuário restrito do banco e o administrador
([Acesso e auditoria](#acesso-e-auditoria-etapa-3)) e abra <https://localhost:8443>.

## Mapa dos módulos

A configuração compartilhada fica na raiz: `.env.example`, `docker-compose.yml`,
`docker-compose.prod.yml`, `pyproject.toml`, `Makefile` e `Dockerfile`.

| Módulo | Conteúdo | Instruções |
| --- | --- | --- |
| `src/lupa/` | API (FastAPI), ingestão e worker, validações, agente, acesso, auditoria, criptografia, migrações | [docs/README.md](docs/README.md), seção "Como o sistema funciona" |
| `front/` | Interface web (SvelteKit) e testes E2E | [front/README.md](front/README.md) |
| `proxy/` | Caddy: HTTPS, front em `/` e API em `/api` | [docs/sistema/front.md](docs/sistema/front.md) |
| `vault/` | Configuração e política do Vault | [docs/sistema/criptografia.md](docs/sistema/criptografia.md) |
| `monitoramento/` | Prometheus e Grafana (perfil `monitoramento`) | [docs/operacao/operacao.md](docs/operacao/operacao.md), seção 9 |
| `scripts/` | Verificação, instalação, Vault, backup, sintéticos e medição | docstring de cada script |
| `tests/` | Espelha `src/lupa/` | [CONTRIBUTING.md](CONTRIBUTING.md) |

O mapa por etapa está em [Onde cada etapa fica](#onde-cada-etapa-fica).

## Documentos

- [CONTRIBUTING.md](CONTRIBUTING.md): caminho de uma alteração, testes e checklist do PR.
- [docs/arquitetura.md](docs/arquitetura.md): limite do sistema, componentes e uma execução de ponta a ponta.
- [docs/adr/](docs/adr/README.md): registros de decisão de arquitetura.
- [docs/runbooks/](docs/runbooks/README.md): procedimentos operacionais.
- [CHANGELOG.md](CHANGELOG.md): mudanças por versão.
- [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md): código de conduta.
- [docs/README.md](docs/README.md): índice de toda a documentação.

## Suporte

- Responsável técnico: Victor Hugo Fleury Barreto (`vhfleury` no GitHub).
- Canal de suporte: `{{canal de suporte do Lupa: e-mail ou mensageria combinada com o gabinete}}`.
- Nunca envie trecho de autos por mensagem ou e-mail.

## Subir

Instalação guiada (gera o `.env`, sobe, Vault, migra, usuário restrito, admin):
`bash scripts/instalar_piloto.sh` (produção) ou `--dev` (no Windows, pelo Git Bash). Os comandos
manuais estão em [Primeira execução](#primeira-execução).

Serviços: `api` (FastAPI, porta `API_PORTA_HOST`, padrão 8000), `db` (PostgreSQL 16, só na rede
interna), `minio` (console em `MINIO_CONSOLE_PORTA_HOST`, padrão 9001; API S3 só na rede interna) e
`minio-init` (cria o bucket `LUPA_MINIO_BUCKET` e sai). Todos expostos apenas em `127.0.0.1`.
Todos rodam sem root: `api` uid 10001, `db` uid 70 (`postgres`), `minio` e `minio-init` uid 10002.

A imagem do MinIO é o fork comunitário `pgsty/minio`, fixado por digest, porque as imagens
oficiais deixaram de estar disponíveis publicamente. **A escolha do object storage está em aberto.**

## Testes, lint e tipagem

```bash
docker compose exec api bash scripts/verificar.sh   # ou: make verificar
```

O script roda `ruff check`, `ruff format --check`, `mypy --strict` e `pytest` (cobertura mínima de
90% em `lupa`), parando no primeiro erro.
Fora do compose, o teste marcado `integracao` é pulado se PostgreSQL ou MinIO estiverem inacessíveis.

Dependências declaradas só no `pyproject.toml` (`dependencies` e o extra `dev`). Os arquivos
`requirements.txt` (produção) e `requirements-dev.txt` (produção + desenvolvimento), com hashes,
são gerados a partir dele pelo `uv`, mirando Linux (roda no Windows sem contêiner). Para mudar
uma versão, edite o `pyproject.toml` e rode `make lock`, ou, sem `make`:

```
uv pip compile pyproject.toml --generate-hashes --python-version 3.12 --python-platform x86_64-manylinux_2_28 --custom-compile-command "make lock" -o requirements.txt
uv pip compile pyproject.toml --generate-hashes --python-version 3.12 --python-platform x86_64-manylinux_2_28 --custom-compile-command "make lock" --extra dev -c requirements.txt -o requirements-dev.txt
```

## Acesso e auditoria (Etapa 3)

Login por usuário e senha (argon2id, mínimo 12 caracteres, fora das 10 mil senhas mais comuns),
seguido de código TOTP de aplicativo autenticador. Sem e-mail em nenhum fluxo. Papéis
`assessor`, `desembargador` e `administrador` (matriz em `src/lupa/acesso/papeis.py`).
O que a auditoria registra e como verificar a integridade: [`docs/sistema/auditoria.md`](docs/sistema/auditoria.md).

Primeira instalação, depois de `docker compose up -d --build --wait`:

```bash
docker compose exec api alembic -c src/lupa/migrations/alembic.ini upgrade head
docker compose exec api python scripts/criar_usuario_banco.py   # usa LUPA_DB_USUARIO_APP/SENHA_APP
docker compose exec api python scripts/criar_admin.py           # usa LUPA_ADMIN_USUARIO/SENHA
docker compose up -d api   # recria a API para ler as variáveis novas do .env
```

- **Usuário de conexão.** `LUPA_DATABASE_URL` (usuário `POSTGRES_USER`) é o dono das tabelas e
  só deve servir para migrações e scripts. A API conecta com `LUPA_DB_USUARIO_APP`, um papel
  com LOGIN, sem superusuário e sem BYPASSRLS, membro de `lupa_app`, criado por
  `scripts/criar_usuario_banco.py`. Em produção, o dono das tabelas precisa ser superusuário ou
  ter `BYPASSRLS` (as funções `SECURITY DEFINER` da migração 0002 dependem disso) e nunca é
  usado pela API. Sem as duas variáveis, a API usa `LUPA_DATABASE_URL` (aceitável só em
  desenvolvimento).
- **Administrador.** `scripts/criar_admin.py` cria o único administrador se ainda não existir.
  No primeiro login ele cadastra o autenticador (a resposta de `/auth/login` traz o segredo e a
  URI `otpauth://` do QR) e é obrigado a trocar a senha. Remova `LUPA_ADMIN_SENHA` do `.env`
  depois.
- **Reset.** Senha e autenticador são reiniciados por quem tem permissão
  (`/usuarios/{id}/resetar-senha`, `/usuarios/{id}/resetar-mfa`); a senha temporária aparece uma
  única vez na resposta e a troca é obrigatória no acesso seguinte.
- **Localização por IP (GeoLite2).** A base gratuita da MaxMind exige conta: crie em
  <https://www.maxmind.com/en/geolite2/signup>, aceite a licença, baixe "GeoLite2 City" (formato
  `.mmdb`), coloque o arquivo fora do git (por exemplo `./geoip/GeoLite2-City.mmdb`), monte no
  contêiner da API (`volumes: ["./geoip:/app/geoip:ro"]`) e defina
  `LUPA_GEOIP_CAMINHO=/app/geoip/GeoLite2-City.mmdb`. Atualize o arquivo manualmente (a MaxMind
  publica versões semanais). Sem a base, IPs públicos ficam "desconhecida"; IPs privados são
  sempre "rede interna".
- **Proxy reverso.** O IP auditado é o da conexão. Atrás de proxy, rode o uvicorn com
  `--proxy-headers --forwarded-allow-ips=<ip do proxy>`.
- **Teste de carga** (1 milhão de eventos, fora da suíte padrão por levar cerca de 1 minuto):
  `docker compose exec api python -m pytest -m carga --no-cov -s`.

## Ingestão — fundações (Etapa 4A)

Upload de PDF ou ZIP do processo, lacre por SHA-256, object storage, fila e worker isolado até o
job em `validado`. Detalhes: [`docs/sistema/ingestao.md`](docs/sistema/ingestao.md).

```bash
docker compose exec api alembic -c src/lupa/migrations/alembic.ini upgrade head   # revisão 0003
curl -X POST "https://.../processos/<id>/arquivos?nome=autos.pdf"      -H "Content-Type: application/octet-stream" --data-binary @autos.pdf     # com cookie de sessão
```

Serviços novos: `redis` (fila RQ, sem persistência e sem porta no host) e `worker`
(`python -m lupa.ingestao.worker`), este só na rede interna `ingestao`, sem saída para fora.
Os parsers rodam em subprocesso com limites de memória, CPU e tempo, sem variáveis `LUPA_*`.
Métricas Prometheus em `GET /metricas` (administrador).

## Onde cada etapa fica

| Etapa | Código | Documentação |
|---|---|---|
| 0. Esqueleto | `src/lupa/config.py`, `logging.py`, `api/` | este README |
| 1. Modelo de dados | `src/lupa/dominio/` | `docs/sistema/modelo-de-dados.md` |
| 2. Validações | `src/lupa/validacoes/` | `docs/sistema/validacoes.md`, `docs/especificacao/catalogo-validacoes.md` |
| 3. Acesso e auditoria | `src/lupa/acesso/`, `src/lupa/auditoria/` | `docs/sistema/auditoria.md` |
| 4A–4F. Ingestão | `src/lupa/ingestao/` | `docs/sistema/ingestao.md`, `docs/piloto/calibracao-projudi.md` |
| 4B. Autos sintéticos | `src/lupa/sinteticos/`, `scripts/gerar_autos.py` | `docs/sistema/sinteticos.md` |
| 5. Agente e chat | `src/lupa/agente/` | `docs/sistema/agente.md`, `docs/especificacao/prompt-injection.md` |
| 6. Interface web | `front/`, `proxy/Caddyfile` | `docs/sistema/front.md` |
| 7.1–7.7. Criptografia em repouso | `src/lupa/seguranca/`, `vault/` | `docs/sistema/criptografia.md`, `docs/decisoes/object-storage.md` |
| 7.8. Backup | `scripts/backup*.sh`, `restaurar.*`, `expurgar_backups.*` | `docs/operacao/backup.md` |
| 7.9. Guias dos usuários | `docs/imagens/` | `docs/guias/guia-assessor.md`, `docs/guias/guia-desembargador.md` |
| 7.10. Operação | `scripts/preparar_repositorio.md` | `docs/operacao/operacao.md` |
| Testes | `tests/` (espelha `src/lupa/`) | — |
| Relatórios, decisões e pendências | — | [Histórico por etapa](docs/etapas/ETAPAS.md#etapas-e-pendencias), `docs/decisoes/registro.md`, `docs/piloto/pendencias.md` (índice em `docs/README.md`) |

## Autos sintéticos (Etapa 4B)

Processos criminais falsos, com gabarito, que servem de régua para a ingestão. Detalhes em
[`docs/sistema/sinteticos.md`](docs/sistema/sinteticos.md).

```bash
docker compose exec api python scripts/gerar_autos.py --destino /tmp/sinteticos processo --semente 1 --paginas 40
docker compose exec api python scripts/gerar_autos.py referencia     # dez processos de referência
docker compose exec api python scripts/gerar_autos.py injecao        # corpus de injeção
docker compose exec api python scripts/medir.py --gabarito G --saida S --json m.json --markdown m.md
```

Os arquivos gerados são grandes e ficam fora do repositório (padrão `.sinteticos/`, ignorada pelo
git; outra pasta com `--destino` ou `LUPA_SINTETICOS_DIR`).

## Interface web (Etapa 6)

Depois de `docker compose up -d --build --wait`, abra **https://localhost:8443** (porta em
`PROXY_PORTA_HOST`). O certificado é autoassinado: aceite o aviso do navegador no primeiro
acesso. O proxy (Caddy) serve o front em `/` e a API em `/api`, no mesmo origin.

- Primeiro acesso de qualquer usuário: senha temporária → cadastro do autenticador (QR code ou
  chave em texto) → troca de senha obrigatória.
- Testes do front: `docker build --target verificacao front` (lint, typecheck, unitários) e
  `bash front/scripts/e2e.sh` (Playwright contra a stack real; **reseta o admin do banco de
  desenvolvimento**).
- Segurança e acessibilidade (6.10): CSP sem nada inline, HSTS, Permissions-Policy e COOP no
  proxy (`python scripts/verificar_cabecalhos.py --url https://localhost:8443`); varredura axe nas
  telas; tema claro/escuro/sistema escolhido no cabeçalho. Limpeza dos dados sintéticos do banco
  de desenvolvimento: `docker compose exec api python scripts/limpar_dev.py --sim`.
- Detalhes, decisões e comandos: `docs/sistema/front.md`.

## Agente e chat (Etapa 5)

Contrato em [`docs/sistema/agente.md`](docs/sistema/agente.md). O agente usa o Claude Agent SDK (`claude-agent-sdk`,
que embute o binário do Claude Code) atrás da interface `ClienteAgente`
(`src/lupa/agente/cliente.py`); só as ferramentas somente leitura do Lupa ficam disponíveis, travadas
no processo da requisição. Toda citação é conferida por código antes de aparecer; pergunta de
valoração de prova, tipificação, conclusão jurídica, opinião sobre o resultado ou minuta é recusada
por regras antes de chamar o modelo.

- `POST /processos/{id}/chat` `{"pergunta": "..."}`: resposta com citações conferidas, recusa ou
  aviso de teto. `GET /processos/{id}/chat`: histórico do usuário no processo.
- `GET /processos/{id}/dossie` (`?resumos=true` pede ao modelo os resumos curtos, rotulados `gerado`).
- Credencial: nunca no repositório. O SDK usa `ANTHROPIC_API_KEY` do ambiente ou o login do Claude
  Code da máquina. Toda a suíte roda com um cliente falso roteirizado; o smoke do cliente real fica
  fora da suíte padrão e é pulado sem credencial (dentro do contêiner não há credencial):

```
docker compose exec api python -m pytest -m llm --no-cov tests/agente/test_smoke_llm.py
```

- Suíte de injeção do agente (passo próprio no `scripts/verificar.sh`, marcador `agente`).
- Tetos e modelo: `LUPA_MODELO`, `LUPA_AGENTE_*` (ver `.env.example`).

## Backup cifrado e guias (Etapas 7.8 e 7.9)

- Backup: `bash scripts/backup.sh`, `restaurar.sh`, `expurgar_backups.sh`; serviço
  `backup` do compose (perfil `backup`), saída por bind mount em `LUPA_BACKUP_DIR` (padrão
  `.backups/`), chaves por mês em `LUPA_BACKUP_CHAVES_DIR` (padrão `.backup-chaves/`). Recusa sem
  espaço livre de 2× a estimativa + 2 GB. Detalhes em `docs/operacao/backup.md`; teste com
  `LUPA_VERIFICAR_BACKUP=1` no `scripts/verificar.sh`.
- Guias para usuários: `docs/guias/guia-assessor.md` e `docs/guias/guia-desembargador.md`; capturas em
  `docs/imagens/` geradas por `bash front/scripts/capturas.sh` (processos sintéticos).

## Criptografia em repouso (Etapas 7.1 a 7.7)

Autos, trechos, conversas e originais ficam cifrados com uma chave por processo (DEK), envelopada
pela chave do gabinete no HashiCorp Vault (Transit); identidades dos réus vão direto ao Transit com
chave própria. Detalhes, formatos e limites em [docs/sistema/criptografia.md](docs/sistema/criptografia.md);
decisão de object storage (pendente de assinatura) em
[docs/decisoes/object-storage.md](docs/decisoes/object-storage.md).

```bash
docker compose up -d vault
bash scripts/vault_inicializar.sh
docker compose up -d --build --wait     # a API e o worker leem o .env com o AppRole
docker compose exec api alembic -c src/lupa/migrations/alembic.ini upgrade head
```

Reiniciar o contêiner `vault` sela o cofre: o healthcheck do `vault` fica `unhealthy` e o
`GET /saude` responde 503 com `"cofre":"falha"` até o unseal (`bash scripts/vault_inicializar.sh
--so-unseal`). Exclusão criptográfica de um
processo: `POST /processos/{id}/descartar` (desembargador ou administrador); rotação da chave de um
gabinete: `POST /gabinetes/{id}/rotacionar-chave` (administrador).

## Operação (Etapa 7.10)

Manual do responsável técnico em [`docs/operacao/operacao.md`](docs/operacao/operacao.md): dimensionamento,
instalação do zero, atualização, Vault (unseal, rotação, backup, pendências de produção),
certificado real e portas, backup e restauração, descarte, limpeza de sintéticos, monitoramento,
resposta a incidente, relatório de uso para o tribunal e checklist de segurança.

- Antes do primeiro commit: `scripts/preparar_repositorio.md` (`.gitattributes` fixa LF).

## Ambiente de piloto (Etapa 8.1)

- **Produção:** `docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d` (só o
  proxy publica portas, 443 e 80; `restart`, limites, rotação de logs, Vault com mlock, dados em
  `LUPA_DADOS_DIR`, backup diário pelo serviço `backup-agendado`).
- **Certificado:** `LUPA_TLS_MODO` = `interno` (dev), `acme` (`LUPA_DOMINIO`, `LUPA_ACME_EMAIL`) ou
  `fornecido` (`LUPA_TLS_CERT`, `LUPA_TLS_CHAVE`); `bash scripts/validar_caddyfile.sh` valida os três.
- **Vault de produção:** `LUPA_AMBIENTE=producao bash scripts/vault_inicializar.sh` (3 partes,
  limiar 2, mostradas uma vez, nada em disco; token raiz revogado no fim).
- **Monitoramento:** `docker compose --profile monitoramento up -d` (Prometheus em
  `127.0.0.1:9090`, Grafana em `127.0.0.1:3000`, painel "Lupa — piloto", alertas em
  `monitoramento/prometheus/regras.yml`).
- **Conferência:** `python scripts/conferir_piloto.py` (checklist da seção 12 do manual).
- [Relatório da etapa 8.1 — Ambiente de piloto](docs/etapas/ETAPAS.md#etapa-8-1).

## Tamanho do repositório

O projeto tem **533 arquivos** e cerca de **99,3 mil linhas**. A contagem considera só o que está versionado no git, então ficam de fora `.venv`, `node_modules` e outros arquivos ignorados.

| Extensão | Arquivos |
|---|---|
| `.py` | 290 |
| `.md` | 54 |
| `.ts` | 39 |
| `.txt` | 29 |
| `.svelte` | 24 |
| `.yaml` | 19 |
| `.sh` | 12 |
| `.png` | 12 |

As linhas incluem tudo: código, testes, documentação e arquivos de dados. As 12 imagens `.png` também entram nessa conta e podem inflar um pouco o número.
