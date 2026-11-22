"""Ferramenta de cálculo (Etapa 5.3): o motor da Etapa 2 como ferramenta do agente.

`executar_validacao(nome)` roda o catálogo da classe sobre os fatos gravados do processo e
devolve o achado completo (resultado, valores, fatos usados e explicação do template). Não grava
achado: a fonte da verdade continua sendo a ingestão. Cada uso gera `validacao_executada` com
`objeto_tipo = "validacao_agente"`.
"""

import json
from typing import Any

from lupa_api.agente.ferramentas.leitura import erro
from lupa_api.agente.ferramentas.sessao import SessaoAgente
from lupa_api.auditoria.eventos import AcaoAuditoria
from lupa_pipeline.dominio.repositorios import listar_fatos_por_processo
from lupa_pipeline.validacoes.catalogo import validacoes_de
from lupa_pipeline.validacoes.modelo import ModeloProcesso
from lupa_pipeline.validacoes.motor import executar_catalogo


def nomes_validacoes(classe: str) -> list[str]:
    """Validações disponíveis na classe.

    Args:
        classe: Matéria do processo.

    Returns:
        Nomes, na ordem do catálogo.
    """
    return [v.nome for v in validacoes_de(classe) if v.nome == "tempestividade_recurso"]


def executar_validacao(sessao: SessaoAgente, argumentos: dict[str, Any]) -> str:
    """Executa uma validação determinística sobre os fatos do processo.

    Args:
        sessao: Sessão do agente.
        argumentos: `nome` da validação.

    Returns:
        Achado completo delimitado, ou erro.
    """
    nome = str(argumentos.get("nome") or "")
    disponiveis = nomes_validacoes(sessao.classe)
    if nome not in disponiveis:
        return erro(f"validação desconhecida; use uma de: {', '.join(disponiveis)}")
    modelo = ModeloProcesso(listar_fatos_por_processo(sessao.session, sessao.processo_id))
    achados = [
        a.model_dump(mode="json")
        for a in executar_catalogo(modelo, sessao.classe, sessao.referencia)
        if a.validacao == nome
    ]
    sessao.registrar(AcaoAuditoria.VALIDACAO_EXECUTADA, "validacao_agente", nome)
    corpo = json.dumps(
        {"achados": achados, "data_referencia": sessao.referencia.isoformat()}, ensure_ascii=False
    )
    return sessao.delimitador.envelopar({"tipo": "resultado_da_validacao"}, corpo)
