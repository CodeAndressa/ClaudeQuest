import uuid

from pydantic import BaseModel, ConfigDict


class TrackSummary(BaseModel):
    """Resumo de trilha usado na listagem (GET /api/v1/learning/tracks)."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    description: str
    difficulty: str
    estimated_hours: int
    image: str | None
    icon: str | None
    order: int


class AlternativeDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    text: str
    is_correct: bool
    feedback: str | None
    order: int


class QuestionDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    question: str
    question_type: str
    explanation: str | None
    points: int
    order: int
    alternatives: list[AlternativeDetail]


class LessonDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    description: str
    content: str
    estimated_minutes: int
    difficulty: str
    lesson_type: str
    order: int
    xp: int
    ai_corrected: bool
    questions: list[QuestionDetail]


class LevelDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    description: str
    level_number: int
    estimated_minutes: int
    xp: int
    stars: int
    required_xp: int
    lessons: list[LessonDetail]


class ModuleDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    description: str
    order: int
    levels: list[LevelDetail]


class TrackDetail(BaseModel):
    """Detalhe completo da trilha, com módulos, níveis, missões, questões e alternativas."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    description: str
    difficulty: str
    estimated_hours: int
    image: str | None
    icon: str | None
    order: int
    is_active: bool
    modules: list[ModuleDetail]
