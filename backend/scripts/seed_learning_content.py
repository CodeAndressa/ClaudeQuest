# ruff: noqa: E501
"""
Cria o catalogo inicial de trilhas e conteudos da ClaudeQuest.

Fonte: vault Obsidian `10 - Learning Content/Learning Content.md.md`.

Cada trilha criada segue a hierarquia implementada no backend:

School -> Track -> Module -> Level -> Lesson -> Question -> Alternative.

Uso: uv run python scripts/seed_learning_content.py
"""

import asyncio
from dataclasses import dataclass

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
    School,
    Track,
)


@dataclass(frozen=True)
class LessonSeed:
    title: str
    description: str
    concept: str
    correct: str
    wrong_a: str
    wrong_b: str
    lesson_type: LessonType = LessonType.QUIZ
    xp: int = 30


@dataclass(frozen=True)
class ModuleSeed:
    title: str
    description: str
    lessons: tuple[LessonSeed, LessonSeed]


@dataclass(frozen=True)
class TrackSeed:
    title: str
    description: str
    difficulty: str
    estimated_hours: int
    icon: str
    order: int
    modules: tuple[ModuleSeed, ModuleSeed]


TRACKS: tuple[TrackSeed, ...] = (
    TrackSeed(
        title="Fundamentos de IA",
        description="Construa a base para usar IA moderna com clareza, criterio e seguranca.",
        difficulty="beginner",
        estimated_hours=5,
        icon="sparkles",
        order=1,
        modules=(
            ModuleSeed(
                title="Como a IA pensa",
                description="Entenda o que modelos de linguagem fazem e onde falham.",
                lessons=(
                    LessonSeed(
                        title="O que e um LLM",
                        description="Aprenda a diferenca entre prever texto e saber fatos.",
                        concept="LLMs geram respostas a partir de padroes, contexto e instrucao.",
                        correct="Como um sistema que gera respostas a partir de padroes e contexto",
                        wrong_a="Como um banco de dados sempre atualizado",
                        wrong_b="Como uma pessoa especialista que nunca erra",
                    ),
                    LessonSeed(
                        title="Quando confiar e quando verificar",
                        description="Separe tarefas criativas de tarefas que exigem evidencia.",
                        concept="Quanto maior o custo de um erro, mais forte deve ser a verificacao.",
                        correct="Ao decidir algo que afeta clientes, dinheiro, leis ou operacao",
                        wrong_a="Ao listar ideias internas de baixo risco",
                        wrong_b="Ao transformar notas pessoais em rascunho",
                    ),
                ),
            ),
            ModuleSeed(
                title="Boas praticas de uso",
                description="Aprenda a pedir, revisar e iterar sem perder controle.",
                lessons=(
                    LessonSeed(
                        title="De pedido vago a pedido claro",
                        description="Transforme uma pergunta solta em uma instrucao acionavel.",
                        concept="Um bom pedido informa objetivo, contexto, publico, restricoes e formato.",
                        correct="Dizer objetivo, contexto e formato esperado",
                        wrong_a="Escrever tudo em letras maiusculas",
                        wrong_b="Pedir sempre a resposta mais longa possivel",
                        lesson_type=LessonType.CHALLENGE,
                    ),
                    LessonSeed(
                        title="Iteracao guiada",
                        description="Melhore uma resposta em ciclos curtos e objetivos.",
                        concept="Iterar bem e pedir ajustes especificos, nao apenas pedir para melhorar.",
                        correct="Reescreva com tom mais direto e reduza para cinco bullets",
                        wrong_a="Melhore isso",
                        wrong_b="Faca qualquer coisa diferente",
                    ),
                ),
            ),
        ),
    ),
    TrackSeed(
        title="Claude Chat",
        description="Domine o Claude Chat para pesquisa, analise, escrita e organizacao.",
        difficulty="beginner",
        estimated_hours=6,
        icon="message-circle",
        order=2,
        modules=(
            ModuleSeed(
                title="Interface",
                description="Navegue pela interface com seguranca.",
                lessons=(
                    LessonSeed(
                        title="Conhecendo a tela inicial",
                        description="Identifique conversa, historico e area de mensagem.",
                        concept="Historico, area de mensagem e controles da conversa organizam o trabalho.",
                        correct="Retomar contextos e trabalhos anteriores com facilidade",
                        wrong_a="Aumentar automaticamente a qualidade do modelo",
                        wrong_b="Substituir revisao humana",
                    ),
                    LessonSeed(
                        title="Arquivos e contexto",
                        description="Use anexos para dar material real ao Claude.",
                        concept="Arquivos ajudam quando voce explica o que eles representam e qual saida espera.",
                        correct="Uma instrucao sobre o que analisar ou produzir",
                        wrong_a="Apenas a frase veja isso",
                        wrong_b="Nada, o arquivo sempre basta sozinho",
                    ),
                ),
            ),
            ModuleSeed(
                title="Projetos",
                description="Agrupe conversas e materiais por objetivo.",
                lessons=(
                    LessonSeed(
                        title="O que sao Projetos",
                        description="Entenda quando usar um projeto em vez de conversa solta.",
                        concept="Projetos reunem conversas, instrucoes e arquivos de um mesmo objetivo.",
                        correct="Quando varias conversas usam o mesmo contexto",
                        wrong_a="Quando voce so precisa de uma pergunta rapida",
                        wrong_b="Quando quer apagar o historico",
                    ),
                    LessonSeed(
                        title="Instrucoes do Projeto",
                        description="Crie instrucoes que guiam respostas futuras.",
                        concept="Instrucoes de projeto definem tom, publico, regras e formato recorrente.",
                        correct="Tom de voz, publico e criterios de resposta",
                        wrong_a="Uma pergunta pontual de hoje",
                        wrong_b="Uma senha de sistema",
                        lesson_type=LessonType.CHALLENGE,
                    ),
                ),
            ),
        ),
    ),
    TrackSeed(
        title="Claude Cowork",
        description="Use IA como parceira de documentacao, planejamento e comunicacao.",
        difficulty="intermediate",
        estimated_hours=7,
        icon="users",
        order=3,
        modules=(
            ModuleSeed(
                title="Documentacao",
                description="Transforme informacao solta em documentos uteis.",
                lessons=(
                    LessonSeed(
                        title="De notas para documento",
                        description="Converta anotacoes em estrutura legivel.",
                        concept="Notas viram documento quando ganham objetivo, decisoes e proximos passos.",
                        correct="Proximos passos",
                        wrong_a="Uma lista de adjetivos",
                        wrong_b="Um titulo decorativo",
                        lesson_type=LessonType.CHALLENGE,
                    ),
                    LessonSeed(
                        title="Perguntas de esclarecimento",
                        description="Use Claude para encontrar lacunas no raciocinio.",
                        concept="Perguntas revelam ambiguidades antes que a equipe execute.",
                        correct="Descobrir lacunas e reduzir ambiguidade",
                        wrong_a="Evitar falar com pessoas envolvidas",
                        wrong_b="Deixar o documento maior",
                    ),
                ),
            ),
            ModuleSeed(
                title="Planejamento",
                description="Crie planos, roadmaps e criterios de aceite.",
                lessons=(
                    LessonSeed(
                        title="Plano em fases",
                        description="Divida objetivos grandes em entregas validaveis.",
                        concept="Uma boa fase entrega valor cedo, reduz risco e permite validacao.",
                        correct="Entregar algo pequeno, testavel e util",
                        wrong_a="Resolver todos os problemas futuros",
                        wrong_b="Evitar qualquer criterio de aceite",
                    ),
                    LessonSeed(
                        title="Criterios de aceite",
                        description="Escreva criterios objetivos para validar entregas.",
                        concept="Criterios de aceite devem ser observaveis e testaveis.",
                        correct="Usuario autenticado consegue abrir o dashboard",
                        wrong_a="A experiencia deve ficar incrivel",
                        wrong_b="O codigo deve parecer melhor",
                        lesson_type=LessonType.CHALLENGE,
                    ),
                ),
            ),
        ),
    ),
    TrackSeed(
        title="Claude Code",
        description="Aprenda desenvolvimento assistido por IA com leitura, testes e entrega.",
        difficulty="intermediate",
        estimated_hours=8,
        icon="terminal",
        order=4,
        modules=(
            ModuleSeed(
                title="Leitura de codigo",
                description="Use IA para entender sistemas existentes antes de alterar.",
                lessons=(
                    LessonSeed(
                        title="Mapa inicial do repositorio",
                        description="Peca uma leitura estrutural antes de pedir mudancas.",
                        concept="Contexto vem antes da edicao: estrutura, comandos, testes e convencoes.",
                        correct="Mapear estrutura, comandos e testes existentes",
                        wrong_a="Reescrever tudo em uma arquitetura nova",
                        wrong_b="Ignorar os testes para ir mais rapido",
                    ),
                    LessonSeed(
                        title="Fluxo de dados",
                        description="Investigue de onde vem e para onde vai um dado.",
                        concept="Entender entrada, validacao, regra, persistencia e resposta localiza bugs.",
                        correct="Por quais arquivos esse dado passa ate chegar na tela?",
                        wrong_a="Voce pode adivinhar sem olhar o codigo?",
                        wrong_b="Qual framework e mais famoso?",
                        lesson_type=LessonType.CHALLENGE,
                    ),
                ),
            ),
            ModuleSeed(
                title="Testes e entrega",
                description="Valide mudancas antes de considerar uma tarefa pronta.",
                lessons=(
                    LessonSeed(
                        title="Teste focado no risco",
                        description="Escolha testes proporcionais ao impacto da mudanca.",
                        concept="O teste certo protege o comportamento que pode quebrar.",
                        correct="Pelo comportamento que pode quebrar e pelo impacto no usuario",
                        wrong_a="Sempre escrever o maior teste possivel",
                        wrong_b="Nunca testar se a mudanca parece simples",
                    ),
                    LessonSeed(
                        title="Resumo de entrega",
                        description="Comunique o que mudou, como validou e o que ficou fora.",
                        concept="Um bom resumo registra mudancas, validacoes e limites conhecidos.",
                        correct="Mudancas feitas, validacoes e limites conhecidos",
                        wrong_a="Apenas uma frase dizendo que esta pronto",
                        wrong_b="Todos os detalhes internos sem priorizar nada",
                    ),
                ),
            ),
        ),
    ),
    TrackSeed(
        title="AI Engineering",
        description="Projete sistemas com agentes, ferramentas, avaliacao e observabilidade.",
        difficulty="advanced",
        estimated_hours=9,
        icon="workflow",
        order=5,
        modules=(
            ModuleSeed(
                title="Agents e ferramentas",
                description="Entenda agentes como loops de decisao com ferramentas.",
                lessons=(
                    LessonSeed(
                        title="O que torna um fluxo agente",
                        description="Diferencie chamada unica de loop com decisao.",
                        concept="Um agente combina objetivo, estado, ferramentas e criterio de parada.",
                        correct="Um loop que observa resultados e decide proximas acoes",
                        wrong_a="Um prompt muito longo sem ferramentas",
                        wrong_b="Uma resposta fixa salva em arquivo",
                    ),
                    LessonSeed(
                        title="Ferramentas com contratos claros",
                        description="Defina entradas, saidas e erros das ferramentas.",
                        concept="Ferramentas boas possuem nome claro, parametros e resultado previsivel.",
                        correct="Parametros e respostas bem definidos",
                        wrong_a="Nome generico como fazer_coisa",
                        wrong_b="Erros silenciosos",
                        lesson_type=LessonType.CHALLENGE,
                    ),
                ),
            ),
            ModuleSeed(
                title="Evaluation",
                description="Meca qualidade de respostas e fluxos de IA.",
                lessons=(
                    LessonSeed(
                        title="Rubricas simples",
                        description="Defina criterios antes de avaliar uma resposta.",
                        concept="Rubricas transformam qualidade em criterios explicitos.",
                        correct="Avaliar respostas por criterios explicitos",
                        wrong_a="Deixar prompts mais misteriosos",
                        wrong_b="Impedir qualquer revisao humana",
                    ),
                    LessonSeed(
                        title="Casos de teste de IA",
                        description="Monte exemplos representativos para comparar modelos.",
                        concept="Um bom conjunto inclui casos comuns, limites e problemas historicos.",
                        correct="Um caso comum, um caso limite e um caso problematico",
                        wrong_a="Somente o exemplo mais facil",
                        wrong_b="Nenhum caso fixo, apenas impressao subjetiva",
                        lesson_type=LessonType.CHALLENGE,
                    ),
                ),
            ),
        ),
    ),
)


SCHOOL_TITLE = "Claude Academy"
SCHOOL_SLUG = "claude-academy"
SCHOOL_DESCRIPTION = "Escola principal com trilhas de IA, Claude e desenvolvimento assistido."
SCHOOL_ICON = "graduation-cap"


def _content_for(track: TrackSeed, module: ModuleSeed, lesson: LessonSeed) -> str:
    return (
        f"# {lesson.title}\n\n"
        f"## Objetivo\n{lesson.description}\n\n"
        f"## Conceito principal\n{lesson.concept}\n\n"
        "## Como praticar\n"
        "1. Leia o conceito com atencao.\n"
        "2. Crie um exemplo seu usando uma situacao real de trabalho.\n"
        "3. Responda a questao da missao e revise o feedback.\n\n"
        f"## Contexto da trilha\nEsta missao pertence a trilha {track.title}, modulo {module.title}.\n\n"
        "## Proximo passo\nAvance para a proxima missao e compare o que mudou no seu criterio de uso."
    )


async def _get_track(session: AsyncSession, title: str) -> Track | None:
    return await session.scalar(select(Track).where(Track.title == title))


async def _get_or_create_school(session: AsyncSession) -> School:
    school = await session.scalar(select(School).where(School.slug == SCHOOL_SLUG))
    if school is None:
        school = School(
            title=SCHOOL_TITLE,
            slug=SCHOOL_SLUG,
            description=SCHOOL_DESCRIPTION,
            icon=SCHOOL_ICON,
            order=1,
            is_active=True,
        )
        session.add(school)
        await session.flush()
        return school

    school.title = SCHOOL_TITLE
    school.description = SCHOOL_DESCRIPTION
    school.icon = SCHOOL_ICON
    school.order = 1
    school.is_active = True
    return school


def _update_track_metadata(track: Track, track_data: TrackSeed) -> None:
    track.description = track_data.description
    track.difficulty = track_data.difficulty
    track.estimated_hours = track_data.estimated_hours
    track.icon = track_data.icon
    track.order = track_data.order
    track.is_active = True


async def _create_track(session: AsyncSession, school: School, track_data: TrackSeed) -> None:
    track = Track(
        school_id=school.id,
        title=track_data.title,
        description=track_data.description,
        difficulty=track_data.difficulty,
        estimated_hours=track_data.estimated_hours,
        icon=track_data.icon,
        order=track_data.order,
        is_active=True,
    )
    session.add(track)
    await session.flush()

    for module_order, module_data in enumerate(track_data.modules, start=1):
        module = Module(
            track_id=track.id,
            title=module_data.title,
            description=module_data.description,
            order=module_order,
            is_active=True,
        )
        session.add(module)
        await session.flush()

        total_xp = sum(lesson.xp for lesson in module_data.lessons)
        level = Level(
            module_id=module.id,
            title="Nivel 1",
            description=f"Introducao a {module_data.title}.",
            level_number=1,
            estimated_minutes=len(module_data.lessons) * 7,
            xp=total_xp,
            required_xp=0,
        )
        session.add(level)
        await session.flush()

        for lesson_order, lesson_data in enumerate(module_data.lessons, start=1):
            lesson = Lesson(
                level_id=level.id,
                title=lesson_data.title,
                description=lesson_data.description,
                content=_content_for(track_data, module_data, lesson_data),
                estimated_minutes=7,
                difficulty=track_data.difficulty,
                lesson_type=lesson_data.lesson_type,
                order=lesson_order,
                xp=lesson_data.xp,
                ai_corrected=False,
            )
            session.add(lesson)
            await session.flush()

            question = Question(
                lesson_id=lesson.id,
                question=f"Qual alternativa representa melhor esta missao: {lesson_data.title}?",
                question_type=QuestionType.MULTIPLE_CHOICE,
                explanation=lesson_data.concept,
                points=1,
                order=1,
            )
            session.add(question)
            await session.flush()

            alternatives = (
                (lesson_data.correct, True, "Correto. Essa resposta segue o conceito da missao."),
                (lesson_data.wrong_a, False, "Ainda nao. Revise o conceito principal da missao."),
                (lesson_data.wrong_b, False, "Nao e a melhor opcao para este contexto."),
            )
            for alt_order, (text, is_correct, feedback) in enumerate(alternatives, start=1):
                session.add(
                    Alternative(
                        question_id=question.id,
                        text=text,
                        is_correct=is_correct,
                        feedback=feedback,
                        order=alt_order,
                    )
                )


async def seed(session: AsyncSession) -> None:
    created_tracks = 0
    skipped_tracks: list[str] = []
    school = await _get_or_create_school(session)

    for track_data in TRACKS:
        existing_track = await _get_track(session, track_data.title)
        if existing_track is not None:
            existing_track.school_id = school.id
            _update_track_metadata(existing_track, track_data)
            skipped_tracks.append(track_data.title)
            continue

        await _create_track(session, school, track_data)
        created_tracks += 1

    await session.commit()

    print(f"Trilhas criadas: {created_tracks}")
    if skipped_tracks:
        print("Trilhas ja existentes atualizadas: " + ", ".join(skipped_tracks))


async def main() -> None:
    async with AsyncSessionLocal() as session:
        await seed(session)


if __name__ == "__main__":
    asyncio.run(main())
