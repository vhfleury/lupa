"""Cria o primeiro desembargador do Lupa a partir de variáveis de ambiente, se ainda não houver.

Uso (no contêiner `api`, depois de `alembic upgrade head` e de `criar_usuario_banco.py`):
`LUPA_DESEMBARGADOR_USUARIO=... LUPA_DESEMBARGADOR_SENHA=... python
intranet/api/scripts/criar_desembargador.py`. A senha precisa seguir a política (12+ caracteres,
fora da lista comum) e será trocada no primeiro acesso; o MFA é cadastrado no primeiro login.
Sai com a contagem de desembargadores criados no log (0 ou 1), nunca com a senha.
"""

import os
import sys

from lupa_intranet.acesso.instalacao import criar_desembargador_inicial
from lupa_pipeline.config import get_settings
from lupa_pipeline.logging import configurar_logging

if __name__ == "__main__":
    configurar_logging()
    sys.exit(criar_desembargador_inicial(get_settings(), os.environ))
