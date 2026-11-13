# Runbooks

Procedimentos operacionais com resultado observável. O nome do arquivo tem verbo e objeto:
`<verbo>-<objeto>.md`. O manual completo do responsável técnico está em
[operacao/operacao.md](../operacao/operacao.md).

| Runbook | Quando usar | Última validação |
| --- | --- | --- |
| [destravar-vault.md](destravar-vault.md) | o Vault reiniciou e `/api/saude` responde `"cofre":"falha"` | 2026-10-21 (desenvolvimento) |

Todo runbook traz: quando usar, responsável, data da última validação, pré-condições, etapas
numeradas com sinal para continuar ou parar, validação do resultado, recuperação de falha, critério
de parada e quem acionar.
