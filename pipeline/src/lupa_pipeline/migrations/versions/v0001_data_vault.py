"""Data Vault da 0.2 (hubs, links, satélites, views e papel `lupa_app`).

Revision ID: 0001
Revises:
Create Date: 2026-11-14

O conteúdo, escrito e revisado à mão, está em `lupa_pipeline.migrations.esquema_v0001`.
"""

from lupa_pipeline.migrations.esquema_v0001 import downgrade, upgrade

__all__ = ["downgrade", "upgrade"]

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None
