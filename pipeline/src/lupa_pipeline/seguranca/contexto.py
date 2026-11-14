"""Contexto de cifra: as DEKs em claro do escopo corrente (requisição, job ou script).

As DEKs abertas ficam só neste objeto, em memória, e somem com ele no fim do escopo. O
middleware da API cria um contexto por requisição (`lupa_intranet.api.cifra`); o worker cria um
por arquivo. Fora desses escopos (testes, scripts) vale um contexto padrão do processo Python.

O processo é identificado pelo `hk_processo` (32 bytes). Leitura: o campo cifrado traz o `hk` no
cabeçalho; a DEK vem do cache do contexto ou do `carregador` (que lê a DEK cifrada de
`sat_processo_chave` pela view `v_processo` e abre no cofre com a chave `lupa`). Gravação: usa o
processo `atual`, definido por `ativar_processo` (rota com `exige_processo`, worker) ou pelo
último processo cuja DEK foi criada no escopo. Nunca registre DEK em log.
"""

import threading
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field

from lupa_pipeline.seguranca.cofre import CHAVE_DADOS, Cofre
from lupa_pipeline.seguranca.envelope import gerar_dek

Carregador = Callable[[bytes], str | None]


class ChaveIndisponivelError(LookupError):
    """Não há DEK para o processo (sem contexto, processo descartado ou sem chave)."""


@dataclass
class ContextoCifra:
    """DEKs abertas de um escopo.

    Attributes:
        deks: DEK em claro por `hk_processo`.
        atual: Processo cujas gravações são cifradas.
        carregador: `hk_processo -> dek_cifrada` lido do banco (ou None).
    """

    deks: dict[bytes, bytes] = field(default_factory=dict)
    atual: bytes | None = None
    carregador: Carregador | None = None
    trava: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def __repr__(self) -> str:
        """Nunca mostra as chaves.

        Returns:
            Só a quantidade de DEKs e se há processo atual.
        """
        return f"ContextoCifra(deks={len(self.deks)}, atual={self.atual is not None})"


_PADRAO = ContextoCifra()
_CONTEXTO: ContextVar[ContextoCifra | None] = ContextVar("lupa_contexto_cifra", default=None)
_COFRE: list[Cofre] = []
_CARREGADOR_PADRAO: list[Carregador] = []


def definir_cofre(cofre: Cofre) -> None:
    """Registra o cofre usado por este processo Python (API, worker, scripts, testes).

    Args:
        cofre: Cofre de chaves.
    """
    _COFRE[:] = [cofre]


def obter_cofre() -> Cofre:
    """Cofre registrado; sem registro, cria pelo `LUPA_COFRE_BACKEND` da configuração.

    Returns:
        O cofre.
    """
    if not _COFRE:
        from lupa_pipeline.config import get_settings
        from lupa_pipeline.seguranca.cofre import criar_cofre

        _COFRE.append(criar_cofre(get_settings()))
    return _COFRE[0]


def definir_carregador_padrao(carregador: Carregador | None) -> None:
    """Carregador do contexto padrão (fora de requisição e de job).

    Args:
        carregador: Leitor da DEK cifrada, ou None para remover.
    """
    _CARREGADOR_PADRAO[:] = [carregador] if carregador else []
    _PADRAO.carregador = carregador


def contexto_atual() -> ContextoCifra:
    """Contexto do escopo corrente (ou o padrão).

    Returns:
        O contexto.
    """
    return _CONTEXTO.get() or _PADRAO


@contextmanager
def contexto_cifra(carregador: Carregador | None = None) -> Iterator[ContextoCifra]:
    """Abre um escopo novo; ao sair, as DEKs abertas são descartadas.

    Args:
        carregador: Leitor da DEK cifrada pelo `hk_processo`.

    Yields:
        O contexto novo.
    """
    contexto = ContextoCifra(carregador=carregador)
    token = _CONTEXTO.set(contexto)
    try:
        yield contexto
    finally:
        contexto.deks.clear()
        contexto.atual = None
        _CONTEXTO.reset(token)


def limpar_contexto_padrao() -> None:
    """Esquece as DEKs do contexto padrão (testes e fim de script)."""
    _PADRAO.deks.clear()
    _PADRAO.atual = None


def abrir_dek(cofre: Cofre, dek_cifrada: str) -> bytes:
    """Abre a DEK com a chave única `lupa` do cofre.

    Args:
        cofre: Cofre.
        dek_cifrada: Token de `sat_processo_chave.chave_dados_cifrada`.

    Returns:
        DEK em claro.
    """
    return cofre.decifrar(CHAVE_DADOS, dek_cifrada)


def nova_dek(cofre: Cofre) -> tuple[bytes, str]:
    """Gera a DEK de um processo novo e a cifra com a chave `lupa` (criada se faltar).

    Args:
        cofre: Cofre.

    Returns:
        DEK em claro e token para `sat_processo_chave.chave_dados_cifrada`.
    """
    cofre.criar_chave(CHAVE_DADOS)
    dek = gerar_dek()
    return dek, cofre.cifrar(CHAVE_DADOS, dek)


def registrar_dek(hk_processo: bytes, dek: bytes, *, atual: bool = True) -> None:
    """Guarda a DEK aberta no contexto corrente.

    Args:
        hk_processo: Processo.
        dek: DEK em claro.
        atual: Se o processo passa a ser o das gravações.
    """
    contexto = contexto_atual()
    with contexto.trava:
        contexto.deks[hk_processo] = dek
        if atual:
            contexto.atual = hk_processo


def ativar_processo(hk_processo: bytes, dek_cifrada: str | None) -> None:
    """Abre a DEK do processo e o torna o processo das gravações do escopo.

    Args:
        hk_processo: Processo.
        dek_cifrada: Chave corrente de `v_processo.chave_dados_cifrada`.

    Raises:
        ChaveIndisponivelError: Processo sem chave (descartado).
    """
    contexto = contexto_atual()
    if hk_processo not in contexto.deks:
        if dek_cifrada is None:
            raise ChaveIndisponivelError(hk_processo.hex())
        registrar_dek(hk_processo, abrir_dek(obter_cofre(), dek_cifrada))
    contexto.atual = hk_processo


def esquecer_processo(hk_processo: bytes) -> None:
    """Remove a DEK do processo do contexto corrente e do padrão (descarte).

    Args:
        hk_processo: Processo.
    """
    for contexto in {id(contexto_atual()): contexto_atual(), id(_PADRAO): _PADRAO}.values():
        contexto.deks.pop(hk_processo, None)
        if contexto.atual == hk_processo:
            contexto.atual = None


def dek_de(hk_processo: bytes) -> bytes:
    """DEK do processo: do cache do contexto ou pelo carregador.

    Args:
        hk_processo: Processo (do cabeçalho do campo cifrado ou da chave do objeto).

    Returns:
        DEK em claro.

    Raises:
        ChaveIndisponivelError: Sem DEK no contexto e sem carregador, ou processo sem chave.
    """
    contexto = contexto_atual()
    dek = contexto.deks.get(hk_processo)
    if dek is not None:
        return dek
    carregador = contexto.carregador or (_CARREGADOR_PADRAO[0] if _CARREGADOR_PADRAO else None)
    if carregador is None:
        raise ChaveIndisponivelError(hk_processo.hex())
    dek_cifrada = carregador(hk_processo)
    if dek_cifrada is None:
        raise ChaveIndisponivelError(hk_processo.hex())
    dek = abrir_dek(obter_cofre(), dek_cifrada)
    registrar_dek(hk_processo, dek, atual=False)
    return dek


def dek_para_gravar() -> tuple[bytes, bytes]:
    """Processo e DEK das gravações do escopo.

    Returns:
        `(hk_processo, dek)`.

    Raises:
        ChaveIndisponivelError: Nenhum processo ativo no escopo.
    """
    contexto = contexto_atual()
    if contexto.atual is None:
        raise ChaveIndisponivelError("nenhum processo ativo para cifrar")
    return contexto.atual, dek_de(contexto.atual)
