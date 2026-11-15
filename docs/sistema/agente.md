# Chat e dossiê

A intranet monta o contexto do processo aberto a partir das views e das evidências vigentes. As instruções e a ficha do processo são separadas dos trechos dos autos. O nome da parte e o polo aparecem como cadastrados. O dossiê reúne qualificação, linha do tempo, peças, validações e suas fontes. Campos que dependem de dados ausentes ficam sem conclusão.

## Perguntas e respostas

O usuário pode pedir um fato documentado, a localização de uma peça, um resumo com fontes ou a conta de uma validação. A política de recusa trata pedidos de minuta, julgamento, estratégia, valoração e assuntos alheios aos autos. Uma recusa é registrada antes de consultar o modelo. Os documentos são dados de consulta e suas instruções internas não autorizam o uso de ferramentas.

As ferramentas têm escopo de processo. A conferência da resposta verifica página e citação literal contra o texto guardado. Citação inválida é descartada e a interface informa quando nenhuma evidência sustenta a resposta. Resultado bloqueado coloca o chat em revisão e o desembargador pode liberar após examinar o caso.

## Limites e registro

Os tetos incluem tamanho da pergunta, turnos, páginas originais consultadas e tokens por chamada, conversa e processo. Os padrões constam em [config.py](../../pipeline/src/lupa_pipeline/config.py). As mensagens ficam no banco, vinculadas à conversa do processo. O registro de chamada guarda versão do modelo e do prompt, hashes, ferramentas, tokens, latência e resultado. A auditoria e os logs operacionais evitam reproduzir o conteúdo consultado.

A API pode enviar ao fornecedor externo trechos dos autos com nomes e outros dados que constem da página. Condições para uso de autos sigilosos e comunicação ao tribunal estão na [minuta de conformidade](../conformidade/CONFORMIDADE.md).
