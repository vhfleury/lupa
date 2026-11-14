"""DEK por processo em `sat_processo_chave`, envolvida pela chave única `lupa` do cofre (D14).

- `criar_chave_processo`: gera a DEK de um processo novo, grava a versão cifrada em
  `sat_processo_chave` e deixa a DEK aberta no contexto de cifra, como processo das gravações.
- `carregador_sql`: lê a DEK cifrada pela view `v_processo` numa sessão própria; usado pelo
  contexto de cifra para abrir a DEK de um processo cujo campo foi lido.
"""

from collections.abc import Callable

from sqlalchemy import select
from sqlalchemy.orm import Session

from lupa_pipeline.dominio.gravacao import gravar_satelite
from lupa_pipeline.dominio.tabelas import sat_processo_chave
from lupa_pipeline.dominio.visoes import VisaoProcesso
from lupa_pipeline.seguranca.cofre import Cofre
from lupa_pipeline.seguranca.contexto import Carregador, nova_dek, registrar_dek


def criar_chave_processo(
    session: Session, cofre: Cofre, hk_processo: bytes, record_source: str
) -> bytes:
    """Cria a DEK do processo e grava a versão cifrada em `sat_processo_chave` (RF-SEG-01).

    Args:
        session: Sessão com transação aberta (o hub do processo já gravado).
        cofre: Cofre com a chave `lupa`.
        hk_processo: Processo.
        record_source: Origem da gravação.

    Returns:
        A DEK em claro, já registrada no contexto como a do processo atual.
    """
    dek, token = nova_dek(cofre)
    atributos = {"chave_dados_cifrada": token}
    gravar_satelite(session, sat_processo_chave, hk_processo, atributos, record_source)
    registrar_dek(hk_processo, dek)
    return dek


def carregador_sql(fabrica: Callable[[], Session]) -> Carregador:
    """Cria o carregador da DEK cifrada a partir de uma fábrica de sessões.

    Args:
        fabrica: Abre uma sessão nova (conexão própria, fora da transação corrente).

    Returns:
        Função `hk_processo -> chave_dados_cifrada` (None se o processo não tem chave).
    """

    def _carregar(hk_processo: bytes) -> str | None:
        consulta = select(VisaoProcesso.chave_dados_cifrada).where(
            VisaoProcesso.hk_processo == hk_processo
        )
        with fabrica() as session:
            return session.scalar(consulta)

    return _carregar
