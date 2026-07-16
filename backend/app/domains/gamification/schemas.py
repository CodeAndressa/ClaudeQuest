from pydantic import BaseModel, Field, model_validator

from app.domains.gamification.xp_rules import Difficulty


class GamificationProfileResponse(BaseModel):
    """XP e nível atuais de um usuário."""

    total_xp: int
    level: int
    xp_to_next_level: int


class GrantXpRequest(BaseModel):
    """Requisição de concessão manual de XP.

    Aceita duas formas mutuamente exclusivas, refletindo os dois chamadores
    esperados deste endpoint:
      - `amount` + `reason`: concessão de um valor já calculado (ex.: um
        admin ajustando XP manualmente, ou uma integração que já sabe o
        valor final).
      - `difficulty` (+ flags de multiplicador): a interface que a futura
        feature de Missões vai usar - ela só sabe "essa missão era Difícil,
        foi na primeira tentativa", não o valor de XP resultante.
    """

    amount: int | None = Field(default=None, gt=0)
    reason: str | None = Field(default=None, min_length=1, max_length=255)

    difficulty: Difficulty | None = None
    first_attempt: bool = False
    streak_over_30_days: bool = False
    special_event: bool = False
    daily_mission: bool = False

    @model_validator(mode="after")
    def _validate_mutually_exclusive_modes(self) -> "GrantXpRequest":
        has_amount = self.amount is not None
        has_difficulty = self.difficulty is not None

        if has_amount == has_difficulty:
            raise ValueError(
                "Informe exatamente um dos dois modos: 'amount' (com 'reason') "
                "ou 'difficulty' (com os multiplicadores opcionais)."
            )
        if has_amount and not self.reason:
            raise ValueError("'reason' é obrigatório quando 'amount' é informado.")
        return self


class GrantXpResponse(BaseModel):
    """Resultado de uma concessão de XP: quanto foi concedido e o novo estado do usuário."""

    xp_granted: int
    reason: str
    total_xp: int
    level: int
    xp_to_next_level: int
