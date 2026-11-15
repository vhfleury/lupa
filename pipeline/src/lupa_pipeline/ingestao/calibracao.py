"""Execução e relatório de conferência da ingestão de autos cíveis."""

import hashlib
import time
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from threading import Event
from typing import Any
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from lupa_pipeline.config import Settings
from lupa_pipeline.dominio.cnj import calcular_digito_verificador
from lupa_pipeline.dominio.enums import ClasseProcessual, EstadoJob, PapelUsuario, StatusProcesso
from lupa_pipeline.dominio.gravacao import (
    chave_do_hub,
    gravar_hub,
    gravar_satelite,
    travar_processo,
)
from lupa_pipeline.dominio.repositorios import listar_fatos_por_processo
from lupa_pipeline.dominio.tabelas import (
    hub_processo,
    hub_usuario,
    sat_processo_dados,
    sat_processo_estado,
    sat_usuario_cadastro,
)
from lupa_pipeline.dominio.visoes import VisaoArquivo, VisaoPagina, VisaoParte
from lupa_pipeline.ingestao import repositorio_eventos, repositorio_pecas
from lupa_pipeline.ingestao.extrator_paginas import VERSAO_EXTRATOR
from lupa_pipeline.ingestao.paginas import gravar_pagina
from lupa_pipeline.ingestao.processamento import processar_arquivo
from lupa_pipeline.ingestao.recepcao import ArquivoRecebido, detectar_tipo, lacrar
from lupa_pipeline.ingestao.storage import ObjectStorage
from lupa_pipeline.ingestao.worker import TRAVA_WORKER
from lupa_pipeline.seguranca.chaves import criar_chave_processo
from lupa_pipeline.seguranca.contexto import obter_cofre
from lupa_pipeline.validacoes.modelo import valor_de

TAMANHO_BLOCO = 1 << 20


@dataclass(frozen=True)
class Execucao:
    """Identificadores persistidos, estado e duração do processamento."""

    processo_id: bytes
    arquivo_id: bytes
    estado: EstadoJob
    segundos: float
    paginas_do_volume: int = 0


def numero_cnj(sequencial: int) -> str:
    """Número CNJ sintético válido para o processo de calibração.

    Args:
        sequencial: Sequencial (até 7 dígitos).

    Returns:
        Número formatado com dígito verificador.
    """
    seq, ano, justica, tribunal, origem = (
        f"{sequencial % 10_000_000:07d}",
        "2026",
        "8",
        "09",
        "0001",
    )
    digito = calcular_digito_verificador(seq, ano, justica, tribunal, origem)
    return f"{seq}-{digito}.{ano}.{justica}.{tribunal}.{origem}"


def semear_assessor(session: Session, origem: str) -> bytes:
    """Cria uma identidade técnica inativa exclusiva desta execução."""
    nome = f"{origem.replace('.', '_')}_{uuid4().hex}"
    hk = gravar_hub(session, hub_usuario, {"nome_usuario": nome}, origem)
    gravar_satelite(
        session,
        sat_usuario_cadastro,
        hk,
        {"papel": PapelUsuario.ASSESSOR.value, "ativo": False},
        origem,
    )
    return hk


def novo_processo(
    session: Session,
    usuario: bytes,
    classe: ClasseProcessual,
    origem: str,
    numero: str | None = None,
) -> bytes:
    """Cria um processo exclusivo da execução, protegendo cadastros preexistentes."""
    chave = {"numero_cnj": numero or numero_cnj(uuid4().int)}
    hk = chave_do_hub(hub_processo, chave)
    if travar_processo(session, hk) is not None:
        raise ValueError("já existe um processo com esse número")
    gravar_hub(session, hub_processo, chave, origem)
    gravar_satelite(
        session, sat_processo_dados, hk, {"classe": classe.value, "hk_usuario": usuario}, origem
    )
    gravar_satelite(
        session, sat_processo_estado, hk, {"status": StatusProcesso.CRIADO.value}, origem
    )
    criar_chave_processo(session, obter_cofre(), hk, origem)
    return hk


def sha256_arquivo(caminho: Path) -> str:
    """SHA-256 do arquivo lido em blocos.

    Args:
        caminho: Arquivo.

    Returns:
        Hash hexadecimal.
    """
    resumo = hashlib.sha256()
    with caminho.open("rb") as entrada:
        while bloco := entrada.read(TAMANHO_BLOCO):
            resumo.update(bloco)
    return resumo.hexdigest()


def enviar_e_processar(
    fabrica: sessionmaker[Session],
    settings: Settings,
    storage: ObjectStorage,
    usuario: bytes,
    caminho: Path,
    classe: ClasseProcessual,
    origem: str,
    *,
    numero: str | None = None,
    volume: dict[str, Any] | None = None,
) -> Execucao:
    """Recebe, cifra e processa um PDF ou ZIP pelo mesmo fluxo A3 e A5 da aplicação."""
    with caminho.open("rb") as entrada:
        tipo = detectar_tipo(entrada.read(8))
    if tipo is None:
        raise ValueError("arquivo não é PDF nem ZIP")
    recebido = ArquivoRecebido(caminho, sha256_arquivo(caminho), caminho.stat().st_size, tipo)
    semeadas = 0
    with fabrica.begin() as session:
        processo = novo_processo(session, usuario, classe, origem, numero)
        lacre = lacrar(
            session,
            storage,
            recebido,
            hk_processo=processo,
            enviado_por=usuario,
            nome_original=caminho.name,
        )
        if volume and volume.get("sha256") == recebido.sha256:
            arquivo = session.get_one(VisaoArquivo, lacre.hk_arquivo)
            for linha in volume["linhas"]:
                if linha.get("versao_extrator") == VERSAO_EXTRATOR:
                    gravar_pagina(session, arquivo, linha)
                    semeadas += 1
    inicio = time.monotonic()
    consulta = select(VisaoArquivo.estado).where(VisaoArquivo.hk_arquivo == lacre.hk_arquivo)

    def ler_estado(fila: Session) -> EstadoJob:
        atual = fila.scalars(consulta).one()
        if atual is None:
            raise ValueError("arquivo sem estado de ingestão")
        return EstadoJob(atual)

    pendentes = {EstadoJob.RECEBIDO, EstadoJob.VALIDADO, EstadoJob.EM_EXTRACAO}
    while True:
        with fabrica.begin() as fila:
            # A trava de sessão do worker e a trava de transação do roteiro são incompatíveis.
            disponivel = fila.scalar(select(func.pg_try_advisory_xact_lock(TRAVA_WORKER)))
            estado = ler_estado(fila)
            if estado not in pendentes:
                return Execucao(
                    processo, lacre.hk_arquivo, estado, time.monotonic() - inicio, semeadas
                )
            if disponivel:
                processar_arquivo(fabrica, settings, storage, lacre.hk_arquivo, Event())
                estado = ler_estado(fila)
                return Execucao(
                    processo, lacre.hk_arquivo, estado, time.monotonic() - inicio, semeadas
                )
        time.sleep(settings.fila_intervalo_s)


def _paginas(session: Session, arquivo_id: bytes) -> dict[str, dict[str, Any]]:
    consulta = select(
        VisaoPagina.id, VisaoPagina.numero, VisaoPagina.tipo, VisaoPagina.origem_arquivo,
        VisaoPagina.pagina_origem, VisaoPagina.flags,
    ).where(VisaoPagina.hk_arquivo == arquivo_id)  # fmt: skip
    chaves = ("id", "numero", "tipo", "origem_arquivo", "pagina_origem", "flags")
    return {linha[0]: dict(zip(chaves, linha, strict=True)) for linha in session.execute(consulta)}


def _fatos(session: Session, processo_id: bytes, paginas: dict[str, dict[str, Any]]) -> list[Any]:
    saida = []
    for fato in listar_fatos_por_processo(session, processo_id):
        evidencia = fato.evidencias[0]
        pagina = paginas.get(evidencia.pagina_id, {})
        saida.append(
            {
                "tipo": str(fato.tipo),
                "valor": valor_de(fato),
                "sujeito": fato.sujeito,
                "confianca": fato.confianca,
                "pagina": pagina.get("numero"),
                "arquivo": pagina.get("origem_arquivo"),
                "pagina_origem": pagina.get("pagina_origem"),
                "trecho": evidencia.trecho,
                "evidencias": len(fato.evidencias),
                "versao_extrator": fato.versao_extrator,
            }
        )
    return sorted(saida, key=lambda f: (f["pagina"] or 0, f["tipo"]))


def coletar(session: Session, processo_id: bytes, arquivo_id: bytes) -> dict[str, Any]:
    """Carrega diagnóstico, índice, partes, fatos e achados correntes do processo."""
    arquivo = session.scalars(
        select(VisaoArquivo).where(
            VisaoArquivo.hk_processo == processo_id, VisaoArquivo.hk_arquivo == arquivo_id
        )
    ).one()
    paginas = _paginas(session, arquivo_id)
    partes = session.execute(
        select(VisaoParte.nome, VisaoParte.polo)
        .where(VisaoParte.hk_processo == processo_id)
        .order_by(VisaoParte.id)
    )
    return {
        "diagnostico": {
            "cenario": arquivo.cenario,
            "total_paginas": arquivo.total_paginas_diagnostico,
            "fronteiras_origem": arquivo.fronteiras_origem,
        },
        "ingestao": {"estado": arquivo.estado, "relatorio": arquivo.relatorio},
        "paginas_por_tipo": dict(Counter(p["tipo"] for p in paginas.values())),
        "paginas_com_flag": sum(1 for p in paginas.values() if any((p["flags"] or {}).values())),
        "indice": repositorio_pecas.indice_processo(session, processo_id),
        "partes": [{"nome": nome, "polo": polo} for nome, polo in partes],
        "fatos": _fatos(session, processo_id, paginas),
        "achados": [
            a.model_dump(mode="json")
            for a in repositorio_eventos.achados_vigentes(session, processo_id)
        ],
    }


def _celula(valor: Any) -> str:
    texto = " ".join(str(valor).split())
    return texto.replace("|", "\\|")


def _secao_diagnostico(dados: dict[str, Any]) -> list[str]:
    diagnostico = dados["diagnostico"] or {}
    ingestao = dados["ingestao"] or {}
    relatorio = ingestao.get("relatorio") or {}
    tempo = relatorio.get("tempo") or {}
    return [
        "## 1. Diagnóstico e páginas",
        "",
        "| Item | Valor |",
        "| --- | --- |",
        f"| Cenário diagnosticado | {diagnostico.get('cenario')} |",
        f"| Total de páginas | {diagnostico.get('total_paginas')} |",
        f"| Fronteiras vindas da origem | {len(diagnostico.get('fronteiras_origem') or [])} |",
        f"| Estado do arquivo | {ingestao.get('estado')} |",
        f"| Páginas por tipo | {_celula(dados['paginas_por_tipo'])} |",
        f"| Páginas abstidas (OCR integral) | {relatorio.get('abstidas')} |",
        f"| CER estimado | {relatorio.get('cer_estimado')} |",
        f"| Páginas com flag de saneamento | {dados['paginas_com_flag']} |",
        f"| Tempo de extração (s) | {tempo.get('parede_segundos')} |",
        f"| Tempo por mil páginas (s) | {tempo.get('por_mil_paginas')} |",
        "",
    ]


def _secao_pecas(dados: dict[str, Any]) -> list[str]:
    linhas = [
        "## 2. Peças (índice)",
        "",
        "Conferir: a peça começa nessa página? O tipo e a origem estão certos? A data é a da peça?",
        "",
        "| # | Páginas | Tipo | Origem | Data | Tipo da data | Confiança | Marcas | Confere? |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for peca in dados["indice"]:
        marcas = ", ".join(peca["resumo_flags"]["peca"]) or "-"
        linhas.append(
            f"| {peca['ordem']} | {peca['pagina_inicial']}-{peca['pagina_final']} | {peca['tipo']} "
            f"| {peca['origem']} | {peca['data'] or '-'} | {peca['tipo_data'] or '-'} "
            f"| {peca['confianca']:.2f} | {marcas} | |"
        )
    return [*linhas, ""]


def _secao_fatos(dados: dict[str, Any]) -> list[str]:
    linhas = [
        "## 3. Eventos (fatos) com evidência",
        "",
        "Partes: "
        + (", ".join(f"{p['nome']} ({p['polo']})" for p in dados["partes"]) or "nenhuma"),
        "",
        "| Página | Tipo | Valor | Confiança | Trecho | Confere? |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for fato in dados["fatos"]:
        linhas.append(
            f"| {fato['pagina']} | {fato['tipo']} | {_celula(fato['valor'])} "
            f"| {fato['confianca']:.2f} | {_celula(fato['trecho'])} | |"
        )
    return [*linhas, ""]


def _secao_achados(dados: dict[str, Any]) -> list[str]:
    linhas = ["## 4. Achados", ""]
    for achado in dados["achados"]:
        linhas += [
            f"### {achado['validacao']}: {achado['resultado']}",
            "",
            _celula(achado["explicacao"]),
            "",
        ]
    return linhas


def para_markdown(dados: dict[str, Any], titulo: str) -> str:
    """Relatório de diagnóstico em Markdown, com colunas "Confere?" para o assessor.

    Args:
        dados: Saída de ``coletar``.
        titulo: Título (sem nome de parte).

    Returns:
        Markdown.
    """
    linhas = [f"# Calibração: {titulo}", ""]
    linhas += _secao_diagnostico(dados)
    linhas += _secao_pecas(dados)
    linhas += _secao_fatos(dados)
    linhas += _secao_achados(dados)
    return "\n".join(linhas) + "\n"
