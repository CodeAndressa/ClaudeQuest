import uuid

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import AuditedModel


class XpLedger(AuditedModel):
    """Registro append-only de cada ganho de XP de um usuário.

    Por design, esta tabela nunca é atualizada nem tem linhas removidas: a
    seção "Penalidades" da documentação de Gamification é explícita — "Não
    remover XP. Jamais retirar progresso do usuário. Nunca punir." Cada linha
    é um evento imutável de concessão de XP.

    O XP total do usuário é sempre a soma de `amount` desta tabela — não
    mantemos um contador desnormalizado (ex.: `users.total_xp`). Trade-off
    assumido: SUM(amount) é O(n) por leitura, mas o ledger de um único
    usuário tende a ter, no máximo, milhares de linhas ao longo de toda a
    vida da conta (cada linha custa uma ação de aprendizado concluída), e um
    índice em `user_id` mantém a soma barata mesmo nesse volume. Evitamos
    assim toda a complexidade de manter dois lugares (ledger + contador)
    sincronizados sob concorrência — a única fonte de verdade é o ledger.
    Se o perfil de acesso mudar (ex.: leitura de XP total em todo request),
    isso pode evoluir para uma materialização/cache sem quebrar este modelo.
    """

    __tablename__ = "xp_ledger"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    amount: Mapped[int] = mapped_column(nullable=False)
    reason: Mapped[str] = mapped_column(String, nullable=False)
