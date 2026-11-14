"""Revisão 0001 do Data Vault, escrita e revisada à mão: tabelas, índices, triggers, views e papel.

O arquivo `versions/v0001_data_vault.py` reexporta `upgrade` e `downgrade` daqui para o código
ficar no pacote (medido pela cobertura). O teste `test_migracao_coincide_com_tabelas` compara o
resultado com `lupa_pipeline.dominio.tabelas` pelo autogenerate do Alembic. Os `CHECK` de enum são
gerados dos enums do domínio; mudar um enum muda esta revisão (D18).
"""

from typing import Any

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import BYTEA, JSONB, UUID

from lupa_pipeline.dominio.enums import (
    CenarioArquivo,
    ClasseProcessual,
    EstadoJob,
    EstadoLote,
    MetodoClassificacao,
    MotivoFalha,
    MotivoQuarentena,
    OrigemPeca,
    PapelMensagem,
    PapelUsuario,
    Polo,
    QualidadeParte,
    ResultadoAchado,
    ResultadoChamada,
    StatusFato,
    StatusMensagem,
    StatusProcesso,
    TipoFato,
    TipoPagina,
    TipoPeca,
)
from lupa_pipeline.dominio.tabelas import checar_enum, checar_valores

PAPEL_APLICACAO = "lupa_app"
TABELAS: list[str] = []


def _hk(nome: str, alvo: str | None = None, *, nulo: bool = False) -> sa.Column[Any]:
    chave = [sa.ForeignKey(alvo)] if alvo else []
    return sa.Column(nome, BYTEA(), *chave, nullable=nulo)


def _texto(nome: str, *, nulo: bool = False) -> sa.Column[Any]:
    return sa.Column(nome, sa.Text(), nullable=nulo)


def _inteiro(nome: str, *, nulo: bool = False) -> sa.Column[Any]:
    return sa.Column(nome, sa.Integer(), nullable=nulo)


def _grande(nome: str, *, nulo: bool = False) -> sa.Column[Any]:
    return sa.Column(nome, sa.BigInteger(), nullable=nulo)


def _booleano(nome: str) -> sa.Column[Any]:
    return sa.Column(nome, sa.Boolean(), nullable=False)


def _instante(nome: str, *, nulo: bool = False) -> sa.Column[Any]:
    return sa.Column(nome, sa.DateTime(timezone=True), nullable=nulo)


def _json(nome: str, *, nulo: bool = False) -> sa.Column[Any]:
    return sa.Column(nome, JSONB, nullable=nulo)


def _usuario(*, nulo: bool = False) -> sa.Column[Any]:
    return _hk("hk_usuario", "hub_usuario.hk_usuario", nulo=nulo)


def _confianca() -> list[Any]:
    return [
        sa.Column("confianca", sa.Double(), nullable=False),
        sa.CheckConstraint("confianca BETWEEN 0 AND 1", name="confianca_intervalo"),
    ]


def _tecnicas() -> list[sa.Column[Any]]:
    return [
        sa.Column(
            "load_dts",
            sa.DateTime(timezone=True),
            server_default=sa.text("clock_timestamp()"),
            nullable=False,
        ),
        _texto("record_source"),
    ]


def _criar(nome: str, *itens: Any) -> None:
    colunas = [i.name for i in itens if isinstance(i, sa.Column) and i.name.startswith("hk_")]
    tamanhos = [
        sa.CheckConstraint(f"octet_length({coluna}) = 32", name=f"{coluna}_tamanho")
        for coluna in colunas
    ]
    op.create_table(nome, *itens, *tamanhos)
    TABELAS.append(nome)


def _hub(entidade: str, *chave: Any) -> None:
    colunas = [item.name for item in chave if isinstance(item, sa.Column)]
    _criar(
        f"hub_{entidade}",
        sa.Column(f"hk_{entidade}", BYTEA(), primary_key=True),
        *chave,
        *_tecnicas(),
        sa.UniqueConstraint(*colunas),
    )


def _link(nome: str, hk: str, *hubs: tuple[str, str]) -> None:
    colunas = [coluna for coluna, _ in hubs]
    _criar(
        nome,
        sa.Column(hk, BYTEA(), primary_key=True),
        *(_hk(coluna, f"{alvo}.{coluna}") for coluna, alvo in hubs),
        *_tecnicas(),
        sa.UniqueConstraint(*colunas),
    )
    for coluna in colunas:
        op.create_index(f"ix_{nome}_{coluna}", nome, [coluna])


def _sat(nome: str, pai: str, alvo: str, *atributos: Any, multiativo: str | None = None) -> None:
    chave = [pai, *([multiativo] if multiativo else []), "load_dts"]
    _criar(
        nome,
        _hk(pai, f"{alvo}.{pai}"),
        *_tecnicas(),
        sa.Column("hash_diff", BYTEA(), nullable=False),
        *atributos,
        sa.PrimaryKeyConstraint(*chave),
    )


PROCESSO = ("hk_processo", "hub_processo")
ARQUIVO = ("hk_arquivo", "hub_arquivo")
PAGINA = ("hk_pagina", "hub_pagina")
PECA = ("hk_peca", "hub_peca")
EVIDENCIA = ("hk_evidencia", "hub_evidencia")
FATO = ("hk_fato", "hub_fato")
ACHADO = ("hk_achado", "hub_achado")
PARTE = ("hk_parte", "hub_parte")
USUARIO = ("hk_usuario", "hub_usuario")
CONVERSA = ("hk_conversa", "hub_conversa")
SESSAO = ("hk_sessao", "hub_sessao")
DESAFIO = ("hk_desafio_mfa", "hub_desafio_mfa")
CHAVE_LOGIN = ("hk_chave_login", "hub_chave_login")


def _criar_hubs() -> None:
    _hub("usuario", _texto("nome_usuario"))
    _hub("processo", _texto("numero_cnj"))
    _hub("arquivo", _texto("numero_cnj"), _texto("sha256"))
    _hub("pagina", _texto("numero_cnj"), _texto("sha256"), _inteiro("numero"))
    _hub("peca", _texto("numero_cnj"), _texto("sha256"), _inteiro("pagina_inicial"))
    _hub(
        "evidencia",
        _texto("numero_cnj"),
        _texto("sha256"),
        _inteiro("numero"),
        _inteiro("inicio"),
        _inteiro("fim"),
        sa.CheckConstraint("inicio >= 0 AND fim > inicio", name="offsets_validos"),
    )
    _hub(
        "fato",
        _texto("numero_cnj"),
        _texto("tipo"),
        _texto("sujeito"),
        _hk("hk_evidencia_origem", "hub_evidencia.hk_evidencia"),
        checar_enum("tipo", TipoFato),
    )
    _hub("achado", _texto("numero_cnj"), _texto("validacao"), _texto("sujeito"))
    _hub("parte", _texto("numero_cnj"), _hk("chave_nome"))
    _hub("conversa", sa.Column("conversa_id", UUID(as_uuid=True), nullable=False))
    _hub("sessao", _texto("token_sha256"))
    _hub("desafio_mfa", _texto("token_sha256"))
    _hub("chave_login", _texto("chave"))


def _criar_links() -> None:
    _link("link_processo_arquivo", "hk_processo_arquivo", PROCESSO, ARQUIVO)
    _link("link_arquivo_pagina", "hk_arquivo_pagina", ARQUIVO, PAGINA)
    _link("link_arquivo_peca", "hk_arquivo_peca", ARQUIVO, PECA)
    _link("link_pagina_evidencia", "hk_pagina_evidencia", PAGINA, EVIDENCIA)
    _link("link_processo_fato", "hk_processo_fato", PROCESSO, FATO)
    _link("link_fato_evidencia", "hk_fato_evidencia", FATO, EVIDENCIA)
    _link("link_processo_achado", "hk_processo_achado", PROCESSO, ACHADO)
    _link("link_achado_fato", "hk_achado_fato", ACHADO, FATO)
    _link("link_processo_parte", "hk_processo_parte", PROCESSO, PARTE)
    _link("link_processo_responsavel", "hk_processo_responsavel", PROCESSO, USUARIO)
    _link("link_processo_conversa", "hk_processo_conversa", PROCESSO, CONVERSA, USUARIO)
    _link("link_sessao_usuario", "hk_sessao_usuario", SESSAO, USUARIO)
    _link("link_desafio_mfa_usuario", "hk_desafio_mfa_usuario", DESAFIO, USUARIO)


def _criar_links_nao_historizados() -> None:
    _criar(
        "link_chamada_modelo",
        sa.Column("hk_chamada", BYTEA(), primary_key=True),
        _hk("hk_processo", "hub_processo.hk_processo"),
        _hk("hk_conversa", "hub_conversa.hk_conversa", nulo=True),
        *_tecnicas(),
        _texto("modelo"),
        _texto("versao_prompt"),
        _texto("hash_prompt_sistema"),
        _texto("hash_entrada"),
        _texto("hash_saida"),
        _inteiro("tokens_entrada"),
        _inteiro("tokens_saida"),
        _inteiro("latencia_ms"),
        sa.Column("ferramentas", sa.ARRAY(sa.Text()), nullable=False),
        _texto("resultado"),
        checar_enum("resultado", ResultadoChamada),
    )
    op.create_index(
        "ix_link_chamada_modelo_hk_processo_load_dts",
        "link_chamada_modelo",
        ["hk_processo", "load_dts"],
    )
    op.create_index("ix_link_chamada_modelo_hk_conversa", "link_chamada_modelo", ["hk_conversa"])
    _criar(
        "link_evento_auditoria",
        sa.Column("hk_evento", BYTEA(), primary_key=True),
        sa.Column("sequencia", sa.BigInteger(), nullable=False),
        _instante("ocorrido_em"),
        _usuario(nulo=True),
        _hk("hk_processo", "hub_processo.hk_processo", nulo=True),
        *_tecnicas(),
        _texto("acao"),
        _texto("objeto_tipo", nulo=True),
        _texto("objeto_id", nulo=True),
        _texto("ip", nulo=True),
        _texto("localizacao", nulo=True),
        _texto("resultado"),
        _texto("versao_modelo", nulo=True),
        _texto("versao_prompt", nulo=True),
        _texto("hash_anterior", nulo=True),
        _texto("hash_evento"),
        sa.UniqueConstraint("sequencia"),
    )
    for colunas in (
        ["ocorrido_em"],
        ["hk_usuario", "ocorrido_em"],
        ["hk_processo", "ocorrido_em"],
        ["acao", "ocorrido_em"],
        ["ip", "ocorrido_em"],
    ):
        nome = "ix_link_evento_auditoria_" + "_".join(colunas)
        op.create_index(nome, "link_evento_auditoria", colunas)


def _criar_satelites_acesso() -> None:
    _sat(
        "sat_usuario_cadastro",
        *USUARIO,
        _texto("papel"),
        _booleano("ativo"),
        checar_enum("papel", PapelUsuario),
    )
    _sat(
        "sat_usuario_credencial",
        *USUARIO,
        _texto("senha_hash"),
        _booleano("troca_senha_obrigatoria"),
        _texto("mfa_segredo", nulo=True),
        _booleano("mfa_confirmado"),
        _grande("mfa_ultimo_passo", nulo=True),
    )
    _sat(
        "sat_sessao_estado",
        *SESSAO,
        _texto("papel"),
        _instante("expira_em"),
        _instante("ultimo_acesso_em"),
        _booleano("revogada"),
        _texto("ip_criacao", nulo=True),
        checar_enum("papel", PapelUsuario),
    )
    _sat(
        "sat_desafio_mfa_estado",
        *DESAFIO,
        _texto("papel"),
        _instante("expira_em"),
        _booleano("consumido"),
        checar_enum("papel", PapelUsuario),
    )
    _sat("sat_chave_login_falha", *CHAVE_LOGIN)
    _sat("sat_chave_login_bloqueio", *CHAVE_LOGIN, _instante("bloqueado_ate", nulo=True))


def _criar_satelites_processo() -> None:
    _sat(
        "sat_processo_dados",
        *PROCESSO,
        _texto("classe"),
        _usuario(),
        checar_enum("classe", ClasseProcessual),
    )
    _sat("sat_processo_estado", *PROCESSO, _texto("status"), checar_enum("status", StatusProcesso))
    _sat("sat_processo_chave", *PROCESSO, _texto("chave_dados_cifrada"))
    _sat(
        "sat_processo_revisao",
        *PROCESSO,
        _texto("situacao"),
        _texto("motivo"),
        _texto("status_anterior"),
        _usuario(nulo=True),
        checar_valores("situacao", ("aberta", "liberada")),
    )
    _sat(
        "sat_processo_responsavel_vigencia",
        "hk_processo_responsavel",
        "link_processo_responsavel",
        _booleano("vigente"),
    )


def _criar_satelites_arquivo() -> None:
    _sat(
        "sat_arquivo_dados",
        *ARQUIVO,
        _inteiro("tamanho_bytes"),
        _texto("nome_original"),
        _texto("mime"),
        _texto("chave_storage"),
        _usuario(),
        sa.CheckConstraint("tamanho_bytes > 0", name="tamanho_positivo"),
    )
    _sat(
        "sat_arquivo_ingestao",
        *ARQUIVO,
        _texto("estado"),
        _texto("motivo_quarentena", nulo=True),
        _texto("motivo_falha", nulo=True),
        _inteiro("tentativas"),
        _inteiro("total_paginas", nulo=True),
        _json("manifesto", nulo=True),
        _json("relatorio", nulo=True),
        _texto("versao_extrator", nulo=True),
        checar_enum("estado", EstadoJob),
        checar_enum("motivo_quarentena", MotivoQuarentena),
        checar_enum("motivo_falha", MotivoFalha),
        sa.CheckConstraint(
            "(estado = 'quarentena') = (motivo_quarentena IS NOT NULL)",
            name="quarentena_com_motivo",
        ),
    )
    op.create_index(
        "ix_sat_arquivo_ingestao_estado_load_dts", "sat_arquivo_ingestao", ["estado", "load_dts"]
    )
    _sat(
        "sat_arquivo_lote",
        *ARQUIVO,
        _inteiro("numero"),
        _texto("estado"),
        _json("resultado"),
        checar_enum("estado", EstadoLote),
        multiativo="numero",
    )
    _sat(
        "sat_arquivo_diagnostico",
        *ARQUIVO,
        _texto("cenario"),
        _inteiro("total_paginas"),
        _booleano("tem_indice"),
        _json("sinais"),
        _json("fronteiras_origem"),
        _json("metadados_descartados"),
        checar_enum("cenario", CenarioArquivo),
        sa.CheckConstraint("total_paginas >= 0", name="paginas_nao_negativas"),
    )


def _criar_satelites_pagina() -> None:
    _sat(
        "sat_pagina_extracao",
        *PAGINA,
        _texto("tipo"),
        _texto("texto"),
        _texto("hash_texto"),
        _texto("texto_nativo", nulo=True),
        _texto("texto_ocr", nulo=True),
        _json("coordenadas"),
        _json("sinais"),
        _json("extracao"),
        _texto("versao_extrator", nulo=True),
        _texto("origem_arquivo", nulo=True),
        _inteiro("pagina_origem", nulo=True),
        checar_enum("tipo", TipoPagina),
    )
    _sat(
        "sat_pagina_saneamento",
        *PAGINA,
        _texto("texto_normalizado", nulo=True),
        _json("flags"),
        _texto("trechos_ocultos"),
        _texto("trechos_suspeitos"),
    )
    _sat("sat_pagina_fronteira", *PAGINA, _json("sinais_fronteira"))
    _sat(
        "sat_peca_classificacao",
        *PECA,
        _texto("tipo"),
        _inteiro("pagina_final"),
        *_confianca(),
        _texto("metodo"),
        _texto("origem"),
        sa.Column("data", sa.Date(), nullable=True),
        _texto("tipo_data", nulo=True),
        _hk("hk_evidencia_data", "hub_evidencia.hk_evidencia", nulo=True),
        _json("flags"),
        _json("classificacao"),
        _booleano("vigente"),
        _usuario(nulo=True),
        checar_enum("tipo", TipoPeca),
        checar_enum("metodo", MetodoClassificacao),
        checar_enum("origem", OrigemPeca),
        checar_valores("tipo_data", ("assinatura", "protocolo", "juntada")),
    )
    _sat(
        "sat_evidencia_trecho",
        *EVIDENCIA,
        _texto("trecho"),
        _texto("hash_trecho"),
        _json("bbox", nulo=True),
    )


def _criar_satelites_analise() -> None:
    _sat(
        "sat_fato_valor",
        *FATO,
        _texto("valor"),
        _texto("extraido_por"),
        _texto("versao_extrator"),
        *_confianca(),
        _texto("status"),
        _usuario(nulo=True),
        checar_enum("status", StatusFato),
    )
    _sat("sat_fato_anotacao", *FATO, _texto("texto"), _usuario())
    _sat(
        "sat_fato_evidencia_vigencia",
        "hk_fato_evidencia",
        "link_fato_evidencia",
        _booleano("vigente"),
    )
    _sat(
        "sat_achado_resultado",
        *ACHADO,
        _texto("versao_catalogo"),
        _texto("resultado"),
        sa.Column("fatos_usados", sa.ARRAY(BYTEA()), nullable=False),
        _texto("valores"),
        _texto("explicacao"),
        checar_enum("resultado", ResultadoAchado),
    )
    _sat("sat_achado_anotacao", *ACHADO, _texto("texto"), _usuario())
    _sat(
        "sat_parte_identidade",
        *PARTE,
        _texto("nome"),
        _texto("polo"),
        _texto("qualidade"),
        _hk("hk_evidencia", "hub_evidencia.hk_evidencia"),
        checar_enum("polo", Polo),
        checar_enum("qualidade", QualidadeParte),
    )


def _criar_satelites_conversa() -> None:
    _sat(
        "sat_conversa_estado",
        *CONVERSA,
        _booleano("encerrada"),
        _texto("motivo_encerramento", nulo=True),
        _grande("tokens_entrada"),
        _grande("tokens_saida"),
        _inteiro("paginas_originais"),
        _inteiro("citacoes_descartadas"),
    )
    _sat(
        "sat_conversa_mensagem",
        *CONVERSA,
        _inteiro("sequencia"),
        _texto("papel"),
        _texto("status"),
        _texto("texto"),
        _json("citacoes"),
        _json("avisos"),
        checar_enum("papel", PapelMensagem),
        checar_enum("status", StatusMensagem),
        multiativo="sequencia",
    )


SQL_FUNCOES = """
CREATE FUNCTION lupa_bloquear_alteracao() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF TG_OP = 'DELETE' AND TG_TABLE_NAME LIKE 'sat\\_%'
       AND current_setting('lupa.descarte', true) = 'on' THEN
        RETURN OLD;
    END IF;
    RAISE EXCEPTION 'tabela % é imutável: % bloqueado', TG_TABLE_NAME, TG_OP
        USING ERRCODE = 'restrict_violation';
END;
$$;

CREATE FUNCTION lupa_fato_exige_evidencia() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM link_fato_evidencia WHERE hk_fato = NEW.hk_fato) THEN
        RAISE EXCEPTION 'fato % sem evidência', encode(NEW.hk_fato, 'hex')
            USING ERRCODE = 'check_violation';
    END IF;
    RETURN NULL;
END;
$$;

CREATE CONSTRAINT TRIGGER fato_exige_evidencia AFTER INSERT ON hub_fato
    DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION lupa_fato_exige_evidencia();
"""

SQL_DESCARTE = """
CREATE FUNCTION lupa_descartar_processo(p_hk_processo BYTEA) RETURNS TEXT
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public, pg_temp AS $$
DECLARE
    v_arquivos BYTEA[];
    v_paginas BYTEA[];
    v_pecas BYTEA[];
    v_evidencias BYTEA[];
    v_fatos BYTEA[];
    v_achados BYTEA[];
    v_partes BYTEA[];
    v_conversas BYTEA[];
    v_chave TEXT;
BEGIN
    PERFORM set_config('lupa.descarte', 'on', true);
    SELECT coalesce(array_agg(hk_arquivo), '{}') INTO v_arquivos
        FROM link_processo_arquivo WHERE hk_processo = p_hk_processo;
    SELECT coalesce(array_agg(hk_pagina), '{}') INTO v_paginas
        FROM link_arquivo_pagina WHERE hk_arquivo = ANY (v_arquivos);
    SELECT coalesce(array_agg(hk_peca), '{}') INTO v_pecas
        FROM link_arquivo_peca WHERE hk_arquivo = ANY (v_arquivos);
    SELECT coalesce(array_agg(hk_evidencia), '{}') INTO v_evidencias
        FROM link_pagina_evidencia WHERE hk_pagina = ANY (v_paginas);
    SELECT coalesce(array_agg(hk_fato), '{}') INTO v_fatos
        FROM link_processo_fato WHERE hk_processo = p_hk_processo;
    SELECT coalesce(array_agg(hk_achado), '{}') INTO v_achados
        FROM link_processo_achado WHERE hk_processo = p_hk_processo;
    SELECT coalesce(array_agg(hk_parte), '{}') INTO v_partes
        FROM link_processo_parte WHERE hk_processo = p_hk_processo;
    SELECT coalesce(array_agg(hk_conversa), '{}') INTO v_conversas
        FROM link_processo_conversa WHERE hk_processo = p_hk_processo;

    DELETE FROM sat_arquivo_dados WHERE hk_arquivo = ANY (v_arquivos);
    DELETE FROM sat_arquivo_ingestao WHERE hk_arquivo = ANY (v_arquivos);
    DELETE FROM sat_arquivo_lote WHERE hk_arquivo = ANY (v_arquivos);
    DELETE FROM sat_arquivo_diagnostico WHERE hk_arquivo = ANY (v_arquivos);
    DELETE FROM sat_pagina_extracao WHERE hk_pagina = ANY (v_paginas);
    DELETE FROM sat_pagina_saneamento WHERE hk_pagina = ANY (v_paginas);
    DELETE FROM sat_pagina_fronteira WHERE hk_pagina = ANY (v_paginas);
    DELETE FROM sat_peca_classificacao WHERE hk_peca = ANY (v_pecas);
    DELETE FROM sat_evidencia_trecho WHERE hk_evidencia = ANY (v_evidencias);
    DELETE FROM sat_fato_valor WHERE hk_fato = ANY (v_fatos);
    DELETE FROM sat_fato_anotacao WHERE hk_fato = ANY (v_fatos);
    DELETE FROM sat_fato_evidencia_vigencia WHERE hk_fato_evidencia IN (
        SELECT hk_fato_evidencia FROM link_fato_evidencia WHERE hk_fato = ANY (v_fatos));
    DELETE FROM sat_achado_resultado WHERE hk_achado = ANY (v_achados);
    DELETE FROM sat_achado_anotacao WHERE hk_achado = ANY (v_achados);
    DELETE FROM sat_parte_identidade WHERE hk_parte = ANY (v_partes);
    DELETE FROM sat_conversa_estado WHERE hk_conversa = ANY (v_conversas);
    DELETE FROM sat_conversa_mensagem WHERE hk_conversa = ANY (v_conversas);
    DELETE FROM sat_processo_revisao WHERE hk_processo = p_hk_processo;

    SELECT chave_dados_cifrada INTO v_chave FROM sat_processo_chave
        WHERE hk_processo = p_hk_processo ORDER BY load_dts DESC LIMIT 1;
    DELETE FROM sat_processo_chave WHERE hk_processo = p_hk_processo;
    IF v_chave IS NULL THEN
        RETURN NULL;
    END IF;
    RETURN encode(sha256(convert_to(v_chave, 'UTF8')), 'hex');
END;
$$;
"""


VISOES_POR_HUB = {
    "v_usuario": """
SELECT encode(h.hk_usuario, 'hex') AS id, h.hk_usuario, h.nome_usuario, h.load_dts AS criado_em,
       c.papel, c.ativo, k.senha_hash, k.troca_senha_obrigatoria, k.mfa_segredo,
       k.mfa_confirmado, k.mfa_ultimo_passo
FROM hub_usuario h
LEFT JOIN LATERAL (
    SELECT papel, ativo
    FROM sat_usuario_cadastro s
    WHERE s.hk_usuario = h.hk_usuario
    ORDER BY s.load_dts DESC LIMIT 1
) c ON true
LEFT JOIN LATERAL (
    SELECT senha_hash, troca_senha_obrigatoria, mfa_segredo, mfa_confirmado, mfa_ultimo_passo
    FROM sat_usuario_credencial s
    WHERE s.hk_usuario = h.hk_usuario
    ORDER BY s.load_dts DESC LIMIT 1
) k ON true
""",
    "v_processo": """
SELECT encode(h.hk_processo, 'hex') AS id, h.hk_processo, h.numero_cnj, h.load_dts AS criado_em,
       d.classe, d.hk_usuario AS hk_criador, encode(d.hk_usuario, 'hex') AS criador_id,
       e.status, k.chave_dados_cifrada, coalesce(r.situacao = 'aberta', false) AS em_revisao
FROM hub_processo h
LEFT JOIN LATERAL (
    SELECT classe, hk_usuario
    FROM sat_processo_dados s
    WHERE s.hk_processo = h.hk_processo
    ORDER BY s.load_dts DESC LIMIT 1
) d ON true
LEFT JOIN LATERAL (
    SELECT status
    FROM sat_processo_estado s
    WHERE s.hk_processo = h.hk_processo
    ORDER BY s.load_dts DESC LIMIT 1
) e ON true
LEFT JOIN LATERAL (
    SELECT chave_dados_cifrada
    FROM sat_processo_chave s
    WHERE s.hk_processo = h.hk_processo
    ORDER BY s.load_dts DESC LIMIT 1
) k ON true
LEFT JOIN LATERAL (
    SELECT situacao
    FROM sat_processo_revisao s
    WHERE s.hk_processo = h.hk_processo
    ORDER BY s.load_dts DESC LIMIT 1
) r ON true
""",
    "v_arquivo": """
SELECT encode(h.hk_arquivo, 'hex') AS id, h.hk_arquivo, h.numero_cnj, h.sha256,
       h.load_dts AS criado_em, l.hk_processo, encode(l.hk_processo, 'hex') AS processo_id,
       d.tamanho_bytes, d.nome_original, d.mime, d.chave_storage,
       d.hk_usuario AS hk_enviado_por, i.estado, i.motivo_quarentena, i.motivo_falha,
       i.tentativas, i.total_paginas, i.manifesto, i.relatorio, i.versao_extrator,
       i.load_dts AS estado_em, g.cenario, g.total_paginas AS total_paginas_diagnostico,
       g.tem_indice, g.sinais, g.fronteiras_origem, g.metadados_descartados
FROM hub_arquivo h
JOIN link_processo_arquivo l ON l.hk_arquivo = h.hk_arquivo
LEFT JOIN LATERAL (
    SELECT tamanho_bytes, nome_original, mime, chave_storage, hk_usuario
    FROM sat_arquivo_dados s
    WHERE s.hk_arquivo = h.hk_arquivo
    ORDER BY s.load_dts DESC LIMIT 1
) d ON true
LEFT JOIN LATERAL (
    SELECT estado, motivo_quarentena, motivo_falha, tentativas, total_paginas, manifesto,
           relatorio, versao_extrator, load_dts
    FROM sat_arquivo_ingestao s
    WHERE s.hk_arquivo = h.hk_arquivo
    ORDER BY s.load_dts DESC LIMIT 1
) i ON true
LEFT JOIN LATERAL (
    SELECT cenario, total_paginas, tem_indice, sinais, fronteiras_origem, metadados_descartados
    FROM sat_arquivo_diagnostico s
    WHERE s.hk_arquivo = h.hk_arquivo
    ORDER BY s.load_dts DESC LIMIT 1
) g ON true
""",
    "v_pagina": """
SELECT encode(h.hk_pagina, 'hex') AS id, h.hk_pagina, h.numero_cnj, h.sha256, h.numero,
       l.hk_arquivo, encode(l.hk_arquivo, 'hex') AS arquivo_id, p.hk_processo,
       encode(p.hk_processo, 'hex') AS processo_id, x.tipo, x.texto, x.hash_texto,
       x.texto_nativo, x.texto_ocr, x.coordenadas, x.sinais, x.extracao, x.versao_extrator,
       x.origem_arquivo, x.pagina_origem, x.load_dts AS extraida_em, s.texto_normalizado,
       s.flags, s.trechos_ocultos, s.trechos_suspeitos, f.sinais_fronteira
FROM hub_pagina h
JOIN link_arquivo_pagina l ON l.hk_pagina = h.hk_pagina
JOIN link_processo_arquivo p ON p.hk_arquivo = l.hk_arquivo
LEFT JOIN LATERAL (
    SELECT tipo, texto, hash_texto, texto_nativo, texto_ocr, coordenadas, sinais, extracao,
           versao_extrator, origem_arquivo, pagina_origem, load_dts
    FROM sat_pagina_extracao s
    WHERE s.hk_pagina = h.hk_pagina
    ORDER BY s.load_dts DESC LIMIT 1
) x ON true
LEFT JOIN LATERAL (
    SELECT texto_normalizado, flags, trechos_ocultos, trechos_suspeitos
    FROM sat_pagina_saneamento s
    WHERE s.hk_pagina = h.hk_pagina
    ORDER BY s.load_dts DESC LIMIT 1
) s ON true
LEFT JOIN LATERAL (
    SELECT sinais_fronteira
    FROM sat_pagina_fronteira s
    WHERE s.hk_pagina = h.hk_pagina
    ORDER BY s.load_dts DESC LIMIT 1
) f ON true
""",
    "v_peca": """
SELECT encode(h.hk_peca, 'hex') AS id, h.hk_peca, h.numero_cnj, h.sha256, h.pagina_inicial,
       l.hk_arquivo, encode(l.hk_arquivo, 'hex') AS arquivo_id, p.hk_processo,
       encode(p.hk_processo, 'hex') AS processo_id, c.tipo, c.pagina_final, c.confianca,
       c.metodo, c.origem, c.data, c.tipo_data, c.hk_evidencia_data, c.flags, c.classificacao,
       c.vigente, c.hk_usuario, c.load_dts AS classificada_em
FROM hub_peca h
JOIN link_arquivo_peca l ON l.hk_peca = h.hk_peca
JOIN link_processo_arquivo p ON p.hk_arquivo = l.hk_arquivo
LEFT JOIN LATERAL (
    SELECT tipo, pagina_final, confianca, metodo, origem, data, tipo_data, hk_evidencia_data,
           flags, classificacao, vigente, hk_usuario, load_dts
    FROM sat_peca_classificacao s
    WHERE s.hk_peca = h.hk_peca
    ORDER BY s.load_dts DESC LIMIT 1
) c ON true
""",
    "v_evidencia": """
SELECT encode(h.hk_evidencia, 'hex') AS id, h.hk_evidencia, h.numero_cnj, h.sha256, h.numero,
       h.inicio, h.fim, l.hk_pagina, encode(l.hk_pagina, 'hex') AS pagina_id, p.hk_processo,
       encode(p.hk_processo, 'hex') AS processo_id, t.trecho, t.hash_trecho, t.bbox
FROM hub_evidencia h
JOIN link_pagina_evidencia l ON l.hk_evidencia = h.hk_evidencia
JOIN link_arquivo_pagina a ON a.hk_pagina = l.hk_pagina
JOIN link_processo_arquivo p ON p.hk_arquivo = a.hk_arquivo
LEFT JOIN LATERAL (
    SELECT trecho, hash_trecho, bbox
    FROM sat_evidencia_trecho s
    WHERE s.hk_evidencia = h.hk_evidencia
    ORDER BY s.load_dts DESC LIMIT 1
) t ON true
""",
    "v_fato": """
SELECT encode(h.hk_fato, 'hex') AS id, h.hk_fato, h.numero_cnj, h.tipo, h.sujeito,
       h.hk_evidencia_origem, l.hk_processo, encode(l.hk_processo, 'hex') AS processo_id,
       v.valor, v.extraido_por, v.versao_extrator, v.confianca, v.status, v.hk_usuario,
       v.load_dts AS atualizado_em,
       EXISTS (
           SELECT 1 FROM link_fato_evidencia e
           LEFT JOIN LATERAL (
               SELECT vigente
               FROM sat_fato_evidencia_vigencia s
               WHERE s.hk_fato_evidencia = e.hk_fato_evidencia
               ORDER BY s.load_dts DESC LIMIT 1
           ) g ON true
           WHERE e.hk_fato = h.hk_fato AND g.vigente
       ) AS vigente
FROM hub_fato h
JOIN link_processo_fato l ON l.hk_fato = h.hk_fato
LEFT JOIN LATERAL (
    SELECT valor, extraido_por, versao_extrator, confianca, status, hk_usuario, load_dts
    FROM sat_fato_valor s
    WHERE s.hk_fato = h.hk_fato
    ORDER BY s.load_dts DESC LIMIT 1
) v ON true
""",
    "v_achado": """
SELECT encode(h.hk_achado, 'hex') AS id, h.hk_achado, h.numero_cnj, h.validacao, h.sujeito,
       l.hk_processo, encode(l.hk_processo, 'hex') AS processo_id, r.versao_catalogo,
       r.resultado, r.fatos_usados, r.valores, r.explicacao, r.load_dts AS criado_em
FROM hub_achado h
JOIN link_processo_achado l ON l.hk_achado = h.hk_achado
LEFT JOIN LATERAL (
    SELECT versao_catalogo, resultado, fatos_usados, valores, explicacao, load_dts
    FROM sat_achado_resultado s
    WHERE s.hk_achado = h.hk_achado
    ORDER BY s.load_dts DESC LIMIT 1
) r ON true
""",
    "v_parte": """
SELECT encode(h.hk_parte, 'hex') AS id, h.hk_parte, h.numero_cnj, h.chave_nome, l.hk_processo,
       encode(l.hk_processo, 'hex') AS processo_id, i.nome, i.polo, i.qualidade, i.hk_evidencia,
       encode(i.hk_evidencia, 'hex') AS evidencia_id
FROM hub_parte h
JOIN link_processo_parte l ON l.hk_parte = h.hk_parte
LEFT JOIN LATERAL (
    SELECT nome, polo, qualidade, hk_evidencia
    FROM sat_parte_identidade s
    WHERE s.hk_parte = h.hk_parte
    ORDER BY s.load_dts DESC LIMIT 1
) i ON true
""",
    "v_conversa": """
SELECT encode(h.hk_conversa, 'hex') AS id, h.hk_conversa, h.conversa_id,
       h.load_dts AS criada_em,
       l.hk_processo, encode(l.hk_processo, 'hex') AS processo_id, l.hk_usuario,
       encode(l.hk_usuario, 'hex') AS usuario_id, e.encerrada, e.motivo_encerramento,
       e.tokens_entrada, e.tokens_saida, e.paginas_originais, e.citacoes_descartadas
FROM hub_conversa h
JOIN link_processo_conversa l ON l.hk_conversa = h.hk_conversa
LEFT JOIN LATERAL (
    SELECT encerrada, motivo_encerramento, tokens_entrada, tokens_saida, paginas_originais,
           citacoes_descartadas
    FROM sat_conversa_estado s
    WHERE s.hk_conversa = h.hk_conversa
    ORDER BY s.load_dts DESC LIMIT 1
) e ON true
""",
    "v_sessao": """
SELECT encode(h.hk_sessao, 'hex') AS id, h.hk_sessao, h.token_sha256, h.load_dts AS criada_em,
       l.hk_usuario, encode(l.hk_usuario, 'hex') AS usuario_id, e.papel, e.expira_em,
       e.ultimo_acesso_em, e.revogada, e.ip_criacao, e.load_dts AS atualizada_em
FROM hub_sessao h
JOIN link_sessao_usuario l ON l.hk_sessao = h.hk_sessao
LEFT JOIN LATERAL (
    SELECT papel, expira_em, ultimo_acesso_em, revogada, ip_criacao, load_dts
    FROM sat_sessao_estado s
    WHERE s.hk_sessao = h.hk_sessao
    ORDER BY s.load_dts DESC LIMIT 1
) e ON true
""",
    "v_desafio_mfa": """
SELECT encode(h.hk_desafio_mfa, 'hex') AS id, h.hk_desafio_mfa, h.token_sha256,
       h.load_dts AS criado_em, l.hk_usuario, encode(l.hk_usuario, 'hex') AS usuario_id,
       e.papel, e.expira_em, e.consumido
FROM hub_desafio_mfa h
JOIN link_desafio_mfa_usuario l ON l.hk_desafio_mfa = h.hk_desafio_mfa
LEFT JOIN LATERAL (
    SELECT papel, expira_em, consumido
    FROM sat_desafio_mfa_estado s
    WHERE s.hk_desafio_mfa = h.hk_desafio_mfa
    ORDER BY s.load_dts DESC LIMIT 1
) e ON true
""",
    "v_bloqueio_login": """
SELECT h.hk_chave_login, h.chave, b.bloqueado_ate, z.zerado_em,
       coalesce((
           SELECT array_agg(f.load_dts ORDER BY f.load_dts) FROM sat_chave_login_falha f
           WHERE f.hk_chave_login = h.hk_chave_login
             AND (z.zerado_em IS NULL OR f.load_dts > z.zerado_em)
       ), '{}') AS falhas
FROM hub_chave_login h
LEFT JOIN LATERAL (
    SELECT bloqueado_ate
    FROM sat_chave_login_bloqueio s
    WHERE s.hk_chave_login = h.hk_chave_login
    ORDER BY s.load_dts DESC LIMIT 1
) b ON true
LEFT JOIN LATERAL (
    SELECT max(s.load_dts) AS zerado_em FROM sat_chave_login_bloqueio s
    WHERE s.hk_chave_login = h.hk_chave_login AND s.bloqueado_ate IS NULL
) z ON true
""",
}

VISOES_DE_HISTORICO = {
    "v_peca_historico": """
SELECT encode(s.hk_peca, 'hex') AS peca_id, s.hk_peca, h.pagina_inicial, s.load_dts,
       s.hk_usuario,
       encode(s.hk_usuario, 'hex') AS usuario_id, s.tipo, s.pagina_final, s.confianca, s.metodo,
       s.origem, s.data, s.tipo_data, s.hk_evidencia_data, s.flags, s.classificacao, s.vigente
FROM sat_peca_classificacao s
JOIN hub_peca h ON h.hk_peca = s.hk_peca
""",
    "v_fato_historico": """
SELECT encode(s.hk_fato, 'hex') AS fato_id, s.hk_fato, s.load_dts, s.hk_usuario,
       encode(s.hk_usuario, 'hex') AS usuario_id, s.valor, s.extraido_por, s.versao_extrator,
       s.confianca, s.status
FROM sat_fato_valor s
""",
    "v_mensagem": """
SELECT DISTINCT ON (s.hk_conversa, s.sequencia)
       encode(s.hk_conversa, 'hex') AS conversa_id, s.hk_conversa, s.sequencia, s.papel,
       s.status, s.texto, s.citacoes, s.avisos, s.load_dts AS criada_em
FROM sat_conversa_mensagem s
ORDER BY s.hk_conversa, s.sequencia, s.load_dts DESC
""",
    "v_anotacao": """
SELECT 'fato' AS alvo_tipo, s.hk_fato AS hk_alvo, encode(s.hk_fato, 'hex') AS alvo_id,
       l.hk_processo, encode(l.hk_processo, 'hex') AS processo_id, s.texto, s.hk_usuario,
       encode(s.hk_usuario, 'hex') AS usuario_id, u.nome_usuario, s.load_dts AS criada_em
FROM sat_fato_anotacao s
JOIN link_processo_fato l ON l.hk_fato = s.hk_fato
JOIN hub_usuario u ON u.hk_usuario = s.hk_usuario
UNION ALL
SELECT 'achado', s.hk_achado, encode(s.hk_achado, 'hex') AS alvo_id, l.hk_processo,
       encode(l.hk_processo, 'hex') AS processo_id, s.texto, s.hk_usuario,
       encode(s.hk_usuario, 'hex') AS usuario_id, u.nome_usuario, s.load_dts
FROM sat_achado_anotacao s
JOIN link_processo_achado l ON l.hk_achado = s.hk_achado
JOIN hub_usuario u ON u.hk_usuario = s.hk_usuario
""",
    "v_responsavel": """
SELECT l.hk_processo, encode(l.hk_processo, 'hex') AS processo_id, l.hk_usuario,
       encode(l.hk_usuario, 'hex') AS usuario_id, u.nome_usuario, v.vigente,
       v.load_dts AS atualizado_em
FROM link_processo_responsavel l
JOIN hub_usuario u ON u.hk_usuario = l.hk_usuario
LEFT JOIN LATERAL (
    SELECT vigente, load_dts
    FROM sat_processo_responsavel_vigencia s
    WHERE s.hk_processo_responsavel = l.hk_processo_responsavel
    ORDER BY s.load_dts DESC LIMIT 1
) v ON true
""",
    "v_fila_ingestao": """
SELECT encode(h.hk_arquivo, 'hex') AS id, h.hk_arquivo, l.hk_processo,
       encode(l.hk_processo, 'hex') AS processo_id, i.estado, i.tentativas,
       h.load_dts AS criado_em
FROM hub_arquivo h
JOIN link_processo_arquivo l ON l.hk_arquivo = h.hk_arquivo
LEFT JOIN LATERAL (
    SELECT estado, tentativas
    FROM sat_arquivo_ingestao s
    WHERE s.hk_arquivo = h.hk_arquivo
    ORDER BY s.load_dts DESC LIMIT 1
) i ON true
WHERE i.estado IN ('recebido', 'validado', 'em_extracao')
ORDER BY h.load_dts, h.hk_arquivo
""",
    "v_auditoria": """
SELECT encode(e.hk_evento, 'hex') AS id, e.hk_evento, e.sequencia, e.ocorrido_em, e.hk_usuario,
       encode(e.hk_usuario, 'hex') AS usuario_id, u.nome_usuario, e.hk_processo,
       encode(e.hk_processo, 'hex') AS processo_id, p.numero_cnj, e.acao, e.objeto_tipo,
       e.objeto_id, e.ip, e.localizacao, e.resultado, e.versao_modelo, e.versao_prompt,
       e.hash_anterior, e.hash_evento, e.load_dts
FROM link_evento_auditoria e
LEFT JOIN hub_usuario u ON u.hk_usuario = e.hk_usuario
LEFT JOIN hub_processo p ON p.hk_processo = e.hk_processo
""",
}

VISOES = {**VISOES_POR_HUB, **VISOES_DE_HISTORICO}


def _criar_visoes() -> None:
    for nome, consulta in VISOES.items():
        op.execute(f"CREATE VIEW {nome} AS {consulta}")


def _criar_funcoes_e_triggers() -> None:
    op.execute(SQL_FUNCOES)
    op.execute(SQL_DESCARTE)
    for tabela in TABELAS:
        op.execute(
            f"CREATE TRIGGER {tabela}_imutavel BEFORE UPDATE OR DELETE ON {tabela} "
            "FOR EACH ROW EXECUTE FUNCTION lupa_bloquear_alteracao()"
        )


SQL_PAPEL = """
DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'lupa_app') THEN
        CREATE ROLE lupa_app NOLOGIN;
    END IF;
END $$;
GRANT USAGE ON SCHEMA public TO lupa_app;
REVOKE ALL ON FUNCTION lupa_descartar_processo(BYTEA) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION lupa_descartar_processo(BYTEA) TO lupa_app;
"""


def _criar_papel() -> None:
    op.execute(SQL_PAPEL)
    for tabela in TABELAS:
        op.execute(f"GRANT SELECT, INSERT ON {tabela} TO {PAPEL_APLICACAO}")
    for visao in VISOES:
        op.execute(f"GRANT SELECT ON {visao} TO {PAPEL_APLICACAO}")


def upgrade() -> None:
    """Cria o Data Vault da 0.2: tabelas, índices, triggers, funções, views e permissões."""
    TABELAS.clear()
    _criar_hubs()
    _criar_links()
    _criar_links_nao_historizados()
    _criar_satelites_acesso()
    _criar_satelites_processo()
    _criar_satelites_arquivo()
    _criar_satelites_pagina()
    _criar_satelites_analise()
    _criar_satelites_conversa()
    _criar_funcoes_e_triggers()
    _criar_visoes()
    _criar_papel()


def downgrade() -> None:
    """Remove o Data Vault; o papel `lupa_app` é global ao cluster e permanece."""
    for visao in reversed(list(VISOES)):
        op.execute(f"DROP VIEW {visao}")
    op.execute("DROP FUNCTION lupa_descartar_processo(BYTEA)")
    linhas = op.get_bind().execute(
        sa.text(
            "SELECT tablename FROM pg_tables "
            "WHERE schemaname = 'public' AND tablename ~ '^(hub|link|sat)_'"
        )
    )
    tabelas = ", ".join(linha[0] for linha in linhas)
    op.execute(f"DROP TABLE {tabelas}")
    op.execute("DROP FUNCTION lupa_fato_exige_evidencia()")
    op.execute("DROP FUNCTION lupa_bloquear_alteracao()")
    op.execute(f"REVOKE USAGE ON SCHEMA public FROM {PAPEL_APLICACAO}")
