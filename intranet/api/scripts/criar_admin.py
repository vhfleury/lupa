"""Cria o único administrador do Lupa a partir de variáveis de ambiente, se ainda não existir.

Uso (no contêiner): `LUPA_ADMIN_USUARIO=... LUPA_ADMIN_SENHA=... python intranet/api/scripts/criar_admin.py`.
A senha precisa seguir a política (12+ caracteres, fora da lista comum) e será trocada no
primeiro acesso; o MFA é cadastrado no primeiro login.
"""

import os
import sys

from lupa_intranet.acesso.instalacao import criar_admin
from lupa_pipeline.config import get_settings
from lupa_pipeline.logging import configurar_logging

if __name__ == "__main__":
    configurar_logging()
    sys.exit(criar_admin(get_settings(), os.environ))
