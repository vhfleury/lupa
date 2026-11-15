"""Amplia os fatos da capa e expõe o histórico da classe em v_processo."""

from alembic import op

from lupa_pipeline.dominio.tabelas import checar_valores
from lupa_pipeline.migrations.esquema_v0001 import PAPEL_APLICACAO, TIPOS_FATO_0001, VISOES

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

TIPOS_CAPA = (
    "relator",
    "orgao_julgador",
    "assunto",
    "valor_causa",
    "juizo_origem",
    "data_distribuicao",
)
VISAO_PROCESSO = """
SELECT encode(h.hk_processo, 'hex') AS id, h.hk_processo, h.numero_cnj, h.load_dts AS criado_em,
       d.classe, c.hk_usuario AS hk_criador, encode(c.hk_usuario, 'hex') AS criador_id,
       e.status, k.chave_dados_cifrada, coalesce(r.situacao = 'aberta', false) AS em_revisao,
       r.motivo AS motivo_revisao, r.status_anterior AS status_anterior_revisao,
       r.load_dts AS revisao_em, d.classe_anterior,
       CASE WHEN d.classe_anterior IS NOT NULL THEN d.hk_usuario END AS hk_classe_corrigida_por,
       CASE WHEN d.classe_anterior IS NOT NULL THEN encode(d.hk_usuario, 'hex') END
           AS classe_corrigida_por_id,
       CASE WHEN d.classe_anterior IS NOT NULL THEN d.load_dts END AS classe_corrigida_em
FROM hub_processo h
LEFT JOIN LATERAL (
    SELECT hk_usuario FROM sat_processo_dados
    WHERE hk_processo = h.hk_processo ORDER BY load_dts LIMIT 1
) c ON true
LEFT JOIN LATERAL (
    SELECT classe, hk_usuario, load_dts,
           lead(classe) OVER (ORDER BY load_dts DESC) AS classe_anterior
    FROM sat_processo_dados WHERE hk_processo = h.hk_processo ORDER BY load_dts DESC LIMIT 1
) d ON true
LEFT JOIN LATERAL (
    SELECT status FROM sat_processo_estado
    WHERE hk_processo = h.hk_processo ORDER BY load_dts DESC LIMIT 1
) e ON true
LEFT JOIN LATERAL (
    SELECT chave_dados_cifrada FROM sat_processo_chave
    WHERE hk_processo = h.hk_processo ORDER BY load_dts DESC LIMIT 1
) k ON true
LEFT JOIN LATERAL (
    SELECT situacao, motivo, status_anterior, load_dts FROM sat_processo_revisao
    WHERE hk_processo = h.hk_processo ORDER BY load_dts DESC LIMIT 1
) r ON true
"""


def _check(tipos: tuple[str, ...]) -> None:
    op.drop_constraint("tipo_valido", "hub_fato", type_="check")
    op.create_check_constraint("tipo_valido", "hub_fato", checar_valores("tipo", tipos).sqltext)


def upgrade() -> None:
    """Preserva as colunas anteriores e acrescenta a autoria da correção."""
    _check(TIPOS_FATO_0001 + TIPOS_CAPA)
    op.execute(f"CREATE OR REPLACE VIEW v_processo AS {VISAO_PROCESSO}")


def downgrade() -> None:
    """Restaura a visão e o CHECK de 0001 sem apagar fatos já extraídos."""
    _check(TIPOS_FATO_0001)
    op.execute("DROP VIEW v_processo")
    op.execute(f"CREATE VIEW v_processo AS {VISOES['v_processo']}")
    op.execute(f"GRANT SELECT ON v_processo TO {PAPEL_APLICACAO}")
