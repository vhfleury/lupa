"""Tokens de cor de `tokens.css`: paleta verde e contraste WCAG nos dois temas (RF-VIS-01, 02).

Segue o algoritmo A2 do plano do padrão visual: extrai as variáveis de `:root` (tema claro) e de
cada bloco do tema escuro, e calcula a razão de contraste de cada par declarado em `PARES`.
"""

import re
from pathlib import Path

import pytest

TOKENS = Path(__file__).resolve().parents[2] / "src" / "lupa_web" / "static" / "css" / "tokens.css"
MINIMO_TEXTO = 4.5
MINIMO_NAO_TEXTO = 3.0
BLOCO = re.compile(r"([^{}]+)\{([^{}]*)\}")
VARIAVEL = re.compile(r"(--[\w-]+)\s*:\s*([^;]+);")
COR = re.compile(r"^#[0-9a-fA-F]{6}$")
SELETOR_CLARO = ":root"
SELETORES_ESCUROS = {
    "escuro-manual": ":root[data-tema='escuro']",
    "escuro-sistema": ":root:not([data-tema='claro'])",
}

PARES_DE_TEXTO = (
    ("--texto", "--fundo"),
    ("--texto", "--superficie"),
    ("--texto", "--superficie-suave"),
    ("--texto-suave", "--fundo"),
    ("--texto-suave", "--superficie"),
    ("--texto-suave", "--superficie-suave"),
    ("--primaria", "--fundo"),
    ("--primaria", "--superficie"),
    ("--primaria-texto", "--primaria"),
    ("--perigo", "--fundo"),
    ("--perigo", "--perigo-fundo"),
    ("--sucesso", "--sucesso-fundo"),
    ("--atencao", "--atencao-fundo"),
    ("--aviso-texto", "--aviso-fundo"),
    ("--texto", "--sucesso-fundo"),
    ("--texto", "--atencao-fundo"),
    ("--texto", "--perigo-fundo"),
    ("--badge-texto", "--badge-fundo"),
)
PARES_NAO_TEXTUAIS = (
    ("--borda-campo", "--fundo"),
    ("--borda-campo", "--superficie"),
    ("--foco", "--fundo"),
    ("--foco", "--superficie"),
    ("--sucesso", "--fundo"),
    ("--atencao", "--fundo"),
    ("--perigo", "--fundo"),
    ("--sucesso", "--sucesso-fundo"),
    ("--atencao", "--atencao-fundo"),
    ("--perigo", "--perigo-fundo"),
    ("--primaria", "--fundo"),
)


def _blocos() -> dict[str, dict[str, str]]:
    texto = re.sub(r"/\*.*?\*/", "", TOKENS.read_text(encoding="utf-8"), flags=re.S)
    blocos: dict[str, dict[str, str]] = {}
    for seletor, corpo in BLOCO.findall(texto):
        nome = " ".join(seletor.split()).replace('"', "'")
        blocos.setdefault(nome, {}).update(dict(VARIAVEL.findall(corpo)))
    return blocos


def temas() -> dict[str, dict[str, str]]:
    """Tokens resolvidos por tema: o claro e cada bloco escuro sobre o claro.

    Returns:
        Valores das variáveis por nome do tema.
    """
    blocos = _blocos()
    claro = blocos.get(SELETOR_CLARO, {})
    resolvidos = {"claro": claro}
    for tema, seletor in SELETORES_ESCUROS.items():
        resolvidos[tema] = claro | blocos.get(seletor, {})
    return resolvidos


def _canal(valor: int) -> float:
    componente = valor / 255
    if componente <= 0.03928:
        return componente / 12.92
    return float(((componente + 0.055) / 1.055) ** 2.4)


def luminancia(cor: str) -> float:
    """Luminância relativa WCAG de uma cor `#rrggbb`.

    Args:
        cor: Cor hexadecimal de seis dígitos.

    Returns:
        Luminância entre 0 e 1.
    """
    vermelho, verde, azul = (int(cor[i : i + 2], 16) for i in (1, 3, 5))
    return 0.2126 * _canal(vermelho) + 0.7152 * _canal(verde) + 0.0722 * _canal(azul)


def contraste(frente: str, fundo: str) -> float:
    """Razão de contraste WCAG entre duas cores.

    Args:
        frente: Cor do texto ou do elemento.
        fundo: Cor do fundo.

    Returns:
        Razão entre 1 e 21.
    """
    claras, escuras = sorted((luminancia(frente), luminancia(fundo)), reverse=True)
    return (claras + 0.05) / (escuras + 0.05)


def _abaixo_do_minimo(pares: tuple[tuple[str, str], ...], minimo: float) -> list[str]:
    falhas = []
    for tema, tokens in temas().items():
        for frente, fundo in pares:
            ausentes = [nome for nome in (frente, fundo) if nome not in tokens]
            if ausentes:
                falhas.append(f"{tema}: token ausente {ausentes}")
                continue
            razao = contraste(tokens[frente], tokens[fundo])
            if razao < minimo:
                falhas.append(f"{tema}: {frente} sobre {fundo} = {razao:.2f}")
    return falhas


def test_primaria_e_verde_do_padrao() -> None:
    """RF-VIS-02: a primária é `#00613b` no claro e `#4cc489` no escuro, sobre fundo branco."""
    resolvidos = temas()
    assert resolvidos["claro"].get("--primaria") == "#00613b"
    assert resolvidos["claro"].get("--fundo") == "#ffffff"
    assert resolvidos["escuro-manual"].get("--primaria") == "#4cc489"
    assert resolvidos["escuro-sistema"].get("--primaria") == "#4cc489"


def test_tema_escuro_redefine_todos_os_tokens_de_cor() -> None:
    """RF-VIS-01: todo token de cor do tema claro é redefinido em cada bloco do tema escuro."""
    blocos = _blocos()
    cores_claras = {
        nome for nome, valor in blocos.get(SELETOR_CLARO, {}).items() if COR.match(valor.strip())
    }
    assert cores_claras
    for seletor in SELETORES_ESCUROS.values():
        assert cores_claras - set(blocos.get(seletor, {})) == set(), seletor


@pytest.mark.parametrize("par", PARES_DE_TEXTO + PARES_NAO_TEXTUAIS, ids=" sobre ".join)
def test_pares_declarados_sao_cores_hexadecimais(par: tuple[str, str]) -> None:
    """RF-VIS-02: cada token dos pares de contraste é uma cor `#rrggbb` nos dois temas."""
    for tema, tokens in temas().items():
        for nome in par:
            assert COR.match(tokens.get(nome, "").strip()), f"{tema}: {nome}"


def test_pares_de_texto_atingem_4_5_nos_dois_temas() -> None:
    """RF-VIS-02: todo par texto/fundo declarado atinge 4,5:1 nos temas claro e escuro."""
    assert _abaixo_do_minimo(PARES_DE_TEXTO, MINIMO_TEXTO) == []


def test_borda_foco_e_tarja_atingem_3_nos_dois_temas() -> None:
    """RF-VIS-02 (WCAG 1.4.11): borda de campo, foco e tarja atingem 3:1 sobre o fundo."""
    assert _abaixo_do_minimo(PARES_NAO_TEXTUAIS, MINIMO_NAO_TEXTO) == []
