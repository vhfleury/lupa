"""Registra as fábricas e fixtures comuns de `tests/apoio/` na suíte da pipeline.

Fase 3 (D23): `apoio_ingestao` volta à lista quando a ingestão for reescrita sobre o Data Vault
(T3.7 a T3.9); até lá ele não importa.
"""

pytest_plugins = ["apoio_comum"]
