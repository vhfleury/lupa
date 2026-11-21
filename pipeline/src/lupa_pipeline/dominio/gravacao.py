"""Gravação só por inserção no Data Vault (A2; D6, D13).

`gravar_hub` e `gravar_link` calculam o `hk` (A1) e inserem com `ON CONFLICT DO NOTHING`;
`gravar_satelite` só insere quando o `hash_diff` difere do da linha mais recente do pai (ou da
mesma subchave, no satélite multiativo). `gravar_hubs`, `gravar_links` e `gravar_satelites`
fazem o mesmo em lote, com um `executemany` por tabela (F17). Nada aqui faz `UPDATE` ou
`DELETE`: mudança de estado é linha nova. Violação de FK ou de `CHECK` propaga; a transação de
quem chama desfaz.
"""

from collections.abc import Callable, Mapping, Sequence

from sqlalchemy import Table, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from lupa_pipeline.dominio.chaves import (
    chave_hash,
    chave_link,
    hash_diff,
    normalizar_cnj,
    normalizar_hash,
)
from lupa_pipeline.dominio.tabelas import atributos_do_satelite
from lupa_pipeline.dominio.visoes import VisaoProcesso

COLUNAS_OPCIONAIS = frozenset({"sujeito"})
NORMALIZADORES: Mapping[str, Callable[[str], str]] = {
    "numero_cnj": normalizar_cnj,
    "sha256": normalizar_hash,
    "token_sha256": normalizar_hash,
    "chave": normalizar_hash,
}


class GravacaoInvalidaError(ValueError):
    """Tabela do tipo errado ou colunas diferentes das que a tabela declara."""


def travar_processo(session: Session, hk_processo: bytes) -> VisaoProcesso | None:
    """Serializa as escritas do processo até o commit e relê seu estado após obter a trava."""
    chave_a = int.from_bytes(hk_processo[:4], "big", signed=True)
    chave_b = int.from_bytes(hk_processo[4:8], "big", signed=True)
    session.execute(select(func.pg_advisory_xact_lock(chave_a, chave_b)))
    return session.get(VisaoProcesso, hk_processo, populate_existing=True)


def _exigir_tipo(tabela: Table, tipo: str) -> None:
    if tabela.info.get("tipo") != tipo:
        raise GravacaoInvalidaError(f"{tabela.name} não é {tipo}")


def _exigir_colunas(tabela: Table, recebidas: Mapping[str, object], esperadas: list[str]) -> None:
    if set(recebidas) != set(esperadas):
        faltam = sorted(set(esperadas) - set(recebidas))
        sobram = sorted(set(recebidas) - set(esperadas))
        raise GravacaoInvalidaError(f"{tabela.name}: faltam {faltam}, sobram {sobram}")


def _normalizar(coluna: str, valor: object) -> object:
    normalizador = NORMALIZADORES.get(coluna)
    if normalizador is None or not isinstance(valor, str):
        return valor
    return normalizador(valor)


def chave_do_hub(tabela: Table, chave: Mapping[str, object]) -> bytes:
    """Calcula o `hk` de um hub sem gravar (A1, passos 1 a 3).

    Args:
        tabela: Hub de `dominio.tabelas`.
        chave: Valor de cada coluna da chave de negócio.

    Returns:
        O `hk` (32 bytes).

    Raises:
        GravacaoInvalidaError: Tabela que não é hub ou colunas diferentes das da chave.
        ChaveInvalidaError: Parte vazia ou com `|`.
    """
    _exigir_tipo(tabela, "hub")
    colunas = list(tabela.info["chave"])
    _exigir_colunas(tabela, chave, colunas)
    partes = [_normalizar(coluna, chave[coluna]) for coluna in colunas]
    opcionais = {posicao for posicao, coluna in enumerate(colunas) if coluna in COLUNAS_OPCIONAIS}
    return chave_hash(partes, vazias_permitidas=opcionais)


def gravar_hub(
    session: Session, tabela: Table, chave: Mapping[str, object], record_source: str
) -> bytes:
    """Grava o hub se ainda não existir (A2, passo 1).

    Args:
        session: Sessão com transação aberta.
        tabela: Hub de `dominio.tabelas`.
        chave: Valor de cada coluna da chave de negócio.
        record_source: Origem da gravação (`api.acesso`, `pipeline.ingestao`...).

    Returns:
        O `hk` do hub.
    """
    hk = chave_do_hub(tabela, chave)
    valores = {coluna: _normalizar(coluna, valor) for coluna, valor in chave.items()}
    comando = insert(tabela).values(
        {tabela.info["hk"]: hk, **valores, "record_source": record_source}
    )
    session.execute(comando.on_conflict_do_nothing(index_elements=[tabela.info["hk"]]))
    return hk


def gravar_link(
    session: Session, tabela: Table, hks: Mapping[str, bytes], record_source: str
) -> bytes:
    """Grava o link se ainda não existir (A2, passo 2).

    Args:
        session: Sessão com transação aberta.
        tabela: Link historizável de `dominio.tabelas`.
        hks: `hk` de cada hub ligado, pela coluna.
        record_source: Origem da gravação.

    Returns:
        O `hk` do link.

    Raises:
        GravacaoInvalidaError: Tabela que não é link ou colunas diferentes das do link.
    """
    _exigir_tipo(tabela, "link")
    colunas = list(tabela.info["hubs"])
    _exigir_colunas(tabela, hks, colunas)
    hk = chave_link(*(hks[coluna] for coluna in colunas))
    comando = insert(tabela).values({tabela.info["hk"]: hk, **hks, "record_source": record_source})
    session.execute(comando.on_conflict_do_nothing(index_elements=[tabela.info["hk"]]))
    return hk


def _hash_diff_corrente(
    session: Session, tabela: Table, hk_pai: bytes, atributos: Mapping[str, object]
) -> bytes | None:
    consulta = select(tabela.c.hash_diff).where(tabela.c[tabela.info["pai"]] == hk_pai)
    subchave = tabela.info["multiativo"]
    if subchave is not None:
        consulta = consulta.where(tabela.c[subchave] == atributos[subchave])
    return session.scalar(consulta.order_by(tabela.c.load_dts.desc()).limit(1))


def gravar_satelite(
    session: Session,
    tabela: Table,
    hk_pai: bytes,
    atributos: Mapping[str, object],
    record_source: str,
) -> bool:
    """Grava uma linha nova do satélite se o conteúdo mudou (A2, passos 3 a 6).

    O `hash_diff` é o SHA-256 do JSON canônico dos atributos. Anotação e falha de login sempre
    inserem.

    Args:
        session: Sessão com transação aberta.
        tabela: Satélite de `dominio.tabelas`.
        hk_pai: `hk` do hub ou link pai.
        atributos: Todas as colunas de negócio do satélite, em claro.
        record_source: Origem da gravação.

    Returns:
        Verdadeiro se inseriu; falso se o `hash_diff` é igual ao corrente.

    Raises:
        GravacaoInvalidaError: Tabela que não é satélite ou atributos diferentes dos declarados.
    """
    _exigir_tipo(tabela, "satelite")
    _exigir_colunas(tabela, atributos, atributos_do_satelite(tabela))
    novo = hash_diff(atributos)
    sempre = tabela.info["sempre_insere"]
    if not sempre and _hash_diff_corrente(session, tabela, hk_pai, atributos) == novo:
        return False
    linha = {tabela.info["pai"]: hk_pai, "hash_diff": novo, "record_source": record_source}
    session.execute(insert(tabela).values({**linha, **atributos}))
    return True


def gravar_hubs(
    session: Session, tabela: Table, chaves: Sequence[Mapping[str, object]], record_source: str
) -> list[bytes]:
    """Grava em um `executemany` os hubs que ainda não existem (A2, passo 1, em lote).

    Args:
        session: Sessão com transação aberta.
        tabela: Hub de `dominio.tabelas`.
        chaves: Chave de negócio de cada hub, na ordem de entrada.
        record_source: Origem da gravação.

    Returns:
        O `hk` de cada chave, na mesma ordem.
    """
    hks = [chave_do_hub(tabela, chave) for chave in chaves]
    linhas = {
        hk: {
            tabela.info["hk"]: hk,
            **{coluna: _normalizar(coluna, valor) for coluna, valor in chave.items()},
            "record_source": record_source,
        }
        for hk, chave in zip(hks, chaves, strict=True)
    }
    if linhas:
        comando = insert(tabela).on_conflict_do_nothing(index_elements=[tabela.info["hk"]])
        session.execute(comando, list(linhas.values()))
    return hks


def gravar_links(
    session: Session, tabela: Table, ligacoes: Sequence[Mapping[str, bytes]], record_source: str
) -> list[bytes]:
    """Grava em um `executemany` os links que ainda não existem (A2, passo 2, em lote).

    Args:
        session: Sessão com transação aberta.
        tabela: Link historizável de `dominio.tabelas`.
        ligacoes: `hk` de cada hub ligado, pela coluna, de cada link.
        record_source: Origem da gravação.

    Returns:
        O `hk` de cada link, na ordem de entrada.

    Raises:
        GravacaoInvalidaError: Tabela que não é link ou colunas diferentes das do link.
    """
    _exigir_tipo(tabela, "link")
    colunas = list(tabela.info["hubs"])
    linhas: dict[bytes, dict[str, object]] = {}
    hks = []
    for hubs in ligacoes:
        _exigir_colunas(tabela, hubs, colunas)
        hk = chave_link(*(hubs[coluna] for coluna in colunas))
        linhas[hk] = {tabela.info["hk"]: hk, **hubs, "record_source": record_source}
        hks.append(hk)
    if linhas:
        comando = insert(tabela).on_conflict_do_nothing(index_elements=[tabela.info["hk"]])
        session.execute(comando, list(linhas.values()))
    return hks


def _hash_diffs_correntes(
    session: Session, tabela: Table, pais: set[bytes]
) -> dict[tuple[object, ...], bytes]:
    pai = tabela.c[tabela.info["pai"]]
    chave = [pai]
    if tabela.info["multiativo"] is not None:
        chave.append(tabela.c[tabela.info["multiativo"]])
    consulta = (
        select(*chave, tabela.c.hash_diff)
        .where(pai.in_(pais))
        .distinct(*chave)
        .order_by(*chave, tabela.c.load_dts.desc())
    )
    return {tuple(linha[:-1]): linha[-1] for linha in session.execute(consulta)}


def gravar_satelites(
    session: Session,
    tabela: Table,
    versoes: Sequence[tuple[bytes, Mapping[str, object]]],
    record_source: str,
) -> int:
    """Grava em um `executemany` as linhas de satélite cujo conteúdo mudou (A2, passos 3 a 6).

    Os `hash_diff` correntes vêm de um único `SELECT DISTINCT ON` antes do laço; cada versão é
    comparada com a corrente do pai (e da subchave, no multiativo), que passa a ser a própria
    versão quando ela entra na lista, como em chamadas sucessivas de `gravar_satelite`.

    Args:
        session: Sessão com transação aberta.
        tabela: Satélite de `dominio.tabelas`.
        versoes: Pares `(hk do pai, atributos)`, na ordem de gravação.
        record_source: Origem da gravação.

    Returns:
        O número de linhas inseridas.

    Raises:
        GravacaoInvalidaError: Tabela que não é satélite ou atributos diferentes dos declarados.
    """
    _exigir_tipo(tabela, "satelite")
    if not versoes:
        return 0
    esperadas = atributos_do_satelite(tabela)
    sempre = tabela.info["sempre_insere"]
    subchave = tabela.info["multiativo"]
    correntes = {} if sempre else _hash_diffs_correntes(session, tabela, {hk for hk, _ in versoes})
    linhas = []
    for hk_pai, atributos in versoes:
        _exigir_colunas(tabela, atributos, esperadas)
        novo = hash_diff(atributos)
        chave = (hk_pai,) if subchave is None else (hk_pai, atributos[subchave])
        if not sempre and correntes.get(chave) == novo:
            continue
        correntes[chave] = novo
        linha = {tabela.info["pai"]: hk_pai, "hash_diff": novo, "record_source": record_source}
        linhas.append({**linha, **atributos})
    if linhas:
        session.execute(insert(tabela), linhas)
    return len(linhas)
