"""Paridade das telas com o SvelteKit: cada tela e ação responde ao papel permitido (RF-INT-02).

Cada caso simula as rotas da API que a tela usa e confere o status e um trecho do HTML; a API
reconfere o papel, e o front só esconde as ações que o papel não tem.
"""

import json
from dataclasses import dataclass, field
from typing import Any

import pytest
import respx
from django.test import Client

from tests.telas.conftest import sessao_da_api

PROCESSO = "c3" * 32
ARQUIVO = "d4" * 32
ASSESSOR = "11" * 32
OUTRO_ASSESSOR = "22" * 32
BASE = f"/processos/{PROCESSO}"

DADOS_PROCESSO = {
    "id": PROCESSO,
    "numero_cnj": "0000003-67.2026.8.07.0001",
    "classe": "agravo_instrumento",
    "status": "criado",
    "em_revisao": False,
    "criador_id": ASSESSOR,
    "criado_em": "2026-03-04T15:30:00+00:00",
    "classe_anterior": "apelacao_civel",
    "classe_corrigida_por_id": ASSESSOR,
    "classe_corrigida_em": "2026-03-05T10:00:00+00:00",
}
ARQUIVOS: dict[str, Any] = {
    "processo_id": PROCESSO,
    "status": "criado",
    "situacao": "quarentena",
    "arquivos": [
        {
            "arquivo_id": ARQUIVO,
            "nome": "autos-sinteticos.pdf",
            "mime": "application/pdf",
            "tamanho_bytes": 1536,
            "enviado_em": "2026-03-04T15:31:00+00:00",
            "estado": "quarentena",
            "motivo_quarentena": "senha",
            "motivo_falha": None,
            "total_paginas": None,
            "relatorio": None,
            "estado_em": "2026-03-04T15:32:00+00:00",
        }
    ],
}
EVIDENCIA = "e5" * 32
OUTRA_EVIDENCIA = "e6" * 32
FATO = "f6" * 32
PAGINA = "a7" * 32
PECA = "b8" * 32
ACHADO = "9a" * 32
ACHADO_ANTIGO = "9b" * 32
DOSSIE: dict[str, Any] = {
    "versao_esquema": "1",
    "ficha": {
        "processo_id": PROCESSO,
        "numero_cnj": "0000003-67.2026.8.07.0001",
        "classe": "agravo_instrumento",
        "status": "criado",
        "partes": [
            {
                "id": "c1" * 32,
                "nome": "Parte Sintética Agravante",
                "polo": "ativo",
                "qualidade": "agravante",
                "evidencia_id": OUTRA_EVIDENCIA,
                "pagina_id": PAGINA,
            }
        ],
        "responsaveis": [{"id": ASSESSOR, "nome_usuario": "assessora.sintetica"}],
        "dados_capa": [
            {
                "tipo": "valor_causa",
                "valor": "1500.50",
                "fato_id": FATO,
                "pagina_id": PAGINA,
                "evidencia_id": EVIDENCIA,
            }
        ],
        "ingestao": {"situacao": "concluido"},
    },
    "pecas": [
        {
            "ordem": 1,
            "peca_id": PECA,
            "arquivo_id": ARQUIVO,
            "tipo": "apelacao",
            "origem": "recorrente",
            "pagina_inicial": 1,
            "pagina_final": 3,
            "data": "2026-02-01",
            "confianca": 0.92,
            "flags": {},
            "resumo_peca": None,
        }
    ],
    "linha_do_tempo": [
        {
            "data": "2026-02-10",
            "tipo": "intimacao",
            "fato_id": FATO,
            "evidencia_id": EVIDENCIA,
            "status": "corrigido",
            "pagina_id": PAGINA,
            "pagina": 2,
            "trecho": "Intimação sintética da parte",
        }
    ],
    "alertas": [
        {"pagina_id": PAGINA, "arquivo_id": ARQUIVO, "pagina": 2, "flags": ["texto_oculto"]}
    ],
    "achados": [
        {
            "achado_id": ACHADO,
            "validacao": "tempestividade",
            "resultado": "conforme",
            "explicacao": "Recurso sintético interposto no prazo.",
            "fatos_usados": [FATO],
            "fontes": [{"fato_id": FATO, "evidencia_id": EVIDENCIA, "pagina_id": PAGINA}],
        }
    ],
}
INDICE = {
    "processo_id": PROCESSO,
    "pecas": [
        {
            "ordem": 1,
            "id": PECA,
            "arquivo_id": ARQUIVO,
            "tipo": "apelacao",
            "origem": "recorrente",
            "pagina_inicial": 1,
            "pagina_final": 3,
            "data": "2026-02-01",
            "tipo_data": None,
            "evidencia_data": None,
            "confianca": 0.92,
            "metodo": "regra",
            "resumo_flags": {"peca": ["sem_assinatura"], "saneamento": {}, "total_saneamento": 2},
        }
    ],
}
EVIDENCIA_DO_FATO = {
    "id": EVIDENCIA,
    "pagina_id": PAGINA,
    "arquivo_id": ARQUIVO,
    "pagina": 2,
    "trecho": "intimada em 10/02/2026",
    "inicio": 4,
    "fim": 26,
}
FATO_VIGENTE = {
    "id": FATO,
    "tipo": "intimacao",
    "valor": "2026-02-10",
    "status": "automatico",
    "confianca": 0.9,
    "extraido_por": "regra",
    "vigente": True,
    "criado_em": "2026-03-04T15:40:00+00:00",
    "evidencias": [EVIDENCIA_DO_FATO],
}
FATOS = {"processo_id": PROCESSO, "fatos": [FATO_VIGENTE]}
HISTORICO_FATOS = {
    "processo_id": PROCESSO,
    "fatos": [FATO_VIGENTE | {"valor": "2026-02-09", "vigente": False}, FATO_VIGENTE],
}
ACHADO_VIGENTE = {
    "id": ACHADO,
    "validacao": "tempestividade",
    "versao_catalogo": "2026.1",
    "resultado": "conforme",
    "fatos_usados": [FATO],
    "valores": {"intimacao": "2026-02-10", "prazo_dias": 15, "fatos": [FATO]},
    "explicacao": "Recurso sintético interposto no prazo.",
    "criado_em": "2026-03-04T15:41:00+00:00",
    "vigente": True,
}
ACHADOS = {"processo_id": PROCESSO, "achados": [ACHADO_VIGENTE]}
HISTORICO_ACHADOS = {
    "processo_id": PROCESSO,
    "achados": [
        ACHADO_VIGENTE
        | {
            "id": ACHADO_ANTIGO,
            "resultado": "atencao",
            "explicacao": "Versão anterior sintética.",
            "vigente": False,
        },
        ACHADO_VIGENTE,
    ],
}
ANOTACOES = {
    "processo_id": PROCESSO,
    "anotacoes": [
        {
            "id": "ad" * 32,
            "achado_id": None,
            "fato_id": FATO,
            "usuario_id": ASSESSOR,
            "autor": "assessora.sintetica",
            "texto": "Nota sintética sobre a intimação.",
            "criado_em": "2026-03-04T16:00:00+00:00",
        }
    ],
}
BBOX = {
    "evidencia_id": EVIDENCIA,
    "arquivo_id": ARQUIVO,
    "pagina": 2,
    "trecho": "intimada em 10/02/2026",
    "sistema": "fracao_da_pagina_origem_superior_esquerda",
    "uniao": {"x": 0.1, "y": 0.2, "largura": 0.5, "altura": 0.05},
    "retangulos": [{"x": 0.1, "y": 0.2, "largura": 0.5, "altura": 0.05}],
}
ARQUIVOS_LEGIVEIS = ARQUIVOS | {
    "situacao": "concluido",
    "arquivos": [
        ARQUIVOS["arquivos"][0]
        | {"estado": "concluido", "motivo_quarentena": None, "total_paginas": 3}
    ],
}
MENSAGEM_USUARIO = {
    "mensagem_id": "71" * 32,
    "papel": "usuario",
    "status": "pergunta",
    "texto": "Onde está a certidão?",
    "citacoes": [],
    "avisos": [],
    "citacoes_descartadas": 0,
    "rotulo": None,
    "criado_em": "2026-03-05T12:00:00+00:00",
}
MENSAGEM_AGENTE = {
    "mensagem_id": "72" * 32,
    "papel": "agente",
    "status": "respondida",
    "texto": "A certidão está na página 2.",
    "citacoes": [
        {
            "pagina_id": PAGINA,
            "trecho": "certidão sintética de intimação",
            "hash_trecho": "73" * 32,
            "pagina_numero": 2,
            "arquivo_id": ARQUIVO,
        }
    ],
    "avisos": ["1 citação(ões) não conferiram com o texto da página", "Aviso sintético."],
    "citacoes_descartadas": 1,
    "rotulo": "gerado por IA",
    "criado_em": "2026-03-05T12:00:05+00:00",
}
CONVERSA = {
    "conversa_id": "74" * 32,
    "criada_em": "2026-03-05T12:00:00+00:00",
    "encerrada": False,
    "motivo_encerramento": None,
    "citacoes_descartadas": 1,
    "mensagens": [MENSAGEM_USUARIO, MENSAGEM_AGENTE],
}
CONVERSA_ANTIGA = {
    "conversa_id": "75" * 32,
    "criada_em": "2026-03-01T09:00:00+00:00",
    "encerrada": True,
    "motivo_encerramento": "teto_conversa",
    "citacoes_descartadas": 0,
    "mensagens": [MENSAGEM_USUARIO | {"texto": "Pergunta anterior sintética"}],
}
CHAT = {"processo_id": PROCESSO, "conversas": [CONVERSA_ANTIGA, CONVERSA]}
REVISAO = {
    "processo_id": PROCESSO,
    "status": "criado",
    "em_revisao": False,
    "motivo": None,
    "aberta_em": None,
}
ASSESSORA = {"id": ASSESSOR, "nome_usuario": "assessora.sintetica", "ativo": True}
OUTRA = {"id": OUTRO_ASSESSOR, "nome_usuario": "outra.sintetica", "ativo": True}


def _responsaveis(papel: str) -> dict[str, Any]:
    desembargador = papel == "desembargador"
    return {
        "responsaveis": [ASSESSORA],
        "disponiveis": [ASSESSORA, OUTRA] if desembargador else [],
        "pode_gerir": desembargador,
    }


def _simular_processo(api: respx.MockRouter, papel: str) -> None:
    api.get(BASE).respond(200, json=DADOS_PROCESSO)
    api.get(f"{BASE}/arquivos").respond(200, json=ARQUIVOS)
    api.get(f"{BASE}/responsaveis").respond(200, json=_responsaveis(papel))
    api.get(f"{BASE}/dossie").respond(200, json=DOSSIE)


def _simular_analise(api: respx.MockRouter) -> None:
    api.get(f"{BASE}/indice").respond(200, json=INDICE)
    api.get(f"{BASE}/achados").respond(200, json=ACHADOS)
    api.get(f"{BASE}/achados/historico").respond(200, json=HISTORICO_ACHADOS)
    api.get(f"{BASE}/fatos").respond(200, json=FATOS)
    api.get(f"{BASE}/fatos/historico").respond(200, json=HISTORICO_FATOS)
    api.get(f"{BASE}/anotacoes").respond(200, json=ANOTACOES)
    api.get(f"{BASE}/evidencias/{EVIDENCIA}/bbox").respond(200, json=BBOX)


def _simular_chat(api: respx.MockRouter) -> None:
    api.get(f"{BASE}/chat").respond(200, json=CHAT)
    api.get(f"{BASE}/revisao").respond(200, json=REVISAO)


def _simular_arquivo(api: respx.MockRouter, papel: str) -> None:
    base = f"{BASE}/arquivos/{ARQUIVO}"
    api.get(f"{base}/relatorio").respond(
        200,
        json={
            "arquivo_id": ARQUIVO,
            "estado": "concluido",
            "versao_extrator": "1.0.0",
            "relatorio": {"cobertura": 1.0, "faltantes": []},
        },
    )
    api.get(f"{base}/diagnostico").respond(
        200,
        json={
            "arquivo_id": ARQUIVO,
            "cenario": "texto_nativo",
            "total_paginas": 3,
            "tem_indice": False,
            "sinais": {},
            "fronteiras_origem": "heuristica",
            "metadados_descartados": [],
        },
    )
    api.get(f"{base}/alertas").respond(
        200,
        json={
            "arquivo_id": ARQUIVO,
            "resumo": {"paginas_com_sinal": 1},
            "metadados_suspeitos": [{"campo": "Subject", "categorias": ["instrucao"]}],
            "paginas": [{"numero": 2, "flags": ["texto_oculto"], "trechos_ocultos": []}],
        },
    )


@dataclass(frozen=True)
class Caso:
    """Uma tela ou ação, o papel que a usa e o que se espera da resposta."""

    tela: str
    papel: str
    metodo: str
    caminho: str
    status: int
    trechos: tuple[str, ...] = ()
    ausentes: tuple[str, ...] = ()
    dados: dict[str, Any] = field(default_factory=dict)
    rota_api: str = ""
    corpo_api: dict[str, Any] | None = None
    destino: str = ""


CASOS = [
    Caso(
        "processo",
        "assessor",
        "GET",
        BASE,
        200,
        trechos=(
            "0000003-67.2026.8.07.0001",
            "Agravo de instrumento",
            "Corrigir classe",
            "Apelação cível",
            "assessora.sintetica",
            "autos-sinteticos.pdf",
            "1,5 KB",
            "O arquivo está protegido por senha.",
            f'href="{BASE}/arquivos/{ARQUIVO}"',
            f'href="{BASE}/dossie"',
            "Parte Sintética Agravante",
            "R$ 1.500,50",
            f'href="{BASE}/visualizador?evidencia={EVIDENCIA}"',
        ),
        ausentes=("Salvar responsáveis", "Descartar processo"),
    ),
    Caso(
        "processo",
        "desembargador",
        "GET",
        BASE,
        200,
        trechos=(
            "Salvar responsáveis",
            "outra.sintetica",
            f'name="anteriores" value="{ASSESSOR}"',
            f'value="{ASSESSOR}" checked',
            f'href="{BASE}/descartar"',
        ),
    ),
    Caso(
        "processo_arquivo",
        "assessor",
        "GET",
        f"{BASE}/arquivos/{ARQUIVO}",
        200,
        trechos=(
            "Relatório de qualidade",
            "Concluído",
            "1.0.0",
            "texto_nativo",
            "Paginas com sinal",
            "Texto oculto",
            "Metadados suspeitos",
        ),
    ),
    Caso(
        "processo_classe",
        "assessor",
        "POST",
        f"{BASE}/classe",
        303,
        dados={"classe": "apelacao_civel"},
        rota_api=f"{BASE}/classe",
        corpo_api={"classe": "apelacao_civel"},
        destino=BASE,
    ),
    Caso(
        "processo_responsaveis",
        "desembargador",
        "POST",
        f"{BASE}/responsaveis",
        303,
        dados={"usuarios": [OUTRO_ASSESSOR], "anteriores": [ASSESSOR]},
        rota_api=f"{BASE}/responsaveis",
        corpo_api={"usuarios": [OUTRO_ASSESSOR], "anteriores": [ASSESSOR]},
        destino=f"{BASE}?aviso=responsaveis",
    ),
    Caso(
        "processo_descarte",
        "desembargador",
        "GET",
        f"{BASE}/descartar",
        200,
        trechos=("Esta ação não pode ser desfeita.", f'action="{BASE}/descartar"', "Cancelar"),
    ),
    Caso(
        "processo_descarte",
        "desembargador",
        "POST",
        f"{BASE}/descartar",
        303,
        rota_api=f"{BASE}/descartar",
        corpo_api={},
        destino="/processos",
    ),
    Caso(
        "dossie",
        "assessor",
        "GET",
        f"{BASE}/dossie",
        200,
        trechos=(
            "Ficha",
            "Parte Sintética Agravante",
            "Polo ativo",
            "R$ 1.500,50",
            "assessora.sintetica",
            "Concluído",
            "10/02/2026",
            "(fl. 2)",
            "Intimação sintética da parte",
            "Apelacao",
            "92%",
            "Sem assinatura",
            "2 alerta(s) de saneamento",
            f'href="{BASE}/visualizador?arquivo={ARQUIVO}&amp;pagina=1"',
            f'action="{BASE}/pecas/{PECA}/reclassificar"',
            "Texto oculto",
            "Tempestividade",
            "Recurso sintético interposto no prazo.",
            f'href="{BASE}/validacoes"',
        ),
    ),
    Caso(
        "dossie_reclassificar",
        "assessor",
        "POST",
        f"{BASE}/pecas/{PECA}/reclassificar",
        303,
        dados={"tipo": "sentenca"},
        rota_api=f"{BASE}/pecas/{PECA}/reclassificar",
        corpo_api={"tipo": "sentenca"},
        destino=f"{BASE}/dossie?aviso=reclassificada",
    ),
    Caso(
        "validacoes",
        "assessor",
        "GET",
        f"{BASE}/validacoes",
        200,
        trechos=(
            "Tempestividade",
            "Conforme",
            "Recurso sintético interposto no prazo.",
            f'href="{BASE}/visualizador?evidencia={EVIDENCIA}"',
            "Prazo dias",
            "Automático",
            "Confirmar",
            "Salvar correção",
            "Nota sintética sobre a intimação.",
            "Salvar anotação",
            "Versão anterior sintética.",
            "Fatos substituídos",
            "09/02/2026",
        ),
    ),
    Caso(
        "validacoes_confirmar",
        "assessor",
        "POST",
        f"{BASE}/fatos/{FATO}/corrigir",
        303,
        dados={"status": "confirmado"},
        rota_api=f"{BASE}/fatos/{FATO}/corrigir",
        corpo_api={"status": "confirmado"},
        destino=f"{BASE}/validacoes?aviso=confirmado",
    ),
    Caso(
        "validacoes_corrigir",
        "assessor",
        "POST",
        f"{BASE}/fatos/{FATO}/corrigir",
        303,
        dados={"status": "corrigido", "valor": " 2026-02-11 ", "fonte": EVIDENCIA},
        rota_api=f"{BASE}/fatos/{FATO}/corrigir",
        corpo_api={
            "status": "corrigido",
            "valor": "2026-02-11",
            "pagina_id": PAGINA,
            "inicio": 4,
            "fim": 26,
            "trecho": "intimada em 10/02/2026",
        },
        destino=f"{BASE}/validacoes?aviso=corrigido&achados=0",
    ),
    Caso(
        "validacoes_anotar",
        "desembargador",
        "POST",
        f"{BASE}/anotacoes",
        303,
        dados={"fato_id": FATO, "texto": " Nota sintética nova "},
        rota_api=f"{BASE}/anotacoes",
        corpo_api={"fato_id": FATO, "texto": "Nota sintética nova"},
        destino=f"{BASE}/validacoes?aviso=anotacao",
    ),
    Caso(
        "visualizador",
        "assessor",
        "GET",
        f"{BASE}/visualizador?evidencia={EVIDENCIA}",
        200,
        trechos=(
            f'src="{BASE}/arquivos/{ARQUIVO}/paginas/2/imagem"',
            "Página 2 de 3",
            '<rect x="0.1000" y="0.2000" width="0.5000" height="0.0500"',
            "intimada em 10/02/2026",
            f'href="{BASE}/visualizador?arquivo={ARQUIVO}&amp;pagina=1&amp;zoom=100"',
            f'href="{BASE}/visualizador?arquivo={ARQUIVO}&amp;pagina=3&amp;zoom=100"',
        ),
    ),
    Caso(
        "chat",
        "assessor",
        "GET",
        f"{BASE}/chat",
        200,
        trechos=(
            "Chat sobre os autos",
            "Conversa atual",
            "Conteúdo gerado por IA",
            "A certidão está na página 2.",
            f'href="{BASE}/visualizador?arquivo={ARQUIVO}&amp;pagina=2"',
            "1 citação descartada nesta resposta",
            "Aviso sintético.",
            'hx-post="',
            'hx-swap="beforeend"',
            "Aguardando resposta",
            "Conversas anteriores",
        ),
        ausentes=("Liberar revisão", "citação(ões) não conferiram"),
    ),
    Caso(
        "chat_pergunta",
        "assessor",
        "POST",
        f"{BASE}/chat",
        303,
        dados={"pergunta": "Pergunta sintética"},
        rota_api=f"{BASE}/chat",
        corpo_api={"pergunta": "Pergunta sintética"},
        destino=f"{BASE}/chat",
    ),
    Caso(
        "chat_liberar",
        "desembargador",
        "GET",
        f"{BASE}/chat/liberar",
        200,
        trechos=("Liberar a revisão?", f'action="{BASE}/chat/liberar"', "Cancelar"),
    ),
    Caso(
        "chat_liberar",
        "desembargador",
        "POST",
        f"{BASE}/chat/liberar",
        303,
        rota_api=f"{BASE}/liberar-revisao",
        corpo_api={},
        destino=f"{BASE}/chat?aviso=liberado",
    ),
]


@pytest.mark.parametrize("caso", CASOS, ids=lambda c: f"{c.tela}-{c.papel}-{c.metodo}")
def test_cada_tela_responde_ao_papel_permitido(
    api_simulada: respx.MockRouter, navegador: Client, caso: Caso
) -> None:
    """RF-INT-02: a tela ou ação responde ao papel que a tem, com o conteúdo vindo da API."""
    api_simulada.get("/auth/sessao").respond(200, json=sessao_da_api(caso.papel))
    _simular_processo(api_simulada, caso.papel)
    _simular_arquivo(api_simulada, caso.papel)
    _simular_analise(api_simulada)
    _simular_chat(api_simulada)
    if caso.tela == "visualizador":
        api_simulada.get(f"{BASE}/arquivos").respond(200, json=ARQUIVOS_LEGIVEIS)
    rota = api_simulada.post(caso.rota_api).respond(200, json={}) if caso.rota_api else None

    if caso.metodo == "GET":
        resposta = navegador.get(caso.caminho)
    else:
        resposta = navegador.post(caso.caminho, caso.dados)

    html = resposta.content.decode()
    assert resposta.status_code == caso.status
    for trecho in caso.trechos:
        assert trecho in html
    for trecho in caso.ausentes:
        assert trecho not in html
    if rota is not None:
        assert json.loads(rota.calls.last.request.content) == caso.corpo_api
        assert resposta["Location"] == caso.destino
