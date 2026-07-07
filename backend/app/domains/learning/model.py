import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import AuditedModel


class UserLessonProgress(AuditedModel):
    """Progresso de conclusao de uma missao por usuario.

    Cada par (usuario, missao) so pode existir uma vez. A linha nasce quando a
    missao e concluida pela primeira vez e guarda quanto XP foi concedido naquele
    momento, evitando duplicidade em retries ou cliques repetidos.
    """

    __tablename__ = "user_lesson_progress"
    __table_args__ = (
        UniqueConstraint("user_id", "lesson_id", name="uq_user_lesson_progress_user_lesson"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    lesson_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("lessons.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    xp_awarded: Mapped[int] = mapped_column(Integer(), nullable=False, default=0)


class QuestionType(enum.StrEnum):
    """Tipos de questÃ£o previstos em 05 - Database/Database Specification.md.md.

    Apenas MULTIPLE_CHOICE Ã© utilizado nesta primeira entrega (LEARN-001 a
    LEARN-006, conteÃºdo apenas de leitura) â€” os demais tipos ficam registrados
    aqui para nÃ£o exigir migraÃ§Ã£o futura quando forem implementados.
    """

    MULTIPLE_CHOICE = "multiple_choice"
    BOOLEAN = "boolean"
    CODE = "code"
    TEXT = "text"
    UPLOAD = "upload"
    DRAG_AND_DROP = "drag_and_drop"


class LessonType(enum.StrEnum):
    """Tipos de missÃ£o (08 - Gamification/Learning Engine.md.md, "Tipos de MissÃ£o")."""

    READING = "reading"
    QUIZ = "quiz"
    CHALLENGE = "challenge"
    LAB = "lab"
    UPLOAD = "upload"
    CHECKLIST = "checklist"
    FREE_ANSWER = "free_answer"


class School(AuditedModel):
    """Escola do catalogo educacional.

    Representa o nivel acima de trilhas na hierarquia oficial:
    Academy -> School -> Track -> Module -> Level -> Lesson.
    """

    __tablename__ = "schools"
    __table_args__ = (UniqueConstraint("slug", name="uq_schools_slug"),)

    title: Mapped[str] = mapped_column(nullable=False)
    slug: Mapped[str] = mapped_column(nullable=False)
    description: Mapped[str] = mapped_column(Text(), nullable=False)
    icon: Mapped[str | None] = mapped_column(default=None)
    order: Mapped[int] = mapped_column(Integer(), nullable=False, default=0, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=True)

    tracks: Mapped[list["Track"]] = relationship(
        back_populates="school",
        cascade="all, delete-orphan",
        order_by="Track.order",
    )


class Track(AuditedModel):
    """Trilha (05 - Database/Database Specification.md.md, seÃ§Ã£o "Tracks").

    Exemplos: Claude Chat, Claude Cowork, Claude Code, Prompt Engineering, MCP.
    """

    __tablename__ = "tracks"

    school_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("schools.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(nullable=False)
    description: Mapped[str] = mapped_column(Text(), nullable=False)
    difficulty: Mapped[str] = mapped_column(nullable=False, default="beginner")
    estimated_hours: Mapped[int] = mapped_column(Integer(), nullable=False, default=0)
    image: Mapped[str | None] = mapped_column(default=None)
    icon: Mapped[str | None] = mapped_column(default=None)
    order: Mapped[int] = mapped_column(Integer(), nullable=False, default=0, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=True)

    school: Mapped[School] = relationship(back_populates="tracks")
    modules: Mapped[list["Module"]] = relationship(
        back_populates="track",
        cascade="all, delete-orphan",
        order_by="Module.order",
    )


class Module(AuditedModel):
    """MÃ³dulo de uma trilha (Learning Content.md.md, "Estrutura dos MÃ³dulos").

    NÃ£o existia como tabela prÃ³pria no Database Specification original (que vai
    direto de Track para Level) â€” adicionada por exigÃªncia explÃ­cita da tarefa
    LEARN-001..006, que define a hierarquia oficial como
    Track -> Module -> Level -> Lesson -> Question -> Alternative. Cada mÃ³dulo
    ensina um Ãºnico tema, nunca misturando assuntos.
    """

    __tablename__ = "modules"
    __table_args__ = (UniqueConstraint("track_id", "order", name="uq_modules_track_id_order"),)

    track_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tracks.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(nullable=False)
    description: Mapped[str] = mapped_column(Text(), nullable=False)
    order: Mapped[int] = mapped_column(Integer(), nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=True)

    track: Mapped[Track] = relationship(back_populates="modules")
    levels: Mapped[list["Level"]] = relationship(
        back_populates="module",
        cascade="all, delete-orphan",
        order_by="Level.level_number",
    )


class Level(AuditedModel):
    """NÃ­vel (05 - Database/Database Specification.md.md, seÃ§Ã£o "Levels").

    Tipos usuais (Learning Engine.md.md, "NÃ­veis"): BÃ¡sico, IntermediÃ¡rio,
    AvanÃ§ado, Especialista, Master â€” representados livremente em `title`.
    """

    __tablename__ = "levels"
    __table_args__ = (
        UniqueConstraint("module_id", "level_number", name="uq_levels_module_id_level_number"),
    )

    module_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("modules.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(nullable=False)
    description: Mapped[str] = mapped_column(Text(), nullable=False)
    level_number: Mapped[int] = mapped_column(Integer(), nullable=False)
    estimated_minutes: Mapped[int] = mapped_column(Integer(), nullable=False, default=10)
    xp: Mapped[int] = mapped_column(Integer(), nullable=False, default=0)
    stars: Mapped[int] = mapped_column(Integer(), nullable=False, default=0)
    required_xp: Mapped[int] = mapped_column(Integer(), nullable=False, default=0)

    module: Mapped[Module] = relationship(back_populates="levels")
    lessons: Mapped[list["Lesson"]] = relationship(
        back_populates="level",
        cascade="all, delete-orphan",
        order_by="Lesson.order",
    )


class Lesson(AuditedModel):
    """MissÃ£o (05 - Database/Database Specification.md.md, seÃ§Ã£o "Lessons").

    Regra de qualidade (Learning Engine.md.md, "CritÃ©rios de Qualidade"): toda
    missÃ£o deve ensinar apenas um conceito principal e ser concluÃ­da em menos
    de 10 minutos.
    """

    __tablename__ = "lessons"
    __table_args__ = (UniqueConstraint("level_id", "order", name="uq_lessons_level_id_order"),)

    level_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("levels.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(nullable=False)
    description: Mapped[str] = mapped_column(Text(), nullable=False)
    content: Mapped[str] = mapped_column(Text(), nullable=False)
    estimated_minutes: Mapped[int] = mapped_column(Integer(), nullable=False, default=5)
    difficulty: Mapped[str] = mapped_column(nullable=False, default="beginner")
    lesson_type: Mapped[LessonType] = mapped_column(
        Enum(LessonType, name="lesson_type", native_enum=True),
        nullable=False,
        default=LessonType.QUIZ,
    )
    order: Mapped[int] = mapped_column(Integer(), nullable=False, default=0)
    xp: Mapped[int] = mapped_column(Integer(), nullable=False, default=0)
    ai_corrected: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=False)

    level: Mapped[Level] = relationship(back_populates="lessons")
    questions: Mapped[list["Question"]] = relationship(
        back_populates="lesson",
        cascade="all, delete-orphan",
        order_by="Question.order",
    )


class Question(AuditedModel):
    """QuestÃ£o de uma missÃ£o (05 - Database/Database Specification.md.md, "Questions")."""

    __tablename__ = "questions"
    __table_args__ = (UniqueConstraint("lesson_id", "order", name="uq_questions_lesson_id_order"),)

    lesson_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("lessons.id", ondelete="CASCADE"), nullable=False, index=True
    )
    question: Mapped[str] = mapped_column(Text(), nullable=False)
    question_type: Mapped[QuestionType] = mapped_column(
        Enum(QuestionType, name="question_type", native_enum=True),
        nullable=False,
        default=QuestionType.MULTIPLE_CHOICE,
    )
    explanation: Mapped[str | None] = mapped_column(Text(), default=None)
    points: Mapped[int] = mapped_column(Integer(), nullable=False, default=1)
    order: Mapped[int] = mapped_column(Integer(), nullable=False, default=0)

    lesson: Mapped[Lesson] = relationship(back_populates="questions")
    alternatives: Mapped[list["Alternative"]] = relationship(
        back_populates="question",
        cascade="all, delete-orphan",
        order_by="Alternative.order",
    )


class Alternative(AuditedModel):
    """Alternativa de uma questÃ£o (05 - Database/Database Specification.md.md, "Alternatives")."""

    __tablename__ = "alternatives"
    __table_args__ = (
        UniqueConstraint("question_id", "order", name="uq_alternatives_question_id_order"),
    )

    question_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("questions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    text: Mapped[str] = mapped_column(Text(), nullable=False)
    is_correct: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=False)
    feedback: Mapped[str | None] = mapped_column(Text(), default=None)
    order: Mapped[int] = mapped_column(Integer(), nullable=False, default=0)

    question: Mapped[Question] = relationship(back_populates="alternatives")
