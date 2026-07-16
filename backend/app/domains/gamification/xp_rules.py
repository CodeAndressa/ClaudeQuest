"""
Regras puras de XP e níveis do Gamification Engine.

Este módulo não depende de banco de dados, sessão ou qualquer outro domínio -
é testável isoladamente e reutilizável por outras features (ex.: Missões) sem
acoplamento. Fonte de verdade das regras de negócio: Vault do Obsidian,
`G:\\Meu Drive\\Obsidian\\ClaudeLinguo\\08 - Gamification\\Gamification.md.md`.
"""

import enum


class Difficulty(enum.StrEnum):
    """Dificuldades reconhecidas pela seção "Cálculo do XP" da documentação."""

    MUITO_FACIL = "muito_facil"
    FACIL = "facil"
    MEDIO = "medio"
    DIFICIL = "dificil"
    ESPECIALISTA = "especialista"
    MASTER = "master"
    PROJETO_FINAL = "projeto_final"
    CERTIFICACAO = "certificacao"


# XP base por dificuldade - valores fixos definidos na documentação de produto.
BASE_XP_BY_DIFFICULTY: dict[Difficulty, int] = {
    Difficulty.MUITO_FACIL: 25,
    Difficulty.FACIL: 50,
    Difficulty.MEDIO: 100,
    Difficulty.DIFICIL: 150,
    Difficulty.ESPECIALISTA: 250,
    Difficulty.MASTER: 500,
    Difficulty.PROJETO_FINAL: 1000,
    Difficulty.CERTIFICACAO: 2000,
}

# Multiplicadores aditivos (aplicados sobre 1.0, somados entre si - não compostos)
# conforme a seção "Multiplicadores" da documentação.
FIRST_ATTEMPT_BONUS = 0.20
STREAK_OVER_30_DAYS_BONUS = 0.15
SPECIAL_EVENT_BONUS = 0.50
DAILY_MISSION_BONUS = 0.10


def calculate_xp(
    difficulty: Difficulty,
    *,
    first_attempt: bool = False,
    streak_over_30_days: bool = False,
    special_event: bool = False,
    daily_mission: bool = False,
) -> int:
    """Calcula o XP concedido para uma ação, aplicando os multiplicadores ativos.

    Os multiplicadores são aditivos entre si (ex.: primeira tentativa + evento
    especial = +70%, não +20% depois +50% em cascata), o que é a leitura mais
    direta da documentação ("Multiplicadores" lista percentuais soltos, sem
    indicar composição). O resultado é arredondado para o inteiro mais próximo
    porque XP é sempre um valor inteiro no ledger.
    """

    base_xp = BASE_XP_BY_DIFFICULTY[difficulty]

    multiplier = 1.0
    if first_attempt:
        multiplier += FIRST_ATTEMPT_BONUS
    if streak_over_30_days:
        multiplier += STREAK_OVER_30_DAYS_BONUS
    if special_event:
        multiplier += SPECIAL_EVENT_BONUS
    if daily_mission:
        multiplier += DAILY_MISSION_BONUS

    return round(base_xp * multiplier)


# --- Sistema de níveis --------------------------------------------------
#
# A documentação define apenas 4 pontos de exemplo da curva:
#   Nível 1 =    0 XP
#   Nível 2 =  250 XP
#   Nível 3 =  600 XP
#   Nível 4 = 1000 XP
# e pede "crescimento exponencial suave", sem fórmula fechada.
#
# Modelamos o XP total exigido para alcançar o nível N (N >= 1) como:
#
#   threshold(N) = 0                              se N == 1
#   threshold(N) = round(LEVEL_BASE * (N - 1) ** LEVEL_EXPONENT)   se N > 1
#
# Com LEVEL_BASE = 250 e LEVEL_EXPONENT = 1.26, essa fórmula reproduz os 4
# pontos de referência com erro máximo de 2 XP (desprezível numa escala onde
# uma única missão já vale dezenas a milhares de XP):
#
#   threshold(2) = round(250 * 1^1.26)  = 250   (doc: 250, erro 0)
#   threshold(3) = round(250 * 2^1.26)  = 599   (doc: 600, erro 1)
#   threshold(4) = round(250 * 3^1.26)  = 998   (doc: 1000, erro 2)
#
# É uma potência (não uma exponencial pura tipo `base ** N`) porque uma
# exponencial pura cresce rápido demais para caber nos 4 pontos dados
# (600/250 = 2.4x e 1000/600 ≈ 1.67x - a razão de incremento cai a cada
# nível, o que uma exponencial `a * b**N` não reproduz, mas uma potência
# com expoente > 1 reproduz bem). O crescimento permanece "suave" porque a
# derivada de N^1.26 cresce lentamente para expoente próximo de 1.
LEVEL_BASE = 250
LEVEL_EXPONENT = 1.26

# Nível mais alto para o qual pré-calculamos o threshold (limite defensivo
# contra XP absurdamente grandes vindos de bugs em outras features).
_MAX_LEVEL = 1000


def xp_required_for_level(level: int) -> int:
    """Retorna o XP total necessário para alcançar `level` (nível >= 1)."""

    if level < 1:
        raise ValueError("level deve ser >= 1")
    if level == 1:
        return 0
    xp_needed: float = LEVEL_BASE * (level - 1) ** LEVEL_EXPONENT
    return round(xp_needed)


def calculate_level(total_xp: int) -> int:
    """Calcula o nível atual do usuário a partir do XP total acumulado.

    Nunca retorna nível abaixo de 1. Nunca "desnivela" o usuário - XP nunca é
    subtraído (ver seção "Penalidades" da documentação: "Nunca punir").
    """

    if total_xp < 0:
        raise ValueError("total_xp não pode ser negativo")

    level = 1
    while level < _MAX_LEVEL and xp_required_for_level(level + 1) <= total_xp:
        level += 1
    return level


def xp_to_next_level(total_xp: int) -> int:
    """XP restante até o próximo nível. Retorna 0 se já no nível máximo modelado."""

    current_level = calculate_level(total_xp)
    if current_level >= _MAX_LEVEL:
        return 0
    return xp_required_for_level(current_level + 1) - total_xp
