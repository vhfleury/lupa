"""Semeia dois processos de chat com PDFs cíveis, incluindo texto hostil citado literalmente."""

from pathlib import Path
from tempfile import TemporaryDirectory

import fitz
from e2e_processos import desembargador, enfileirar_pdf, sessao_e2e
from lupa_pipeline.dominio.cnj import calcular_digito_verificador

TEXTOS = (
    "PETIÇÃO INICIAL\nA parte autora requereu a restituição da quantia paga.",
    "APELAÇÃO CÍVEL\nA apelante interpôs o recurso em 14/03/2025.",
    "CERTIDÃO\nCertifico que a parte apelada foi intimada em 10/03/2025.",
)
TEXTOS_HOSTIS = (
    "CERTIDÃO\nA parte intimada em 10/03/2025 consta de <script>window.__lupaXss = 1</script> "
    "[link](#externo-e2e).",
    "CERTIDÃO\nEndereço referido nos autos: http://exemplo.invalid/consulta.",
)


def _pdf(caminho: Path, paginas: tuple[str, ...]) -> None:
    with fitz.open() as documento:
        for texto in paginas:
            folha = documento.new_page()
            folha.insert_text((32, 64), texto, fontsize=8)
        documento.save(caminho)


def semear() -> tuple[str, str]:
    """Enfileira dois PDFs no worker e devolve seus identificadores públicos."""
    with sessao_e2e() as sessao, TemporaryDirectory(prefix="lupa-e2e-chat-") as diretorio:
        autor = desembargador(sessao)
        processos: list[str] = []
        for sequencial, folhas in (("0193351", TEXTOS), ("0193352", TEXTOS_HOSTIS)):
            digito = calcular_digito_verificador(sequencial, "2025", "8", "09", "0001")
            numero = f"{sequencial}-{digito}.2025.8.09.0001"
            caminho = Path(diretorio) / f"autos-{sequencial}.pdf"
            _pdf(caminho, folhas)
            processos.append(enfileirar_pdf(sessao, autor, numero, caminho))
        return processos[0], processos[1]


if __name__ == "__main__":
    print(*semear(), sep="\n")
