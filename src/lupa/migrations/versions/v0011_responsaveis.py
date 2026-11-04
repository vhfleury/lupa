"""Responsabilidade compartilhada por processo."""

from alembic import op

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Cria vínculos, preserva criadores assessores e isola por gabinete."""
    op.execute(
        "ALTER TABLE usuario ADD CONSTRAINT uq_usuario_id_gabinete_id UNIQUE (id, gabinete_id)"
    )
    op.execute("""
        CREATE TABLE processo_responsavel (
            processo_id uuid NOT NULL,
            usuario_id uuid NOT NULL,
            gabinete_id uuid NOT NULL,
            PRIMARY KEY (processo_id, usuario_id),
            FOREIGN KEY (processo_id, gabinete_id) REFERENCES processo(id, gabinete_id),
            FOREIGN KEY (usuario_id, gabinete_id) REFERENCES usuario(id, gabinete_id)
        )
    """)
    op.execute("CREATE INDEX ix_processo_responsavel_usuario ON processo_responsavel(usuario_id)")
    op.execute("""
        INSERT INTO processo_responsavel (processo_id, usuario_id, gabinete_id)
        SELECT p.id, p.criado_por, p.gabinete_id FROM processo p
        JOIN usuario u ON u.id = p.criado_por AND u.gabinete_id = p.gabinete_id
        WHERE u.papel = 'assessor'
    """)
    op.execute("ALTER TABLE processo_responsavel ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE processo_responsavel FORCE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY processo_responsavel_escopo ON processo_responsavel
        USING (current_setting('lupa.papel', true) = 'administrador'
          OR gabinete_id = NULLIF(current_setting('lupa.gabinete_id', true), '')::uuid)
        WITH CHECK (current_setting('lupa.papel', true) = 'administrador'
          OR gabinete_id = NULLIF(current_setting('lupa.gabinete_id', true), '')::uuid)
    """)
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON processo_responsavel TO lupa_app")
    op.execute("""
        CREATE FUNCTION lupa_responsavel_inicial() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
          INSERT INTO processo_responsavel (processo_id, usuario_id, gabinete_id)
          SELECT NEW.id, u.id, NEW.gabinete_id FROM usuario u
          WHERE u.id = NEW.criado_por AND u.papel = 'assessor'
            AND u.gabinete_id = NEW.gabinete_id;
          RETURN NEW;
        END;
        $$
    """)
    op.execute("""
        CREATE TRIGGER processo_responsavel_inicial AFTER INSERT ON processo
        FOR EACH ROW EXECUTE FUNCTION lupa_responsavel_inicial()
    """)


def downgrade() -> None:
    """Remove os vínculos de responsabilidade compartilhada."""
    op.execute("DROP TRIGGER processo_responsavel_inicial ON processo")
    op.execute("DROP FUNCTION lupa_responsavel_inicial()")
    op.execute("DROP TABLE processo_responsavel")
    op.execute("ALTER TABLE usuario DROP CONSTRAINT uq_usuario_id_gabinete_id")
