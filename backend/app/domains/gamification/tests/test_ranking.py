from uuid import UUID, uuid4

import pytest

from app.domains.gamification.ranking import (
    BADGE_WEIGHT,
    CERTIFICATE_WEIGHT,
    RankingEntry,
    RankingService,
    calculate_score,
)

# --- calculate_score (função pura) -----------------------------------------


class TestCalculateScore:
    def test_score_with_only_xp_equals_the_xp_itself(self) -> None:
        score = calculate_score(total_xp=350, badges_count=0, certificates_count=0)

        assert score == 350

    def test_zero_everything_scores_zero(self) -> None:
        score = calculate_score(total_xp=0, badges_count=0, certificates_count=0)

        assert score == 0

    def test_each_badge_adds_the_badge_weight(self) -> None:
        score = calculate_score(total_xp=0, badges_count=3, certificates_count=0)

        assert score == 3 * BADGE_WEIGHT

    def test_each_certificate_adds_the_certificate_weight(self) -> None:
        score = calculate_score(total_xp=0, badges_count=0, certificates_count=2)

        assert score == 2 * CERTIFICATE_WEIGHT

    def test_combines_all_three_sources_additively(self) -> None:
        score = calculate_score(total_xp=500, badges_count=2, certificates_count=1)

        # 500 + 2*100 + 1*500 = 1200
        assert score == 1200

    def test_certificate_weighs_more_than_a_badge(self) -> None:
        # A tarefa pede pesos declarados explicitamente; este teste trava a
        # ordem de grandeza pretendida (certificado > badge) contra uma futura
        # alteração acidental dos pesos.
        assert CERTIFICATE_WEIGHT > BADGE_WEIGHT

    def test_a_single_certificate_outweighs_several_badges(self) -> None:
        certificate_score = calculate_score(total_xp=0, badges_count=0, certificates_count=1)
        four_badges_score = calculate_score(total_xp=0, badges_count=4, certificates_count=0)

        assert certificate_score > four_badges_score

    def test_ranking_entry_score_property_matches_calculate_score(self) -> None:
        entry = RankingEntry(
            user_id=uuid4(), name="Estudante", total_xp=80, badges_count=1, certificates_count=1
        )

        assert entry.score == calculate_score(
            total_xp=80, badges_count=1, certificates_count=1
        )


# --- RankingService (com repositório fake) ---------------------------------


class _FakeRankingRepository:
    def __init__(self, entries: list[RankingEntry]) -> None:
        self._entries = entries

    async def get_all_entries(self) -> list[RankingEntry]:
        return self._entries


def _entry(
    *,
    user_id: UUID | None = None,
    name: str = "Usuária",
    total_xp: int = 0,
    badges_count: int = 0,
    certificates_count: int = 0,
) -> RankingEntry:
    return RankingEntry(
        user_id=user_id or uuid4(),
        name=name,
        total_xp=total_xp,
        badges_count=badges_count,
        certificates_count=certificates_count,
    )


def _service(entries: list[RankingEntry]) -> RankingService:
    return RankingService(_FakeRankingRepository(entries))  # type: ignore[arg-type]


class TestGlobalRankingTop10:
    async def test_returns_all_users_ordered_by_score_desc_when_fewer_than_ten(self) -> None:
        low = _entry(name="Baixo", total_xp=10)
        mid = _entry(name="Médio", total_xp=100)
        high = _entry(name="Alto", total_xp=1000)
        service = _service([low, mid, high])

        ranking = await service.get_global_ranking(current_user_id=uuid4())

        assert [entry.name for entry in ranking.top] == ["Alto", "Médio", "Baixo"]
        assert [entry.position for entry in ranking.top] == [1, 2, 3]

    async def test_returns_only_top_ten_when_there_are_more_than_ten_users(self) -> None:
        entries = [_entry(name=f"user-{i}", total_xp=i * 10) for i in range(15)]
        service = _service(entries)

        ranking = await service.get_global_ranking(current_user_id=uuid4())

        assert len(ranking.top) == 10
        # O de maior XP (i=14) deve ser o primeiro colocado.
        assert ranking.top[0].name == "user-14"
        assert ranking.top[0].position == 1
        assert ranking.top[-1].name == "user-5"
        assert ranking.top[-1].position == 10

    async def test_empty_platform_returns_empty_top_and_no_current_user(self) -> None:
        service = _service([])

        ranking = await service.get_global_ranking(current_user_id=uuid4())

        assert ranking.top == []
        assert ranking.current_user is None


class TestCurrentUserPosition:
    async def test_current_user_inside_top_ten_appears_in_top_and_as_current_user(self) -> None:
        me_id = uuid4()
        me = _entry(user_id=me_id, name="Eu", total_xp=1000)
        other = _entry(name="Outra", total_xp=10)
        service = _service([other, me])

        ranking = await service.get_global_ranking(current_user_id=me_id)

        assert ranking.current_user is not None
        assert ranking.current_user.user_id == me_id
        assert ranking.current_user.position == 1
        assert any(entry.user_id == me_id for entry in ranking.top)

    async def test_current_user_outside_top_ten_is_still_returned_with_correct_position(
        self,
    ) -> None:
        me_id = uuid4()
        me = _entry(user_id=me_id, name="Eu", total_xp=1)
        # 10 outros usuários, todos com XP maior que o meu — me empurram para
        # a 11ª posição, fora do Top 10.
        others = [_entry(name=f"acima-{i}", total_xp=1000 + i) for i in range(10)]
        service = _service([me, *others])

        ranking = await service.get_global_ranking(current_user_id=me_id)

        assert len(ranking.top) == 10
        assert all(entry.user_id != me_id for entry in ranking.top)
        assert ranking.current_user is not None
        assert ranking.current_user.user_id == me_id
        assert ranking.current_user.position == 11

    async def test_current_user_not_found_among_entries_returns_none(self) -> None:
        service = _service([_entry(name="Outra", total_xp=100)])

        ranking = await service.get_global_ranking(current_user_id=uuid4())

        assert ranking.current_user is None


class TestScoreTieBreak:
    async def test_ties_are_broken_deterministically_by_ascending_user_id(self) -> None:
        smaller_id = UUID("00000000-0000-0000-0000-000000000001")
        larger_id = UUID("00000000-0000-0000-0000-000000000002")
        entry_larger = _entry(user_id=larger_id, name="B", total_xp=500)
        entry_smaller = _entry(user_id=smaller_id, name="A", total_xp=500)
        # Inseridos fora de ordem de user_id de propósito, para provar que o
        # desempate não depende da ordem de chegada dos dados.
        service = _service([entry_larger, entry_smaller])

        ranking = await service.get_global_ranking(current_user_id=uuid4())

        assert [entry.user_id for entry in ranking.top] == [smaller_id, larger_id]
        assert ranking.top[0].position == 1
        assert ranking.top[1].position == 2

    async def test_tie_via_equivalent_score_from_different_sources_is_still_broken_by_user_id(
        self,
    ) -> None:
        smaller_id = UUID("00000000-0000-0000-0000-000000000001")
        larger_id = UUID("00000000-0000-0000-0000-000000000002")
        # Mesmo score (600) alcançado por combinações diferentes de fontes.
        via_xp = _entry(user_id=larger_id, name="Via XP", total_xp=600)
        via_badges = _entry(user_id=smaller_id, name="Via badges", total_xp=100, badges_count=5)
        service = _service([via_xp, via_badges])

        ranking = await service.get_global_ranking(current_user_id=uuid4())

        assert via_xp.score == via_badges.score == 600
        assert [entry.user_id for entry in ranking.top] == [smaller_id, larger_id]

    async def test_three_way_tie_orders_all_by_ascending_user_id(self) -> None:
        ids = [
            UUID("00000000-0000-0000-0000-000000000003"),
            UUID("00000000-0000-0000-0000-000000000001"),
            UUID("00000000-0000-0000-0000-000000000002"),
        ]
        entries = [_entry(user_id=uid, name=str(uid), total_xp=200) for uid in ids]
        service = _service(entries)

        ranking = await service.get_global_ranking(current_user_id=uuid4())

        assert [entry.user_id for entry in ranking.top] == sorted(ids)
        assert [entry.position for entry in ranking.top] == [1, 2, 3]


class TestRankingServiceRequiresAsyncRepository:
    async def test_get_global_ranking_awaits_repository_entries(self) -> None:
        # Confirma que o Service não faz nenhuma suposição sobre a origem dos
        # dados além do contrato assíncrono do repositório (fake aqui,
        # RankingRepository real — com JOINs entre users/xp_ledger/badges/
        # certificates — na integração).
        with pytest.raises(TypeError):
            RankingService(entries_not_a_repository=[])  # type: ignore[call-arg]
