"""Tabelas do Data Vault 2.0 (hubs, links e satélites); espelham a revisão `v0001_data_vault`.

Convenções (plano da 0.2, "O que muda"): `hk_*` é `BYTEA` de 32 bytes; hub tem a chave de negócio
única; link tem os `hk` dos hubs ligados, únicos em conjunto e com um índice por FK; satélite tem
PK `(hk_<pai>, load_dts)` (mais a subchave, se multiativo), `hash_diff` e `record_source`; toda
tabela tem `load_dts` com `clock_timestamp()` e é imutável (trigger `<tabela>_imutavel`). Colunas
de enum são `TEXT` com `CHECK` gerado do enum. Colunas de JSON guardadas em `TEXT` usam
`JsonTexto`.

O `info` de cada tabela diz o tipo (`hub`, `link`, `satelite`) e o que `gravacao` precisa: as
colunas da chave de negócio do hub, as colunas de hub do link, a coluna do pai, a subchave
multiativa e se o satélite sempre insere.
"""

from enum import StrEnum
from typing import Any

from sqlalchemy import (
    ARRAY,
    BigInteger,
    Boolean,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    Double,
    ForeignKey,
    Index,
    Integer,
    MetaData,
    PrimaryKeyConstraint,
    Table,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import BYTEA, JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.sql.schema import SchemaItem

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
from lupa_pipeline.dominio.tipos import JsonTexto

CONVENCAO_NOMES = {
    "ix": "ix_%(table_name)s_%(column_0_N_name)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_N_name)s",
    "pk": "pk_%(table_name)s",
}
TAMANHO_HK = 32
TIPOS_DATA_PECA = ("assinatura", "protocolo", "juntada")
SITUACOES_REVISAO = ("aberta", "liberada")
COLUNAS_TECNICAS = frozenset({"load_dts", "record_source", "hash_diff"})

metadata = MetaData(naming_convention=CONVENCAO_NOMES)


def checar_enum(coluna: str, enum: type[StrEnum]) -> CheckConstraint:
    """Cria CHECK que restringe a coluna de texto aos valores do enum.

    Args:
        coluna: Nome da coluna.
        enum: Enum com os valores permitidos.

    Returns:
        A constraint nomeada `<coluna>_valido`.
    """
    return checar_valores(coluna, tuple(membro.value for membro in enum))


def checar_valores(coluna: str, valores: tuple[str, ...]) -> CheckConstraint:
    """Cria CHECK que restringe a coluna de texto a uma lista fixa de valores.

    Args:
        coluna: Nome da coluna.
        valores: Valores permitidos.

    Returns:
        A constraint nomeada `<coluna>_valido`.
    """
    lista = ", ".join(f"'{valor}'" for valor in valores)
    return CheckConstraint(f"{coluna} IN ({lista})", name=f"{coluna}_valido")


def _hk(nome: str, alvo: str | None = None, *, nulo: bool = False) -> Column[Any]:
    chave = [ForeignKey(alvo)] if alvo else []
    return Column(nome, BYTEA, *chave, nullable=nulo)


def _texto(nome: str, *, nulo: bool = False) -> Column[Any]:
    return Column(nome, Text, nullable=nulo)


def _inteiro(nome: str, *, nulo: bool = False) -> Column[Any]:
    return Column(nome, Integer, nullable=nulo)


def _grande(nome: str) -> Column[Any]:
    return Column(nome, BigInteger, nullable=False)


def _booleano(nome: str) -> Column[Any]:
    return Column(nome, Boolean, nullable=False)


def _instante(nome: str, *, nulo: bool = False) -> Column[Any]:
    return Column(nome, DateTime(timezone=True), nullable=nulo)


def _json(nome: str, *, nulo: bool = False) -> Column[Any]:
    return Column(nome, JSONB, nullable=nulo)


def _real(nome: str) -> Column[Any]:
    return Column(nome, Double, nullable=False)


def _json_texto(nome: str, *, nulo: bool = False) -> Column[Any]:
    return Column(nome, JsonTexto, nullable=nulo)


def _usuario(nome: str = "hk_usuario", *, nulo: bool = False) -> Column[Any]:
    return _hk(nome, "hub_usuario.hk_usuario", nulo=nulo)


def _confianca() -> list[SchemaItem]:
    return [
        _real("confianca"),
        CheckConstraint("confianca BETWEEN 0 AND 1", name="confianca_intervalo"),
    ]


def _tecnicas() -> list[Column[Any]]:
    return [
        Column(
            "load_dts",
            DateTime(timezone=True),
            nullable=False,
            server_default=text("clock_timestamp()"),
        ),
        _texto("record_source"),
    ]


def _tabela(nome: str, itens: list[SchemaItem], info: dict[str, Any]) -> Table:
    colunas_hk = [i.name for i in itens if isinstance(i, Column) and i.name.startswith("hk_")]
    tamanhos = [
        CheckConstraint(f"octet_length({coluna}) = {TAMANHO_HK}", name=f"{coluna}_tamanho")
        for coluna in colunas_hk
    ]
    return Table(nome, metadata, *itens, *tamanhos, info=info)


def hub(nome: str, entidade: str, *chave: SchemaItem) -> Table:
    """Declara um hub: `hk_<entidade>`, chave de negócio única e colunas técnicas.

    Args:
        nome: Nome da tabela (`hub_<entidade>`).
        entidade: Entidade do hub.
        *chave: Colunas da chave de negócio (na ordem do hash) e CHECKs extras.

    Returns:
        A tabela.
    """
    colunas = [item.name for item in chave if isinstance(item, Column)]
    itens: list[SchemaItem] = [
        Column(f"hk_{entidade}", BYTEA, primary_key=True),
        *chave,
        *_tecnicas(),
        UniqueConstraint(*colunas),
    ]
    return _tabela(nome, itens, {"tipo": "hub", "hk": f"hk_{entidade}", "chave": tuple(colunas)})


def link(nome: str, hk: str, *hubs: tuple[str, str]) -> Table:
    """Declara um link historizável: `hk` próprio e os `hk` dos hubs, únicos em conjunto.

    Args:
        nome: Nome da tabela (`link_<a>_<b>`).
        hk: Coluna da chave do link.
        *hubs: Pares `(coluna, hub)` na ordem do hash do link.

    Returns:
        A tabela.
    """
    colunas = [coluna for coluna, _ in hubs]
    itens: list[SchemaItem] = [
        Column(hk, BYTEA, primary_key=True),
        *(_hk(coluna, f"{alvo}.{coluna}") for coluna, alvo in hubs),
        *_tecnicas(),
        UniqueConstraint(*colunas),
        *(Index(f"ix_{nome}_{coluna}", coluna) for coluna in colunas),
    ]
    return _tabela(nome, itens, {"tipo": "link", "hk": hk, "hubs": tuple(colunas)})


def satelite(
    nome: str,
    pai: str,
    alvo: str,
    *atributos: SchemaItem,
    multiativo: str | None = None,
    sempre_insere: bool = False,
) -> Table:
    """Declara um satélite: PK `(pai, [subchave], load_dts)`, `hash_diff` e atributos.

    Args:
        nome: Nome da tabela (`sat_<pai>_<assunto>`).
        pai: Coluna `hk` do pai.
        alvo: Tabela do pai (hub ou link).
        *atributos: Colunas de negócio e CHECKs.
        multiativo: Coluna que distingue as linhas ativas ao mesmo tempo, se houver.
        sempre_insere: Se toda gravação insere, sem comparar o `hash_diff` (anotação, falha).

    Returns:
        A tabela.
    """
    chave = [pai, *([multiativo] if multiativo else []), "load_dts"]
    itens: list[SchemaItem] = [
        _hk(pai, f"{alvo}.{pai}"),
        *_tecnicas(),
        Column("hash_diff", BYTEA, nullable=False),
        *atributos,
        PrimaryKeyConstraint(*chave),
    ]
    info = {
        "tipo": "satelite",
        "pai": pai,
        "multiativo": multiativo,
        "sempre_insere": sempre_insere,
    }
    return _tabela(nome, itens, info)


def atributos_do_satelite(tabela: Table) -> list[str]:
    """Colunas de negócio de um satélite, que entram no `hash_diff`.

    Args:
        tabela: Satélite.

    Returns:
        Nomes das colunas, sem o pai e sem as colunas técnicas.
    """
    pai = tabela.info["pai"]
    return [c.name for c in tabela.columns if c.name != pai and c.name not in COLUNAS_TECNICAS]


hub_usuario = hub("hub_usuario", "usuario", _texto("nome_usuario"))
hub_processo = hub("hub_processo", "processo", _texto("numero_cnj"))
hub_arquivo = hub("hub_arquivo", "arquivo", _texto("numero_cnj"), _texto("sha256"))
hub_pagina = hub("hub_pagina", "pagina", _texto("numero_cnj"), _texto("sha256"), _inteiro("numero"))
hub_peca = hub(
    "hub_peca", "peca", _texto("numero_cnj"), _texto("sha256"), _inteiro("pagina_inicial")
)
hub_evidencia = hub(
    "hub_evidencia",
    "evidencia",
    _texto("numero_cnj"),
    _texto("sha256"),
    _inteiro("numero"),
    _inteiro("inicio"),
    _inteiro("fim"),
    CheckConstraint("inicio >= 0 AND fim > inicio", name="offsets_validos"),
)
hub_fato = hub(
    "hub_fato",
    "fato",
    _texto("numero_cnj"),
    _texto("tipo"),
    _texto("sujeito"),
    _hk("hk_evidencia_origem", "hub_evidencia.hk_evidencia"),
    checar_enum("tipo", TipoFato),
)
hub_achado = hub(
    "hub_achado", "achado", _texto("numero_cnj"), _texto("validacao"), _texto("sujeito")
)
hub_parte = hub("hub_parte", "parte", _texto("numero_cnj"), _hk("chave_nome"))
hub_conversa = hub(
    "hub_conversa", "conversa", Column("conversa_id", PG_UUID(as_uuid=True), nullable=False)
)
hub_sessao = hub("hub_sessao", "sessao", _texto("token_sha256"))
hub_desafio_mfa = hub("hub_desafio_mfa", "desafio_mfa", _texto("token_sha256"))
hub_chave_login = hub("hub_chave_login", "chave_login", _texto("chave"))

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

link_processo_arquivo = link("link_processo_arquivo", "hk_processo_arquivo", PROCESSO, ARQUIVO)
link_arquivo_pagina = link("link_arquivo_pagina", "hk_arquivo_pagina", ARQUIVO, PAGINA)
link_arquivo_peca = link("link_arquivo_peca", "hk_arquivo_peca", ARQUIVO, PECA)
link_pagina_evidencia = link("link_pagina_evidencia", "hk_pagina_evidencia", PAGINA, EVIDENCIA)
link_processo_fato = link("link_processo_fato", "hk_processo_fato", PROCESSO, FATO)
link_fato_evidencia = link("link_fato_evidencia", "hk_fato_evidencia", FATO, EVIDENCIA)
link_processo_achado = link("link_processo_achado", "hk_processo_achado", PROCESSO, ACHADO)
link_achado_fato = link("link_achado_fato", "hk_achado_fato", ACHADO, FATO)
link_processo_parte = link("link_processo_parte", "hk_processo_parte", PROCESSO, PARTE)
link_processo_responsavel = link(
    "link_processo_responsavel", "hk_processo_responsavel", PROCESSO, USUARIO
)
link_processo_conversa = link(
    "link_processo_conversa", "hk_processo_conversa", PROCESSO, CONVERSA, USUARIO
)
link_sessao_usuario = link(
    "link_sessao_usuario", "hk_sessao_usuario", ("hk_sessao", "hub_sessao"), USUARIO
)
link_desafio_mfa_usuario = link(
    "link_desafio_mfa_usuario",
    "hk_desafio_mfa_usuario",
    ("hk_desafio_mfa", "hub_desafio_mfa"),
    USUARIO,
)

link_chamada_modelo = _tabela(
    "link_chamada_modelo",
    [
        Column("hk_chamada", BYTEA, primary_key=True),
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
        Column("ferramentas", ARRAY(Text), nullable=False),
        _texto("resultado"),
        checar_enum("resultado", ResultadoChamada),
        Index("ix_link_chamada_modelo_hk_processo_load_dts", "hk_processo", "load_dts"),
        Index("ix_link_chamada_modelo_hk_conversa", "hk_conversa"),
    ],
    {"tipo": "link", "hk": "hk_chamada", "hubs": ("hk_processo", "hk_conversa")},
)

link_evento_auditoria = _tabela(
    "link_evento_auditoria",
    [
        Column("hk_evento", BYTEA, primary_key=True),
        Column("sequencia", BigInteger, nullable=False, unique=True),
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
        Index("ix_link_evento_auditoria_ocorrido_em", "ocorrido_em"),
        Index("ix_link_evento_auditoria_hk_usuario_ocorrido_em", "hk_usuario", "ocorrido_em"),
        Index("ix_link_evento_auditoria_hk_processo_ocorrido_em", "hk_processo", "ocorrido_em"),
        Index("ix_link_evento_auditoria_acao_ocorrido_em", "acao", "ocorrido_em"),
        Index("ix_link_evento_auditoria_ip_ocorrido_em", "ip", "ocorrido_em"),
    ],
    {"tipo": "link", "hk": "hk_evento", "hubs": ("hk_usuario", "hk_processo")},
)

sat_usuario_cadastro = satelite(
    "sat_usuario_cadastro",
    *USUARIO,
    _texto("papel"),
    _booleano("ativo"),
    checar_enum("papel", PapelUsuario),
)
sat_usuario_credencial = satelite(
    "sat_usuario_credencial",
    *USUARIO,
    _texto("senha_hash"),
    _booleano("troca_senha_obrigatoria"),
    _texto("mfa_segredo", nulo=True),
    _booleano("mfa_confirmado"),
    Column("mfa_ultimo_passo", BigInteger, nullable=True),
)
sat_processo_dados = satelite(
    "sat_processo_dados",
    *PROCESSO,
    _texto("classe"),
    _usuario(),
    checar_enum("classe", ClasseProcessual),
)
sat_processo_estado = satelite(
    "sat_processo_estado", *PROCESSO, _texto("status"), checar_enum("status", StatusProcesso)
)
sat_processo_revisao = satelite(
    "sat_processo_revisao",
    *PROCESSO,
    _texto("situacao"),
    _texto("motivo"),
    _texto("status_anterior"),
    _usuario(nulo=True),
    checar_valores("situacao", SITUACOES_REVISAO),
)
sat_arquivo_dados = satelite(
    "sat_arquivo_dados",
    *ARQUIVO,
    _inteiro("tamanho_bytes"),
    _texto("nome_original"),
    _texto("mime"),
    _texto("chave_storage"),
    _usuario(),
    CheckConstraint("tamanho_bytes > 0", name="tamanho_positivo"),
)
sat_arquivo_ingestao = satelite(
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
    CheckConstraint(
        "(estado = 'quarentena') = (motivo_quarentena IS NOT NULL)", name="quarentena_com_motivo"
    ),
    Index("ix_sat_arquivo_ingestao_estado_load_dts", "estado", "load_dts"),
)
sat_arquivo_lote = satelite(
    "sat_arquivo_lote",
    *ARQUIVO,
    _inteiro("numero"),
    _texto("estado"),
    _json("resultado"),
    checar_enum("estado", EstadoLote),
    multiativo="numero",
)
sat_arquivo_diagnostico = satelite(
    "sat_arquivo_diagnostico",
    *ARQUIVO,
    _texto("cenario"),
    _inteiro("total_paginas"),
    _booleano("tem_indice"),
    _json("sinais"),
    _json("fronteiras_origem"),
    _json("metadados_descartados"),
    checar_enum("cenario", CenarioArquivo),
    CheckConstraint("total_paginas >= 0", name="paginas_nao_negativas"),
)
sat_pagina_extracao = satelite(
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
sat_pagina_saneamento = satelite(
    "sat_pagina_saneamento",
    *PAGINA,
    _texto("texto_normalizado", nulo=True),
    _json("flags"),
    _json_texto("trechos_ocultos"),
    _json_texto("trechos_suspeitos"),
)
sat_pagina_fronteira = satelite("sat_pagina_fronteira", *PAGINA, _json("sinais_fronteira"))
sat_peca_classificacao = satelite(
    "sat_peca_classificacao",
    *PECA,
    _texto("tipo"),
    _inteiro("pagina_final"),
    *_confianca(),
    _texto("metodo"),
    _texto("origem"),
    Column("data", Date, nullable=True),
    _texto("tipo_data", nulo=True),
    _hk("hk_evidencia_data", "hub_evidencia.hk_evidencia", nulo=True),
    _json("flags"),
    _json("classificacao"),
    _booleano("vigente"),
    _usuario(nulo=True),
    checar_enum("tipo", TipoPeca),
    checar_enum("metodo", MetodoClassificacao),
    checar_enum("origem", OrigemPeca),
    checar_valores("tipo_data", TIPOS_DATA_PECA),
)
sat_evidencia_trecho = satelite(
    "sat_evidencia_trecho",
    *EVIDENCIA,
    _texto("trecho"),
    _texto("hash_trecho"),
    _json("bbox", nulo=True),
)
sat_fato_valor = satelite(
    "sat_fato_valor",
    *FATO,
    _json_texto("valor"),
    _texto("extraido_por"),
    _texto("versao_extrator"),
    *_confianca(),
    _texto("status"),
    _usuario(nulo=True),
    checar_enum("status", StatusFato),
)
sat_fato_anotacao = satelite(
    "sat_fato_anotacao",
    *FATO,
    _texto("texto"),
    _usuario(),
    sempre_insere=True,
)
sat_fato_evidencia_vigencia = satelite(
    "sat_fato_evidencia_vigencia", "hk_fato_evidencia", "link_fato_evidencia", _booleano("vigente")
)
sat_achado_resultado = satelite(
    "sat_achado_resultado",
    *ACHADO,
    _texto("versao_catalogo"),
    _texto("resultado"),
    Column("fatos_usados", ARRAY(BYTEA), nullable=False),
    _json_texto("valores"),
    _texto("explicacao"),
    checar_enum("resultado", ResultadoAchado),
)
sat_achado_anotacao = satelite(
    "sat_achado_anotacao",
    *ACHADO,
    _texto("texto"),
    _usuario(),
    sempre_insere=True,
)
sat_parte_identidade = satelite(
    "sat_parte_identidade",
    *PARTE,
    _texto("nome"),
    _texto("polo"),
    _texto("qualidade"),
    _hk("hk_evidencia", "hub_evidencia.hk_evidencia"),
    checar_enum("polo", Polo),
    checar_enum("qualidade", QualidadeParte),
)
sat_processo_responsavel_vigencia = satelite(
    "sat_processo_responsavel_vigencia",
    "hk_processo_responsavel",
    "link_processo_responsavel",
    _booleano("vigente"),
)
sat_conversa_estado = satelite(
    "sat_conversa_estado",
    *CONVERSA,
    _booleano("encerrada"),
    _texto("motivo_encerramento", nulo=True),
    _grande("tokens_entrada"),
    _grande("tokens_saida"),
    _inteiro("paginas_originais"),
    _inteiro("citacoes_descartadas"),
)
sat_conversa_mensagem = satelite(
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
sat_sessao_estado = satelite(
    "sat_sessao_estado",
    "hk_sessao",
    "hub_sessao",
    _texto("papel"),
    _instante("expira_em"),
    _instante("ultimo_acesso_em"),
    _booleano("revogada"),
    _texto("ip_criacao", nulo=True),
    checar_enum("papel", PapelUsuario),
)
sat_desafio_mfa_estado = satelite(
    "sat_desafio_mfa_estado",
    "hk_desafio_mfa",
    "hub_desafio_mfa",
    _texto("papel"),
    _instante("expira_em"),
    _booleano("consumido"),
    checar_enum("papel", PapelUsuario),
)
sat_chave_login_falha = satelite(
    "sat_chave_login_falha", "hk_chave_login", "hub_chave_login", sempre_insere=True
)
sat_chave_login_bloqueio = satelite(
    "sat_chave_login_bloqueio",
    "hk_chave_login",
    "hub_chave_login",
    _instante("bloqueado_ate", nulo=True),
    sempre_insere=True,
)
