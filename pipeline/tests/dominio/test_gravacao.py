"""Gravação só por inserção e imutabilidade do Data Vault (A2; D6, D13; RES-13)."""

import pytest
from sqlalchemy import Table, func, select, text
from sqlalchemy.exc import DBAPIError, IntegrityError, ProgrammingError
from sqlalchemy.orm import Session

from lupa_pipeline.dominio.chaves import chave_hash, chave_link
from lupa_pipeline.dominio.gravacao import (
    GravacaoInvalidaError,
    gravar_hub,
    gravar_link,
    gravar_satelite,
)
from lupa_pipeline.dominio.sessao import assumir_papel_aplicacao
from lupa_pipeline.dominio.tabelas import (
    hub_achado,
    hub_arquivo,
    hub_chave_login,
    hub_processo,
    hub_usuario,
    link_processo_arquivo,
    link_processo_responsavel,
    sat_arquivo_lote,
    sat_chave_login_falha,
    sat_processo_estado,
    sat_usuario_cadastro,
)

pytestmark = pytest.mark.integracao

ORIGEM = "teste"
NUMERO_COM_MASCARA = "0001234-56.2025.8.09.0001"
NUMERO = "00012345620258090001"
SHA256 = "CD" * 32


def _contar(sessao: Session, tabela: Table) -> int:
    return sessao.scalar(select(func.count()).select_from(tabela)) or 0


def _processo(sessao: Session) -> bytes:
    return gravar_hub(sessao, hub_processo, {"numero_cnj": NUMERO_COM_MASCARA}, ORIGEM)


def _usuario(sessao: Session, nome: str = "assessor.um") -> bytes:
    return gravar_hub(sessao, hub_usuario, {"nome_usuario": nome}, ORIGEM)


def _arquivo(sessao: Session) -> bytes:
    return gravar_hub(sessao, hub_arquivo, {"numero_cnj": NUMERO, "sha256": SHA256}, ORIGEM)


def test_gravar_hub_devolve_o_hk_da_chave_normalizada(sessao: Session) -> None:
    """RES-02: o `hk` vem do CNJ só com dígitos, que é também o valor gravado (A2, passo 1)."""
    hk = _processo(sessao)
    assert hk == chave_hash([NUMERO])
    gravado = sessao.scalar(
        select(hub_processo.c.numero_cnj).where(hub_processo.c.hk_processo == hk)
    )
    assert gravado == NUMERO


def test_gravar_hub_de_novo_nao_duplica(sessao: Session) -> None:
    """D6: o mesmo hub gravado duas vezes fica numa linha só."""
    assert _processo(sessao) == _processo(sessao)
    assert _contar(sessao, hub_processo) == 1


def test_gravar_hub_poe_hash_em_minusculas(sessao: Session) -> None:
    """RES-02: o `sha256` da chave fica em minúsculas no `hk` e na coluna."""
    hk = _arquivo(sessao)
    assert hk == chave_hash([NUMERO, SHA256.lower()])
    assert sessao.scalar(select(hub_arquivo.c.sha256)) == SHA256.lower()


def test_gravar_hub_aceita_sujeito_vazio(sessao: Session) -> None:
    """RES-02: achado sem sujeito tem chave com a última parte vazia."""
    chave = {"numero_cnj": NUMERO, "validacao": "tempestividade_recurso", "sujeito": ""}
    hk = gravar_hub(sessao, hub_achado, chave, ORIGEM)
    assert hk == chave_hash([NUMERO, "tempestividade_recurso", ""], vazias_permitidas={2})


def test_gravar_hub_recusa_colunas_diferentes_da_chave(sessao: Session) -> None:
    """D13: a chave de negócio tem exatamente as colunas do hub."""
    with pytest.raises(GravacaoInvalidaError, match="sobram"):
        gravar_hub(sessao, hub_processo, {"numero_cnj": NUMERO, "classe": "x"}, ORIGEM)
    with pytest.raises(GravacaoInvalidaError, match="não é hub"):
        gravar_hub(sessao, sat_processo_estado, {"numero_cnj": NUMERO}, ORIGEM)


def test_gravar_link_devolve_o_hk_e_nao_duplica(sessao: Session) -> None:
    """D6: o link é o SHA-256 dos `hk` dos hubs e não se repete (A2, passo 2)."""
    hks = {"hk_processo": _processo(sessao), "hk_arquivo": _arquivo(sessao)}
    primeiro = gravar_link(sessao, link_processo_arquivo, hks, ORIGEM)
    assert primeiro == gravar_link(sessao, link_processo_arquivo, hks, ORIGEM)
    assert primeiro == chave_link(hks["hk_processo"], hks["hk_arquivo"])
    assert _contar(sessao, link_processo_arquivo) == 1


def test_gravar_link_recusa_hub_faltando(sessao: Session) -> None:
    """D13: o link exige o `hk` de cada hub ligado."""
    with pytest.raises(GravacaoInvalidaError, match="faltam"):
        gravar_link(sessao, link_processo_arquivo, {"hk_processo": _processo(sessao)}, ORIGEM)


def _estado(sessao: Session, hk: bytes, status: str) -> bool:
    return gravar_satelite(sessao, sat_processo_estado, hk, {"status": status}, ORIGEM)


def test_satelite_nao_insere_com_hash_diff_igual(sessao: Session) -> None:
    """D6: gravar o mesmo estado duas vezes não cria linha nova (A2, passo 4)."""
    hk = _processo(sessao)
    assert _estado(sessao, hk, "criado") is True
    assert _estado(sessao, hk, "criado") is False
    assert _contar(sessao, sat_processo_estado) == 1


def test_satelite_insere_com_hash_diff_diferente(sessao: Session) -> None:
    """D6: mudança de estado é linha nova, comparada só com a mais recente (A2, passo 5)."""
    hk = _processo(sessao)
    assert _estado(sessao, hk, "criado") is True
    assert _estado(sessao, hk, "em_ingestao") is True
    assert _estado(sessao, hk, "criado") is True
    estados = sessao.scalars(
        select(sat_processo_estado.c.status).order_by(sat_processo_estado.c.load_dts)
    ).all()
    assert estados == ["criado", "em_ingestao", "criado"]


def test_satelite_multiativo_compara_dentro_da_mesma_subchave(sessao: Session) -> None:
    """D6: no satélite de lotes cada `numero` tem o próprio histórico (A2, passo 6)."""
    hk = _arquivo(sessao)

    def lote(numero: int) -> bool:
        atributos = {"numero": numero, "estado": "concluido", "resultado": {"paginas": [numero]}}
        return gravar_satelite(sessao, sat_arquivo_lote, hk, atributos, ORIGEM)

    assert (lote(1), lote(2), lote(1), lote(2)) == (True, True, False, False)
    assert _contar(sessao, sat_arquivo_lote) == 2


def test_satelite_que_sempre_insere_grava_cada_falha(sessao: Session) -> None:
    """RF-ACE-02: cada falha de login é uma linha, mesmo sem atributo (A2, passo 6)."""
    hk = gravar_hub(sessao, hub_chave_login, {"chave": "AB" * 32}, ORIGEM)
    for _ in range(3):
        assert gravar_satelite(sessao, sat_chave_login_falha, hk, {}, ORIGEM) is True
    assert _contar(sessao, sat_chave_login_falha) == 3


def test_satelite_recusa_atributo_faltando(sessao: Session) -> None:
    """D13: o satélite recebe todas as colunas de negócio, sem sobra nem falta."""
    with pytest.raises(GravacaoInvalidaError, match="ativo"):
        gravar_satelite(sessao, sat_usuario_cadastro, _usuario(sessao), {"papel": "x"}, ORIGEM)


def test_satelite_de_pai_inexistente_propaga_o_erro_de_fk(sessao: Session) -> None:
    """D6: violação de FK propaga para a transação de quem chama (A2, passo 7)."""
    with pytest.raises(IntegrityError, match="foreign key"):
        _estado(sessao, chave_hash(["inexistente"]), "criado")


def test_check_do_enum_propaga_na_gravacao(sessao: Session) -> None:
    """D6: valor fora do enum é recusado pelo CHECK gerado (A2, passo 7)."""
    with pytest.raises(IntegrityError, match="status_valido"):
        _estado(sessao, _processo(sessao), "bloqueado")


def test_gravacao_funciona_sob_o_papel_da_aplicacao(sessao: Session) -> None:
    """RES-13: `lupa_app` grava hub, link e satélite só com INSERT e SELECT."""
    assumir_papel_aplicacao(sessao)
    processo, usuario = _processo(sessao), _usuario(sessao)
    hks = {"hk_processo": processo, "hk_usuario": usuario}
    assert gravar_link(sessao, link_processo_responsavel, hks, ORIGEM)
    assert _estado(sessao, processo, "criado") is True
    assert _estado(sessao, processo, "criado") is False


COMANDOS = {
    "hub": (
        "UPDATE hub_processo SET record_source = 'outro' WHERE hk_processo = :hk",
        "DELETE FROM hub_processo WHERE hk_processo = :hk",
    ),
    "link": (
        "UPDATE link_processo_responsavel SET record_source = 'outro' WHERE hk_processo = :hk",
        "DELETE FROM link_processo_responsavel WHERE hk_processo = :hk",
    ),
    "satelite": (
        "UPDATE sat_processo_estado SET status = 'pronto' WHERE hk_processo = :hk",
        "DELETE FROM sat_processo_estado WHERE hk_processo = :hk",
    ),
}


def _semear(sessao: Session) -> bytes:
    processo, usuario = _processo(sessao), _usuario(sessao)
    hks = {"hk_processo": processo, "hk_usuario": usuario}
    gravar_link(sessao, link_processo_responsavel, hks, ORIGEM)
    _estado(sessao, processo, "criado")
    return processo


@pytest.mark.parametrize("tipo", ["hub", "link", "satelite"])
def test_update_e_delete_sao_recusados_sob_lupa_app(sessao: Session, tipo: str) -> None:
    """D6, RES-13: `lupa_app` não tem UPDATE nem DELETE em hub, link e satélite."""
    processo = _semear(sessao)
    assumir_papel_aplicacao(sessao)
    for comando in COMANDOS[tipo]:
        with pytest.raises(ProgrammingError, match="permission denied"), sessao.begin_nested():
            sessao.execute(text(comando), {"hk": processo})


@pytest.mark.parametrize("tipo", ["hub", "link", "satelite"])
def test_update_e_delete_sao_recusados_pelo_trigger_mesmo_para_o_dono(
    sessao: Session, tipo: str
) -> None:
    """D6, RES-13: o trigger `<tabela>_imutavel` recusa UPDATE e DELETE de qualquer papel."""
    processo = _semear(sessao)
    for comando in COMANDOS[tipo]:
        with pytest.raises(DBAPIError, match="imutável"), sessao.begin_nested():
            sessao.execute(text(comando), {"hk": processo})


def test_descarte_libera_delete_so_em_satelite(sessao: Session) -> None:
    """RES-13: com `lupa.descarte` ligado, satélite aceita DELETE; hub e link continuam fixos."""
    processo = _semear(sessao)
    sessao.execute(text("SELECT set_config('lupa.descarte', 'on', true)"))
    sessao.execute(text(COMANDOS["satelite"][1]), {"hk": processo})
    assert _contar(sessao, sat_processo_estado) == 0
    for tipo in ("hub", "link"):
        with pytest.raises(DBAPIError, match="imutável"), sessao.begin_nested():
            sessao.execute(text(COMANDOS[tipo][1]), {"hk": processo})
