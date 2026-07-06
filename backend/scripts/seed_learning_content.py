"""
Cria a trilha "Claude Chat" com conteúdo mínimo completo, conforme previsto em
10 - Learning Content/Learning Content.md.md e 08 - Gamification/Learning Engine.md.md:
Track -> Module -> Level -> Lesson -> Question -> Alternative.

Estrutura criada:
- 1 trilha: "Claude Chat"
  - 2 módulos: "Interface" e "Projetos"
    - 1 nível cada
      - 2 missões cada (múltipla escolha, 1 questão com alternativas por missão)

Uso: uv run python scripts/seed_learning_content.py
"""

import asyncio
from typing import TypedDict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import AsyncSessionLocal
from app.domains.learning.model import (
    Alternative,
    Lesson,
    LessonType,
    Level,
    Module,
    Question,
    QuestionType,
    Track,
)

TRACK_TITLE = "Claude Chat"


class _LessonSeed(TypedDict):
    title: str
    description: str
    content: str
    question: str
    alternatives: list[tuple[str, bool]]


class _ModuleSeed(TypedDict):
    title: str
    description: str
    lessons: list[_LessonSeed]


_MODULES: list[_ModuleSeed] = [
    {
        "title": "Interface",
        "description": "Aprenda a navegar pela interface do Claude Chat com confiança.",
        "lessons": [
            {
                "title": "Conhecendo a tela inicial",
                "description": "Entenda os principais elementos da tela inicial do Claude Chat.",
                "content": (
                    "A tela inicial do Claude Chat apresenta a caixa de mensagem, o histórico "
                    "de conversas e o seletor de modelos. Vamos explorar cada um deles."
                ),
                "question": "Onde fica o histórico de conversas no Claude Chat?",
                "alternatives": [
                    ("Na barra lateral esquerda", True),
                    ("Dentro das configurações de conta", False),
                ],
            },
            {
                "title": "Iniciando uma nova conversa",
                "description": "Aprenda a iniciar e nomear uma nova conversa.",
                "content": (
                    "Toda nova conversa começa com um clique em 'Nova conversa'. Você pode "
                    "renomeá-la a qualquer momento para facilitar sua organização."
                ),
                "question": "Como você inicia uma nova conversa no Claude Chat?",
                "alternatives": [
                    ("Clicando no botão 'Nova conversa'", True),
                    ("Recarregando a página do navegador", False),
                ],
            },
        ],
    },
    {
        "title": "Projetos",
        "description": "Organize conversas relacionadas usando Projetos no Claude Chat.",
        "lessons": [
            {
                "title": "O que são Projetos",
                "description": "Entenda para que servem os Projetos no Claude Chat.",
                "content": (
                    "Projetos agrupam conversas e arquivos relacionados a um mesmo objetivo, "
                    "mantendo contexto compartilhado entre elas."
                ),
                "question": "Qual o principal benefício de usar Projetos?",
                "alternatives": [
                    ("Compartilhar contexto entre conversas relacionadas", True),
                    ("Aumentar o limite de mensagens diárias", False),
                ],
            },
            {
                "title": "Criando seu primeiro Projeto",
                "description": "Pratique a criação de um Projeto no Claude Chat.",
                "content": (
                    "Para criar um Projeto, acesse a seção 'Projetos' na barra lateral e "
                    "clique em 'Novo projeto'. Em seguida, adicione instruções e arquivos."
                ),
                "question": "Onde você cria um novo Projeto?",
                "alternatives": [
                    ("Na seção 'Projetos' da barra lateral", True),
                    ("No menu de configurações de segurança", False),
                ],
            },
        ],
    },
]


async def seed(session: AsyncSession) -> None:
    existing_track = await session.scalar(select(Track).where(Track.title == TRACK_TITLE))
    if existing_track is not None:
        print(f"Trilha '{TRACK_TITLE}' já existe — nada a fazer.")
        return

    track = Track(
        title=TRACK_TITLE,
        description="Domine completamente o Claude Chat: interface, projetos, memória e mais.",
        difficulty="beginner",
        estimated_hours=4,
        icon="message-circle",
        order=1,
        is_active=True,
    )
    session.add(track)
    await session.flush()

    for module_order, module_data in enumerate(_MODULES, start=1):
        module = Module(
            track_id=track.id,
            title=module_data["title"],
            description=module_data["description"],
            order=module_order,
        )
        session.add(module)
        await session.flush()

        level = Level(
            module_id=module.id,
            title="Nível 1",
            description=f"Introdução a {module_data['title']}.",
            level_number=1,
            estimated_minutes=10,
            xp=20,
            required_xp=0,
        )
        session.add(level)
        await session.flush()

        for lesson_order, lesson_data in enumerate(module_data["lessons"], start=1):
            lesson = Lesson(
                level_id=level.id,
                title=lesson_data["title"],
                description=lesson_data["description"],
                content=lesson_data["content"],
                estimated_minutes=5,
                difficulty="beginner",
                lesson_type=LessonType.QUIZ,
                order=lesson_order,
                xp=10,
                ai_corrected=False,
            )
            session.add(lesson)
            await session.flush()

            question = Question(
                lesson_id=lesson.id,
                question=lesson_data["question"],
                question_type=QuestionType.MULTIPLE_CHOICE,
                points=1,
                order=1,
            )
            session.add(question)
            await session.flush()

            for alt_order, (text, is_correct) in enumerate(lesson_data["alternatives"], start=1):
                session.add(
                    Alternative(
                        question_id=question.id,
                        text=text,
                        is_correct=is_correct,
                        order=alt_order,
                    )
                )

    await session.commit()
    print(f"Trilha '{TRACK_TITLE}' criada com {len(_MODULES)} módulos.")


async def main() -> None:
    async with AsyncSessionLocal() as session:
        await seed(session)


if __name__ == "__main__":
    asyncio.run(main())
