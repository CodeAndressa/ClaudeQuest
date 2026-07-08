"""Eventos (GAME-009).

Reúne, num único arquivo, model + repository + service + schemas + router de
Eventos — decisão deliberada para minimizar sobreposição com os outros arquivos
novos sendo criados em paralelo no mesmo diretório (Ligas, Missões Diárias e
Semanais), cada um em seu próprio módulo. Mesmo padrão já usado em
`app/domains/gamification/badges.py` e `app/domains/gamification/certificates.py`.

Fonte de verdade das regras de negócio: Vault do Obsidian,
`G:\\Meu Drive\\Obsidian\\ClaudeLinguo\\08 - Gamification\\Missões Diárias,
Semanais e Eventos.md.md` (seção "Eventos").

Escopo desta entrega:

1. **Catálogo de eventos com janela de datas**, configurado pelo Admin (`name`,
   `starts_at`, `ends_at`) — como ainda não existe um Admin Portal real no
   backend (só um shell estático no frontend, ver ADMIN-001), a configuração é
   exposta como endpoints admin-only, no mesmo padrão de `badges.py`
   (`current_user.role == UserRole.ADMIN`), em vez de esperar por um Admin
   Portal futuro.
2. **Consulta de "evento ativo agora"**, pública para qualquer usuário
   autenticado — é a informação mínima que o resto do sistema precisa para
   decidir se aplica o multiplicador `SPECIAL_EVENT_BONUS` (já reservado em
   `xp_rules.py`, acionado pela flag `special_event` de `calculate_xp`).

Limitação deliberada, documentada aqui e no relatório final da tarefa: este
módulo **não** aciona o multiplicador automaticamente ao conceder XP. A
documentação descreve um evento como algo que também libera missões temporárias
exclusivas e badges/itens cosméticos (seção "Regras gerais de um evento") — nada
disso existe ainda no código, e a integração "verificar evento ativo e aplicar
o bônus automaticamente ao conceder XP" depende de tocar
`app/domains/learning/service.py` (onde XP é concedido hoje), o que está fora
do escopo desta tarefa para não colidir com o trabalho em paralelo de outros
agentes nesse mesmo arquivo. Este módulo expõe o método de serviço público
`EventService.is_event_active_now`, pronto para ser chamado por quem for fazer
essa integração cross-módulo depois.

Também não implementamos aqui (fora de escopo, sem entidade correspondente
ainda no projeto — mesma lacuna já documentada por `badges.py` e
`certificates.py` em relação ao sistema de progresso/Attempts):

* Missões temporárias exclusivas de um evento.
* Badges/itens cosméticos exclusivos de evento que se tornam "históricos" ao
  final do evento.
* O job/mecanismo que "vira o dia/semana" — Eventos não têm job de geração
  automática (diferente de Missões Diárias/Semanais): o Admin cadastra a
  janela de datas manualmente, e a checagem de "ativo agora" é sempre feita
  sob demanda, comparando com a hora corrente.
"""

import uuid
from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy import Boolean, DateTime, select
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


class Event(AuditedModel):
    """Um evento de tempo limitado (ex.: Halloween, Claude Week, Hackathon).

    `is_active` permite ao Admin desativar manualmente um evento antes do
    prazo (ex.: encerramento antecipado por incidente), mesmo padrão já usado
    em `Track`/`School` no domínio `learning`. Um evento só é considerado
    "ativo agora" quando `is_active` é verdadeiro **e** o instante atual está
    dentro da janela `[starts_at, ends_at]` — ver `EventService.is_event_active_now`.
    """

    __tablename__ = "events"

    name: Mapped[str] = mapped_column(nullable=False)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=True)


# --------------------------------------------------------------------------- #
# Schemas
# --------------------------------------------------------------------------- #


class EventResponse(BaseModel):
    """Um evento, para listagem administrativa e para a consulta de "ativo agora"."""

    id: UUID
    name: str
    starts_at: datetime
    ends_at: datetime
    is_active: bool

    model_config = {"from_attributes": True}


class CreateEventRequest(BaseModel):
    """Body de `POST /gamification/events` (admin-only)."""

    name: str
    starts_at: datetime
    ends_at: datetime


# --------------------------------------------------------------------------- #
# Errors
# --------------------------------------------------------------------------- #

_INVALID_EVENT_WINDOW = AppError(
    code="invalid_event_window",
    message="A data de término do evento deve ser posterior à data de início.",
    status_code=422,
)

_EVENT_NOT_FOUND = AppError(
    code="event_not_found",
    message="Evento não encontrado.",
    status_code=404,
)

_FORBIDDEN = AppError(
    code="forbidden",
    message="Apenas administradores podem gerenciar eventos.",
    status_code=403,
)


# --------------------------------------------------------------------------- #
# Repository
# --------------------------------------------------------------------------- #


class EventRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_all(self) -> list[Event]:
        statement = select(Event).where(Event.deleted_at.is_(None)).order_by(Event.starts_at)
        result = await self._session.execute(statement)
        return list(result.scalars().all())

    async def get_by_id(self, event_id: UUID) -> Event | None:
        statement = select(Event).where(Event.id == event_id, Event.deleted_at.is_(None))
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def create(self, *, name: str, starts_at: datetime, ends_at: datetime) -> Event:
        event = Event(name=name, starts_at=starts_at, ends_at=ends_at, is_active=True)
        self._session.add(event)
        await self._session.flush()
        return event

    async def get_active_at(self, moment: datetime) -> Event | None:
        statement = select(Event).where(
            Event.deleted_at.is_(None),
            Event.is_active.is_(True),
            Event.starts_at <= moment,
            Event.ends_at >= moment,
        )
        result = await self._session.execute(statement)
        return result.scalars().first()

    async def deactivate(self, event: Event) -> Event:
        event.is_active = False
        await self._session.flush()
        return event


# --------------------------------------------------------------------------- #
# Service
# --------------------------------------------------------------------------- #


class EventService:
    def __init__(self, events: EventRepository) -> None:
        self._events = events

    async def create_event(
        self, *, name: str, starts_at: datetime, ends_at: datetime
    ) -> Event:
        if ends_at <= starts_at:
            raise _INVALID_EVENT_WINDOW

        return await self._events.create(name=name, starts_at=starts_at, ends_at=ends_at)

    async def list_all(self) -> list[Event]:
        return await self._events.list_all()

    async def is_event_active_now(self) -> Event | None:
        """Retorna o evento ativo no instante atual, se houver.

        Ponto de extensão público para a integração futura (fora de escopo
        aqui) que aciona a flag `special_event` de `calculate_xp`
        (`app/domains/gamification/xp_rules.py`) ao conceder XP — ver docstring
        do módulo.
        """

        return await self._events.get_active_at(datetime.now(UTC))

    async def deactivate_event(self, event_id: UUID) -> Event:
        event = await self._events.get_by_id(event_id)
        if event is None:
            raise _EVENT_NOT_FOUND

        return await self._events.deactivate(event)


# --------------------------------------------------------------------------- #
# Router
# --------------------------------------------------------------------------- #
#
# Registrado à parte do router principal de gamification (app/domains/gamification/
# router.py), tocado em paralelo por outras tarefas — este router é incluído
# diretamente em app/api/v1/router.py com o mesmo prefixo "/gamification" para
# expor os endpoints sob o mesmo namespace de API sem editar arquivos concorrentes.

events_router = APIRouter(prefix="/gamification", tags=["gamification", "events"])


def get_event_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> EventService:
    return EventService(EventRepository(session))


@events_router.post("/events")
async def create_event(
    request: Request,
    payload: CreateEventRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    event_service: Annotated[EventService, Depends(get_event_service)],
) -> SuccessResponse[EventResponse]:
    if current_user.role != UserRole.ADMIN:
        raise _FORBIDDEN

    event = await event_service.create_event(
        name=payload.name, starts_at=payload.starts_at, ends_at=payload.ends_at
    )
    data = EventResponse.model_validate(event)
    return success_response(request, "Evento criado com sucesso.", data)


@events_router.get("/events")
async def list_events(
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    event_service: Annotated[EventService, Depends(get_event_service)],
) -> SuccessResponse[list[EventResponse]]:
    if current_user.role != UserRole.ADMIN:
        raise _FORBIDDEN

    events = await event_service.list_all()
    data = [EventResponse.model_validate(event) for event in events]
    return success_response(request, "Eventos recuperados com sucesso.", data)


@events_router.get("/events/active")
async def get_active_event(
    request: Request,
    _current_user: Annotated[User, Depends(get_current_user)],
    event_service: Annotated[EventService, Depends(get_event_service)],
) -> SuccessResponse[EventResponse | None]:
    # Endpoint público a qualquer usuário autenticado (não admin-only): é
    # consumido pela UI para exibir "evento ativo" a qualquer aluno.
    event = await event_service.is_event_active_now()
    data = EventResponse.model_validate(event) if event is not None else None
    message = "Evento ativo recuperado com sucesso." if event else "Nenhum evento ativo no momento."
    return success_response(request, message, data)


@events_router.patch("/events/{event_id}/deactivate")
async def deactivate_event(
    request: Request,
    event_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    event_service: Annotated[EventService, Depends(get_event_service)],
) -> SuccessResponse[EventResponse]:
    if current_user.role != UserRole.ADMIN:
        raise _FORBIDDEN

    event = await event_service.deactivate_event(event_id)
    data = EventResponse.model_validate(event)
    return success_response(request, "Evento desativado com sucesso.", data)
