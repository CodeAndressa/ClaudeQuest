from uuid import UUID, uuid4

import pytest

from app.domains.gamification.model import XpLedger
from app.domains.gamification.schemas import GrantXpRequest
from app.domains.gamification.service import GamificationService
from app.domains.gamification.xp_rules import Difficulty, xp_required_for_level
from app.shared.errors import AppError


class _FakeXpLedgerRepository:
    def __init__(self) -> None:
        self.entries: list[XpLedger] = []

    async def add_entry(self, *, user_id: UUID, amount: int, reason: str) -> XpLedger:
        entry = XpLedger(user_id=user_id, amount=amount, reason=reason)
        self.entries.append(entry)
        return entry

    async def get_total_xp(self, user_id: UUID) -> int:
        return sum(entry.amount for entry in self.entries if entry.user_id == user_id)


@pytest.fixture
def fake_repository() -> _FakeXpLedgerRepository:
    return _FakeXpLedgerRepository()


@pytest.fixture
def service(fake_repository: _FakeXpLedgerRepository) -> GamificationService:
    return GamificationService(fake_repository)  # type: ignore[arg-type]


class TestGetProfile:
    async def test_returns_level_1_and_zero_xp_for_a_new_user(
        self, service: GamificationService
    ) -> None:
        profile = await service.get_profile(uuid4())

        assert profile.total_xp == 0
        assert profile.level == 1
        assert profile.xp_to_next_level == xp_required_for_level(2)

    async def test_reflects_accumulated_xp(
        self, service: GamificationService, fake_repository: _FakeXpLedgerRepository
    ) -> None:
        user_id = uuid4()
        await fake_repository.add_entry(user_id=user_id, amount=300, reason="quiz")

        profile = await service.get_profile(user_id)

        assert profile.total_xp == 300
        assert profile.level == 2


class TestGrantXpWithAmount:
    async def test_grants_the_exact_amount_informed(
        self, service: GamificationService
    ) -> None:
        user_id = uuid4()

        result = await service.grant_xp(
            user_id, GrantXpRequest(amount=42, reason="ajuste manual")
        )

        assert result.xp_granted == 42
        assert result.reason == "ajuste manual"
        assert result.total_xp == 42

    async def test_accumulates_across_multiple_grants(
        self, service: GamificationService
    ) -> None:
        user_id = uuid4()
        await service.grant_xp(user_id, GrantXpRequest(amount=100, reason="quiz"))

        result = await service.grant_xp(user_id, GrantXpRequest(amount=50, reason="streak"))

        assert result.total_xp == 150


class TestGrantXpWithDifficulty:
    async def test_calculates_xp_from_difficulty(self, service: GamificationService) -> None:
        user_id = uuid4()

        result = await service.grant_xp(
            user_id, GrantXpRequest(difficulty=Difficulty.MEDIO)
        )

        assert result.xp_granted == 100
        assert result.reason == "difficulty:medio"

    async def test_applies_multiplier_flags(self, service: GamificationService) -> None:
        user_id = uuid4()

        result = await service.grant_xp(
            user_id,
            GrantXpRequest(difficulty=Difficulty.MEDIO, first_attempt=True, daily_mission=True),
        )

        # 100 * (1 + 0.20 + 0.10) = 130
        assert result.xp_granted == 130

    async def test_updates_level_after_a_large_grant(
        self, service: GamificationService
    ) -> None:
        user_id = uuid4()

        result = await service.grant_xp(
            user_id, GrantXpRequest(difficulty=Difficulty.CERTIFICACAO)
        )

        assert result.total_xp == 2000
        assert result.level > 1
        assert result.xp_to_next_level >= 0


class TestGrantXpDefenseInDepth:
    async def test_rejects_a_malformed_payload_even_bypassing_schema_validation(
        self, service: GamificationService
    ) -> None:
        # O @model_validator de GrantXpRequest já impede, na borda da API, um payload sem
        # amount/reason e sem difficulty. Este teste simula um chamador direto do Service
        # (ex.: a futura feature de Missões) que construiu o schema sem passar pela
        # validação normal - via model_construct, que pula @model_validator - para provar
        # que o Service também não confia cegamente no payload.
        malformed_payload = GrantXpRequest.model_construct(
            amount=None,
            reason=None,
            difficulty=None,
            first_attempt=False,
            streak_over_30_days=False,
            special_event=False,
            daily_mission=False,
        )

        with pytest.raises(AppError) as exc_info:
            await service.grant_xp(uuid4(), malformed_payload)

        assert exc_info.value.code == "invalid_xp_grant_payload"
