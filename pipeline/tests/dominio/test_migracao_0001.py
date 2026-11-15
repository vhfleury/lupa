"""Revisão `v0001_data_vault`: sobe, desce e cria o Data Vault da 0.2 (D3, D18; RES-02, RES-13)."""

from collections.abc import Iterator
from uuid import uuid4

import pytest
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import Engine, inspect, text
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.orm import Session

from apoio_comum import banco_vazio, migrar
from lupa_pipeline.dominio.chaves import chave_hash, chave_link
from lupa_pipeline.dominio.tabelas import HUBS, LINKS, SATELITES, metadata
from lupa_pipeline.migrations.esquema_v0001 import VISOES

pytestmark = pytest.mark.integracao

PAPEL = "lupa_app"
NUMERO_CNJ = "00012345620258090001"
SHA256 = "ab" * 32


@pytest.fixture
def engine_vazio() -> Iterator[Engine]:
    """Database próprio, sem migração, para subir e descer a revisão."""
    with banco_vazio("migracao") as engine:
        yield engine


def _tabelas_do_vault(engine: Engine) -> set[str]:
    nomes = set(inspect(engine).get_table_names())
    return {nome for nome in nomes if nome.split("_", 1)[0] in {"hub", "link", "sat"}}


def test_upgrade_cria_o_data_vault_e_downgrade_remove(engine_vazio: Engine) -> None:
    """RES-09: o banco nasce vazio pela revisão nova, que sobe e desce sem resto."""
    migrar(engine_vazio, "head")
    assert _tabelas_do_vault(engine_vazio) == set(metadata.tables)
    assert set(VISOES) <= set(inspect(engine_vazio).get_view_names())
    migrar(engine_vazio, "base", descer=True)
    assert _tabelas_do_vault(engine_vazio) == set()
    assert inspect(engine_vazio).get_view_names() == []
    migrar(engine_vazio, "head")
    assert _tabelas_do_vault(engine_vazio) == set(metadata.tables)


def test_migracao_coincide_com_tabelas(engine_teste: Engine) -> None:
    """RES-02: a revisão escrita à mão gera o mesmo esquema que `dominio.tabelas`."""
    with engine_teste.connect() as conexao:
        diferencas = compare_metadata(MigrationContext.configure(conexao), metadata)
    assert diferencas == []


def test_modelo_tem_os_hubs_links_e_satelites_do_plano() -> None:
    """RES-03: 13 hubs, 15 links e 27 satélites, com os prefixos de RES-13."""
    assert (len(HUBS), len(LINKS), len(SATELITES)) == (13, 15, 27)
    assert all(t.name.startswith("hub_") for t in HUBS)
    assert all(t.name.startswith("link_") for t in LINKS)
    assert all(t.name.startswith("sat_") for t in SATELITES)


def test_toda_tabela_tem_o_trigger_de_imutabilidade(engine_teste: Engine) -> None:
    """RES-13: cada tabela tem `<tabela>_imutavel` antes de UPDATE e DELETE."""
    with engine_teste.connect() as conexao:
        gatilhos = set(
            conexao.execute(
                text(
                    "SELECT tgname FROM pg_trigger t JOIN pg_proc p ON p.oid = t.tgfoid "
                    "WHERE p.proname = 'lupa_bloquear_alteracao' AND NOT t.tgisinternal"
                )
            ).scalars()
        )
    assert gatilhos == {f"{nome}_imutavel" for nome in metadata.tables} | {
        "link_evento_auditoria_bloquear_truncate"
    }


def test_papel_da_aplicacao_so_le_e_insere(engine_teste: Engine) -> None:
    """RES-13: `lupa_app` tem SELECT e INSERT nas tabelas e só SELECT nas views."""
    with engine_teste.connect() as conexao:
        linhas = conexao.execute(
            text(
                "SELECT table_name, string_agg(privilege_type, ',' ORDER BY privilege_type) "
                "FROM information_schema.role_table_grants WHERE grantee = :papel "
                "GROUP BY table_name"
            ),
            {"papel": PAPEL},
        ).all()
    privilegios = {nome: valor for nome, valor in linhas}
    assert privilegios == {nome: "INSERT,SELECT" for nome in metadata.tables} | {
        nome: "SELECT" for nome in VISOES
    }


def test_papel_da_aplicacao_executa_o_descarte(engine_teste: Engine) -> None:
    """RF-PRO-05: `lupa_app` pode chamar `lupa_descartar_processo`, que roda como dono."""
    with engine_teste.connect() as conexao:
        pode = conexao.execute(
            text(
                "SELECT has_function_privilege(:papel, 'lupa_descartar_processo(bytea)', "
                "'EXECUTE'), (SELECT prosecdef FROM pg_proc "
                "WHERE proname = 'lupa_descartar_processo')"
            ),
            {"papel": PAPEL},
        ).one()
    assert tuple(pode) == (True, True)


def _inserir_usuario(sessao: Session, papel: str) -> None:
    hk = chave_hash([f"usuario.{uuid4().hex[:8]}"])
    sessao.execute(
        text(
            "INSERT INTO hub_usuario (hk_usuario, nome_usuario, record_source) "
            "VALUES (:hk, :nome, 'teste')"
        ),
        {"hk": hk, "nome": hk.hex()[:12]},
    )
    sessao.execute(
        text(
            "INSERT INTO sat_usuario_cadastro (hk_usuario, hash_diff, record_source, papel, ativo) "
            "VALUES (:hk, :hk, 'teste', :papel, true)"
        ),
        {"hk": hk, "papel": papel},
    )


def test_check_gerado_do_enum_recusa_valor_fora_dele(sessao: Session) -> None:
    """RF-ACE-03: o papel `administrador` da 0.1 não existe mais no banco."""
    _inserir_usuario(sessao, "desembargador")
    with pytest.raises(IntegrityError, match="papel_valido"):
        _inserir_usuario(sessao, "administrador")


def test_hk_sem_32_bytes_e_recusado(sessao: Session) -> None:
    """RES-13: `hk_*` é SHA-256; outro tamanho é recusado pelo CHECK."""
    with pytest.raises(IntegrityError, match="hk_processo_tamanho"):
        sessao.execute(
            text(
                "INSERT INTO hub_processo (hk_processo, numero_cnj, record_source) "
                "VALUES (:hk, :numero, 'teste')"
            ),
            {"hk": bytes(16), "numero": NUMERO_CNJ},
        )


def _inserir_fato(sessao: Session, *, com_evidencia: bool) -> None:
    hk_evidencia = chave_hash([NUMERO_CNJ, SHA256, 1, 0, 10])
    hk_fato = chave_hash([NUMERO_CNJ, "tipo_recurso", "", hk_evidencia], vazias_permitidas={2})
    sessao.execute(
        text(
            "INSERT INTO hub_evidencia (hk_evidencia, numero_cnj, sha256, numero, inicio, fim, "
            "record_source) VALUES (:hk, :numero, :sha, 1, 0, 10, 'teste')"
        ),
        {"hk": hk_evidencia, "numero": NUMERO_CNJ, "sha": SHA256},
    )
    sessao.execute(
        text(
            "INSERT INTO hub_fato (hk_fato, numero_cnj, tipo, sujeito, hk_evidencia_origem, "
            "record_source) VALUES (:hk, :numero, 'tipo_recurso', '', :evidencia, 'teste')"
        ),
        {"hk": hk_fato, "numero": NUMERO_CNJ, "evidencia": hk_evidencia},
    )
    if com_evidencia:
        sessao.execute(
            text(
                "INSERT INTO link_fato_evidencia (hk_fato_evidencia, hk_fato, hk_evidencia, "
                "record_source) VALUES (:hk, :fato, :evidencia, 'teste')"
            ),
            {"hk": chave_link(hk_fato, hk_evidencia), "fato": hk_fato, "evidencia": hk_evidencia},
        )


def test_fato_sem_evidencia_e_recusado_no_commit(sessao: Session) -> None:
    """RF-FAT-01: o trigger adiado recusa `hub_fato` sem linha em `link_fato_evidencia`."""
    _inserir_fato(sessao, com_evidencia=False)
    with pytest.raises(DBAPIError, match="sem evidência"):
        sessao.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))


def test_fato_com_evidencia_passa_no_commit(sessao: Session) -> None:
    """RF-FAT-01: com o link para a evidência, o fato é aceito."""
    _inserir_fato(sessao, com_evidencia=True)
    sessao.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))


def test_nome_de_pessoa_so_fica_em_coluna_autorizada() -> None:
    """RF-FAT-04, RF-SEG-01: nome de parte só em `sat_parte_identidade`, em texto."""
    colunas = {
        f"{tabela.name}.{coluna.name}"
        for tabela in metadata.tables.values()
        for coluna in tabela.columns
        if coluna.name.startswith("nome") or coluna.name in {"documento", "cpf"}
    }
    assert colunas == {
        "hub_usuario.nome_usuario",
        "sat_parte_identidade.nome",
        "sat_arquivo_dados.nome_original",
    }
    assert type(metadata.tables["sat_parte_identidade"].c.nome.type).__name__ == "Text"
