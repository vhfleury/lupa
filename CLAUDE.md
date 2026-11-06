# Lupa — Convenções do projeto

Regras que valem para todo código do repositório. Vieram do plano de execução da v1.

## Linguagem e estilo

- Python 3.12. PEP 8 verificado por `ruff` com `line-length = 100`. Tipagem completa verificada por `mypy --strict`.
- Docstrings no estilo Google em todo módulo, classe e função pública, verificadas por `ruff` com a regra `D` e convenção `google`.
- Funções curtas com uma responsabilidade. Nomes em português para conceitos jurídicos (`peca`, `achado`, `evidencia`) e em inglês para infraestrutura (`repository`, `session`, `handler`). Sem comentários explicando o que o código faz; o nome e a docstring fazem isso.
- Sem lógica em `__init__.py`. Sem imports circulares. Sem `print`; logging estruturado em JSON.

## Testes

- `pytest` com cobertura mínima de 90% em `lupa`, medida por `pytest-cov`.
- Testes nomeados pelo comportamento: `test_apelacao_interposta_no_sexto_dia_e_intempestiva`.
- `scripts/verificar.sh` roda lint, formatação, tipagem e testes, parando no primeiro erro.

## Contêineres

- Tudo roda via `docker compose`. Nenhuma instrução de execução depende de instalação na máquina do desenvolvedor.
- Imagens com usuário não root, `python:3.12-slim` como base, dependências fixadas em `requirements.txt` com hashes.

## Segurança

- Segredos só por arquivo `.env` ignorado pelo git ou pelo Vault. Nunca em código ou em imagem.
- Nenhum conteúdo de autos, senha, token ou texto de pergunta entra em log.

## Entrega de cada etapa

- `RELATORIO-ETAPA-N.M.md` em `docs/etapas/` com: o que foi feito, decisões que o roteiro não previa, o que ficou de fora e por quê, comando para rodar os testes e saída resumida.
- Não alterar arquivos de outras etapas sem registrar no relatório.
