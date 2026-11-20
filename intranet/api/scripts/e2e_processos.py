"""Gera autos cíveis, cria um assessor e lacra o PDF para o worker da stack E2E."""

import hashlib
import secrets
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from tempfile import TemporaryDirectory

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from lupa_api.acesso.servico import Ator, Contexto, criar_usuario
from lupa_api.api.rotas.ingestao import cadastrar_por_arquivo
from lupa_pipeline.config import get_settings
from lupa_pipeline.dominio.enums import ClasseProcessual, PapelUsuario
from lupa_pipeline.dominio.sessao import assumir_papel_aplicacao
from lupa_pipeline.dominio.visoes import VisaoUsuario
from lupa_pipeline.ingestao.recepcao import ArquivoRecebido, TipoArquivo
from lupa_pipeline.ingestao.storage import criar_storage


@contextmanager
def sessao_e2e() -> Iterator[Session]:
    """Abre uma transação com o papel da aplicação na stack sintética."""
    settings = get_settings()
    if settings.ambiente not in {"teste", "desenvolvimento"}:
        raise SystemExit("E2E exige ambiente de teste ou desenvolvimento")
    engine = create_engine(settings.url_banco_aplicacao())
    try:
        with Session(engine) as sessao, sessao.begin():
            assumir_papel_aplicacao(sessao)
            yield sessao
    finally:
        engine.dispose()


def ator(usuario: VisaoUsuario) -> Ator:
    """Representa o autor da preparação, executada fora de uma sessão HTTP."""
    return Ator(
        usuario.hk_usuario, usuario.id, PapelUsuario(str(usuario.papel)), usuario.nome_usuario, b""
    )


def desembargador(sessao: Session) -> Ator:
    """Lê o usuário criado por e2e_preparar na instalação do E2E."""
    usuario = sessao.scalars(
        select(VisaoUsuario).where(VisaoUsuario.papel == PapelUsuario.DESEMBARGADOR.value)
    ).one()
    return ator(usuario)


def enfileirar_pdf(sessao: Session, autor: Ator, pdf: Path) -> str:
    """Identifica os autos pela capa e os envia pelo serviço de cadastro da intranet."""
    ctx = Contexto(None, None, datetime.now(UTC))
    with pdf.open("rb") as arquivo:
        sha = hashlib.file_digest(arquivo, "sha256").hexdigest()
    recebido = ArquivoRecebido(pdf, sha, pdf.stat().st_size, TipoArquivo.PDF)
    settings = get_settings()
    status, resposta = cadastrar_por_arquivo(
        sessao, criar_storage(settings), recebido, pdf.name, autor, ctx, settings
    )
    if status != 201 or not resposta["processo_criado"]:
        raise RuntimeError(f"O cadastro do PDF sintético falhou (HTTP {status})")
    return str(resposta["processo_id"])


def preparar() -> tuple[str, str, str]:
    """Entrega credenciais do assessor e o id do processo sintético que ele cadastrou."""
    from lupa_pipeline.sinteticos.empacotamento import exportar
    from lupa_pipeline.sinteticos.gabarito import Cenario, Composicao
    from lupa_pipeline.sinteticos.gerador import gerar_conteudo
    from lupa_pipeline.sinteticos.roteiro import Configuracao

    with sessao_e2e() as sessao, TemporaryDirectory(prefix="lupa-e2e-") as diretorio:
        nome = f"assessor.autos.{secrets.token_hex(3)}"
        ctx = Contexto(None, None, datetime.now(UTC))
        criado = criar_usuario(sessao, desembargador(sessao), nome, PapelUsuario.ASSESSOR, ctx)
        config = Configuracao(
            semente=751,
            classe=ClasseProcessual.APELACAO_CIVEL,
            paginas_alvo=18,
            mistura={Composicao.NATIVA: 1.0},
            proporcao_vazias=0.0,
        )
        conteudo = gerar_conteudo(config)
        try:
            (gerado,) = exportar(conteudo, Path(diretorio), (Cenario.PDF_INDICE,))
        finally:
            conteudo.documento.close()
        processo = enfileirar_pdf(sessao, ator(criado.usuario), gerado.caminho)
        return nome, criado.senha_temporaria, processo


if __name__ == "__main__":
    print(*preparar(), sep="\n")
