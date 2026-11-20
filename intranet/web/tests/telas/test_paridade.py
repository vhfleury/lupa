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
ARQUIVOS = {
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
]


@pytest.mark.parametrize("caso", CASOS, ids=lambda c: f"{c.tela}-{c.papel}-{c.metodo}")
def test_cada_tela_responde_ao_papel_permitido(
    api_simulada: respx.MockRouter, navegador: Client, caso: Caso
) -> None:
    """RF-INT-02: a tela ou ação responde ao papel que a tem, com o conteúdo vindo da API."""
    api_simulada.get("/auth/sessao").respond(200, json=sessao_da_api(caso.papel))
    _simular_processo(api_simulada, caso.papel)
    _simular_arquivo(api_simulada, caso.papel)
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
