"""
Importa todos os modelos de domínio para registrá-los em Base.metadata antes do
autogenerate do Alembic. Cada novo domínio adiciona sua linha aqui.
"""

from app.domains.auth.model import Session  # noqa: F401
from app.domains.organizations.model import Organization  # noqa: F401
from app.domains.users.model import User  # noqa: F401
