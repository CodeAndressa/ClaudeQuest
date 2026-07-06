"""
Importa todos os modelos de domÃ­nio para registrÃ¡-los em Base.metadata antes do
autogenerate do Alembic. Cada novo domÃ­nio adiciona sua linha aqui.
"""

from app.domains.auth.model import Session  # noqa: F401
from app.domains.auth.password_reset import PasswordResetToken  # noqa: F401
from app.domains.gamification.badges import Badge, UserBadge  # noqa: F401
from app.domains.gamification.certificates import Certificate, UserCertificate  # noqa: F401
from app.domains.gamification.model import XpLedger  # noqa: F401
from app.domains.learning.model import (  # noqa: F401
    Alternative,
    Lesson,
    Level,
    Module,
    Question,
    Track,
    UserLessonProgress,
)
from app.domains.organizations.model import Organization  # noqa: F401
from app.domains.users.model import User  # noqa: F401
