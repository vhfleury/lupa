"""Gravação das páginas e leitura da extração corrente de um arquivo (A5)."""

from collections.abc import Sequence
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from lupa_pipeline.dominio.esquemas import calcular_hash
from lupa_pipeline.dominio.gravacao import (
    gravar_hub,
    gravar_hubs,
    gravar_link,
    gravar_links,
    gravar_satelite,
    gravar_satelites,
)
from lupa_pipeline.dominio.tabelas import (
    atributos_do_satelite,
    hub_pagina,
    link_arquivo_pagina,
    sat_pagina_extracao,
    sat_pagina_saneamento,
)
from lupa_pipeline.dominio.visoes import VisaoArquivo, VisaoPagina, atual
from lupa_pipeline.ingestao.repositorio import ORIGEM


def gravar_pagina(session: Session, arquivo: VisaoArquivo, linha: dict[str, Any]) -> bytes:
    """Insere a página e as versões de extração e saneamento quando mudam."""
    chave = {"numero_cnj": arquivo.numero_cnj, "sha256": arquivo.sha256, "numero": linha["numero"]}
    hk = gravar_hub(session, hub_pagina, chave, ORIGEM)
    gravar_link(
        session, link_arquivo_pagina, {"hk_arquivo": arquivo.hk_arquivo, "hk_pagina": hk}, ORIGEM
    )
    atributos = linha | {"hash_texto": calcular_hash(linha["texto"])}
    for tabela in (sat_pagina_extracao, sat_pagina_saneamento):
        valores = {campo: atributos[campo] for campo in atributos_do_satelite(tabela)}
        gravar_satelite(session, tabela, hk, valores, ORIGEM)
    return hk


def gravar_paginas(
    session: Session, arquivo: VisaoArquivo, linhas: Sequence[dict[str, Any]]
) -> list[bytes]:
    """Grava as páginas de um lote com as mesmas linhas de `gravar_pagina`, uma a uma (F17).

    Hubs e links vão num `executemany` cada; os `hash_diff` correntes de cada satélite são lidos
    uma vez, e só as versões que mudam entram no `executemany` do satélite.

    Args:
        session: Sessão com a transação do lote.
        arquivo: Arquivo dono das páginas.
        linhas: Páginas extraídas, na ordem de gravação.

    Returns:
        O `hk_pagina` de cada linha, na mesma ordem.
    """
    chaves = [
        {"numero_cnj": arquivo.numero_cnj, "sha256": arquivo.sha256, "numero": linha["numero"]}
        for linha in linhas
    ]
    hks = gravar_hubs(session, hub_pagina, chaves, ORIGEM)
    ligacoes = [{"hk_arquivo": arquivo.hk_arquivo, "hk_pagina": hk} for hk in hks]
    gravar_links(session, link_arquivo_pagina, ligacoes, ORIGEM)
    atributos = [linha | {"hash_texto": calcular_hash(linha["texto"])} for linha in linhas]
    for tabela in (sat_pagina_extracao, sat_pagina_saneamento):
        campos = atributos_do_satelite(tabela)
        versoes = [
            (hk, {campo: valores[campo] for campo in campos})
            for hk, valores in zip(hks, atributos, strict=True)
        ]
        gravar_satelites(session, tabela, versoes, ORIGEM)
    return hks


def prontas(session: Session, arquivo: bytes, versao: str) -> set[int]:
    """Retorna os números com extração na versão solicitada."""
    return set(
        session.scalars(
            select(VisaoPagina.numero).where(
                VisaoPagina.hk_arquivo == arquivo, VisaoPagina.versao_extrator == versao
            )
        )
    )


def paginas_para_indice(session: Session, arquivo: bytes, versao: str) -> list[dict[str, Any]]:
    """Lê as páginas da extração corrente, ordenadas para o índice e o relatório."""
    consulta = (
        select(VisaoPagina)
        .where(VisaoPagina.hk_arquivo == arquivo, VisaoPagina.versao_extrator == versao)
        .order_by(VisaoPagina.numero)
    )
    campos = (
        "numero",
        "tipo",
        "texto",
        "texto_normalizado",
        "flags",
        "coordenadas",
        "extracao",
        "origem_arquivo",
        "pagina_origem",
        "numero_cnj",
        "sha256",
        "hk_pagina",
    )
    return [
        {campo: getattr(pagina, campo) for campo in campos}
        for pagina in session.scalars(atual(consulta))
    ]
