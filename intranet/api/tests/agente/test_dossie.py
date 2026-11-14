"""Dossiê em esquema fixo (5.10): determinístico, e o modelo só preenche resumo citado."""

from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import Engine

from apoio_comum import eventos_do_banco
from lupa_intranet.agente.cliente import ClienteFalso, PedidoAgente, Roteiro, resposta_json
from lupa_intranet.agente.contexto import segmentos
from lupa_pipeline.ingestao.saneamento import normalizar
from tests.agente.conftest import NOME_PARTE, TEXTOS, ProcessoAgente
from tests.conftest import logar

pytestmark = pytest.mark.integracao

CAMPOS_TEXTO_LIVRE = {"trecho", "explicacao", "classe", "nome"}


def textos_livres_sem_rotulo(valor: Any, chave: str = "", rotulado: bool = False) -> list[str]:
    """Campos com frase livre fora de `trecho`, `explicacao`, dos valores do motor e do `gerado`.

    Args:
        valor: Dossiê serializado (ou parte).
        chave: Chave do valor.
        rotulado: Se está dentro de bloco com `rotulo = "gerado"`.

    Returns:
        Chaves com frase livre sem rótulo.
    """
    if chave == "valores":
        return []
    if isinstance(valor, dict):
        dentro = rotulado or valor.get("rotulo") == "gerado"
        return [c for k, v in valor.items() for c in textos_livres_sem_rotulo(v, k, dentro)]
    if isinstance(valor, list):
        return [c for v in valor for c in textos_livres_sem_rotulo(v, chave, rotulado)]
    if isinstance(valor, str) and " " in valor and chave not in CAMPOS_TEXTO_LIVRE and not rotulado:
        return [chave]
    return []


def _cliente_http(app: FastAPI, engine: Engine, processo: ProcessoAgente) -> TestClient:
    cliente = TestClient(app, base_url="https://testserver")
    logar(cliente, engine, processo.assessor)
    return cliente


def _hash(numero: int, trecho: str) -> str:
    base = normalizar(TEXTOS[numero]).texto
    return next(h for s, h in segmentos(base) if trecho in s)


def test_dossie_deterministico_tem_esquema_fixo_e_e_auditado(
    app_teste: FastAPI, engine_teste: Engine, processo_agente: ProcessoAgente
) -> None:
    """Dossie deterministico tem esquema fixo e e auditado."""
    falso = ClienteFalso([Roteiro(resposta="nunca")])
    app_teste.state.cliente_agente = falso
    cliente = _cliente_http(app_teste, engine_teste, processo_agente)
    resposta = cliente.get(f"/processos/{processo_agente.processo_id}/dossie")
    assert resposta.status_code == 200, resposta.text
    dossie = resposta.json()
    assert set(dossie) == {
        "versao_esquema",
        "ficha",
        "pecas",
        "linha_do_tempo",
        "alertas",
        "achados",
    }
    (parte,) = dossie["ficha"]["partes"]
    assert (parte["nome"], parte["polo"], parte["qualidade"], parte["pagina_id"]) == (
        NOME_PARTE,
        "ativo",
        "particular",
        processo_agente.paginas[1],
    )
    assert dossie["ficha"]["responsaveis"] == [
        {"id": processo_agente.assessor.id, "nome_usuario": processo_agente.assessor.nome}
    ]
    assert dossie["ficha"]["ingestao"]["situacao"] == "processando"
    assert [p["tipo"] for p in dossie["pecas"]] == ["sentenca", "apelacao", "certidao"]
    assert all(p["resumo_peca"] is None for p in dossie["pecas"])
    datas = [(e["data"], e["tipo"], e["pagina"]) for e in dossie["linha_do_tempo"]]
    assert datas == [
        ("2024-01-05", "data_decisao_recorrida", 1),
        ("2025-03-10", "data_intimacao", 3),
        ("2025-03-14", "data_interposicao", 2),
    ]
    assert [(a["pagina"], a["flags"]) for a in dossie["alertas"]] == [(2, ["padrao_instrucao"])]
    (achado,) = dossie["achados"]
    assert achado["validacao"] == "tempestividade_recurso"
    assert len(achado["fatos_usados"]) == len(achado["fontes"]) == 5
    assert all(f["pagina_id"] in processo_agente.paginas.values() for f in achado["fontes"])
    assert textos_livres_sem_rotulo(dossie) == []
    assert falso.pedidos == []
    eventos = eventos_do_banco(
        engine_teste, acao="processo_aberto", processo_id=processo_agente.processo_id
    )
    assert any(e.objeto_id == f"/processos/{processo_agente.processo_id}/dossie" for e in eventos)
    assert cliente.get("/processos/" + "f" * 64 + "/dossie").status_code == 404


def _roteiro_resumo(pedido: PedidoAgente) -> Roteiro:
    if "SENTENÇA" in pedido.mensagem:
        trecho = "Parte autora: Marina Lima"
        citacao = {"pagina_id": "{p1}", "trecho": trecho, "hash_trecho": _hash(1, trecho)}
        return Roteiro(resposta=resposta_json("A sentença identifica Marina Lima [1].", [citacao]))
    if "RAZÕES" in pedido.mensagem:
        trecho = "interpõe apelação em 14/03/2025"
        citacao = {"pagina_id": "{p2}", "trecho": trecho, "hash_trecho": _hash(2, trecho)}
        return Roteiro(resposta=resposta_json("Uma. Duas. Três frases [1].", [citacao]))
    return Roteiro(resposta=resposta_json("Certidão de intimação.", []))


def test_resumo_so_entra_com_citacao_conferida_ate_duas_frases_e_rotulo_gerado(
    app_teste: FastAPI, engine_teste: Engine, processo_agente: ProcessoAgente
) -> None:
    """Resumo so entra com citacao conferida ate duas frases e rotulo gerado."""

    def _roteiro(pedido: PedidoAgente) -> Roteiro:
        roteiro = _roteiro_resumo(pedido)
        texto = (
            str(roteiro.resposta)
            .replace("{p1}", str(processo_agente.paginas[1]))
            .replace("{p2}", str(processo_agente.paginas[2]))
        )
        return Roteiro(resposta=texto)

    falso = ClienteFalso(_roteiro)
    app_teste.state.cliente_agente = falso
    cliente = _cliente_http(app_teste, engine_teste, processo_agente)
    dossie = cliente.get(f"/processos/{processo_agente.processo_id}/dossie?resumos=true").json()
    resumos = [p["resumo_peca"] for p in dossie["pecas"]]
    assert resumos[0]["rotulo"] == "gerado"
    assert resumos[0]["texto"] == "A sentença identifica Marina Lima [1]."
    assert len(resumos[0]["citacoes"]) == 1
    assert resumos[1:] == [None, None]
    assert len(falso.pedidos) == 3 and all(p.ferramentas == () for p in falso.pedidos)
    assert textos_livres_sem_rotulo(dossie) == []
    tudo = "\n".join(falso.recebidos)
    assert NOME_PARTE in tudo
    chamadas = eventos_do_banco(
        engine_teste, acao="chamada_modelo", processo_id=processo_agente.processo_id
    )
    assert len(chamadas) == 3
