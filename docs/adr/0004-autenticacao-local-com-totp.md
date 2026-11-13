# ADR 0004 — Autenticação local com senha e TOTP

| Status | Data | Responsável |
| --- | --- | --- |
| Aceito | 2026-10-20 | Victor Hugo Fleury Barreto |

## Contexto

O desenho original previa autenticação exclusiva pelo SSO do tribunal, sem contas locais. Os requisitos da v1 definem o produto como do fornecedor: o tribunal não tem acesso ao sistema e não participa do piloto.

## Restrições

- Sem e-mail no cadastro nem no fluxo de login (requisitos, seção 3).
- MFA obrigatório.
- Nenhuma biblioteca de QR code estava autorizada no back.

## Alternativas consideradas

| Alternativa | Por que foi descartada |
| --- | --- |
| SSO do tribunal (SAML/OIDC) | O tribunal não participa do piloto; não há provedor de identidade a integrar. |
| Recuperação de senha por e-mail | Os requisitos vedam e-mail no cadastro. A recuperação é manual e registrada. |

## Decisão

Login por usuário e senha (argon2id, mínimo de 12 caracteres, fora das 10 mil mais comuns), seguido de TOTP de aplicativo autenticador. O banco guarda o SHA-256 do token de sessão. Reset de senha e de MFA é feito pelo desembargador ou pelo administrador, com credencial temporária e troca obrigatória.

## Consequências

- Cinco falhas bloqueiam por 15 minutos; usuário inexistente e senha errada recebem resposta idêntica.
- O administrador é único e só nasce por `scripts/criar_admin.py`.
- Uma cópia do banco não permite sequestrar sessões.
- Substitui, para a v1, a seção "Identidade" de [especificacao/arquitetura.md](../especificacao/arquitetura.md).

## Fontes

- [especificacao/requisitos-v1.md](../especificacao/requisitos-v1.md), seções 2 e 3
- [decisoes/registro.md](../decisoes/registro.md), Etapa 3
- `src/lupa/acesso/`
