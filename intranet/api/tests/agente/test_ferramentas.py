"""Ferramentas do agente (5.2 a 5.4), travadas no processo da sessão."""

import json
from secrets import token_hex
from typing import Any

import pytest

from lupa_intranet.agente.cliente import ClienteFalso, PassoFerramenta, PedidoAgente, Roteiro
from lupa_intranet.agente.ferramentas import leitura
from lupa_intranet.agente.ferramentas.calculo import executar_validacao
from lupa_intranet.agente.ferramentas.leitura import (
    buscar_texto,
    ler_pagina_estruturada,
    listar_achados,
    listar_fatos,
    listar_pecas,
)
from lupa_intranet.agente.ferramentas.original import OBJETO_PAGINA_ORIGINAL, ler_pagina_original
from lupa_intranet.agente.ferramentas.registro import criar_ferramentas
from lupa_intranet.agente.ferramentas.sessao import SessaoAgente, flags_ligadas
from lupa_intranet.auditoria.eventos import AcaoAuditoria
from lupa_pipeline.dominio.visoes import VisaoPagina
from tests.agente.conftest import (
    NOME_PARTE,
    SENTINELA_OCULTO,
    TEXTO_OUTRO,
    EventosCapturados,
    ProcessoAgente,
)

pytestmark = pytest.mark.integracao


def _forjar(processo: ProcessoAgente, **extra: object) -> dict[str, object]:
    return {"processo_id": str(processo.outro_processo_id)} | extra


def _sem_dado_do_outro(saida: str, processo: ProcessoAgente) -> None:
    assert "PROCESSO B" not in saida
    assert str(processo.outro_processo_id) not in saida
    assert str(processo.outra_pagina_id) not in saida
    assert processo.outro_numero_cnj not in saida


def test_toda_ferramenta_ignora_processo_forjado_no_argumento(
    sessao_agente: SessaoAgente, processo_agente: ProcessoAgente
) -> None:
    """Toda ferramenta ignora processo forjado no argumento."""
    saidas = [
        listar_pecas(sessao_agente, _forjar(processo_agente)),
        listar_fatos(sessao_agente, _forjar(processo_agente)),
        listar_achados(sessao_agente, _forjar(processo_agente)),
        buscar_texto(sessao_agente, _forjar(processo_agente, termo="PROCESSO B")),
        buscar_texto(sessao_agente, _forjar(processo_agente, termo="recorrente")),
        ler_pagina_estruturada(sessao_agente, _forjar(processo_agente, numero=1)),
        executar_validacao(sessao_agente, _forjar(processo_agente, nome="tempestividade_recurso")),
    ]
    for saida in saidas:
        _sem_dado_do_outro(saida, processo_agente)
    assert json.loads(saidas[3]) == {"resultados": 0}
    assert "intimei a parte recorrente" in saidas[4]
    assert "SENTENÇA" in saidas[5]


def test_pagina_de_outro_processo_e_recusada_mesmo_com_id_real(
    sessao_agente: SessaoAgente, processo_agente: ProcessoAgente
) -> None:
    """Pagina de outro processo e recusada mesmo com id real."""
    for funcao in (ler_pagina_estruturada, ler_pagina_original):
        saida = funcao(sessao_agente, {"pagina_id": str(processo_agente.outra_pagina_id)})
        assert json.loads(saida) == {"erro": "página não pertence a este processo"}
        assert TEXTO_OUTRO not in saida
    assert sessao_agente.paginas_originais == 0


def test_resolucao_de_pagina_por_numero_e_erros_claros(
    sessao_agente: SessaoAgente, processo_agente: ProcessoAgente
) -> None:
    """Resolucao de pagina por numero e erros claros."""
    casos: dict[str, dict[str, Any]] = {
        "identificador inválido": {"pagina_id": "nao-e-uuid"},
        "informe pagina_id ou numero": {},
        "página não encontrada neste processo": {"numero": 99},
        "arquivo não pertence a este processo": {"numero": 1, "arquivo_id": token_hex(32)},
    }
    for mensagem, argumentos in casos.items():
        assert json.loads(ler_pagina_estruturada(sessao_agente, argumentos)) == {"erro": mensagem}
    por_arquivo = ler_pagina_estruturada(
        sessao_agente, {"numero": 3, "arquivo_id": str(processo_agente.arquivo_id)}
    )
    assert "intimei a parte recorrente" in por_arquivo


def test_pagina_estruturada_vem_delimitada_rotulada_com_nomes_e_sem_texto_oculto(
    sessao_agente: SessaoAgente, processo_agente: ProcessoAgente
) -> None:
    """Pagina estruturada vem delimitada rotulada com_nomes e sem texto oculto."""
    saida = ler_pagina_estruturada(sessao_agente, {"pagina_id": str(processo_agente.paginas[2])})
    delimitador = sessao_agente.delimitador
    assert saida.startswith(delimitador.abre) and saida.endswith(delimitador.fecha)
    assert '"origem": "parte"' in saida and '"tipo_peca": "apelacao"' in saida
    assert '"flags": ["padrao_instrucao"]' in saida
    assert NOME_PARTE in saida
    assert SENTINELA_OCULTO not in saida
    assert "[hash=" in saida


def test_fatos_e_achados_vem_com_nomes_com_evidencia_citavel(
    sessao_agente: SessaoAgente,
) -> None:
    """Fatos e achados vem com_nomes com evidencia citavel."""
    fatos = listar_fatos(sessao_agente, {"tipo": "data_intimacao"})
    assert "intimei a parte recorrente em 10/03/2025" in fatos and "hash_trecho" in fatos
    assert "data_decisao_recorrida" not in fatos
    achados = listar_achados(sessao_agente, {})
    assert "tempestividade_recurso" in achados
    assert TEXTO_OUTRO not in listar_pecas(sessao_agente, {}) + fatos + achados


def test_executar_validacao_devolve_achado_completo_e_registra(
    sessao_agente: SessaoAgente, capturados: EventosCapturados
) -> None:
    """Executar validacao devolve achado completo e registra."""
    saida = executar_validacao(sessao_agente, {"nome": "tempestividade_recurso"})
    corpo = saida.split("\n", 2)[2].rsplit("\n", 1)[0]
    resultado = json.loads(corpo)
    achado = resultado["achados"][0]
    assert achado["validacao"] == "tempestividade_recurso"
    assert achado["resultado"] in {"conforme", "atencao", "verificar"}
    assert achado["valores"] and achado["explicacao"]
    assert resultado["data_referencia"] == "2025-04-01"
    assert capturados.eventos == [
        (AcaoAuditoria.VALIDACAO_EXECUTADA, "validacao_agente", "tempestividade_recurso")
    ]
    erro = json.loads(executar_validacao(sessao_agente, {"nome": "calcular_tudo"}))
    assert "validação desconhecida" in erro["erro"]


def test_pagina_original_tem_limite_por_conversa_e_cada_uso_e_auditado(
    sessao_agente: SessaoAgente, processo_agente: ProcessoAgente, capturados: EventosCapturados
) -> None:
    """Pagina original tem limite por conversa e cada uso e auditado."""
    pagina = str(processo_agente.paginas[2])
    primeira = ler_pagina_original(sessao_agente, {"pagina_id": pagina})
    assert '"texto": "original"' in primeira and '"categoria": "ignorar_instrucoes"' in primeira
    assert SENTINELA_OCULTO not in primeira and NOME_PARTE in primeira
    ler_pagina_original(sessao_agente, {"numero": 1})
    recusa = json.loads(ler_pagina_original(sessao_agente, {"numero": 3}))
    assert "limite de 2 páginas originais por conversa atingido" in recusa["erro"]
    assert sessao_agente.paginas_originais == 2
    assert [e[:2] for e in capturados.eventos] == [
        (AcaoAuditoria.PAGINA_VISTA, OBJETO_PAGINA_ORIGINAL)
    ] * 2


def test_busca_valida_tamanho_do_termo_e_escapa_curingas(sessao_agente: SessaoAgente) -> None:
    """Busca valida tamanho do termo e escapa curingas."""
    assert "erro" in json.loads(buscar_texto(sessao_agente, {"termo": "ab"}))
    assert json.loads(buscar_texto(sessao_agente, {"termo": "%%%"})) == {"resultados": 0}
    assert NOME_PARTE in buscar_texto(sessao_agente, {"termo": "Marina"})


def test_pagina_sem_normalizado_gravado_usa_o_recalculado(
    sessao_agente: SessaoAgente, processo_agente: ProcessoAgente
) -> None:
    """Pagina sem normalizado gravado usa o recalculado."""
    pagina = sessao_agente.session.get(VisaoPagina, bytes.fromhex(processo_agente.paginas[3]))
    assert pagina is not None
    pagina.texto_normalizado = None
    assert "intimei a parte recorrente" in leitura.texto_analise(pagina)
    assert flags_ligadas({"a": True, "b": False, "c": 0}) == ["a"]


async def test_ferramentas_registradas_gravam_saidas_somente_do_processo(
    sessao_agente: SessaoAgente, processo_agente: ProcessoAgente
) -> None:
    """Ferramentas registradas gravam saídas somente do processo."""
    ferramentas = criar_ferramentas(sessao_agente)
    assert [f.nome for f in ferramentas] == [
        "listar_pecas", "ler_pagina_estruturada", "buscar_texto", "listar_fatos",
        "listar_achados", "executar_validacao", "ler_pagina_original",
    ]  # fmt: skip
    passos = tuple(
        PassoFerramenta(
            f.nome, {"numero": 1, "termo": "sentença", "nome": "tempestividade_recurso"}
        )
        for f in ferramentas
    )
    falso = ClienteFalso([Roteiro(passos=passos, resposta="{}")])
    pedido = PedidoAgente("s", "m", "modelo", 5, ferramentas)
    await falso.responder(pedido)
    assert len(sessao_agente.saidas) == len(ferramentas)
    tudo = "\n".join(falso.recebidos)
    assert NOME_PARTE in tudo and TEXTO_OUTRO not in tudo
