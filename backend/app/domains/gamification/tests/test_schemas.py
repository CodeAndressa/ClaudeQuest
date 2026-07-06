import pytest
from pydantic import ValidationError

from app.domains.gamification.schemas import GrantXpRequest
from app.domains.gamification.xp_rules import Difficulty


class TestGrantXpRequestValidation:
    def test_accepts_amount_with_reason(self) -> None:
        payload = GrantXpRequest(amount=50, reason="bonus")

        assert payload.amount == 50
        assert payload.reason == "bonus"

    def test_accepts_difficulty_alone(self) -> None:
        payload = GrantXpRequest(difficulty=Difficulty.FACIL)

        assert payload.difficulty == Difficulty.FACIL

    def test_rejects_both_amount_and_difficulty(self) -> None:
        with pytest.raises(ValidationError):
            GrantXpRequest(amount=50, reason="bonus", difficulty=Difficulty.FACIL)

    def test_rejects_neither_amount_nor_difficulty(self) -> None:
        with pytest.raises(ValidationError):
            GrantXpRequest()

    def test_rejects_amount_without_reason(self) -> None:
        with pytest.raises(ValidationError):
            GrantXpRequest(amount=50)

    def test_rejects_non_positive_amount(self) -> None:
        with pytest.raises(ValidationError):
            GrantXpRequest(amount=0, reason="bonus")

    def test_multiplier_flags_default_to_false(self) -> None:
        payload = GrantXpRequest(difficulty=Difficulty.FACIL)

        assert payload.first_attempt is False
        assert payload.streak_over_30_days is False
        assert payload.special_event is False
        assert payload.daily_mission is False
