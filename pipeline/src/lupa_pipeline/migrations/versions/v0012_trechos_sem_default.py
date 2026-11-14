"""Tira o `DEFAULT '[]'` em claro de `pagina.trechos_ocultos` e `trechos_suspeitos`.

As colunas guardam JSON cifrado (`lupa1:`); a lista vazia agora vem do modelo e é cifrada como
qualquer outro valor. A leitura recusa valor em claro.
"""

from alembic import op

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None

COLUNAS = ("trechos_ocultos", "trechos_suspeitos")


def upgrade() -> None:
    """Remove o default em claro das duas colunas."""
    for coluna in COLUNAS:
        op.execute(f"ALTER TABLE pagina ALTER COLUMN {coluna} DROP DEFAULT")


def downgrade() -> None:
    """Devolve o default `'[]'` das duas colunas."""
    for coluna in COLUNAS:
        op.execute(f"ALTER TABLE pagina ALTER COLUMN {coluna} SET DEFAULT '[]'")
