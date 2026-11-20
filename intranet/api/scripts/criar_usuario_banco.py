"""Cria ou atualiza o usuário de conexão da API (sem superusuário, membro de `lupa_app`).

Uso (no contêiner, após `alembic upgrade head`): `python intranet/api/scripts/criar_usuario_banco.py`.
Lê `LUPA_DB_USUARIO_APP` e `LUPA_DB_SENHA_APP`; conecta com `LUPA_DATABASE_URL` (dono).
"""

import sys

from lupa_api.acesso.instalacao import criar_usuario_banco
from lupa_pipeline.config import get_settings
from lupa_pipeline.logging import configurar_logging

if __name__ == "__main__":
    configurar_logging()
    sys.exit(criar_usuario_banco(get_settings()))
