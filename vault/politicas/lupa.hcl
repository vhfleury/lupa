# Política mínima do AppRole da aplicação: só o Transit, só a chave única `lupa` (D14).
# Criar (idempotente), ler e configurar a chave; cifrar, decifrar e recifrar (rewrap) a DEK de
# cada processo. Sem apagar a chave: a rotação e o resto da gestão são do responsável técnico.
# Nada de exportar chave, nada de outros engines, nada de sys/.
path "transit/keys/lupa" {
  capabilities = ["create", "read", "update"]
}
path "transit/encrypt/lupa" {
  capabilities = ["update"]
}
path "transit/decrypt/lupa" {
  capabilities = ["update"]
}
path "transit/rewrap/lupa" {
  capabilities = ["update"]
}
# Etapa 8.1: chave de verificação de saúde. Só cifrar e decifrar (a chave é criada pelo
# vault_inicializar com o token raiz; a aplicação não a cria nem apaga).
path "transit/encrypt/lupa-saude" {
  capabilities = ["update"]
}
path "transit/decrypt/lupa-saude" {
  capabilities = ["update"]
}
