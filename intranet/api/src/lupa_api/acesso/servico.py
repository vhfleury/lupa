"""Casos de uso de acesso: login em dois passos, troca e reset de senha, gestão de assessores.

Toda função recebe a sessão do banco já sob o papel `lupa_app`. Lê pelas views e grava só por
`dominio.gravacao` (D13): mudança de cadastro, credencial, sessão ou bloqueio é linha nova de
satélite (D6). Cada ação relevante grava um evento de auditoria (A14, A15).
"""

import ipaddress
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, TypedDict, Unpack

from sqlalchemy import select
from sqlalchemy.orm import Session

from lupa_api.acesso import mfa, senhas, sessoes
from lupa_api.acesso.erros import (
    ConflitoError,
    CredenciaisInvalidasError,
    DadosInvalidosError,
    LoginBloqueadoError,
    NaoAutenticadoError,
    NaoEncontradoError,
    PermissaoNegadaError,
)
from lupa_api.acesso.papeis import Permissao, tem_permissao
from lupa_api.auditoria.eventos import AcaoAuditoria, NovoEvento, ResultadoEvento
from lupa_api.auditoria.registrador import registrar
from lupa_pipeline.dominio.enums import PapelUsuario
from lupa_pipeline.dominio.esquemas import calcular_hash
from lupa_pipeline.dominio.gravacao import gravar_hub, gravar_satelite
from lupa_pipeline.dominio.tabelas import (
    hub_chave_login,
    hub_usuario,
    sat_chave_login_bloqueio,
    sat_chave_login_falha,
    sat_usuario_cadastro,
    sat_usuario_credencial,
)
from lupa_pipeline.dominio.visoes import VisaoBloqueioLogin, VisaoDesafioMfa, VisaoUsuario, atual

MAXIMO_FALHAS = 5
JANELA_FALHAS = timedelta(hours=24)
DURACOES_BLOQUEIO = (timedelta(minutes=1), timedelta(minutes=5), timedelta(minutes=15))
MAXIMO_FALHAS_IP = 20
JANELA_FALHAS_IP = timedelta(minutes=15)
PADRAO_NOME_USUARIO = re.compile(r"^[a-z0-9][a-z0-9._-]{2,63}$")
MENSAGEM_CREDENCIAIS = "usuário ou senha inválidos"
MENSAGEM_CODIGO = "código inválido"
MENSAGEM_BLOQUEIO = "muitas tentativas; tente novamente mais tarde"
ORIGEM = "intranet.acesso"


class CamposEvento(TypedDict, total=False):
    """Campos opcionais de um evento de auditoria (ver `NovoEvento`)."""

    hk_usuario: bytes | None
    hk_processo: bytes | None
    objeto_tipo: str | None
    objeto_id: str | None
    versao_modelo: str | None
    versao_prompt: str | None


@dataclass(frozen=True)
class Contexto:
    """Dados da requisição usados na auditoria.

    Attributes:
        ip: IP de origem.
        localizacao: Localização aproximada.
        agora: Instante de referência da requisição.
    """

    ip: str | None
    localizacao: str | None
    agora: datetime


@dataclass(frozen=True)
class Ator:
    """Usuário autenticado que executa a ação.

    Attributes:
        hk_usuario: Chave do usuário.
        usuario_id: Hex do `hk_usuario` (D12).
        papel: Papel.
        nome_usuario: Nome de usuário.
        hk_sessao: Sessão corrente.
        troca_senha_obrigatoria: Se a única ação permitida é trocar a senha.
    """

    hk_usuario: bytes
    usuario_id: str
    papel: PapelUsuario
    nome_usuario: str
    hk_sessao: bytes
    troca_senha_obrigatoria: bool = False


@dataclass(frozen=True)
class ResultadoSenha:
    """Resultado do primeiro passo do login.

    Attributes:
        desafio: Token a enviar no segundo passo.
        provisionamento: Dados do autenticador quando o MFA ainda não foi configurado.
    """

    desafio: str
    provisionamento: mfa.ProvisionamentoMfa | None


@dataclass(frozen=True)
class ResultadoLogin:
    """Resultado do segundo passo do login.

    Attributes:
        token: Token da sessão criada.
        troca_senha_obrigatoria: Se o usuário precisa trocar a senha agora.
    """

    token: str
    troca_senha_obrigatoria: bool


@dataclass(frozen=True)
class UsuarioComSenha:
    """Usuário recém-criado ou resetado com a senha temporária (exibida uma única vez).

    Attributes:
        usuario: Usuário como está na view.
        senha_temporaria: Senha temporária.
    """

    usuario: VisaoUsuario
    senha_temporaria: str


def auditar(
    session: Session,
    ctx: Contexto,
    acao: AcaoAuditoria,
    resultado: ResultadoEvento = ResultadoEvento.OK,
    **campos: Unpack[CamposEvento],
) -> None:
    """Registra um evento com IP e localização do contexto.

    Args:
        session: Sessão do banco.
        ctx: Contexto da requisição.
        acao: Ação auditada.
        resultado: Desfecho.
        **campos: Demais campos de `NovoEvento`.
    """
    evento = NovoEvento.model_validate(
        {"acao": acao, "resultado": resultado, "ip": ctx.ip, "localizacao": ctx.localizacao}
        | dict(campos)
    )
    registrar(session, evento)


def ler_usuario(session: Session, hk_usuario: bytes) -> VisaoUsuario | None:
    """Lê o usuário corrente pela view, relendo o que a sessão já tinha carregado.

    Args:
        session: Sessão do banco.
        hk_usuario: Usuário.

    Returns:
        O usuário, ou None se não existe.
    """
    consulta = select(VisaoUsuario).where(VisaoUsuario.hk_usuario == hk_usuario)
    return session.scalars(atual(consulta)).one_or_none()


def _localizar(session: Session, nome_usuario: str) -> VisaoUsuario | None:
    consulta = select(VisaoUsuario).where(VisaoUsuario.nome_usuario == nome_usuario)
    return session.scalars(atual(consulta)).one_or_none()


def _credencial(usuario: VisaoUsuario) -> dict[str, Any]:
    return {
        "senha_hash": usuario.senha_hash,
        "troca_senha_obrigatoria": usuario.troca_senha_obrigatoria,
        "mfa_segredo": usuario.mfa_segredo,
        "mfa_confirmado": usuario.mfa_confirmado,
        "mfa_ultimo_passo": usuario.mfa_ultimo_passo,
    }


def _atualizar_credencial(session: Session, usuario: VisaoUsuario, **mudancas: Any) -> VisaoUsuario:
    atributos = _credencial(usuario) | mudancas
    gravar_satelite(session, sat_usuario_credencial, usuario.hk_usuario, atributos, ORIGEM)
    relido = ler_usuario(session, usuario.hk_usuario)
    if relido is None:
        raise NaoEncontradoError("usuário não encontrado")
    return relido


def _atualizar_cadastro(session: Session, usuario: VisaoUsuario, ativo: bool) -> VisaoUsuario:
    atributos = {"papel": usuario.papel, "ativo": ativo}
    gravar_satelite(session, sat_usuario_cadastro, usuario.hk_usuario, atributos, ORIGEM)
    relido = ler_usuario(session, usuario.hk_usuario)
    if relido is None:
        raise NaoEncontradoError("usuário não encontrado")
    return relido


def _chave(nome_usuario: str) -> str:
    return calcular_hash(nome_usuario.strip().lower())


def _chave_ip(ip: str | None) -> str | None:
    """Chave do rate limit por IP; None quando não há IP utilizável (ex.: cliente de teste)."""
    if ip is None:
        return None
    try:
        endereco = ipaddress.ip_address(ip)
    except ValueError:
        return None
    return calcular_hash(f"ip:{endereco.compressed}")


def _estado_chave(session: Session, chave: str) -> VisaoBloqueioLogin | None:
    consulta = select(VisaoBloqueioLogin).where(VisaoBloqueioLogin.chave == chave)
    return session.scalars(atual(consulta)).one_or_none()


def _contar_falhas(session: Session, chave: str, desde: datetime) -> int:
    estado = _estado_chave(session, chave)
    if estado is None:
        return 0
    return sum(1 for instante in estado.falhas if instante > desde)


def _hub_chave(session: Session, chave: str) -> bytes:
    return gravar_hub(session, hub_chave_login, {"chave": chave}, ORIGEM)


def _gravar_falha(session: Session, chave: str) -> None:
    gravar_satelite(session, sat_chave_login_falha, _hub_chave(session, chave), {}, ORIGEM)


def _gravar_bloqueio(session: Session, chave: str, ate: datetime | None) -> None:
    atributos = {"bloqueado_ate": ate}
    gravar_satelite(
        session, sat_chave_login_bloqueio, _hub_chave(session, chave), atributos, ORIGEM
    )


def _zerar_falhas(session: Session, chave: str, agora: datetime) -> None:
    if _contar_falhas(session, chave, agora - JANELA_FALHAS):
        _gravar_bloqueio(session, chave, None)


def duracao_bloqueio(falhas: int) -> timedelta | None:
    """Duração do bloqueio por nome depois de `falhas` falhas seguidas (progressivo).

    A 5ª falha bloqueia por 1 minuto, a 10ª por 5 e a 15ª (e cada 5 a mais) por 15 minutos.
    As falhas só zeram com um login certo ou depois de 24 horas sem falhar.

    Args:
        falhas: Falhas consecutivas na janela.

    Returns:
        Duração do bloqueio, ou None se a contagem não fecha um ciclo de 5.
    """
    if falhas == 0 or falhas % MAXIMO_FALHAS:
        return None
    nivel = min(falhas // MAXIMO_FALHAS, len(DURACOES_BLOQUEIO)) - 1
    return DURACOES_BLOQUEIO[nivel]


def _campos_usuario(usuario: VisaoUsuario | None) -> CamposEvento:
    if usuario is None:
        return {"objeto_tipo": "usuario"}
    return {"hk_usuario": usuario.hk_usuario, "objeto_tipo": "usuario", "objeto_id": usuario.id}


def _registrar_falha(
    session: Session,
    chave: str,
    usuario: VisaoUsuario | None,
    ctx: Contexto,
    acao: AcaoAuditoria,
) -> None:
    _gravar_falha(session, chave)
    chave_ip = _chave_ip(ctx.ip)
    if chave_ip is not None:
        _gravar_falha(session, chave_ip)
    auditar(session, ctx, acao, ResultadoEvento.FALHA, **_campos_usuario(usuario))
    if (
        chave_ip is not None
        and _contar_falhas(session, chave_ip, ctx.agora - JANELA_FALHAS_IP) == MAXIMO_FALHAS_IP
    ):
        auditar(
            session, ctx, AcaoAuditoria.LOGIN_BLOQUEADO, ResultadoEvento.BLOQUEADO, objeto_tipo="ip"
        )
    duracao = duracao_bloqueio(_contar_falhas(session, chave, ctx.agora - JANELA_FALHAS))
    if duracao is None:
        return
    _gravar_bloqueio(session, chave, ctx.agora + duracao)
    auditar(
        session,
        ctx,
        AcaoAuditoria.LOGIN_BLOQUEADO,
        ResultadoEvento.BLOQUEADO,
        **_campos_usuario(usuario),
    )


def _recusar_se_ip_excedido(session: Session, ctx: Contexto) -> None:
    chave_ip = _chave_ip(ctx.ip)
    if chave_ip is None:
        return
    if _contar_falhas(session, chave_ip, ctx.agora - JANELA_FALHAS_IP) < MAXIMO_FALHAS_IP:
        return
    auditar(session, ctx, AcaoAuditoria.LOGIN_FALHA, ResultadoEvento.BLOQUEADO, objeto_tipo="ip")
    raise LoginBloqueadoError(MENSAGEM_BLOQUEIO)


def _recusar_se_bloqueado(
    session: Session, chave: str, usuario: VisaoUsuario | None, ctx: Contexto
) -> None:
    estado = _estado_chave(session, chave)
    if estado is None or estado.bloqueado_ate is None or estado.bloqueado_ate <= ctx.agora:
        return
    auditar(
        session,
        ctx,
        AcaoAuditoria.LOGIN_FALHA,
        ResultadoEvento.BLOQUEADO,
        **_campos_usuario(usuario),
    )
    raise LoginBloqueadoError(MENSAGEM_BLOQUEIO)


def _senha_confere(usuario: VisaoUsuario | None, senha: str) -> bool:
    if usuario is None or usuario.senha_hash is None:
        senhas.verificar_senha(senhas.hash_ficticio(), senha)
        return False
    return senhas.verificar_senha(usuario.senha_hash, senha) and bool(usuario.ativo)


def _iniciar_mfa(
    session: Session, usuario: VisaoUsuario
) -> tuple[VisaoUsuario, mfa.ProvisionamentoMfa | None]:
    if usuario.mfa_confirmado and usuario.mfa_segredo:
        return usuario, None
    segredo = mfa.gerar_segredo()
    usuario = _atualizar_credencial(session, usuario, mfa_segredo=segredo, mfa_ultimo_passo=None)
    return usuario, mfa.provisionar(segredo, usuario.nome_usuario)


def autenticar_senha(
    session: Session, nome_usuario: str, senha: str, ctx: Contexto
) -> ResultadoSenha:
    """Primeiro passo do login: confere a senha e emite o desafio do TOTP (A14, passos 1 a 5).

    Usuário inexistente, inativo e senha errada produzem o mesmo erro e contam igualmente para
    o bloqueio progressivo por nome (5 falhas: 1 min; 10: 5 min; 15: 15 min). Além disso, 20
    falhas do mesmo IP em 15 minutos recusam qualquer login desse IP (rate limit por IP).

    Args:
        session: Sessão do banco.
        nome_usuario: Nome de usuário.
        senha: Senha informada.
        ctx: Contexto da requisição.

    Returns:
        Token do desafio e, no primeiro acesso, os dados para cadastrar o autenticador.

    Raises:
        LoginBloqueadoError: Se o nome ou o IP estiver bloqueado.
        CredenciaisInvalidasError: Se a senha não conferir.
    """
    _recusar_se_ip_excedido(session, ctx)
    chave = _chave(nome_usuario)
    usuario = _localizar(session, nome_usuario)
    _recusar_se_bloqueado(session, chave, usuario, ctx)
    if usuario is None or not _senha_confere(usuario, senha):
        _registrar_falha(session, chave, usuario, ctx, AcaoAuditoria.LOGIN_FALHA)
        raise CredenciaisInvalidasError(MENSAGEM_CREDENCIAIS)
    _zerar_falhas(session, chave, ctx.agora)
    if usuario.senha_hash is not None and senhas.precisa_rehash(usuario.senha_hash):
        usuario = _atualizar_credencial(session, usuario, senha_hash=senhas.gerar_hash(senha))
    usuario, provisionamento = _iniciar_mfa(session, usuario)
    auditar(session, ctx, AcaoAuditoria.LOGIN_OK, **_campos_usuario(usuario))
    return ResultadoSenha(sessoes.criar_desafio(session, usuario, ctx.agora), provisionamento)


def _usuario_do_desafio(
    session: Session, token: str, ctx: Contexto
) -> tuple[VisaoUsuario, VisaoDesafioMfa]:
    desafio = sessoes.carregar_desafio(session, token, ctx.agora)
    if desafio is None:
        raise CredenciaisInvalidasError(MENSAGEM_CODIGO)
    usuario = ler_usuario(session, desafio.hk_usuario)
    if usuario is None or not usuario.ativo or not usuario.mfa_segredo:
        raise CredenciaisInvalidasError(MENSAGEM_CODIGO)
    return usuario, desafio


def concluir_mfa(
    session: Session, token_desafio: str, codigo: str, ctx: Contexto, *, confirmando: bool
) -> ResultadoLogin:
    """Segundo passo do login: confere o TOTP e só então cria a sessão (A14, passos 6 e 7).

    Args:
        session: Sessão do banco.
        token_desafio: Token emitido no primeiro passo.
        codigo: Código TOTP.
        ctx: Contexto da requisição.
        confirmando: Verdadeiro no primeiro cadastro do autenticador (`/auth/mfa/confirmar`).

    Returns:
        Token da sessão e se a troca de senha é obrigatória.

    Raises:
        CredenciaisInvalidasError: Desafio inválido ou código errado/reutilizado.
        LoginBloqueadoError: Se o nome estiver bloqueado.
    """
    _recusar_se_ip_excedido(session, ctx)
    usuario, desafio = _usuario_do_desafio(session, token_desafio, ctx)
    chave = _chave(usuario.nome_usuario)
    _recusar_se_bloqueado(session, chave, usuario, ctx)
    if bool(usuario.mfa_confirmado) == confirmando:
        raise CredenciaisInvalidasError(MENSAGEM_CODIGO)
    passo = mfa.verificar_codigo(
        str(usuario.mfa_segredo), codigo, usuario.mfa_ultimo_passo, ctx.agora
    )
    if passo is None:
        _registrar_falha(session, chave, usuario, ctx, AcaoAuditoria.MFA_FALHA)
        raise CredenciaisInvalidasError(MENSAGEM_CODIGO)
    usuario = _atualizar_credencial(session, usuario, mfa_ultimo_passo=passo, mfa_confirmado=True)
    sessoes.consumir_desafio(session, desafio)
    _zerar_falhas(session, chave, ctx.agora)
    token = sessoes.criar_sessao(session, usuario, ctx.ip, ctx.agora)
    auditar(session, ctx, AcaoAuditoria.MFA_OK, **_campos_usuario(usuario))
    return ResultadoLogin(token, bool(usuario.troca_senha_obrigatoria))


def sair(session: Session, ator: Ator, ctx: Contexto) -> None:
    """Revoga a sessão corrente.

    Args:
        session: Sessão do banco.
        ator: Usuário autenticado.
        ctx: Contexto da requisição.
    """
    sessoes.revogar_sessao(session, ator.hk_sessao)
    auditar(session, ctx, AcaoAuditoria.LOGOUT, hk_usuario=ator.hk_usuario)


def trocar_senha(
    session: Session, ator: Ator, senha_atual: str, nova_senha: str, ctx: Contexto
) -> None:
    """Troca a senha do próprio usuário e revoga as demais sessões dele.

    Args:
        session: Sessão do banco.
        ator: Usuário autenticado.
        senha_atual: Senha em uso (ou a temporária).
        nova_senha: Nova senha.
        ctx: Contexto da requisição.

    Raises:
        NaoAutenticadoError: Usuário da sessão não existe mais.
        CredenciaisInvalidasError: Se a senha atual não conferir.
        DadosInvalidosError: Se a nova senha violar a política ou repetir a atual.
    """
    usuario = ler_usuario(session, ator.hk_usuario)
    if usuario is None or usuario.senha_hash is None:
        raise NaoAutenticadoError("sessão inválida")
    if not senhas.verificar_senha(usuario.senha_hash, senha_atual):
        falha = ResultadoEvento.FALHA
        auditar(session, ctx, AcaoAuditoria.SENHA_TROCADA, falha, hk_usuario=ator.hk_usuario)
        raise CredenciaisInvalidasError("senha atual inválida")
    if nova_senha == senha_atual:
        raise DadosInvalidosError("a nova senha deve ser diferente da atual")
    try:
        senhas.validar_politica(nova_senha, usuario.nome_usuario)
    except senhas.SenhaFracaError as erro:
        raise DadosInvalidosError(str(erro)) from erro
    _atualizar_credencial(
        session, usuario, senha_hash=senhas.gerar_hash(nova_senha), troca_senha_obrigatoria=False
    )
    sessoes.revogar_sessoes_do_usuario(session, usuario.hk_usuario, exceto=ator.hk_sessao)
    auditar(session, ctx, AcaoAuditoria.SENHA_TROCADA, hk_usuario=ator.hk_usuario)


def _exigir(ator: Ator, permissao: Permissao) -> None:
    if not tem_permissao(ator.papel, permissao):
        raise PermissaoNegadaError("ação não permitida para o seu papel")


def listar_usuarios(session: Session, ator: Ator) -> list[VisaoUsuario]:
    """Lista todos os usuários (só desembargador; RF-ACE-03).

    Args:
        session: Sessão do banco.
        ator: Usuário autenticado.

    Returns:
        Usuários ordenados por nome.

    Raises:
        PermissaoNegadaError: Se o papel não gere assessores.
    """
    _exigir(ator, Permissao.GERIR_ASSESSOR)
    consulta = select(VisaoUsuario).order_by(VisaoUsuario.nome_usuario)
    return list(session.scalars(atual(consulta)))


def _validar_nome(session: Session, nome_usuario: str) -> None:
    if not PADRAO_NOME_USUARIO.fullmatch(nome_usuario):
        raise DadosInvalidosError("nome de usuário: 3 a 64 caracteres em a-z, 0-9, '.', '_', '-'")
    if _localizar(session, nome_usuario) is not None:
        raise ConflitoError("nome de usuário já em uso")


def _gravar_usuario(
    session: Session, nome_usuario: str, papel: PapelUsuario, senha: str
) -> VisaoUsuario:
    hk = gravar_hub(session, hub_usuario, {"nome_usuario": nome_usuario}, ORIGEM)
    cadastro = {"papel": papel.value, "ativo": True}
    gravar_satelite(session, sat_usuario_cadastro, hk, cadastro, ORIGEM)
    credencial = {
        "senha_hash": senhas.gerar_hash(senha),
        "troca_senha_obrigatoria": True,
        "mfa_segredo": None,
        "mfa_confirmado": False,
        "mfa_ultimo_passo": None,
    }
    gravar_satelite(session, sat_usuario_credencial, hk, credencial, ORIGEM)
    usuario = ler_usuario(session, hk)
    if usuario is None:
        raise NaoEncontradoError("usuário não encontrado")
    return usuario


def _auditar_sobre(
    session: Session, ctx: Contexto, acao: AcaoAuditoria, ator: Ator, alvo: VisaoUsuario
) -> None:
    auditar(
        session,
        ctx,
        acao,
        hk_usuario=ator.hk_usuario,
        objeto_tipo="usuario",
        objeto_id=alvo.id,
    )


def criar_usuario(
    session: Session, ator: Ator, nome_usuario: str, papel: PapelUsuario, ctx: Contexto
) -> UsuarioComSenha:
    """Cria assessor com senha temporária e troca obrigatória (RF-ACE-04).

    O desembargador só é criado pelo script de instalação (RF-ACE-05).

    Args:
        session: Sessão do banco.
        ator: Quem cria.
        nome_usuario: Nome de usuário.
        papel: Papel do novo usuário; só `assessor` é aceito.
        ctx: Contexto da requisição.

    Returns:
        O usuário criado e a senha temporária.

    Raises:
        PermissaoNegadaError: Se o ator não gere assessores ou o papel não é assessor.
        DadosInvalidosError: Nome inválido.
        ConflitoError: Nome em uso.
    """
    if not tem_permissao(ator.papel, Permissao.GERIR_ASSESSOR) or papel != PapelUsuario.ASSESSOR:
        negado = ResultadoEvento.NEGADO
        auditar(session, ctx, AcaoAuditoria.USUARIO_CRIADO, negado, hk_usuario=ator.hk_usuario)
        raise PermissaoNegadaError("ação não permitida para o seu papel")
    _validar_nome(session, nome_usuario)
    senha = senhas.gerar_senha_temporaria()
    usuario = _gravar_usuario(session, nome_usuario, papel, senha)
    _auditar_sobre(session, ctx, AcaoAuditoria.USUARIO_CRIADO, ator, usuario)
    return UsuarioComSenha(usuario, senha)


def _assessor_gerido(
    session: Session, ator: Ator, alvo_id: str, permissao: Permissao
) -> VisaoUsuario:
    _exigir(ator, permissao)
    consulta = select(VisaoUsuario).where(VisaoUsuario.id == alvo_id)
    alvo = session.scalars(atual(consulta)).one_or_none()
    if alvo is None:
        raise NaoEncontradoError("usuário não encontrado")
    if alvo.hk_usuario == ator.hk_usuario or alvo.papel != PapelUsuario.ASSESSOR.value:
        raise PermissaoNegadaError("ação não permitida sobre este usuário")
    return alvo


def alterar_ativo(
    session: Session, ator: Ator, alvo_id: str, ativo: bool, ctx: Contexto
) -> VisaoUsuario:
    """Desativa ou reativa um assessor; desativar revoga as sessões e não apaga nada.

    Args:
        session: Sessão do banco.
        ator: Quem executa.
        alvo_id: Hex do `hk_usuario` do assessor.
        ativo: Novo estado.
        ctx: Contexto da requisição.

    Returns:
        O usuário alterado.
    """
    alvo = _assessor_gerido(session, ator, alvo_id, Permissao.GERIR_ASSESSOR)
    alvo = _atualizar_cadastro(session, alvo, ativo)
    if not ativo:
        sessoes.revogar_sessoes_do_usuario(session, alvo.hk_usuario)
    acao = AcaoAuditoria.USUARIO_REATIVADO if ativo else AcaoAuditoria.USUARIO_DESATIVADO
    _auditar_sobre(session, ctx, acao, ator, alvo)
    return alvo


def resetar_senha(session: Session, ator: Ator, alvo_id: str, ctx: Contexto) -> UsuarioComSenha:
    """Gera senha temporária com troca obrigatória e revoga as sessões do assessor.

    Args:
        session: Sessão do banco.
        ator: Quem executa.
        alvo_id: Hex do `hk_usuario` do assessor.
        ctx: Contexto da requisição.

    Returns:
        O usuário e a senha temporária.
    """
    alvo = _assessor_gerido(session, ator, alvo_id, Permissao.RESETAR_ASSESSOR)
    senha = senhas.gerar_senha_temporaria()
    alvo = _atualizar_credencial(
        session, alvo, senha_hash=senhas.gerar_hash(senha), troca_senha_obrigatoria=True
    )
    sessoes.revogar_sessoes_do_usuario(session, alvo.hk_usuario)
    _auditar_sobre(session, ctx, AcaoAuditoria.SENHA_RESETADA, ator, alvo)
    return UsuarioComSenha(alvo, senha)


def resetar_mfa(session: Session, ator: Ator, alvo_id: str, ctx: Contexto) -> VisaoUsuario:
    """Apaga o segredo TOTP do assessor; o próximo login cadastra um novo autenticador.

    Args:
        session: Sessão do banco.
        ator: Quem executa.
        alvo_id: Hex do `hk_usuario` do assessor.
        ctx: Contexto da requisição.

    Returns:
        O usuário alterado.
    """
    alvo = _assessor_gerido(session, ator, alvo_id, Permissao.RESETAR_ASSESSOR)
    alvo = _atualizar_credencial(
        session, alvo, mfa_segredo=None, mfa_confirmado=False, mfa_ultimo_passo=None
    )
    sessoes.revogar_sessoes_do_usuario(session, alvo.hk_usuario)
    _auditar_sobre(session, ctx, AcaoAuditoria.MFA_RESETADO, ator, alvo)
    return alvo


def criar_desembargador(session: Session, nome_usuario: str, senha: str, ctx: Contexto) -> bool:
    """Cria o primeiro desembargador, se ainda não houver nenhum (A14, passo 11; RF-ACE-05).

    Args:
        session: Sessão do banco sob `lupa_app`.
        nome_usuario: Nome do desembargador.
        senha: Senha inicial (troca obrigatória no primeiro acesso).
        ctx: Contexto (IP None quando rodado por script).

    Returns:
        Verdadeiro se criou; falso se já havia desembargador.

    Raises:
        DadosInvalidosError: Nome ou senha fora da política.
        ConflitoError: Nome já em uso por um assessor.
    """
    papel = PapelUsuario.DESEMBARGADOR
    existente = session.scalar(select(VisaoUsuario.hk_usuario).where(VisaoUsuario.papel == papel))
    if existente is not None:
        return False
    _validar_nome(session, nome_usuario)
    try:
        senhas.validar_politica(senha, nome_usuario)
    except senhas.SenhaFracaError as erro:
        raise DadosInvalidosError(str(erro)) from erro
    usuario = _gravar_usuario(session, nome_usuario, papel, senha)
    auditar(
        session,
        ctx,
        AcaoAuditoria.USUARIO_CRIADO,
        hk_usuario=usuario.hk_usuario,
        objeto_tipo="usuario",
        objeto_id=usuario.id,
    )
    return True
