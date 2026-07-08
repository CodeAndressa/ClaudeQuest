"""Certificados (GAME-006).

Escopo desta entrega — ver `08 - Gamification/Gamification.md.md` (seção "Certificados")
e `05 - Database/Database Specification.md.md` (seções "Certificates" / "User Certificates").

Reúne model, repository, service e schemas num único arquivo por decisão explícita da
tarefa (evita conflito de merge com o agente paralelo que está criando `badges.py` na
mesma pasta).

Duas limitações deliberadas, documentadas aqui e no relatório final da tarefa:

1. **Sem geração real de PDF/QR Code.** `UserCertificate.pdf_url` fica sempre `None`.
   A geração do arquivo (motor de PDF + QR Code de verificação) é o epico CERT-001,
   fora do escopo desta tarefa — aqui só existe o registro/catálogo e a emissão manual.
2. **Emissão é sempre manual (admin-only), nunca automática por "100% da trilha".**
   A regra de negócio correta ("emitir automaticamente quando o usuário completa 100%
   de uma trilha") depende do sistema de progresso (`UserProgress`), que ainda não
   existe no código (mesma lacuna apontada pelo agente de Badges, que depende do mesmo
   sistema para conceder badges de conclusão). Enquanto isso não existir, a emissão
   fica exposta apenas como uma ação administrativa explícita via
   `POST /certificates/{certificate_id}/issue`.
"""

import secrets
import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy import DateTime, ForeignKey, Integer, String, select
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import AuditedModel
from app.database.session import get_db_session
from app.domains.auth.dependencies import get_current_user
from app.domains.users.model import User, UserRole
from app.shared.errors import AppError
from app.shared.response import success_response
from app.shared.schemas import SuccessResponse

# --------------------------------------------------------------------------- #
# Models
# --------------------------------------------------------------------------- #


class Certificate(AuditedModel):
    """Catálogo de certificados emitíveis, um por trilha.

    (05 - Database/Database Specification.md.md, seção "Certificates"). O campo
    `template` previsto no documento original não é implementado aqui — pertence
    à geração real de PDF (fora de escopo, ver módulo docstring).
    """

    __tablename__ = "certificates"

    track_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tracks.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String, nullable=False)
    hours: Mapped[int] = mapped_column(Integer, nullable=False)


class UserCertificate(AuditedModel):
    """Emissão de um certificado para um usuário específico.

    (05 - Database/Database Specification.md.md, seção "User Certificates").
    `validation_code` é único e gerado no momento da emissão — é o que permite a
    validação pública (sem autenticação) via
    `GET /certificates/validate/{validation_code}`. `pdf_url` fica sempre `None`
    nesta entrega (ver módulo docstring).
    """

    __tablename__ = "user_certificates"

    certificate_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("certificates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    validation_code: Mapped[str] = mapped_column(String, nullable=False, unique=True, index=True)
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    pdf_url: Mapped[str | None] = mapped_column(String, default=None)


def generate_validation_code() -> str:
    """Gera um código de validação único e opaco (não é o PDF em si, apenas o código).

    `secrets.token_urlsafe` é criptograficamente seguro e produz uma string curta,
    própria para digitação manual num formulário de validação pública.
    """

    return secrets.token_urlsafe(16)


# --------------------------------------------------------------------------- #
# Schemas
# --------------------------------------------------------------------------- #


class IssueCertificateRequest(BaseModel):
    """Body de `POST /certificates/{certificate_id}/issue`."""

    user_id: uuid.UUID


class UserCertificateResponse(BaseModel):
    """Um certificado emitido, na perspectiva do próprio usuário (`GET /me/certificates`)."""

    id: uuid.UUID
    certificate_id: uuid.UUID
    title: str
    hours: int
    validation_code: str
    issued_at: datetime
    pdf_url: str | None


class CertificateValidationResponse(BaseModel):
    """Resultado de uma validação pública de certificado (sem autenticação)."""

    valid: bool
    user_name: str
    title: str
    hours: int
    issued_at: datetime


# --------------------------------------------------------------------------- #
# Repository
# --------------------------------------------------------------------------- #


class CertificateRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, *, track_id: uuid.UUID, title: str, hours: int) -> Certificate:
        """Cria uma entrada de catálogo de certificado (ainda sem PDF/QR Code — ver
        docstring do módulo). Usada hoje só pelos scripts de seed; um endpoint de
        gestão de catálogo fica para o Admin Portal (ADMIN-002)."""
        certificate = Certificate(track_id=track_id, title=title, hours=hours)
        self._session.add(certificate)
        await self._session.flush()
        return certificate

    async def get_by_id(self, certificate_id: uuid.UUID) -> Certificate | None:
        statement = select(Certificate).where(
            Certificate.id == certificate_id, Certificate.deleted_at.is_(None)
        )
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def list_for_track(self, track_id: uuid.UUID) -> list[Certificate]:
        statement = select(Certificate).where(
            Certificate.track_id == track_id,
            Certificate.deleted_at.is_(None),
        )
        result = await self._session.execute(statement)
        return list(result.scalars().all())

    async def get_issued(
        self, *, certificate_id: uuid.UUID, user_id: uuid.UUID
    ) -> UserCertificate | None:
        statement = select(UserCertificate).where(
            UserCertificate.certificate_id == certificate_id,
            UserCertificate.user_id == user_id,
            UserCertificate.deleted_at.is_(None),
        )
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def issue(
        self, *, certificate_id: uuid.UUID, user_id: uuid.UUID, issued_at: datetime
    ) -> UserCertificate:
        existing = await self.get_issued(certificate_id=certificate_id, user_id=user_id)
        if existing is not None:
            return existing

        user_certificate = UserCertificate(
            certificate_id=certificate_id,
            user_id=user_id,
            validation_code=generate_validation_code(),
            issued_at=issued_at,
            pdf_url=None,
        )
        self._session.add(user_certificate)
        await self._session.flush()
        return user_certificate

    async def list_for_user(self, user_id: uuid.UUID) -> list[tuple[UserCertificate, Certificate]]:
        statement = (
            select(UserCertificate, Certificate)
            .join(Certificate, Certificate.id == UserCertificate.certificate_id)
            .where(
                UserCertificate.user_id == user_id,
                UserCertificate.deleted_at.is_(None),
                Certificate.deleted_at.is_(None),
            )
            .order_by(UserCertificate.issued_at.desc())
        )
        result = await self._session.execute(statement)
        return [(row.UserCertificate, row.Certificate) for row in result]

    async def get_by_validation_code(
        self, validation_code: str
    ) -> tuple[UserCertificate, Certificate] | None:
        statement = (
            select(UserCertificate, Certificate)
            .join(Certificate, Certificate.id == UserCertificate.certificate_id)
            .where(
                UserCertificate.validation_code == validation_code,
                UserCertificate.deleted_at.is_(None),
                Certificate.deleted_at.is_(None),
            )
        )
        result = await self._session.execute(statement)
        row = result.first()
        if row is None:
            return None
        return row.UserCertificate, row.Certificate


async def issue_completed_track_certificates(
    session: AsyncSession, *, user_id: uuid.UUID, track_id: uuid.UUID
) -> list[UserCertificate]:
    """Emite certificados de uma trilha concluída, sem duplicar emissões existentes."""

    repository = CertificateRepository(session)
    certificates = await repository.list_for_track(track_id)
    issued: list[UserCertificate] = []
    for certificate in certificates:
        user_certificate = await repository.issue(
            certificate_id=certificate.id,
            user_id=user_id,
            issued_at=datetime.now(UTC),
        )
        issued.append(user_certificate)
    return issued


class UserLookupRepository:
    """Busca mínima de usuário.

    Isolada para não depender de `UserRepository` do domínio users além do
    necessário — só precisamos do nome para a resposta de validação pública.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_name(self, user_id: uuid.UUID) -> str | None:
        statement = select(User.name).where(User.id == user_id, User.deleted_at.is_(None))
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()


# --------------------------------------------------------------------------- #
# Service
# --------------------------------------------------------------------------- #


_CERTIFICATE_NOT_FOUND = AppError(
    code="certificate_not_found",
    message="Certificado não encontrado.",
    status_code=404,
)

_VALIDATION_CODE_NOT_FOUND = AppError(
    code="invalid_validation_code",
    message="Código de validação inválido ou não encontrado.",
    status_code=404,
)

_FORBIDDEN = AppError(
    code="forbidden",
    message="Apenas administradores podem emitir certificados.",
    status_code=403,
)


class CertificateService:
    def __init__(
        self,
        certificate_repository: CertificateRepository,
        user_lookup_repository: UserLookupRepository,
    ) -> None:
        self._certificates = certificate_repository
        self._users = user_lookup_repository

    async def issue_certificate(
        self, *, certificate_id: uuid.UUID, user_id: uuid.UUID
    ) -> UserCertificateResponse:
        certificate = await self._certificates.get_by_id(certificate_id)
        if certificate is None:
            raise _CERTIFICATE_NOT_FOUND

        issued = await self._certificates.issue(
            certificate_id=certificate_id,
            user_id=user_id,
            issued_at=datetime.now(certificate.created_at.tzinfo),
        )

        return UserCertificateResponse(
            id=issued.id,
            certificate_id=certificate.id,
            title=certificate.title,
            hours=certificate.hours,
            validation_code=issued.validation_code,
            issued_at=issued.issued_at,
            pdf_url=issued.pdf_url,
        )

    async def list_my_certificates(self, user_id: uuid.UUID) -> list[UserCertificateResponse]:
        rows = await self._certificates.list_for_user(user_id)
        return [
            UserCertificateResponse(
                id=user_certificate.id,
                certificate_id=certificate.id,
                title=certificate.title,
                hours=certificate.hours,
                validation_code=user_certificate.validation_code,
                issued_at=user_certificate.issued_at,
                pdf_url=user_certificate.pdf_url,
            )
            for user_certificate, certificate in rows
        ]

    async def validate_code(self, validation_code: str) -> CertificateValidationResponse:
        row = await self._certificates.get_by_validation_code(validation_code)
        if row is None:
            raise _VALIDATION_CODE_NOT_FOUND

        user_certificate, certificate = row
        user_name = await self._users.get_name(user_certificate.user_id)
        if user_name is None:
            # Usuário foi removido (soft delete) após a emissão: o certificado em si
            # continua existindo como registro histórico, mas não há nome para exibir.
            raise _VALIDATION_CODE_NOT_FOUND

        return CertificateValidationResponse(
            valid=True,
            user_name=user_name,
            title=certificate.title,
            hours=certificate.hours,
            issued_at=user_certificate.issued_at,
        )


# --------------------------------------------------------------------------- #
# Router
# --------------------------------------------------------------------------- #

router = APIRouter(prefix="/gamification", tags=["certificates"])


def get_certificate_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> CertificateService:
    return CertificateService(CertificateRepository(session), UserLookupRepository(session))


@router.get("/me/certificates")
async def list_my_certificates(
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    certificate_service: Annotated[CertificateService, Depends(get_certificate_service)],
) -> SuccessResponse[list[UserCertificateResponse]]:
    certificates = await certificate_service.list_my_certificates(current_user.id)
    return success_response(request, "Certificados recuperados com sucesso.", certificates)


@router.get("/certificates/validate/{validation_code}")
async def validate_certificate(
    request: Request,
    validation_code: str,
    certificate_service: Annotated[CertificateService, Depends(get_certificate_service)],
) -> SuccessResponse[CertificateValidationResponse]:
    # Endpoint público, sem autenticação: existe para que terceiros (ex.: um recrutador)
    # possam conferir a validade de um certificado compartilhado pelo usuário.
    result = await certificate_service.validate_code(validation_code)
    return success_response(request, "Certificado válido.", result)


@router.post("/certificates/{certificate_id}/issue")
async def issue_certificate(
    request: Request,
    certificate_id: uuid.UUID,
    payload: IssueCertificateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    certificate_service: Annotated[CertificateService, Depends(get_certificate_service)],
) -> SuccessResponse[UserCertificateResponse]:
    if current_user.role != UserRole.ADMIN:
        raise _FORBIDDEN

    result = await certificate_service.issue_certificate(
        certificate_id=certificate_id, user_id=payload.user_id
    )
    return success_response(request, "Certificado emitido com sucesso.", result)
