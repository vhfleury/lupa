# ADR 0017 — Cadastro do processo pelo arquivo

| Status | Data | Responsável |
| --- | --- | --- |
| Aceito | 2026-11-15 | Projeto Lupa |

## Contexto

O número CNJ compõe a identidade do arquivo, das páginas e dos fatos. O armazenamento do original usa a chave de dados do processo. O cadastro precisa identificar o processo antes do lacre.

## Restrições

A leitura da capa ocorre durante o envio de PDF ou ZIP. Os parsers trabalham com limites de memória, CPU e tempo, em subprocessos sem credenciais e com criação de sockets bloqueada. A API tem acesso a redes diferentes das do worker. A especificação admite esse isolamento para a identificação.

## Alternativas consideradas

O cadastro manual exigia que o usuário transcrevesse número e classe em todos os envios. Adiar a identificação integralmente para o worker exigiria outro local para guardar o original enquanto a chave do processo fosse desconhecida.

## Decisão

A API inspeciona o arquivo temporário e lê as primeiras páginas com o sandbox existente. Quando falta identificação, devolve os dados lidos e o navegador reenvia o mesmo arquivo com o complemento. Uma trava transacional pelo número serializa a criação. Um processo existente conserva sua classe e sua chave. O worker extrai os seis campos da capa como fatos com evidência. As correções de classe entram no histórico do processo e acionam as validações na mesma transação.

## Consequências

O primeiro envio depende do tempo de leitura da capa. Uma tentativa incompleta transfere os bytes novamente. O servidor remove o temporário ao fim de cada tentativa. A inspeção pode recusar o arquivo antes da criação do processo. A fila e o lacre passam a receber os arquivos já associados ao processo identificado.

## Fontes

- [Especificação da 0.2, decisões 29 a 39](../especificacao/0.2/especificacao.md)
- [Plano e algoritmos A1 a A6](../planos/plano_cadastro_pelo_arquivo.md)
- [ADR 0003, sandbox de parsing](0003-sandbox-de-parsing-por-subprocesso.md)
