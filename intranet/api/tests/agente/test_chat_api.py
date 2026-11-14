"""Rotas do chat (5.5 a 5.9) com o cliente falso: citações, recusa, tetos e auditoria."""

import json
from collections.abc import Callable
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import Engine, select
from sqlalchemy.engine import RowMapping
from sqlalchemy.orm import Session

from apoio_comum import eventos_do_banco
from lupa_intranet.agente.cliente import (
    ClienteAgenteError,
    ClienteFalso,
    PassoFerramenta,
    PedidoAgente,
    RespostaAgente,
    Roteiro,
    resposta_json,
)
from lupa_intranet.agente.contexto import prompt_sistema, segmentos
from lupa_intranet.auditoria.eventos import AcaoAuditoria
from lupa_pipeline.config import Settings, get_settings
from lupa_pipeline.dominio.esquemas import calcular_hash
from lupa_pipeline.dominio.tabelas import link_chamada_modelo
from lupa_pipeline.dominio.visoes import VisaoConversa, VisaoMensagem
from tests.agente.conftest import NOME_PARTE, TEXTO_OUTRO, TEXTOS, ProcessoAgente
from tests.conftest import logar

pytestmark = pytest.mark.integracao


def _cliente_http(app: FastAPI, engine: Engine, processo: ProcessoAgente) -> TestClient:
    cliente = TestClient(app, base_url="https://testserver")
    logar(cliente, engine, processo.assessor)
    return cliente


def _usar(app: FastAPI, falso: Any) -> Any:
    app.state.cliente_agente = falso
    return falso


def _perguntar(cliente: TestClient, processo: ProcessoAgente, pergunta: str) -> dict[str, Any]:
    resposta = cliente.post(f"/processos/{processo.processo_id}/chat", json={"pergunta": pergunta})
    assert resposta.status_code == 200, resposta.text
    corpo: dict[str, Any] = resposta.json()
    return corpo


def _hash_de(pagina_texto: str, trecho: str) -> str:
    return next(h for s, h in segmentos(pagina_texto) if trecho in s)


def _citacao(processo: ProcessoAgente, numero: int, trecho: str) -> dict[str, str]:
    from lupa_pipeline.ingestao.saneamento import normalizar

    base = normalizar(TEXTOS[numero]).texto
    return {
        "pagina_id": str(processo.paginas[numero]),
        "trecho": trecho,
        "hash_trecho": _hash_de(base, trecho),
    }


def test_resposta_com_citacao_conferida_e_rotulo_gerado(
    app_teste: FastAPI, engine_teste: Engine, processo_agente: ProcessoAgente
) -> None:
    """Resposta com citacao conferida e rotulo gerado."""
    citacao = _citacao(processo_agente, 3, "intimei a parte recorrente em 10/03/2025")
    falso = _usar(
        app_teste,
        ClienteFalso([Roteiro(
            passos=(PassoFerramenta("ler_pagina_estruturada", {"numero": 3}),),
            resposta=resposta_json("A parte foi intimada em 10/03/2025 [1].", [citacao]),
        )]),
    )  # fmt: skip
    cliente = _cliente_http(app_teste, engine_teste, processo_agente)
    corpo = _perguntar(cliente, processo_agente, "Quando a parte foi intimada?")
    assert corpo["status"] == "respondida"
    assert corpo["rotulo"] == "gerado por IA"
    assert corpo["citacoes"] == [
        citacao | {"pagina_numero": 3, "arquivo_id": str(processo_agente.arquivo_id)}
    ]
    assert corpo["citacoes_descartadas"] == 0 and corpo["processo_em_revisao"] is False
    assert corpo["avisos"] == [] and corpo["citacoes_descartadas_na_conversa"] == 0
    assert falso.chamadas[0].nome == "mcp__lupa__ler_pagina_estruturada"


def test_citacao_inventada_chega_sem_a_citacao_com_aviso_e_contador(
    app_teste: FastAPI, engine_teste: Engine, processo_agente: ProcessoAgente
) -> None:
    """Citacao inventada chega sem a citacao com aviso e contador."""
    valida = _citacao(processo_agente, 3, "intimei a parte recorrente")
    inventada = valida | {"trecho": "intimei o réu pessoalmente"}
    _usar(
        app_teste,
        ClienteFalso([Roteiro(resposta=resposta_json("Texto [1][2].", [valida, inventada]))]),
    )
    cliente = _cliente_http(app_teste, engine_teste, processo_agente)
    primeira = _perguntar(cliente, processo_agente, "Quando a parte foi intimada?")
    assert [{k: c[k] for k in valida} for c in primeira["citacoes"]] == [valida]
    assert primeira["citacoes_descartadas"] == 1
    assert "1 citação(ões) não conferiram" in primeira["avisos"][0]
    segunda = _perguntar(cliente, processo_agente, "E de novo?")
    assert segunda["citacoes_descartadas_na_conversa"] == 2
    assert (
        len(
            eventos_do_banco(
                engine_teste, acao="citacao_descartada", processo_id=processo_agente.processo_id
            )
        )
        == 2
    )


def test_resposta_sem_citacao_valida_fica_marcada_sem_evidencia(
    app_teste: FastAPI, engine_teste: Engine, processo_agente: ProcessoAgente
) -> None:
    """Resposta sem citacao valida fica marcada sem evidencia."""
    _usar(app_teste, ClienteFalso([Roteiro(resposta=resposta_json("Não há intimação do MP."))]))
    cliente = _cliente_http(app_teste, engine_teste, processo_agente)
    corpo = _perguntar(cliente, processo_agente, "O MP foi intimado?")
    assert corpo["status"] == "sem_evidencia"
    assert corpo["texto"] == "Sem evidência nos autos."
    assert "sem evidência conferida" in corpo["avisos"][0]


def test_pergunta_vedada_e_recusada_sem_chamar_o_modelo(
    app_teste: FastAPI, engine_teste: Engine, processo_agente: ProcessoAgente
) -> None:
    """Pergunta vedada e recusada sem chamar o modelo."""
    falso = _usar(app_teste, ClienteFalso([Roteiro(resposta="nunca")]))
    cliente = _cliente_http(app_teste, engine_teste, processo_agente)
    corpo = _perguntar(cliente, processo_agente, "O recurso deve ser provido?")
    assert corpo["status"] == "recusa"
    assert "Experimente:" in corpo["texto"]
    assert falso.pedidos == []


def test_tempestividade_respondida_so_com_a_ferramenta_de_calculo(
    app_teste: FastAPI, engine_teste: Engine, processo_agente: ProcessoAgente
) -> None:
    """Tempestividade respondida so com a ferramenta de calculo."""

    def _compor(resultados: list[str]) -> str:
        achado = json.loads(resultados[0].split("\n", 2)[2].rsplit("\n", 1)[0])
        citacao = _citacao(processo_agente, 2, "interpõe apelação em 14/03/2025")
        return resposta_json(
            f"Resultado da validação: {achado['achados'][0]['resultado']} [1].", [citacao]
        )

    falso = _usar(app_teste, ClienteFalso([Roteiro(
        passos=(PassoFerramenta("executar_validacao", {"nome": "tempestividade_recurso"}),),
        resposta=_compor,
    )]))  # fmt: skip
    cliente = _cliente_http(app_teste, engine_teste, processo_agente)
    corpo = _perguntar(cliente, processo_agente, "O recurso é tempestivo?")
    assert corpo["status"] == "respondida"
    assert corpo["texto"].startswith("Resultado da validação: ")
    assert [c.nome for c in falso.chamadas] == ["mcp__lupa__executar_validacao"]
    eventos = eventos_do_banco(
        engine_teste,
        acao=AcaoAuditoria.VALIDACAO_EXECUTADA.value,
        processo_id=processo_agente.processo_id,
    )
    assert [e.objeto_tipo for e in eventos] == ["validacao_agente"]


def test_pergunta_e_ferramentas_preservam_nome_do_processo_sem_ler_autos_do_vizinho(
    app_teste: FastAPI, engine_teste: Engine, processo_agente: ProcessoAgente
) -> None:
    """O nome do processo autorizado permanece no contexto e o outro processo fica fora."""
    passos = (
        PassoFerramenta("ler_pagina_estruturada", {"numero": 1}),
        PassoFerramenta("ler_pagina_original", {"pagina_id": processo_agente.outra_pagina_id}),
    )
    falso = _usar(app_teste, ClienteFalso([Roteiro(passos=passos, resposta=resposta_json("ok"))]))
    cliente = _cliente_http(app_teste, engine_teste, processo_agente)
    _perguntar(cliente, processo_agente, f"Onde {NOME_PARTE} foi citada?")
    tudo = "\n".join(falso.recebidos)
    assert NOME_PARTE in tudo and TEXTO_OUTRO not in tudo
    assert "página não pertence a este processo" in tudo


def test_chamada_modelo_e_pergunta_chat_auditadas_sem_conteudo(
    app_teste: FastAPI, engine_teste: Engine, processo_agente: ProcessoAgente
) -> None:
    """Chamada modelo e pergunta chat auditadas sem conteudo."""
    _usar(app_teste, ClienteFalso([Roteiro(
        passos=(PassoFerramenta("listar_pecas"),), resposta=resposta_json("Há três peças."),
        tokens=(1200, 300),
    )]))  # fmt: skip
    cliente = _cliente_http(app_teste, engine_teste, processo_agente)
    pergunta = "Quantas peças há no processo?"
    corpo = _perguntar(cliente, processo_agente, pergunta)
    perguntas = eventos_do_banco(
        engine_teste, acao="pergunta_chat", processo_id=processo_agente.processo_id
    )
    chamadas = eventos_do_banco(
        engine_teste, acao="chamada_modelo", processo_id=processo_agente.processo_id
    )
    assert len(perguntas) == 1 and perguntas[0].objeto_tipo == "mensagem"
    assert len(chamadas) == 1
    assert chamadas[0].objeto_tipo == "chamada_modelo" and chamadas[0].tokens_entrada == 1200
    evento = chamadas[0]
    prompt = prompt_sistema()
    assert (evento.versao_modelo, evento.versao_prompt) == ("claude-opus-5-5", prompt.identificador)
    with Session(engine_teste) as session:
        linha = (
            session.execute(
                select(link_chamada_modelo).where(
                    link_chamada_modelo.c.hk_chamada == bytes.fromhex(str(evento.objeto_id))
                )
            )
            .mappings()
            .one()
        )
        assert linha is not None
        assert linha["hash_prompt_sistema"] == calcular_hash(prompt.texto)
        assert linha["hash_saida"] == calcular_hash(resposta_json("Há três peças."))
        assert len(linha["hash_entrada"]) == 64
        assert (linha["tokens_entrada"], linha["tokens_saida"], linha["resultado"]) == (
            1200,
            300,
            "ok",
        )
        assert linha["ferramentas"] == ["mcp__lupa__listar_pecas"]
        conversa = session.get(VisaoConversa, bytes.fromhex(corpo["conversa_id"]))
        assert conversa is not None and conversa.tokens_entrada == 1200
    for evento in perguntas + chamadas:
        valores = " ".join(str(getattr(evento, c)) for c in evento.__table__.columns.keys())
        assert pergunta not in valores and "três peças" not in valores


def _settings_com(settings: Settings, **valores: Any) -> Callable[[], Settings]:
    return lambda: settings.model_copy(update=valores)


def test_teto_da_conversa_encerra_com_mensagem_e_bloqueia_proxima_pergunta(
    app_teste: FastAPI, engine_teste: Engine, processo_agente: ProcessoAgente,
    settings_ficticias: Settings,
) -> None:  # fmt: skip
    """Teto da conversa encerra com mensagem e bloqueia a pergunta seguinte."""
    app_teste.dependency_overrides[get_settings] = _settings_com(
        settings_ficticias, agente_max_tokens_conversa=1000
    )
    _usar(app_teste, ClienteFalso([Roteiro(resposta=resposta_json("ok"), tokens=(900, 200))]))
    cliente = _cliente_http(app_teste, engine_teste, processo_agente)
    primeira = _perguntar(cliente, processo_agente, "Quantas peças?")
    assert primeira["conversa_encerrada"] is True
    assert any("limite de uso" in a for a in primeira["avisos"])
    segunda = _perguntar(cliente, processo_agente, "E agora?")
    assert segunda["conversa_id"] == primeira["conversa_id"]
    assert segunda["status"] == "teto"


def test_teto_do_processo_bloqueia_novas_chamadas(
    app_teste: FastAPI, engine_teste: Engine, processo_agente: ProcessoAgente,
    settings_ficticias: Settings,
) -> None:  # fmt: skip
    """Teto do processo bloqueia novas chamadas."""
    app_teste.dependency_overrides[get_settings] = _settings_com(
        settings_ficticias, agente_max_tokens_processo=500
    )
    falso = _usar(
        app_teste, ClienteFalso([Roteiro(resposta=resposta_json("ok"), tokens=(400, 200))])
    )
    cliente = _cliente_http(app_teste, engine_teste, processo_agente)
    primeira = _perguntar(cliente, processo_agente, "Quantas peças?")
    assert "limite de uso do assistente para este processo" in primeira["avisos"][-1]
    segunda = _perguntar(cliente, processo_agente, "E agora?")
    assert segunda["status"] == "teto"
    assert len(falso.pedidos) == 1


def test_teto_por_chamada_descarta_a_resposta(
    app_teste: FastAPI, engine_teste: Engine, processo_agente: ProcessoAgente,
    settings_ficticias: Settings,
) -> None:  # fmt: skip
    """Teto por chamada descarta a resposta."""
    app_teste.dependency_overrides[get_settings] = _settings_com(
        settings_ficticias, agente_max_tokens_chamada=100
    )
    _usar(app_teste, ClienteFalso([Roteiro(resposta=resposta_json("ok"), tokens=(400, 200))]))
    cliente = _cliente_http(app_teste, engine_teste, processo_agente)
    corpo = _perguntar(cliente, processo_agente, "Quantas peças?")
    assert corpo["status"] == "descartada" and "limite de tamanho" in corpo["texto"]


def test_saida_fora_do_esquema_tem_uma_nova_tentativa_e_depois_e_descartada(
    app_teste: FastAPI, engine_teste: Engine, processo_agente: ProcessoAgente
) -> None:
    """Teto da conversa encerra com mensagem e bloqueia a pergunta seguinte."""
    falso = _usar(
        app_teste,
        ClienteFalso([Roteiro(resposta="texto solto"), Roteiro(resposta=resposta_json("ok"))]),
    )
    cliente = _cliente_http(app_teste, engine_teste, processo_agente)
    assert _perguntar(cliente, processo_agente, "Quantas peças?")["status"] == "sem_evidencia"
    assert len(falso.pedidos) == 2
    sempre_invalido = _usar(app_teste, ClienteFalso([Roteiro(resposta="sempre solto")]))
    corpo = _perguntar(cliente, processo_agente, "Quantas peças?")
    assert corpo["status"] == "descartada" and len(sempre_invalido.pedidos) == 2
    resultados = [c["resultado"] for c in _chamadas(engine_teste, processo_agente)]
    assert resultados.count("invalida") == 3


def _chamadas(engine: Engine, processo: ProcessoAgente) -> list[RowMapping]:
    with Session(engine) as session:
        consulta = (
            select(link_chamada_modelo)
            .where(link_chamada_modelo.c.hk_processo == bytes.fromhex(processo.processo_id))
            .order_by(link_chamada_modelo.c.load_dts)
        )
        return list(session.execute(consulta).mappings())


class _ClienteQuebrado:
    async def responder(self, pedido: PedidoAgente) -> RespostaAgente:
        raise ClienteAgenteError("authentication_failed")


def test_falha_do_cliente_vira_mensagem_clara_e_chamada_com_erro(
    app_teste: FastAPI, engine_teste: Engine, processo_agente: ProcessoAgente
) -> None:
    """Falha do cliente vira mensagem clara e chamada com erro."""
    _usar(app_teste, _ClienteQuebrado())
    cliente = _cliente_http(app_teste, engine_teste, processo_agente)
    corpo = _perguntar(cliente, processo_agente, "Quantas peças?")
    assert corpo["status"] == "descartada" and "indisponível" in corpo["texto"]
    assert [c["resultado"] for c in _chamadas(engine_teste, processo_agente)] == ["erro"]


def test_id_inexistente_responde_404_e_pergunta_longa_422(
    app_teste: FastAPI, engine_teste: Engine, processo_agente: ProcessoAgente
) -> None:
    """Um id inexistente nunca chega ao modelo."""
    falso = _usar(app_teste, ClienteFalso([Roteiro(resposta="nunca")]))
    cliente = _cliente_http(app_teste, engine_teste, processo_agente)
    rota = "/processos/" + "f" * 64 + "/chat"
    assert cliente.post(rota, json={"pergunta": "Quantas peças?"}).status_code == 404
    assert cliente.get(rota).status_code == 404
    longa = cliente.post(
        f"/processos/{processo_agente.processo_id}/chat", json={"pergunta": "x" * 2001}
    )
    assert longa.status_code == 422
    assert falso.pedidos == []


def test_historico_lista_conversas_do_usuario_e_e_auditado(
    app_teste: FastAPI, engine_teste: Engine, processo_agente: ProcessoAgente
) -> None:
    """Historico lista conversas do usuario e e auditado."""
    _usar(app_teste, ClienteFalso([Roteiro(resposta=resposta_json("Três peças."))]))
    cliente = _cliente_http(app_teste, engine_teste, processo_agente)
    _perguntar(cliente, processo_agente, "Quantas peças?")
    _perguntar(cliente, processo_agente, "Quais as chances de provimento?")
    resposta = cliente.get(f"/processos/{processo_agente.processo_id}/chat")
    assert resposta.status_code == 200
    conversas = resposta.json()["conversas"]
    assert len(conversas) == 1
    papeis = [(m["papel"], m["status"]) for m in conversas[0]["mensagens"]]
    assert papeis == [
        ("usuario", "pergunta"), ("agente", "sem_evidencia"),
        ("usuario", "pergunta"), ("agente", "recusa"),
    ]  # fmt: skip
    assert conversas[0]["mensagens"][1]["rotulo"] == "gerado por IA"
    abertos = eventos_do_banco(
        engine_teste, acao="processo_aberto", processo_id=processo_agente.processo_id
    )
    assert any(e.objeto_id == f"/processos/{processo_agente.processo_id}/chat" for e in abertos)
    with Session(engine_teste) as session:
        assert session.scalar(select(VisaoMensagem.sequencia).limit(1)) is not None


def test_historico_mantem_pergunta_antes_da_resposta_na_mesma_transacao(
    app_teste: FastAPI, engine_teste: Engine, processo_agente: ProcessoAgente
) -> None:
    """Pergunta e resposta gravadas no mesmo instante saem na ordem pergunta, resposta (6.8)."""
    _usar(app_teste, ClienteFalso([Roteiro(resposta=resposta_json("Não consta."))]))
    cliente = _cliente_http(app_teste, engine_teste, processo_agente)
    for pergunta in ("Redija o voto.", "A testemunha é confiável?", "Quantas peças?"):
        _perguntar(cliente, processo_agente, pergunta)
    historico = cliente.get(f"/processos/{processo_agente.processo_id}/chat").json()
    papeis = [m["papel"] for m in historico["conversas"][-1]["mensagens"]]
    assert papeis == ["usuario", "agente"] * 3
