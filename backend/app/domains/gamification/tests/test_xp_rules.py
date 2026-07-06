import pytest

from app.domains.gamification import xp_rules
from app.domains.gamification.xp_rules import (
    BASE_XP_BY_DIFFICULTY,
    Difficulty,
    calculate_level,
    calculate_xp,
    xp_required_for_level,
    xp_to_next_level,
)


class TestCalculateXp:
    @pytest.mark.parametrize(
        ("difficulty", "expected"),
        [
            (Difficulty.MUITO_FACIL, 25),
            (Difficulty.FACIL, 50),
            (Difficulty.MEDIO, 100),
            (Difficulty.DIFICIL, 150),
            (Difficulty.ESPECIALISTA, 250),
            (Difficulty.MASTER, 500),
            (Difficulty.PROJETO_FINAL, 1000),
            (Difficulty.CERTIFICACAO, 2000),
        ],
    )
    def test_base_xp_without_multipliers(self, difficulty: Difficulty, expected: int) -> None:
        assert calculate_xp(difficulty) == expected

    def test_all_difficulties_are_mapped(self) -> None:
        assert set(BASE_XP_BY_DIFFICULTY.keys()) == set(Difficulty)

    def test_first_attempt_bonus(self) -> None:
        # Médio = 100 XP; +20% = 120
        assert calculate_xp(Difficulty.MEDIO, first_attempt=True) == 120

    def test_streak_over_30_days_bonus(self) -> None:
        # Médio = 100 XP; +15% = 115
        assert calculate_xp(Difficulty.MEDIO, streak_over_30_days=True) == 115

    def test_special_event_bonus(self) -> None:
        # Médio = 100 XP; +50% = 150
        assert calculate_xp(Difficulty.MEDIO, special_event=True) == 150

    def test_daily_mission_bonus(self) -> None:
        # Médio = 100 XP; +10% = 110
        assert calculate_xp(Difficulty.MEDIO, daily_mission=True) == 110

    def test_multipliers_are_additive_not_compounded(self) -> None:
        # Médio = 100 XP; +20% + 50% = +70% => 170 (não 100*1.2*1.5=180)
        result = calculate_xp(Difficulty.MEDIO, first_attempt=True, special_event=True)
        assert result == 170

    def test_all_multipliers_combined(self) -> None:
        # 100 * (1 + 0.20 + 0.15 + 0.50 + 0.10) = 100 * 1.95 = 195
        result = calculate_xp(
            Difficulty.MEDIO,
            first_attempt=True,
            streak_over_30_days=True,
            special_event=True,
            daily_mission=True,
        )
        assert result == 195

    def test_result_is_rounded_to_nearest_integer(self) -> None:
        # 25 * 1.15 = 28.75 -> arredonda para 29
        assert calculate_xp(Difficulty.MUITO_FACIL, streak_over_30_days=True) == 29


class TestXpRequiredForLevel:
    def test_level_1_requires_zero_xp(self) -> None:
        assert xp_required_for_level(1) == 0

    def test_matches_documentation_reference_points_within_small_error(self) -> None:
        # Documentação: Nível 2=250, Nível 3=600, Nível 4=1000 (exemplo ilustrativo).
        # A fórmula de potência suave aproxima esses pontos com erro <= 2 XP.
        assert xp_required_for_level(2) == pytest.approx(250, abs=2)
        assert xp_required_for_level(3) == pytest.approx(600, abs=2)
        assert xp_required_for_level(4) == pytest.approx(1000, abs=2)

    def test_thresholds_are_strictly_increasing(self) -> None:
        thresholds = [xp_required_for_level(n) for n in range(1, 30)]
        assert thresholds == sorted(thresholds)
        assert len(set(thresholds)) == len(thresholds)

    def test_raises_for_level_below_one(self) -> None:
        with pytest.raises(ValueError):
            xp_required_for_level(0)


class TestCalculateLevel:
    def test_zero_xp_is_level_1(self) -> None:
        assert calculate_level(0) == 1

    def test_just_below_level_2_threshold_stays_level_1(self) -> None:
        assert calculate_level(xp_required_for_level(2) - 1) == 1

    def test_exact_threshold_reaches_the_level(self) -> None:
        assert calculate_level(xp_required_for_level(2)) == 2
        assert calculate_level(xp_required_for_level(3)) == 3
        assert calculate_level(xp_required_for_level(4)) == 4

    def test_documentation_reference_points(self) -> None:
        assert calculate_level(0) == 1
        assert calculate_level(250) == 2
        assert calculate_level(xp_required_for_level(3) - 1) == 2
        assert calculate_level(600) == 3
        assert calculate_level(1000) >= 4

    def test_never_returns_level_below_one(self) -> None:
        assert calculate_level(0) >= 1

    def test_raises_for_negative_xp(self) -> None:
        with pytest.raises(ValueError):
            calculate_level(-1)

    def test_large_xp_does_not_loop_forever(self) -> None:
        # Garantia de que o laço interno de calculate_level tem limite defensivo.
        level = calculate_level(10**9)
        assert level >= 1


class TestXpToNextLevel:
    def test_zero_xp_needs_full_level_2_threshold(self) -> None:
        assert xp_to_next_level(0) == xp_required_for_level(2)

    def test_returns_remaining_xp_mid_level(self) -> None:
        threshold_2 = xp_required_for_level(2)
        threshold_3 = xp_required_for_level(3)
        midpoint = (threshold_2 + threshold_3) // 2
        assert xp_to_next_level(midpoint) == threshold_3 - midpoint

    def test_returns_zero_exactly_at_a_threshold_minus_progress(self) -> None:
        threshold_2 = xp_required_for_level(2)
        assert xp_to_next_level(threshold_2) == xp_required_for_level(3) - threshold_2

    def test_returns_zero_when_already_at_the_modeled_max_level(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # _MAX_LEVEL é um limite defensivo contra XP absurdamente grande vindo de bugs em
        # outras features; reduzi-lo temporariamente torna esse ramo alcançável em teste
        # sem precisar de um total_xp real na casa dos trilhões.
        monkeypatch.setattr(xp_rules, "_MAX_LEVEL", 3)

        assert xp_rules.calculate_level(10**9) == 3
        assert xp_to_next_level(10**9) == 0
