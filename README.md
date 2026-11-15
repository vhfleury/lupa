# Lupa

O Lupa 0.2 auxilia um gabinete cível de segundo grau a localizar peças e provas, conferir prazos e requisitos documentais de recursos e consultar os autos com citações verificáveis. O dossiê reúne partes, linha do tempo, fatos e achados. O assessor e o desembargador podem abrir a página que fundamenta cada resultado.

## Primeira execução em desenvolvimento

Instale Docker com Compose v2, Bash e Python 3 no host. No Windows, execute os scripts em Git Bash. Em uma instalação nova, copie `.env.example` para `.env` e configure as credenciais de desenvolvimento. O procedimento completo, incluindo a criação das contas de banco e do primeiro desembargador, está no [manual de operação](docs/operacao/operacao.md#primeira-instalação).

```sh
docker compose build api worker front
docker compose up -d db minio minio-init vault
bash scripts/vault_inicializar.sh
docker compose run --rm -T api alembic -c pipeline/src/lupa_pipeline/migrations/alembic.ini upgrade head
docker compose run --rm -T api python intranet/api/scripts/criar_usuario_banco.py
docker compose run --rm -T api python intranet/api/scripts/criar_desembargador.py
docker compose up -d --wait
```

Abra `https://localhost:8443`. Em `/api/saude`, os campos `api`, `db`, `minio` e `cofre` indicam a saúde dos componentes. O primeiro login conduz ao cadastro do autenticador e à troca de senha temporária.

## Reproduzir uma conferência

```sh
docker compose exec worker python -m lupa_pipeline.validacoes --fatos pipeline/tests/validacoes/fatos_exemplo.json --classe apelacao_civel --referencia 2026-10-20
```

No exemplo, o recurso chegou um dia útil após o vencimento de 24/08/2026. O preparo e a representação aparecem como conformes. A lista esperada inclui as datas, a regra aplicada e os identificadores das fontes. [Gabarito](pipeline/tests/validacoes/achados_exemplo.json).

## Repositório

| Diretório | Componente |
| --- | --- |
| [pipeline/](pipeline/) | Data Vault, criptografia, ingestão, leitura de PDF e ZIP, catálogo de validações e gerador sintético |
| [intranet/api/](intranet/api/) | API, contas, sessão, chat, dossiê e auditoria |
| [intranet/web/](intranet/web/README.md) | Interface SvelteKit, testes de componentes, Playwright e capturas |
| [intranet/proxy/](intranet/proxy/) | Proxy HTTPS e cabeçalhos de segurança |
| [vault/](vault/) | Configuração e política do Vault Transit |
| [docs/](docs/README.md) | Especificação, arquitetura, guias, operação, conformidade e decisões |

Para desenvolvimento e verificação das suítes, consulte [CONTRIBUTING.md](CONTRIBUTING.md). As mudanças de versão ficam no [changelog](CHANGELOG.md).
