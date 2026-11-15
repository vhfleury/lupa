"""Gera autos cíveis, cria um assessor e lacra o PDF para o worker da stack E2E."""

import hashlib
import secrets
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from tempfile import TemporaryDirectory

from lupa_intranet.acesso.servico import Ator, Contexto, auditar, criar_usuario
from lupa_intranet.api.rotas.processos import CorpoProcesso, gravar_processo
from lupa_intranet.auditoria.eventos import AcaoAuditoria
from lupa_pipeline.config import get_settings
from lupa_pipeline.dominio.enums import ClasseProcessual, PapelUsuario
from lupa_pipeline.dominio.sessao import assumir_papel_aplicacao
from lupa_pipeline.dominio.visoes import VisaoUsuario
from lupa_pipeline.ingestao.recepcao import ArquivoRecebido, TipoArquivo, lacrar
from lupa_pipeline.ingestao.storage import criar_storage
from lupa_pipeline.seguranca.cofre import criar_cofre
from lupa_pipeline.seguranca.contexto import contexto_cifra, definir_cofre
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

ORIGEM = "scripts.e2e"


@contextmanager
def sessao_e2e() -> Iterator[Session]:
    """Abre uma transação com o papel da aplicação e o cofre real da stack sintética."""
    settings = get_settings()
    if settings.ambiente not in {"teste", "desenvolvimento"}:
        raise SystemExit("E2E exige ambiente de teste ou desenvolvimento")
    engine = create_engine(settings.url_banco_aplicacao())
    definir_cofre(criar_cofre(settings))
    try:
        with Session(engine) as sessao, sessao.begin(), contexto_cifra():
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


def enfileirar_pdf(sessao: Session, autor: Ator, numero: str, pdf: Path) -> str:
    """Cadastra a apelação cível e lacra o arquivo usando a mesma DEK e fila da intranet."""
    ctx = Contexto(None, None, datetime.now(UTC))
    corpo = CorpoProcesso(numero_cnj=numero, classe=ClasseProcessual.APELACAO_CIVEL)
    processo = gravar_processo(sessao, corpo, autor, origem=ORIGEM)
    auditar(
        sessao,
        ctx,
        AcaoAuditoria.PROCESSO_CRIADO,
        hk_usuario=autor.hk_usuario,
        hk_processo=processo,
        objeto_tipo="processo",
        objeto_id=processo.hex(),
    )
    with pdf.open("rb") as arquivo:
        sha = hashlib.file_digest(arquivo, "sha256").hexdigest()
    recebido = ArquivoRecebido(pdf, sha, pdf.stat().st_size, TipoArquivo.PDF)
    lacrar(
        sessao,
        criar_storage(get_settings()),
        recebido,
        hk_processo=processo,
        enviado_por=autor.hk_usuario,
        nome_original=pdf.name,
    )
    return processo.hex()


def preparar() -> tuple[str, str, str]:
    """Entrega credenciais do assessor e o id do processo sintético que ele cadastrou."""
    from lupa_pipeline.sinteticos.empacotamento import exportar
    from lupa_pipeline.sinteticos.gabarito import Cenario, Composicao, Gabarito
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
        gerado = exportar(gerar_conteudo(config), Path(diretorio), (Cenario.PDF_INDICE,))[0]
        numero = Gabarito.model_validate_json(gerado.gabarito.read_bytes()).processo.numero_cnj
        processo = enfileirar_pdf(sessao, ator(criado.usuario), numero, gerado.caminho)
        return nome, criado.senha_temporaria, processo


if __name__ == "__main__":
    print(*preparar(), sep="\n")
