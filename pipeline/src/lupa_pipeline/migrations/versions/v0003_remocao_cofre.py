"""Remove a chave de dados por processo: tabela, coluna de `v_processo` e retorno do descarte."""

from alembic import op

from lupa_pipeline.migrations import esquema_v0001
from lupa_pipeline.migrations.esquema_v0001 import PAPEL_APLICACAO, PROCESSO, SQL_DESCARTE
from lupa_pipeline.migrations.versions.v0002_cadastro_pelo_arquivo import VISAO_PROCESSO

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None

TRECHO_CHAVE = """
    SELECT chave_dados_cifrada INTO v_chave FROM sat_processo_chave
        WHERE hk_processo = p_hk_processo ORDER BY load_dts DESC LIMIT 1;
    DELETE FROM sat_processo_chave WHERE hk_processo = p_hk_processo;
    IF v_chave IS NULL THEN
        RETURN NULL;
    END IF;
    RETURN encode(sha256(convert_to(v_chave, 'UTF8')), 'hex');
"""
JUNCAO_CHAVE = """
LEFT JOIN LATERAL (
    SELECT chave_dados_cifrada FROM sat_processo_chave
    WHERE hk_processo = h.hk_processo ORDER BY load_dts DESC LIMIT 1
) k ON true"""

SQL_DESCARTE_SEM_CHAVE = (
    SQL_DESCARTE.replace("RETURNS TEXT", "RETURNS VOID")
    .replace("    v_chave TEXT;\n", "")
    .replace(TRECHO_CHAVE, "\n")
)
VISAO_PROCESSO_SEM_CHAVE = VISAO_PROCESSO.replace(" k.chave_dados_cifrada,", "").replace(
    JUNCAO_CHAVE, ""
)


def _recriar_descarte(sql: str) -> None:
    op.execute("DROP FUNCTION lupa_descartar_processo(BYTEA)")
    op.execute(sql)
    op.execute("REVOKE ALL ON FUNCTION lupa_descartar_processo(BYTEA) FROM PUBLIC")
    op.execute(f"GRANT EXECUTE ON FUNCTION lupa_descartar_processo(BYTEA) TO {PAPEL_APLICACAO}")


def _recriar_visao(sql: str) -> None:
    op.execute("DROP VIEW v_processo")
    op.execute(f"CREATE VIEW v_processo AS {sql}")
    op.execute(f"GRANT SELECT ON v_processo TO {PAPEL_APLICACAO}")


def upgrade() -> None:
    """Tira a chave cifrada da view e do descarte e remove `sat_processo_chave`."""
    _recriar_visao(VISAO_PROCESSO_SEM_CHAVE)
    _recriar_descarte(SQL_DESCARTE_SEM_CHAVE)
    op.drop_table("sat_processo_chave")


def downgrade() -> None:
    """Recria `sat_processo_chave` vazia, a função que devolve o hash e a view da 0002."""
    esquema_v0001._sat("sat_processo_chave", *PROCESSO, esquema_v0001._texto("chave_dados_cifrada"))
    op.execute(
        "CREATE TRIGGER sat_processo_chave_imutavel BEFORE UPDATE OR DELETE ON sat_processo_chave "
        "FOR EACH ROW EXECUTE FUNCTION lupa_bloquear_alteracao()"
    )
    op.execute(f"GRANT SELECT, INSERT ON sat_processo_chave TO {PAPEL_APLICACAO}")
    _recriar_descarte(SQL_DESCARTE)
    _recriar_visao(VISAO_PROCESSO)
