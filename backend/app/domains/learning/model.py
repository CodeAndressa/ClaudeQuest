import enum
import uuid

from sqlalchemy import Boolean, Enum, ForeignKey, Integer, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import AuditedModel


class QuestionType(enum.StrEnum):
    """Tipos de questão previstos em 05 - Database/Database Specification.md.md.

    Apenas MULTIPLE_CHOICE é utilizado nesta primeira entrega (LEARN-001 a
    LEARN-006, conteúdo apenas de leitura) — os demais tipos ficam registrados
    aqui para não exigir migração futura quando forem implementados.
    """

    MULTIPLE_CHOICE = "multiple_choice"
    BOOLEAN = "boolean"
    CODE = "code"
    TEXT = "text"
    UPLOAD = "upload"
    DRAG_AND_DROP = "drag_and_drop"


class LessonType(enum.StrEnum):
    """Tipos de missão (08 - Gamification/Learning Engine.md.md, "Tipos de Missão")."""

    READING = "reading"
    QUIZ = "quiz"
    CHALLENGE = "challenge"
    LAB = "lab"
    UPLOAD = "upload"
    CHECKLIST = "checklist"
    FREE_ANSWER = "free_answer"


class Track(AuditedModel):
    """Trilha (05 - Database/Database Specification.md.md, seção "Tracks").

    Exemplos: Claude Chat, Claude Cowork, Claude Code, Prompt Engineering, MCP.
    """

    __tablename__ = "tracks"

    title: Mapped[str] = mapped_column(nullable=False)
    description: Mapped[str] = mapped_column(Text(), nullable=False)
    difficulty: Mapped[str] = mapped_column(nullable=False, default="beginner")
    estimated_hours: Mapped[int] = mapped_column(Integer(), nullable=False, default=0)
    image: Mapped[str | None] = mapped_column(default=None)
    icon: Mapped[str | None] = mapped_column(default=None)
    order: Mapped[int] = mapped_column(Integer(), nullable=False, default=0, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=True)

    modules: Mapped[list["Module"]] = relationship(
        back_populates="track",
        cascade="all, delete-orphan",
        order_by="Module.order",
    )


class Module(AuditedModel):
    """Módulo de uma trilha (Learning Content.md.md, "Estrutura dos Módulos").

    Não existia como tabela própria no Database Specification original (que vai
    direto de Track para Level) — adicionada por exigência explícita da tarefa
    LEARN-001..006, que define a hierarquia oficial como
    Track -> Module -> Level -> Lesson -> Question -> Alternative. Cada módulo
    ensina um único tema, nunca misturando assuntos.
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
    """Nível (05 - Database/Database Specification.md.md, seção "Levels").

    Tipos usuais (Learning Engine.md.md, "Níveis"): Básico, Intermediário,
    Avançado, Especialista, Master — representados livremente em `title`.
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
    """Missão (05 - Database/Database Specification.md.md, seção "Lessons").

    Regra de qualidade (Learning Engine.md.md, "Critérios de Qualidade"): toda
    missão deve ensinar apenas um conceito principal e ser concluída em menos
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
    """Questão de uma missão (05 - Database/Database Specification.md.md, "Questions")."""

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
    """Alternativa de uma questão (05 - Database/Database Specification.md.md, "Alternatives")."""

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
