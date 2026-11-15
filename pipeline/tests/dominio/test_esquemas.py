"""Testes dos esquemas pydantic e do número CNJ (sem banco)."""

import pytest
from pydantic import ValidationError

from apoio_comum import FabricaFato, gerar_numero_cnj
from lupa_pipeline.dominio.cnj import NumeroCnjInvalidoError, validar_numero_cnj
from lupa_pipeline.dominio.enums import (
    ClasseProcessual,
    MetodoClassificacao,
    OrigemPeca,
    PapelUsuario,
    ResultadoAchado,
    TipoPagina,
    TipoPeca,
)
from lupa_pipeline.dominio.esquemas import (
    Achado,
    Anotacao,
    Arquivo,
    Evidencia,
    Fato,
    Pagina,
    Peca,
    Processo,
    Usuario,
    calcular_hash,
)


def test_numero_cnj_com_digito_correto_e_aceito() -> None:
    """Número gerado com o módulo 97 passa na validação."""
    numero = gerar_numero_cnj(123)
    assert validar_numero_cnj(numero) == numero


def test_numero_cnj_com_digito_errado_e_rejeitado() -> None:
    """Trocar o dígito verificador torna o número inválido."""
    numero = gerar_numero_cnj(123)
    digito_errado = f"{(int(numero[8:10]) + 1) % 100:02d}"
    adulterado = f"{numero[:8]}{digito_errado}{numero[10:]}"
    with pytest.raises(NumeroCnjInvalidoError, match="dígito"):
        validar_numero_cnj(adulterado)


def test_numero_cnj_fora_do_formato_e_rejeitado() -> None:
    """Formato diferente de NNNNNNN-DD.AAAA.J.TR.OOOO é rejeitado."""
    with pytest.raises(NumeroCnjInvalidoError, match="formato"):
        validar_numero_cnj("123-45.2025.8.09.0001")


def test_processo_com_cnj_de_digito_errado_e_rejeitado_pelo_pydantic() -> None:
    """O esquema `Processo` aplica a validação CNJ."""
    numero = gerar_numero_cnj(7)
    adulterado = numero.replace(numero[8:10], f"{(int(numero[8:10]) + 1) % 100:02d}", 1)
    with pytest.raises(ValidationError):
        Processo(
            numero_cnj=adulterado,
            id=calcular_hash("proc"),
            classe=ClasseProcessual.APELACAO_CIVEL,
            criado_por=calcular_hash("usuario"),
        )


def test_fato_sem_evidencia_e_rejeitado_pelo_pydantic(fabrica_fato: FabricaFato) -> None:
    """`Fato.evidencias` exige ao menos um item."""
    dados = fabrica_fato().model_dump()
    dados["evidencias"] = ()
    with pytest.raises(ValidationError, match="evidencias"):
        Fato(**dados)


def test_fato_com_evidencia_e_aceito_e_imutavel(fabrica_fato: FabricaFato) -> None:
    """Fato válido é criado e não pode ser alterado depois."""
    fato = fabrica_fato()
    assert len(fato.evidencias) == 1
    with pytest.raises(ValidationError):
        fato.confianca = 0.1  # type: ignore[misc]  # Exercita a proteção em tempo de execução.


def test_evidencia_calcula_hash_do_trecho_quando_omitido() -> None:
    """`hash_trecho` vira sha256(trecho) se não informado."""
    evidencia = Evidencia(
        id=calcular_hash("ev"), pagina_id=calcular_hash("pag"), trecho="abc", inicio=0, fim=3
    )
    assert evidencia.hash_trecho == calcular_hash("abc")


def test_evidencia_com_hash_divergente_e_rejeitada() -> None:
    """Hash informado precisa corresponder ao trecho."""
    with pytest.raises(ValidationError, match="hash_trecho"):
        Evidencia(
            id=calcular_hash("ev"),
            pagina_id=calcular_hash("pag"),
            trecho="abc",
            hash_trecho="0" * 64,
            inicio=0,
            fim=3,
        )


def test_evidencia_com_fim_nao_maior_que_inicio_e_rejeitada() -> None:
    """`fim` deve ser maior que `inicio`."""
    with pytest.raises(ValidationError, match="fim deve ser maior"):
        Evidencia(
            id=calcular_hash("ev"), pagina_id=calcular_hash("pag"), trecho="abc", inicio=5, fim=5
        )


def test_peca_com_pagina_final_antes_da_inicial_e_rejeitada() -> None:
    """`pagina_final >= pagina_inicial`."""
    with pytest.raises(ValidationError, match="pagina_final"):
        Peca(
            id=calcular_hash("peca"),
            arquivo_id=calcular_hash("arquivo"),
            tipo=TipoPeca.SENTENCA,
            pagina_inicial=10,
            pagina_final=9,
            confianca=1.0,
            metodo=MetodoClassificacao.REGRA,
            origem=OrigemPeca.JUIZO,
        )


def test_peca_de_uma_pagina_e_aceita() -> None:
    """Página inicial igual à final é válida."""
    peca = Peca(
        id=calcular_hash("peca"),
        arquivo_id=calcular_hash("arquivo"),
        tipo=TipoPeca.CERTIDAO,
        pagina_inicial=3,
        pagina_final=3,
        confianca=0.5,
        metodo=MetodoClassificacao.MANUAL,
        origem=OrigemPeca.DESCONHECIDA,
    )
    assert peca.pagina_final == 3


def test_pagina_calcula_e_confere_hash_do_texto() -> None:
    """`hash_texto` é calculado e, se informado, conferido."""
    pagina = Pagina(
        id=calcular_hash("pagina"),
        arquivo_id=calcular_hash("arquivo"),
        numero=1,
        tipo=TipoPagina.NATIVA,
        texto="x",
    )
    assert pagina.hash_texto == calcular_hash("x")
    with pytest.raises(ValidationError, match="hash_texto"):
        Pagina(
            id=calcular_hash("pagina"),
            arquivo_id=calcular_hash("arquivo"),
            numero=1,
            tipo=TipoPagina.OCR,
            texto="x",
            hash_texto="y",
        )


def test_achado_com_resultado_fora_do_enum_e_rejeitado() -> None:
    """`resultado` só aceita conforme, atencao ou verificar."""
    with pytest.raises(ValidationError, match="resultado"):
        Achado(
            id=calcular_hash("ach"),
            processo_id=calcular_hash("proc"),
            validacao="tempestividade",
            versao_catalogo="1",
            resultado="talvez",
            explicacao="-",
        )
    achado = Achado(
        id=calcular_hash("ach"),
        processo_id=calcular_hash("proc"),
        validacao="tempestividade",
        versao_catalogo="1",
        resultado=ResultadoAchado.VERIFICAR,
        explicacao="-",
    )
    assert achado.resultado is ResultadoAchado.VERIFICAR


def test_anotacao_exige_exatamente_um_alvo() -> None:
    """Anotação aponta para um achado ou um fato, nunca ambos nem nenhum."""
    dados = {"id": calcular_hash("nota"), "usuario_id": calcular_hash("usuario"), "texto": "nota"}
    with pytest.raises(ValidationError, match="exatamente um"):
        Anotacao(**dados)
    with pytest.raises(ValidationError, match="exatamente um"):
        Anotacao(**dados, achado_id=calcular_hash("achado"), fato_id=calcular_hash("fato"))
    assert Anotacao(**dados, fato_id=calcular_hash("fato")).achado_id is None


@pytest.mark.parametrize("papel", list(PapelUsuario))
def test_usuario_dos_dois_papeis_tem_id_publico_e_senha_oculta(papel: PapelUsuario) -> None:
    """RF-ACE-03: os dois papéis do gabinete têm credencial protegida na representação."""
    usuario = Usuario(id=calcular_hash("usuario"), nome_usuario="a", papel=papel, senha_hash="h")
    assert usuario.papel == papel
    assert "senha_hash" not in repr(usuario)


def test_sujeito_e_ids_dos_fatos_exigem_hash_publico(fabrica_fato: FabricaFato) -> None:
    """RF-FAT-01, D12: valor vazio indica fato comum e demais sujeitos exigem um hk."""
    dados = fabrica_fato().model_dump()
    assert Fato(**dados).sujeito == ""
    assert Fato(**(dados | {"sujeito": calcular_hash("parte")})).sujeito == calcular_hash("parte")
    for alteracao in ({"id": "x"}, {"sujeito": "apelante"}):
        with pytest.raises(ValidationError):
            Fato(**(dados | alteracao))


def test_arquivo_exige_hks_nos_identificadores() -> None:
    """RF-ING-01, D12: aceita a identidade do hub e rejeita UUID na referência ao processo."""
    dados = {
        "id": calcular_hash("arquivo"),
        "processo_id": calcular_hash("processo"),
        "enviado_por": calcular_hash("usuario"),
        "sha256": calcular_hash("pdf"),
        "tamanho_bytes": 8,
        "nome_original": "autos.pdf",
        "chave_storage": "autos/teste",
        "mime": "application/pdf",
    }
    assert Arquivo.model_validate(dados).processo_id == dados["processo_id"]
    with pytest.raises(ValidationError, match="processo_id"):
        Arquivo.model_validate(dados | {"processo_id": "00000000-0000-4000-8000-000000000000"})
