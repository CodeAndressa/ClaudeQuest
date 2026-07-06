from uuid import UUID

from app.domains.gamification.repository import XpLedgerRepository
from app.domains.gamification.schemas import (
    GamificationProfileResponse,
    GrantXpRequest,
    GrantXpResponse,
)
from app.domains.gamification.xp_rules import calculate_level, calculate_xp, xp_to_next_level
from app.shared.errors import AppError

_DIFFICULTY_REASON_PREFIX = "difficulty:"

_INVALID_GRANT_PAYLOAD = AppError(
    code="invalid_xp_grant_payload",
    message="Requisição de XP inválida: 'amount' e 'reason' são obrigatórios "
    "quando 'difficulty' não é informado.",
    status_code=422,
)


class GamificationService:
    def __init__(self, xp_ledger: XpLedgerRepository) -> None:
        self._xp_ledger = xp_ledger

    async def get_profile(self, user_id: UUID) -> GamificationProfileResponse:
        total_xp = await self._xp_ledger.get_total_xp(user_id)
        return GamificationProfileResponse(
            total_xp=total_xp,
            level=calculate_level(total_xp),
            xp_to_next_level=xp_to_next_level(total_xp),
        )

    async def grant_xp(self, user_id: UUID, payload: GrantXpRequest) -> GrantXpResponse:
        if payload.difficulty is not None:
            amount = calculate_xp(
                payload.difficulty,
                first_attempt=payload.first_attempt,
                streak_over_30_days=payload.streak_over_30_days,
                special_event=payload.special_event,
                daily_mission=payload.daily_mission,
            )
            reason = f"{_DIFFICULTY_REASON_PREFIX}{payload.difficulty.value}"
        elif payload.amount is not None and payload.reason is not None:
            amount = payload.amount
            reason = payload.reason
        else:
            # Defesa em profundidade: o validador de GrantXpRequest já garante essa
            # invariante na borda da API, mas o Service não deve confiar cegamente em
            # dados vindos de outros chamadores (ex.: a futura feature de Missões).
            raise _INVALID_GRANT_PAYLOAD

        await self._xp_ledger.add_entry(user_id=user_id, amount=amount, reason=reason)
        total_xp = await self._xp_ledger.get_total_xp(user_id)

        return GrantXpResponse(
            xp_granted=amount,
            reason=reason,
            total_xp=total_xp,
            level=calculate_level(total_xp),
            xp_to_next_level=xp_to_next_level(total_xp),
        )
