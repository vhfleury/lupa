# Destravar o Vault de desenvolvimento

Use após reiniciar o Vault e perceber saúde 503 com falha do cofre ou `vault` selado em `docker compose ps`. Execute na raiz do repositório no host da instalação, com acesso ao material criado na inicialização.

O responsável técnico opera o cofre. O ensaio de destravamento registrado em desenvolvimento ocorreu em 21/10/2026. Na 0.2, o procedimento usa o material e o modo de desenvolvimento da própria instalação.

```sh
docker compose up -d vault
bash scripts/vault_inicializar.sh --so-unseal
docker compose exec vault vault status
docker compose ps
```

1. Confirme que o Vault responde com `Sealed false`. Abra a rota `/api/saude` pelo proxy e confira o cofre.
2. Se as credenciais AppRole foram renovadas, recrie os serviços `api` e `worker` para que leiam o ambiente atualizado. Encerre o procedimento quando o campo `cofre` voltar a `ok`.
3. Uma falha de material de unseal exige recuperar o material original daquela instalação pelo canal do responsável técnico. Recriar a chave Transit tornaria as DEKs existentes indecifráveis.

Para instalação inicial, consulte o [manual de operação](../operacao/operacao.md#primeira-instalação).
