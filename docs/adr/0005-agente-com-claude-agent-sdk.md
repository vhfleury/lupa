# ADR 0005 — Agente com o Claude Agent SDK e modelo externo

| Status | Data | Responsável |
| --- | --- | --- |
| Aceito | 2026-10-20 | Victor Hugo Fleury Barreto |

## Contexto

O desenho original previa um modelo open-weight local, sem ferramentas. Os requisitos da v1 pedem um chat que localiza, extrai e resume informações dos autos com citação de página.

## Restrições

- O agente não escreve, não acessa rede e não executa código.
- Nenhum dado de autos treina modelo.
- A credencial nunca entra no repositório.
- A documentação do SDK veda oferecer login do claude.ai em produto de terceiro.

## Alternativas consideradas

| Alternativa | Por que foi descartada |
| --- | --- |
| Modelo open-weight local (vLLM com GPU) | Padrão do desenho original. Os requisitos não registram o motivo do descarte: `{{motivo de descartar o modelo local}}`. |
| Modelo sem ferramentas | Os requisitos pedem consulta ao resultado estruturado e cálculo determinístico de prazo e prescrição, que são ferramentas de leitura. |
| Login do Claude Code no piloto | Vedado pela documentação do SDK; no piloto a credencial é `ANTHROPIC_API_KEY` vinda de cofre. |

## Decisão

O agente usa o `claude-agent-sdk` atrás da interface `ClienteAgente` (`src/lupa/agente/cliente.py`), com ferramentas só de leitura, travadas num único processo por conversa. O texto enviado sai pseudonimizado (nome e CPF dos réus). Toda citação é conferida por código antes de aparecer. Pergunta de valoração, tipificação ou conclusão jurídica é recusada por regras antes da chamada.

## Consequências

- Trechos dos autos saem do servidor para o fornecedor do modelo; isso consta do aviso de tratamento.
- A pseudonimização cobre só réus; vítimas e testemunhas estão em decisão (pendências do piloto, item 1; removido, ver histórico do Git).
- A imagem da API cresce cerca de 300 MB, porque o wheel embute o binário do Claude Code.
- O SDK não tem `max_tokens` por chamada: o teto é conferido depois e o laço é limitado por `max_turns`.
- Trocar de modelo exige rodar a suíte do agente.
- A suíte inteira roda com um cliente falso roteirizado; o smoke real (`pytest -m llm`) fica fora da suíte padrão.

## Fontes

- [especificacao/requisitos-v1.md](../especificacao/requisitos-v1.md), seções 4.4, 5 e 6
- [decisoes/registro.md](../decisoes/registro.md), Etapa 5
- [sistema/agente.md](../sistema/agente.md)
