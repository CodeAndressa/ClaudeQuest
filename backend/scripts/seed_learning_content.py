# ruff: noqa: E501
"""
Cria o catálogo inicial de trilhas e conteúdos da ClaudeQuest.

Fonte: vault Obsidian `10 - Learning Content/Learning Content.md.md`.

Cada trilha criada segue a hierarquia implementada no backend:

School -> Track -> Module -> Level -> Lesson -> Question -> Alternative.

Idempotente: quando uma trilha já existe (mesmo `title`), seus metadados e todo o
conteúdo aninhado (módulos, níveis, missões, questões e alternativas) são
sincronizados com os dados definidos abaixo, sem recriar registros - os IDs
existentes são preservados para não quebrar referências como
`user_lesson_progress.lesson_id`.

Uso: uv run python scripts/seed_learning_content.py
"""

import asyncio
import re
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from math import ceil

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
class AlternativeSeed:
    text: str
    is_correct: bool
    feedback: str


@dataclass(frozen=True)
class QuestionSeed:
    question: str
    question_type: QuestionType
    explanation: str
    alternatives: tuple[AlternativeSeed, ...]
    points: int = 1


@dataclass(frozen=True)
class LessonSeed:
    title: str
    description: str
    content: str
    concept: str
    correct: str
    wrong_a: str
    wrong_b: str
    lesson_type: LessonType = LessonType.QUIZ
    xp: int = 30
    questions: tuple[QuestionSeed, ...] = ()


@dataclass(frozen=True)
class ModuleSeed:
    title: str
    description: str
    lessons: tuple[LessonSeed, ...]


@dataclass(frozen=True)
class TrackSeed:
    title: str
    description: str
    difficulty: str
    estimated_hours: int
    icon: str
    order: int
    modules: tuple[ModuleSeed, ...]


_PORTUGUESE_ACCENTS = {
    "alem": "além",
    "aplicacao": "aplicação",
    "aplicacoes": "aplicações",
    "aprovacao": "aprovação",
    "acao": "ação",
    "acoes": "ações",
    "analise": "análise",
    "ate": "até",
    "autorizacao": "autorização",
    "avaliacao": "avaliação",
    "avaliacoes": "avaliações",
    "avancado": "avançado",
    "basico": "básico",
    "comunicacao": "comunicação",
    "configuracao": "configuração",
    "conteudo": "conteúdo",
    "conteudos": "conteúdos",
    "criacao": "criação",
    "colaboracao": "colaboração",
    "comparacao": "comparação",
    "conclusao": "conclusão",
    "criterio": "critério",
    "criterios": "critérios",
    "decisao": "decisão",
    "decisoes": "decisões",
    "descricao": "descrição",
    "documentacao": "documentação",
    "evidencia": "evidência",
    "evidencias": "evidências",
    "execucao": "execução",
    "explicacao": "explicação",
    "explicito": "explícito",
    "explicita": "explícita",
    "experiencia": "experiência",
    "funcao": "função",
    "funcoes": "funções",
    "geracao": "geração",
    "implementacao": "implementação",
    "informacao": "informação",
    "informacoes": "informações",
    "integracao": "integração",
    "introducao": "introdução",
    "intencao": "intenção",
    "intermediario": "intermediário",
    "missao": "missão",
    "missoes": "missões",
    "modulo": "módulo",
    "modulos": "módulos",
    "nao": "não",
    "necessaria": "necessária",
    "necessarias": "necessárias",
    "necessario": "necessário",
    "necessarios": "necessários",
    "nivel": "nível",
    "niveis": "níveis",
    "opcao": "opção",
    "opcoes": "opções",
    "organizacao": "organização",
    "otimizacao": "otimização",
    "possivel": "possível",
    "possiveis": "possíveis",
    "pratica": "prática",
    "praticas": "práticas",
    "proximo": "próximo",
    "proximos": "próximos",
    "questao": "questão",
    "questoes": "questões",
    "relatorio": "relatório",
    "relatorios": "relatórios",
    "responsavel": "responsável",
    "responsaveis": "responsáveis",
    "restricao": "restrição",
    "restricoes": "restrições",
    "revisao": "revisão",
    "seguranca": "segurança",
    "sequencia": "sequência",
    "solucao": "solução",
    "solucoes": "soluções",
    "so": "só",
    "sao": "são",
    "estao": "estão",
    "tambem": "também",
    "titulo": "título",
    "titulos": "títulos",
    "usuario": "usuário",
    "usuarios": "usuários",
    "validacao": "validação",
    "verificacao": "verificação",
    "voce": "você",
    "voces": "vocês",
    "ja": "já",
    "limitacao": "limitação",
    "limitacoes": "limitações",
    "observavel": "observável",
    "permissao": "permissão",
    "permissoes": "permissões",
    "recuperacao": "recuperação",
    "transacao": "transação",
    "transacoes": "transações",
}


def _with_portuguese_accents(text: str) -> str:
    def replace_word(match: re.Match[str]) -> str:
        original = match.group(0)
        replacement = _PORTUGUESE_ACCENTS[original.casefold()]
        if original.isupper():
            return replacement.upper()
        if original[0].isupper():
            return replacement[0].upper() + replacement[1:]
        return replacement

    pattern = r"\b(" + "|".join(map(re.escape, _PORTUGUESE_ACCENTS)) + r")\b"
    return re.sub(pattern, replace_word, text, flags=re.IGNORECASE)


def _estimated_lesson_minutes(lesson: LessonSeed) -> int:
    word_count = len(re.findall(r"\w+", lesson.content))
    base_and_rate = {
        LessonType.READING: (3, 180, 6, 15),
        LessonType.QUIZ: (6, 220, 7, 12),
        LessonType.CHALLENGE: (10, 220, 12, 20),
        LessonType.LAB: (15, 200, 18, 30),
        LessonType.UPLOAD: (12, 220, 15, 25),
        LessonType.CHECKLIST: (8, 220, 10, 18),
        LessonType.FREE_ANSWER: (10, 220, 12, 20),
    }
    base, words_per_minute, minimum, maximum = base_and_rate[lesson.lesson_type]
    return max(minimum, min(maximum, base + ceil(word_count / words_per_minute)))


def _estimated_track_hours(track: TrackSeed) -> int:
    total_minutes = sum(
        _estimated_lesson_minutes(lesson) for module in track.modules for lesson in module.lessons
    )
    return max(1, ceil(total_minutes / 60))


TRACKS: tuple[TrackSeed, ...] = (
    TrackSeed(
        title="Fundamentos de IA",
        description="Construa a base para usar IA moderna com clareza, critério e segurança.",
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
                        title="O que é um LLM",
                        description="Aprenda a diferença entre prever texto e saber fatos.",
                        content="""## Introdução

Toda vez que você digita uma pergunta para uma IA e recebe uma resposta em segundos, algo específico está acontecendo por trás - e entender o quê muda completamente como você usa essa ferramenta no trabalho. Quem trata um LLM como um mecanismo de busca ou como um especialista infalível vai, cedo ou tarde, tomar uma decisão ruim baseada numa resposta que soava certa mas não era.

## Conceito

Um LLM (Large Language Model, ou "modelo de linguagem de grande escala") é um sistema treinado com uma quantidade enorme de texto - livros, artigos, código, conversas - para aprender os padrões estatísticos de como a linguagem humana funciona. Ele não "memoriza fatos" da forma como um banco de dados guarda registros; ele aprende, com base em bilhões de exemplos, qual é a próxima palavra mais provável dado tudo o que veio antes. Quando você pede um resumo, uma explicação ou um código, o modelo está construindo a resposta palavra por palavra, escolhendo a cada passo o que é mais coerente com o padrão aprendido e com o contexto que você forneceu.

É por isso que um LLM pode "alucinar": como ele foi otimizado para gerar texto plausível e fluente, não para consultar uma fonte de verdade, é possível que ele produza uma informação errada com a mesma confiança e fluência de uma informação correta. Um nome de lei que não existe, uma citação inventada, uma estatística que parece precisa mas nunca foi verificada - tudo isso pode sair com a mesma naturalidade de um fato real, porque o modelo está otimizando para "o que soa certo", não para "o que é verificadamente certo".

Uma analogia útil: pense num profissional muito bem lido, com memória de curto prazo excelente e ótima capacidade de argumentação, mas que não tem acesso a nenhum arquivo, banco de dados ou internet no momento em que fala com você - e que também não tem o hábito de dizer "não sei". Essa pessoa vai te dar respostas fluentes e geralmente úteis, baseadas em tudo o que já leu na vida, mas ocasionalmente vai preencher uma lacuna de memória com algo inventado, sem perceber que está fazendo isso. O LLM funciona de um jeito parecido: forte em padrões de linguagem e raciocínio, mas sem uma conexão direta e confiável com "o que é verdade agora".

## Exemplo prático

Imagine que você pede à IA o nome do responsável atual por um departamento da sua empresa, ou o valor exato de uma taxa regulatória vigente. O modelo pode responder com um nome ou número que parece perfeitamente razoável - porque se encaixa no padrão de como essas respostas costumam ser formuladas - mas que pode estar desatualizado ou simplesmente errado, já que o modelo não está consultando um cadastro em tempo real. Já se você pedir para ele explicar um conceito, estruturar um argumento ou reescrever um texto, ele está no seu terreno mais forte: gerar linguagem coerente a partir de um padrão, tarefa em que erros de fato pesam muito menos.

## Erro comum

O erro mais comum é tratar a fluência da resposta como sinônimo de precisão: como o texto sai bem escrito e seguro, presume-se que também está correto. Fluência e exatidão são coisas diferentes - um LLM é consistentemente fluente, mas só é consistentemente exato quando o assunto está bem representado nos padrões que ele aprendeu e quando não depende de informação atualizada ou específica demais.

## Resumo

Um LLM gera respostas prevendo padrões de linguagem a partir do contexto que você dá, não consultando um repositório de fatos verificados - por isso, saber reconhecer quando uma resposta é "linguagem plausível" versus "fato confirmado" é a base de tudo o que vem a seguir nesta trilha.""",
                        concept="LLMs geram respostas a partir de padrões, contexto e instrução.",
                        correct="Como um sistema que gera respostas a partir de padrões e contexto",
                        wrong_a="Como um banco de dados sempre atualizado",
                        wrong_b="Como uma pessoa especialista que nunca erra",
                        questions=(
                            QuestionSeed(
                                question="O que acontece enquanto um LLM constrói uma resposta-",
                                question_type=QuestionType.MULTIPLE_CHOICE,
                                explanation="O modelo estima a continuação mais provável usando o contexto disponível.",
                                alternatives=(
                                    AlternativeSeed(
                                        "Prevê sucessivamente partes do texto com base em padrões",
                                        True,
                                        "Correto: a geração acontece passo a passo a partir de probabilidades.",
                                    ),
                                    AlternativeSeed(
                                        "Consulta obrigatoriamente um cadastro de fatos verificados",
                                        False,
                                        "Um LLM não consulta uma fonte de verdade por padrão.",
                                    ),
                                    AlternativeSeed(
                                        "Recupera uma resposta completa que estava armazenada",
                                        False,
                                        "A resposta é gerada, não recuperada como um registro pronto.",
                                    ),
                                ),
                            ),
                            QuestionSeed(
                                question="A IA citou com segurança uma pesquisa que não existe. Qual característica explica melhor o ocorrido-",
                                question_type=QuestionType.MULTIPLE_CHOICE,
                                explanation="Fluência mede plausibilidade linguística, não comprovação factual.",
                                alternatives=(
                                    AlternativeSeed(
                                        "O modelo gerou uma continuação plausível sem validar a fonte",
                                        True,
                                        "Exato: plausibilidade não equivale a verificação.",
                                    ),
                                    AlternativeSeed(
                                        "A resposta segura prova que a pesquisa foi publicada",
                                        False,
                                        "O tom da resposta não comprova a existência da fonte.",
                                    ),
                                    AlternativeSeed(
                                        "Todo erro desse tipo é causado apenas por falta de internet",
                                        False,
                                        "A alucinação pode ocorrer mesmo com ferramentas disponíveis.",
                                    ),
                                ),
                            ),
                            QuestionSeed(
                                question="Você precisa informar a taxa regulatória vigente a um cliente. Qual fluxo reduz o risco-",
                                question_type=QuestionType.MULTIPLE_CHOICE,
                                explanation="Informações atuais e de alto impacto devem ser verificadas em fonte oficial.",
                                alternatives=(
                                    AlternativeSeed(
                                        "Usar a IA para estruturar a resposta e confirmar o valor na fonte oficial",
                                        True,
                                        "Esse fluxo combina produtividade e verificação adequada ao risco.",
                                    ),
                                    AlternativeSeed(
                                        "Publicar o primeiro número gerado porque o texto parece convincente",
                                        False,
                                        "Fluência não substitui uma fonte oficial atualizada.",
                                    ),
                                    AlternativeSeed(
                                        "Pedir o mesmo número várias vezes e escolher o mais frequente",
                                        False,
                                        "Repetição não transforma uma resposta em evidência.",
                                    ),
                                ),
                            ),
                            QuestionSeed(
                                question="Em qual tarefa a principal força linguística de um LLM é mais útil-",
                                question_type=QuestionType.MULTIPLE_CHOICE,
                                explanation="Transformação e estruturação de linguagem dependem menos de fatos atuais.",
                                alternatives=(
                                    AlternativeSeed(
                                        "Reorganizar um rascunho fornecido em uma explicação clara",
                                        True,
                                        "Essa tarefa aproveita a transformação de linguagem.",
                                    ),
                                    AlternativeSeed(
                                        "Confirmar sozinho quem ocupa hoje um cargo interno",
                                        False,
                                        "Informação interna atual exige uma fonte confiável.",
                                    ),
                                    AlternativeSeed(
                                        "Garantir sem fonte o valor atual de uma obrigação legal",
                                        False,
                                        "Dados legais atuais e de alto impacto precisam de validação.",
                                    ),
                                ),
                            ),
                        ),
                    ),
                    LessonSeed(
                        title="Quando confiar e quando verificar",
                        description="Separe tarefas criativas de tarefas que exigem evidência.",
                        content="""## Introdução

Depois de entender que uma IA pode soar confiante mesmo quando está errada, a pergunta prática do dia a dia se torna: quanto esforço eu devo gastar verificando essa resposta antes de usá-la? Verificar tudo sempre é um desperdício de tempo; não verificar nada é um risco. O profissional que usa IA com critério sabe calibrar isso conforme a situação.

## Conceito

A regra prática mais útil aqui não é sobre o assunto da pergunta, mas sobre a consequência do erro: quanto maior o custo de uma resposta errada passar despercebida, mais forte deve ser a verificação humana antes de agir sobre ela. Isso significa que o mesmo tipo de pergunta pode exigir níveis de checagem completamente diferentes dependendo de para que ela vai ser usada.

Pense em duas dimensões que aumentam esse custo: reversibilidade e alcance. Uma decisão é mais arriscada quando é difícil de desfazer (um e-mail já enviado, um contrato já assinado, um valor já cobrado) e quando afeta outras pessoas além de você (um cliente, a empresa, a conformidade legal, uma operação em produção). Quando essas duas coisas se combinam - algo difícil de reverter e que impacta terceiros - a verificação precisa ser rigorosa: conferir fontes, testar antes de aplicar, pedir uma segunda opinião humana. Quando o erro é barato e reversível - um rascunho que só você vai ler, uma ideia que ainda vai passar por revisão -, gastar o mesmo rigor de verificação seria desperdiçar tempo que poderia ir para outra coisa.

Uma boa analogia é como um piloto trata os instrumentos do avião: ele confia neles o tempo todo para tarefas de rotina, mas em decisões críticas - pouso, mudança de rota, emergência - ele cruza a informação do instrumento com outras fontes antes de agir. A IA é um instrumento poderoso e geralmente confiável, mas em decisões de alto impacto ela é uma entre várias fontes que devem ser cruzadas, não a palavra final.

## Exemplo prático

Pedir à IA algumas ideias de título para um rascunho interno de brainstorm é baixo risco: se um título não for bom, alguém vai perceber e trocar, sem custo real. Já pedir à IA para calcular o valor de reembolso que deve ser enviado a um cliente, ou para resumir uma cláusula contratual que vai virar comunicação oficial, é alto risco: um erro ali pode gerar prejuízo financeiro, problema jurídico ou dano à relação com o cliente - e por isso exige que um humano confira os números, a fonte e a lógica antes de qualquer coisa seguir adiante.

## Erro comum

O erro mais comum é aplicar o mesmo nível de confiança (alto ou baixo) para tudo, em vez de ajustá-lo à situação. Confiar demais em respostas que afetam terceiros é arriscado; verificar excessivamente rascunhos e ideias internas é ineficiente. Os dois extremos desperdiçam o potencial da ferramenta - um por excesso de risco, outro por excesso de cautela.

## Resumo

Quanto mais uma resposta de IA puder afetar clientes, dinheiro, leis ou a operação, mais forte deve ser a checagem humana antes de agir sobre ela - calibrar esse nível de verificação é uma habilidade, não uma regra fixa.""",
                        concept="Quanto maior o custo de um erro, mais forte deve ser a verificação.",
                        correct="Ao decidir algo que afeta clientes, dinheiro, leis ou operação",
                        wrong_a="Ao listar ideias internas de baixo risco",
                        wrong_b="Ao transformar notas pessoais em rascunho",
                    ),
                ),
            ),
            ModuleSeed(
                title="Boas práticas de uso",
                description="Aprenda a pedir, revisar e iterar sem perder controle.",
                lessons=(
                    LessonSeed(
                        title="De pedido vago a pedido claro",
                        description="Transforme uma pergunta solta em uma instrução acionável.",
                        content="""## Introdução

Duas pessoas podem fazer "a mesma pergunta" para uma IA e receber respostas com qualidades completamente diferentes - e a diferença quase nunca está na ferramenta, está no pedido. Saber transformar uma ideia vaga em um pedido bem estruturado é provavelmente a habilidade que mais separa quem usa IA de forma amadora de quem usa com profissionalismo.

## Conceito

Um pedido vago deixa a IA adivinhando o que você realmente precisa, e ela vai preencher essas lacunas com suposições - que podem ou não bater com o que está na sua cabeça. Um pedido claro, por outro lado, comunica de forma explícita pelo menos três coisas: o objetivo (o que essa resposta precisa realizar), o contexto (para quem é, em que situação se encaixa) e o formato esperado (texto corrido, lista, e-mail, tabela, tamanho aproximado). Quanto mais dessas informações você fornece de antemão, menos rodadas de ajuste você vai precisar depois.

Vale pensar nisso como dar instruções para um assistente novo e muito capaz, mas que acabou de chegar e não conhece o seu contexto de trabalho. Se você disser apenas "escreve um e-mail para o cliente", esse assistente vai produzir algo genérico - correto na forma, mas provavelmente errado no tom, no nível de detalhe ou na urgência que a situação pedia. Se você disser "escreve um e-mail curto e direto para um cliente que está insatisfeito com um atraso, pedindo desculpas e informando a nova data, sem prometer desconto", o assistente tem o que precisa para acertar de primeira. A IA funciona da mesma forma: ela não lê sua mente, ela lê seu pedido.

Isso não significa escrever parágrafos enormes de instrução para qualquer coisa simples - significa incluir o mínimo de contexto que remove a ambiguidade real que existiria na tarefa. Um pedido claro é econômico e específico ao mesmo tempo: específico o suficiente para eliminar as principais suposições erradas, sem virar um exercício de escrita à parte.

## Exemplo prático

Pedido vago: "me ajuda a escrever sobre o novo processo". A IA não sabe qual processo, para quem é o texto, nem o que "ajudar a escrever" significa nesse caso - pode devolver um texto genérico e longo demais, ou curto demais. Pedido claro: "preciso de um comunicado de até 150 palavras para a equipe de operações, explicando que a partir de segunda-feira as solicitações de reembolso passam a ser feitas pelo novo formulário interno, em tom direto e sem jargão técnico". A segunda versão já contém objetivo, público, contexto e formato - a resposta que volta tem muito mais chance de ser usável sem retrabalho.

## Erro comum

O erro mais comum é assumir que a IA vai "entender o que eu quis dizer" a partir de uma frase curta, do jeito que um colega que já trabalha com você há anos entenderia. A IA não tem esse histórico compartilhado - cada conversa começa do zero, então a responsabilidade de fornecer o contexto necessário é sempre de quem pergunta, não de quem responde.

## Resumo

Um pedido bem-feito comunica com clareza o objetivo, o contexto e o formato esperado da resposta - quanto menos a IA precisa adivinhar, melhor e mais rápido é o resultado que você recebe.""",
                        concept="Um bom pedido informa objetivo, contexto, público, restrições e formato.",
                        correct="Dizer objetivo, contexto e formato esperado",
                        wrong_a="Escrever tudo em letras maiúsculas",
                        wrong_b="Pedir sempre a resposta mais longa possível",
                        lesson_type=LessonType.CHALLENGE,
                    ),
                    LessonSeed(
                        title="Iteração guiada",
                        description="Melhore uma resposta em ciclos curtos e objetivos.",
                        content="""## Introdução

Receber uma resposta imperfeita da IA não é o fim do processo - é o início da parte mais poderosa dele. Mas muita gente trava justamente aqui, pedindo "melhora isso" repetidamente e recebendo variações igualmente insatisfatórias. Saber iterar bem transforma uma primeira resposta mediana em um resultado realmente útil, em poucas trocas.

## Conceito

O problema de pedir apenas "melhore isso" é que "melhor" não tem uma definição objetiva - a IA precisa adivinhar em que dimensão você quer melhoria: tom, tamanho, estrutura, nível técnico, ou algo completamente diferente. Sem essa direção, ela tende a fazer ajustes genéricos e superficiais, que muitas vezes não tocam no que de fato te incomodava na resposta original.

Iterar bem significa dar um feedback específico e mensurável, do mesmo jeito que você daria para um colega revisando o próprio texto. Em vez de "melhore", diga o que especificamente não está funcionando e o que você quer no lugar: tom mais direto ou mais formal, comprimento menor ou maior, uma estrutura diferente (bullets em vez de parágrafo, por exemplo), ou a remoção e inclusão de pontos específicos de conteúdo. Cada instrução concreta reduz o espaço de adivinhação da IA e aumenta a chance de o próximo resultado já vir no que você precisa.

Uma boa forma de pensar nisso é como dirigir um carro em vez de empurrá-lo: "melhore isso" é como empurrar o carro esperando que ele ande na direção certa sozinho - pode até se mexer, mas sem controle sobre para onde vai. Dar uma instrução específica é como segurar o volante: você indica exatamente a direção, e o resultado do próximo passo reflete isso. Cada rodada de iteração é uma chance de corrigir o rumo com precisão, não de torcer para que a sorte melhore.

## Exemplo prático

Depois de receber um rascunho de comunicado que ficou longo e burocrático demais, pedir apenas "melhore" provavelmente vai gerar outra versão igualmente burocrática, só com palavras trocadas. Pedir algo como "reescreva com um tom mais direto e reduza para cinco bullets, mantendo apenas as informações que a equipe precisa para agir hoje" dá à IA um alvo claro: o que mudar (tom e formato) e o critério de sucesso (cinco bullets, foco em ação). O resultado tende a chegar muito mais perto do que era necessário logo na primeira tentativa de ajuste.

## Erro comum

O erro mais comum é repetir pedidos vagos de refinamento várias vezes seguidas - "melhore", "tenta de novo", "não ficou bom" - esperando que, por tentativa e erro, a IA acerte sozinha o que está na sua cabeça. Isso gasta tempo e rodadas sem necessariamente aproximar o resultado do que você queria, porque o problema nunca foi a capacidade da IA, foi a falta de direção específica no pedido.

## Resumo

Iterar bem é dar instruções específicas e mensuráveis sobre o que mudar - tom, tamanho, estrutura, conteúdo - em vez de pedir uma melhoria genérica; quanto mais precisa a instrução, mais rápido você chega ao resultado que precisa.""",
                        concept="Iterar bem é pedir ajustes específicos, não apenas pedir para melhorar.",
                        correct="Reescreva com tom mais direto e reduza para cinco bullets",
                        wrong_a="Melhore isso",
                        wrong_b="Faça qualquer coisa diferente",
                    ),
                ),
            ),
        ),
    ),
    TrackSeed(
        title="Claude Chat",
        description="Domine o Claude Chat para pesquisa, análise, escrita e organização.",
        difficulty="beginner",
        estimated_hours=6,
        icon="message-circle",
        order=2,
        modules=(
            ModuleSeed(
                title="Interface",
                description="Navegue pela interface com segurança.",
                lessons=(
                    LessonSeed(
                        title="Conhecendo a tela inicial",
                        description="Identifique conversa, histórico e área de mensagem.",
                        content="""## Introdução

Toda vez que você abre o Claude Chat para resolver um problema de trabalho, uma pergunta silenciosa decide o resultado: você vai começar do zero ou vai continuar de onde parou? Quem usa IA todo dia lida com dezenas de assuntos em paralelo - um e-mail difícil, uma análise de planilha, um rascunho de apresentação - e a tela inicial é o painel de controle que evita que esses assuntos se percam ou se misturem.

## Conceito

O histórico de conversas do Claude Chat não é uma lista de "coisas que você já perguntou" - é a sua memória de trabalho externa. Cada conversa guarda não só as respostas, mas o raciocínio, os ajustes de tom e as correções que você fez ao longo do caminho. Isso significa que retomar uma conversa é diferente de começar uma nova: você não precisa reexplicar o contexto, porque ele já está ali, construído.

Pense na diferença entre reabrir um documento onde você parou e ter que reescrever o documento inteiro de memória cada vez que precisa continuar. Sem organização de histórico, é isso que acontece com o uso de IA: cada nova sessão exige recriar o contexto que já existia, e informação se perde nesse processo - um detalhe do briefing, uma preferência de formato que você já tinha combinado.

Nomear as conversas de forma clara (em vez de deixar o título automático genérico) é o que torna esse histórico útil de verdade. Uma conversa chamada "Relatório mensal - Cliente X" é encontrada em segundos; uma chamada "Nova conversa" de três dias atrás é praticamente perdida, mesmo estando tecnicamente salva.

## Exemplo prático

Imagine que você passou a tarde inteira ajustando com o Claude o texto de uma proposta comercial, testando três versões de abertura até chegar na que funcionava. No dia seguinte, o cliente pede uma alteração pontual. Se você abre o histórico e retoma aquela mesma conversa, o Claude já sabe qual versão foi escolhida, por quê, e qual tom foi definido - a alteração leva um minuto. Se você abre uma conversa nova e cola só o texto final, precisa reexplicar o contexto todo, e corre o risco de receber sugestões que contradizem decisões já tomadas.

## Erro comum

Um equívoco comum é tratar cada pergunta como uma conversa nova "para não misturar assuntos", quando na verdade isso multiplica o trabalho de recontextualizar - o critério certo para separar conversas é o objetivo, não o número de perguntas.

## Resumo

Organizar e retomar conversas no Claude Chat transforma a IA de uma ferramenta de respostas isoladas em um espaço de trabalho contínuo, onde o contexto acumulado poupa tempo todos os dias.""",
                        concept="Histórico, área de mensagem e controles da conversa organizam o trabalho.",
                        correct="Retomar contextos e trabalhos anteriores com facilidade",
                        wrong_a="Aumentar automaticamente a qualidade do modelo",
                        wrong_b="Substituir revisão humana",
                    ),
                    LessonSeed(
                        title="Arquivos e contexto",
                        description="Use anexos para dar material real ao Claude.",
                        content="""## Introdução

Anexar um arquivo ao Claude Chat parece resolver metade do trabalho sozinho - afinal, a informação já está ali. Mas quem usa IA no dia a dia rapidamente descobre que um arquivo sem instrução gera respostas genéricas, superficiais ou simplesmente erradas para o que se precisava, porque o Claude não sabe, por conta própria, o que fazer com aquele material.

## Conceito

Um arquivo é dado; uma instrução é intenção. O Claude consegue ler uma planilha, um PDF ou um documento e entender seu conteúdo estrutural - números, seções, parágrafos -, mas não consegue adivinhar qual recorte importa para você, qual é o objetivo da análise, nem o formato de saída que serve para o seu contexto de trabalho. Sem essa instrução, o modelo faz a aposta mais genérica possível: um resumo geral, superficial, que cobre um pouco de tudo e não responde de fato a nenhuma pergunta específica.

É como entregar uma pilha de documentos para um novo colega de trabalho e dizer apenas "dá uma olhada nisso". Tecnicamente ele vai ler, mas sem saber se você quer um resumo executivo, uma lista de inconsistências, uma comparação com o mês anterior ou uma minuta de resposta, o resultado será um retrabalho: ou a pessoa (ou o Claude) devolve algo genérico, ou faz perguntas de volta, ou - pior - assume um objetivo errado com confiança.

A instrução que acompanha o arquivo é o que converte dado bruto em trabalho útil. Ela precisa dizer duas coisas: o que analisar dentro daquele material (qual recorte, qual comparação, qual critério) e o que produzir como saída (um resumo, uma tabela, uma lista de riscos, um texto pronto para enviar). Quanto mais específica essa instrução, mais a resposta se aproxima do que você realmente precisa na primeira tentativa.

## Exemplo prático

Compare duas abordagens com o mesmo relatório financeiro em PDF anexado. Na primeira, a mensagem é só "veja esse relatório" - o Claude devolve um resumo geral do documento, tocando en passant em receita, despesas e observações, sem destacar nada de especialmente relevante. Na segunda, a mensagem é "esse é o relatório financeiro do trimestre; liste os três itens de despesa que mais cresceram em relação ao trimestre anterior e sugira uma pergunta para levar à reunião de diretoria sobre cada um" - o resultado é direto, específico e já pronto para uso, porque a instrução definiu o recorte e o formato esperado.

## Erro comum

Um erro frequente é achar que detalhar demais o arquivo (explicando cada coluna ou seção) substitui explicar o objetivo - mas o Claude precisa muito mais saber "para quê" do que "o que é" o arquivo, já que o conteúdo ele consegue ler sozinho.

## Resumo

Um arquivo bem anexado com uma instrução clara sobre o que analisar e o que produzir rende, de primeira, o resultado que levaria várias idas e vindas sem essa instrução.""",
                        concept="Arquivos ajudam quando você explica o que eles representam e qual saída espera.",
                        correct="Uma instrução sobre o que analisar ou produzir",
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
                        title="O que são Projetos",
                        description="Entenda quando usar um projeto em vez de conversa solta.",
                        content="""## Introdução

Quem usa o Claude Chat para acompanhar um cliente, um produto ou um relatório recorrente rapidamente sente um atrito: as informações relevantes ficam espalhadas em várias conversas separadas, e cada nova pergunta exige recolher de novo o contexto. Os Projetos existem exatamente para resolver esse atrito, e saber quando usá-los é o que separa quem trabalha de forma organizada de quem reconstrói contexto o tempo todo.

## Conceito

Um Projeto é um espaço que reúne, num único lugar, várias conversas que compartilham o mesmo pano de fundo: os mesmos arquivos de referência, as mesmas instruções de contexto e o mesmo objetivo geral. Diferente de uma conversa avulsa - que carrega contexto só dentro dela mesma -, um Projeto disponibiliza esse contexto para todas as conversas que acontecem dentro dele, automaticamente.

A lógica para decidir entre conversa solta e Projeto é simples: pergunte se o que você está fazendo é um evento único ou uma linha de trabalho contínua. Uma dúvida pontual, sem relação com nada antes ou depois, cabe perfeitamente numa conversa avulsa. Mas quando várias conversas, ao longo do tempo, precisam do mesmo contexto de fundo - os mesmos documentos de referência, o mesmo histórico de decisões, o mesmo objetivo maior - cada conversa nova nesse Projeto já nasce sabendo tudo isso, sem que você precise repetir nada.

Pense num Projeto como uma pasta de trabalho física de um cliente específico, com os documentos relevantes já organizados dentro dela, versus folhas de papel avulsas guardadas em qualquer gaveta. Nas duas situações você tem as informações, mas só numa delas voltar ao assunto depois de duas semanas não exige recriar tudo de novo.

## Exemplo prático

Imagine que você acompanha o mesmo cliente todo mês: analisa os resultados, escreve um relatório de status e responde perguntas dele ao longo das semanas. Se cada uma dessas tarefas vira uma conversa nova sem contexto compartilhado, você reanexa os mesmos documentos de referência e reexplica o histórico do cliente repetidamente. Com um Projeto criado para esse cliente - contendo os documentos de referência e o contexto do relacionamento -, cada conversa nova (a análise de julho, o relatório de agosto, a dúvida pontual de setembro) já parte sabendo quem é o cliente e o que já foi combinado antes.

## Erro comum

Um equívoco comum é criar um Projeto para qualquer assunto isolado, "só para garantir organização" - isso na verdade dilui o valor do Projeto, que está em reunir contexto reutilizável, não em criar pastas para tarefas que nunca mais vão se repetir.

## Resumo

Um Projeto vale a pena quando o mesmo contexto vai ser usado em várias conversas ao longo do tempo; para um assunto único e isolado, uma conversa avulsa já basta.""",
                        concept="Projetos reúnem conversas, instruções e arquivos de um mesmo objetivo.",
                        correct="Quando várias conversas usam o mesmo contexto",
                        wrong_a="Quando você só precisa de uma pergunta rápida",
                        wrong_b="Quando quer apagar o histórico",
                    ),
                    LessonSeed(
                        title="Instruções do Projeto",
                        description="Crie instruções que guiam respostas futuras.",
                        content="""## Introdução

Criar um Projeto e deixar as instruções em branco (ou escrever ali uma pergunta específica do dia) é desperdiçar a parte que mais economiza trabalho: as instruções de Projeto são o que faz cada conversa nova, dentro daquele Projeto, já começar se comportando do jeito certo - sem que você precise reexplicar isso toda vez.

## Conceito

As instruções de um Projeto funcionam como um briefing permanente, lido antes de cada conversa nova começar. Diferente de uma instrução dada dentro de uma conversa (que vale só para aquele momento), as instruções de Projeto se aplicam a tudo que acontece ali dentro, de forma consistente. Por isso, elas devem conter o que é estável ao longo do tempo - não o que muda a cada pergunta.

Três elementos costumam fazer a diferença: o tom de voz esperado (formal, direto, didático, técnico), o público que vai receber o resultado final (um cliente, a diretoria, a própria equipe) e os critérios de resposta - formato preferido, nível de detalhe, o que sempre incluir ou sempre evitar. Esses três elementos são justamente o que muda pouco entre uma conversa e outra dentro do mesmo Projeto, e é isso que os torna bons candidatos a instrução fixa.

O erro de categoria mais comum é confundir instrução de Projeto com conteúdo de conversa. Uma pergunta pontual ("compare os números de junho e julho") pertence a uma conversa específica, porque é um evento único, não uma regra permanente. Da mesma forma, uma instrução de Projeto não é o lugar para guardar informação sensível como senhas ou credenciais - ela é um conjunto de diretrizes de comportamento, não um cofre de dados.

## Exemplo prático

Uma boa instrução de Projeto para o acompanhamento mensal de um cliente poderia ser: "Escreva sempre em tom formal, mas acessível - o público final é a diretoria do cliente, que não tem conhecimento técnico profundo. Toda resposta que envolver números deve vir acompanhada de uma frase de interpretação, não só o dado bruto. Nunca sugira cortes de orçamento sem antes listar alternativas." Note que nada ali é uma pergunta do dia - tudo é uma regra que vale para qualquer conversa dentro daquele Projeto, hoje ou daqui a três meses.

## Erro comum

Um erro frequente é escrever nas instruções algo como "hoje preciso que você analise o relatório de vendas de junho" - isso é uma tarefa pontual, não uma instrução de comportamento permanente, e deveria estar na conversa específica, não nas instruções do Projeto.

## Resumo

Boas instruções de Projeto definem tom, público e critérios de resposta que devem valer sempre - nunca uma pergunta específica do momento, nem informação sensível.""",
                        concept="Instruções de projeto definem tom, público, regras e formato recorrente.",
                        correct="Tom de voz, público e critérios de resposta",
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
        description="Use IA como parceira de documentação, planejamento e comunicação.",
        difficulty="intermediate",
        estimated_hours=7,
        icon="users",
        order=3,
        modules=(
            ModuleSeed(
                title="Documentação",
                description="Transforme informação solta em documentos úteis.",
                lessons=(
                    LessonSeed(
                        title="De notas para documento",
                        description="Converta anotações em estrutura legível.",
                        content="""## Introdução

Quem trabalha com IA todos os dias vive gerando anotações: pontos de reunião, ideias soltas, decisões faladas rápido demais. O problema não é anotar - é achar que anotação e documento são a mesma coisa. Saber transformar notas cruas em um documento que outra pessoa consegue ler, entender e agir sem precisar te perguntar nada é uma das competências mais valiosas de quem colabora com IA no trabalho.

## Conceito

Uma nota captura um momento: o que foi dito, numa ordem que só faz sentido para quem estava na sala. Um documento, por outro lado, é escrito para quem não estava na sala. Essa é a diferença central - documento é uma ferramenta de comunicação assíncrona, não um registro de memória.

Para uma nota virar documento, três elementos precisam aparecer com clareza: o objetivo (por que isso existe, o que estamos tentando resolver), as decisões tomadas (o que ficou definido, e por quê, para não reabrir a discussão do zero depois) e os próximos passos (quem faz o quê, e até quando). Sem esses três elementos, o texto pode até estar bem escrito e ainda assim ser inútil - porque ninguém consegue agir a partir dele.

Pense na diferença entre um diário de bordo e um mapa de navegação. O diário registra o que aconteceu; o mapa diz para onde ir a partir de onde você está. Notas de reunião são o diário. Um bom documento é o mapa - e é justamente isso que a IA é excelente em ajudar a construir, desde que você peça por isso explicitamente, em vez de só pedir para "organizar as notas".

## Exemplo prático

Antes: "Falamos sobre o app ficar lento. Time acha que é o banco. Ana vai ver isso. Talvez mudar o cache também." Depois de pedir para a IA transformar isso em documento: "Objetivo: reduzir o tempo de carregamento do app, hoje em ~4s. Decisão: investigar primeiro a hipótese de gargalo no banco antes de mexer em cache, para não otimizar a causa errada. Próximos passos: Ana investiga queries lentas até sexta; time revisita a decisão sobre cache somente se o banco não explicar o problema." O segundo texto permite que qualquer pessoa da equipe, inclusive alguém que faltou à reunião, entenda o que fazer.

## Erro comum

O erro mais comum é confundir "documento organizado" com "documento útil": pedir para a IA deixar as notas com títulos bonitos e tópicos numerados, sem garantir que decisões e próximos passos estejam explícitos. Formatação não é estrutura - um documento pode estar visualmente impecável e ainda assim não dizer a ninguém o que fazer a seguir.

## Resumo

Um documento só existe de verdade quando alguém que não estava na conversa consegue ler, entender o que foi decidido e saber o que fazer depois - e isso exige objetivo, decisões e próximos passos, não apenas boa formatação.""",
                        concept="Notas viram documento quando ganham objetivo, decisões e próximos passos.",
                        correct="Próximos passos",
                        wrong_a="Uma lista de adjetivos",
                        wrong_b="Um título decorativo",
                        lesson_type=LessonType.CHALLENGE,
                    ),
                    LessonSeed(
                        title="Perguntas de esclarecimento",
                        description="Use Claude para encontrar lacunas no raciocínio.",
                        content="""## Introdução

É tentador pedir para a IA "seguir em frente" assim que um plano ou documento parece pronto. Mas planos raramente estão tão completos quanto parecem - e descobrir isso durante a execução custa muito mais caro do que descobrir antes de começar. Pedir para a IA questionar o que você escreveu, antes de agir, é uma das formas mais baratas de evitar retrabalho.

## Conceito

Ambiguidade é diferente de erro. Um plano pode estar tecnicamente correto e mesmo assim conter lacunas - coisas que fazem sentido para quem escreveu, mas que podem ser interpretadas de formas diferentes por quem vai executar. O problema é que essas lacunas costumam ficar invisíveis justamente para quem escreveu o plano, porque a intenção já está clara na cabeça de quem escreveu - só não está no texto.

É aí que entra o valor de pedir perguntas de esclarecimento: em vez de pedir para a IA "executar" ou "concordar" com um plano, você pede para ela "encontrar o que está ambíguo ou faltando antes de começar". Isso muda o papel da IA de executora passiva para revisora ativa, e é exatamente esse segundo papel que reduz risco de retrabalho.

Uma boa analogia é a checklist de decolagem de um piloto: não é feita porque o avião provavelmente tem defeito, é feita porque revisar sistematicamente antes de sair do chão é muito mais barato do que corrigir no ar. Perguntas de esclarecimento cumprem esse papel para planos e documentos - uma revisão estrutural, feita no momento mais barato possível: antes de qualquer trabalho ter começado.

## Exemplo prático

Um time pede para a IA implementar "notificações para usuários inativos". Antes de começar, pede também: "que perguntas você faria antes de implementar isso?" A IA responde: "o que conta como inativo - quantos dias sem login? A notificação é por e-mail, push ou os dois? Usuários que já cancelaram a conta devem ser incluídos?" Essas três perguntas, respondidas em cinco minutos de conversa, evitaram que o time construísse a funcionalidade errada e precisasse refazer parte dela depois de testada com usuários reais.

## Erro comum

O equívoco mais comum é achar que pedir esclarecimentos é sinal de que o plano está mal feito, ou que isso atrasa o trabalho. Na prática é o oposto: um plano só parece completo até alguém perguntar sobre ele. Pular essa etapa não elimina a ambiguidade, apenas adia a hora - mais cara - em que ela vai aparecer.

## Resumo

Pedir para a IA questionar um plano antes de executar não atrasa o trabalho - descobre lacunas e reduz ambiguidade no momento mais barato possível, antes que qualquer esforço real tenha sido gasto.""",
                        concept="Perguntas revelam ambiguidades antes que a equipe execute.",
                        correct="Descobrir lacunas e reduzir ambiguidade",
                        wrong_a="Evitar falar com pessoas envolvidas",
                        wrong_b="Deixar o documento maior",
                    ),
                ),
            ),
            ModuleSeed(
                title="Planejamento",
                description="Crie planos, roadmaps e critérios de aceite.",
                lessons=(
                    LessonSeed(
                        title="Plano em fases",
                        description="Divida objetivos grandes em entregas validáveis.",
                        content="""## Introdução

Diante de um objetivo grande, o impulso natural é planejar tudo de uma vez, do início ao fim, antes de mexer em qualquer coisa. Mas quanto maior o plano de uma vez só, maior a chance de ele estar errado em algum ponto - e maior o custo de descobrir isso tarde. Saber quebrar um objetivo grande em fases pequenas é o que separa planejamento que funciona de planejamento que só parece completo no papel.

## Conceito

Uma fase não é apenas "um pedaço menor de trabalho" - é um pedaço menor que, sozinho, já entrega algo testável e útil. Essa é a diferença entre dividir um plano em fases e simplesmente dividir uma lista de tarefas em partes: a fase tem valor próprio, mesmo que as fases seguintes nunca aconteçam.

Isso importa porque planos grandes carregam riscos escondidos que só aparecem quando algo é de fato testado com uso real. Se você planeja tudo de uma vez e só valida no final, qualquer suposição errada - sobre o usuário, sobre a tecnologia, sobre a prioridade certa - só é descoberta depois que todo o esforço já foi gasto. Fases pequenas trazem essa validação para mais cedo, quando ainda é barato mudar de direção.

Pense em construir uma casa comparado a montar um acampamento em etapas. Você não espera a casa inteira pronta para saber se o terreno é bom; monta uma barraca primeiro, testa se o local funciona, e só então investe em algo maior. Um plano em fases funciona do mesmo jeito: cada fase é uma barraca que confirma (ou corrige) a direção antes do próximo investimento maior.

## Exemplo prático

Um objetivo grande como "lançar um sistema de recomendação de produtos" pode ser levado à IA assim: "quero fazer isso, me ajude a quebrar em fases, sendo que cada fase precisa entregar algo que já possamos testar com usuários reais, mesmo que pequeno." Uma boa resposta divide isso em algo como: fase 1, recomendar os produtos mais vendidos da categoria (sem nenhuma personalização, mas já útil); fase 2, personalizar por histórico de compra; fase 3, incorporar comportamento de navegação. Cada fase, isolada, já ajuda o usuário - e cada uma valida uma suposição antes de investir na próxima.

## Erro comum

O erro mais comum é confundir "fase pequena" com "fase incompleta" - dividir o trabalho por etapas técnicas (por exemplo, "fase 1: banco de dados, fase 2: backend, fase 3: frontend") em vez de por valor entregue. Isso não reduz risco nenhum, porque nenhuma fase isolada é testável ou útil por si só; o risco só é descoberto no final, exatamente como num plano único.

## Resumo

Dividir um plano em fases não existe para organizar tarefas - existe para entregar algo pequeno, testável e útil o quanto antes, validando a direção certa antes de investir mais.""",
                        concept="Uma boa fase entrega valor cedo, reduz risco e permite validação.",
                        correct="Entregar algo pequeno, testável e útil",
                        wrong_a="Resolver todos os problemas futuros",
                        wrong_b="Evitar qualquer critério de aceite",
                    ),
                    LessonSeed(
                        title="Critérios de aceite",
                        description="Escreva critérios objetivos para validar entregas.",
                        content="""## Introdução

Depois de planejar um trabalho, ainda falta responder a uma pergunta simples e frequentemente ignorada: como saber, com certeza, que ele está pronto? Sem uma resposta clara para isso, "pronto" vira uma questão de opinião - e opiniões divergem, geram retrabalho e discussões que poderiam ter sido evitadas. Critérios de aceite existem para resolver exatamente esse problema.

## Conceito

Um critério de aceite é uma afirmação sobre o resultado que pode ser verificada como verdadeira ou falsa, por qualquer pessoa, sem depender de interpretação. Essa é a característica que define um bom critério: ele precisa ser observável - algo que se possa checar de fato - e não apenas descritivo de uma intenção ou sensação.

A armadilha é que critérios vagos parecem perfeitamente razoáveis quando escritos: "o sistema deve ser rápido", "a experiência deve ser boa", "o relatório deve fazer sentido". O problema aparece depois, na hora de decidir se o trabalho está de fato pronto - porque duas pessoas podem discordar honestamente se "rápido" ou "bom" foram alcançados. Um critério observável elimina essa discordância antes que ela aconteça, porque a resposta é factual, não uma questão de gosto.

Uma boa forma de pensar nisso é a diferença entre um juiz e um crítico de arte. O crítico avalia se algo é bom com base em impressão e gosto pessoal - legítimo, mas subjetivo. O juiz aplica uma regra e chega a um veredito que qualquer pessoa, examinando as mesmas evidências, chegaria também. Critérios de aceite colocam quem revisa o trabalho no papel de juiz, não de crítico.

## Exemplo prático

Critério vago: "a experiência de login deve ficar incrível." Critério observável: "um usuário com credenciais válidas consegue autenticar e chegar ao dashboard em até 3 segundos, e um usuário com senha errada recebe uma mensagem de erro específica em até 2 tentativas." O segundo pode ser testado por qualquer pessoa da equipe - ou até automaticamente - e a resposta será a mesma independentemente de quem verificar. O primeiro depende inteiramente de quem está julgando naquele dia.

## Erro comum

O erro comum é escrever critérios que soam concretos, mas ainda escondem subjetividade - como "a página deve carregar rápido" sem definir um número, ou "os dados devem estar corretos" sem dizer contra o que comparar. Um critério só é de fato observável quando duas pessoas diferentes, olhando para o mesmo resultado, chegam à mesma conclusão sobre se ele foi cumprido.

## Resumo

Um bom critério de aceite é observável e testável - como "usuário autenticado consegue abrir o dashboard" - e não uma descrição de sensação ou intenção, como "a experiência deve ficar incrível".""",
                        concept="Critérios de aceite devem ser observáveis e testáveis.",
                        correct="Usuário autenticado consegue abrir o dashboard",
                        wrong_a="A experiência deve ficar incrível",
                        wrong_b="O código deve parecer melhor",
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
                title="Leitura de código",
                description="Use IA para entender sistemas existentes antes de alterar.",
                lessons=(
                    LessonSeed(
                        title="Mapa inicial do repositório",
                        description="Peça uma leitura estrutural antes de pedir mudanças.",
                        content="""## Introdução

Quando você chega em um repositório que não conhece, a tentação é pedir logo a mudança que precisa fazer. Mas a IA, assim como uma pessoa nova no time, não tem contexto - ela não sabe onde ficam as regras de negócio, como os testes são organizados nem quais convenções o time já decidiu seguir. Pular essa etapa é a causa mais comum de código que "funciona" mas quebra um padrão do projeto ou duplica algo que já existia.

## Conceito

Mapear um repositório significa pedir para a IA explorar e resumir, antes de qualquer edição, quatro coisas: a estrutura de pastas (como o código está organizado), os comandos que fazem o projeto rodar (build, testes, lint), os testes existentes (o que já está protegido) e as convenções do time (padrões de nomenclatura, arquitetura, arquivos de instrução como um CLAUDE.md). Esse mapeamento não é burocracia - é o mesmo raciocínio de um desenvolvedor sênior que, ao entrar num projeto novo, primeiro lê o README e navega pela árvore de arquivos antes de tocar em qualquer linha.

Pense na diferença entre um médico que examina o paciente antes de prescrever e um que já chega receitando com base só na queixa. A IA sem contexto tende a "prescrever" a solução mais genérica possível - muitas vezes reescrevendo algo do zero quando bastava seguir um padrão já existente no projeto. Um prompt de exploração bem feito muda esse comportamento por completo, porque força a IA a ancorar suas próximas decisões em fatos do repositório, não em suposições.

Na prática, isso custa poucos minutos e economiza horas de retrabalho. Um exemplo de prompt de exploração inicial: "Antes de mexer em qualquer código, explore este repositório e me dê um resumo: como o backend e o frontend estão organizados, quais comandos rodam os testes e o lint, se existe algum arquivo de convenções como um CLAUDE.md ou README, e onde ficam os testes que cobrem a área que eu preciso mudar. Não sugira mudanças ainda, só me traga esse mapa."

## Exemplo prático

Imagine que você precisa adicionar um campo novo em um endpoint de usuários. Sem mapear o repositório, a IA pode criar o endpoint numa estrutura de pastas que não segue o padrão do projeto (por exemplo, agrupando por camada técnica quando o time organiza por domínio) e esquecer de registrar o modelo no lugar certo. Com o mapeamento prévio, a IA já sabe que o projeto segue "domínio, não camada técnica", encontra o service e o repository existentes daquele domínio, e só então propõe a alteração - no lugar certo, seguindo o padrão já estabelecido.

## Erro comum

O erro mais comum é confundir "explorar o repositório" com "redesenhar o repositório": ao invés de mapear o que já existe, a IA (ou o desenvolvedor apressado) aproveita a oportunidade para propor uma arquitetura nova mais "elegante". Isso ignora testes, convenções e decisões que o time já tomou por bons motivos, e gera um diff enorme e arriscado onde bastava uma mudança pequena e localizada.

## Resumo

Mapear a estrutura, os comandos e os testes antes de pedir qualquer mudança transforma a IA de uma ferramenta genérica em uma colaboradora que respeita as decisões já tomadas no seu projeto.""",
                        concept="Contexto vem antes da edição: estrutura, comandos, testes e convenções.",
                        correct="Mapear estrutura, comandos e testes existentes",
                        wrong_a="Reescrever tudo em uma arquitetura nova",
                        wrong_b="Ignorar os testes para ir mais rápido",
                    ),
                    LessonSeed(
                        title="Fluxo de dados",
                        description="Investigue de onde vem e para onde vai um dado.",
                        content="""## Introdução

Bugs raramente vivem onde o sintoma aparece. Um valor errado na tela pode ter nascido três camadas antes, numa validação silenciosa ou numa transformação de dados esquecida. Para depurar com eficiência usando IA, a habilidade mais valiosa não é "saber a resposta certa na hora" - é saber fazer a pergunta que faz a IA rastrear o caminho certo.

## Conceito

Todo dado que aparece numa interface passou por uma sequência de etapas: entrada (onde o usuário ou outro sistema o forneceu), validação (onde ele foi checado e possivelmente rejeitado ou transformado), regra de negócio (onde foi processado, calculado ou combinado com outros dados), persistência (onde foi salvo ou lido do banco) e resposta (como chegou até a tela). Rastrear o fluxo de dados significa percorrer essa cadeia inteira, arquivo por arquivo, até identificar exatamente em qual elo a informação diverge do esperado.

Essa técnica é como seguir o cano de um vazamento: em vez de sair trocando peças da casa inteira na esperança de acertar, você segue o fluxo da água - da torneira até o ralo - até encontrar o ponto exato do furo. Aplicado ao código, isso normalmente segue o próprio fluxo da requisição: Router recebe, Service aplica a regra, Repository lê ou grava no banco, resposta volta formatada. Um bug de "número errado na tela" pode estar em qualquer um desses pontos, e adivinhar sem rastrear custa muito mais tempo do que simplesmente seguir o caminho.

A pergunta certa para começar uma investigação nunca é sobre tecnologia em abstrato ("qual framework é mais usado para isso?") - é sempre sobre o caminho concreto daquele dado específico no seu sistema: por quais arquivos ele passa, do input até a saída.

## Exemplo prático

Suponha que o total de um pedido aparece errado na tela do cliente. Em vez de pedir "conserta esse bug", um prompt eficaz para o Claude Code seria: "o campo 'total do pedido' está aparecendo errado na tela. Rastreie o fluxo desse dado: onde ele entra, por qual service e regra de cálculo ele passa, como é persistido no banco e como é formatado na resposta da API. Me mostre esse caminho arquivo por arquivo antes de propor uma correção." Isso costuma revelar, por exemplo, que o valor está correto no banco, mas uma conversão de tipo na camada de resposta está truncando os centavos - um problema que seria quase impossível de adivinhar sem seguir o rastro.

## Erro comum

O erro mais comum é pular direto para a correção mais "óbvia" - geralmente mexendo na camada onde o sintoma aparece (a tela) - sem verificar se o problema realmente nasceu ali. Isso produz remendos que escondem o sintoma sem resolver a causa, e o mesmo bug volta disfarçado em outro lugar mais tarde.

## Resumo

Antes de corrigir um bug, pergunte por quais arquivos aquele dado passa até chegar na tela: rastrear o fluxo é sempre mais rápido e mais confiável do que adivinhar.""",
                        concept="Entender entrada, validação, regra, persistência e resposta localiza bugs.",
                        correct="Por quais arquivos esse dado passa até chegar na tela?",
                        wrong_a="Você pode adivinhar sem olhar o código?",
                        wrong_b="Qual framework é mais famoso?",
                        lesson_type=LessonType.CHALLENGE,
                    ),
                ),
            ),
            ModuleSeed(
                title="Testes e entrega",
                description="Valide mudanças antes de considerar uma tarefa pronta.",
                lessons=(
                    LessonSeed(
                        title="Teste focado no risco",
                        description="Escolha testes proporcionais ao impacto da mudança.",
                        content="""## Introdução

Testar tudo com o mesmo nível de detalhe parece disciplina, mas na prática é desperdício: tempo gasto testando exaustivamente uma função trivial é tempo que não sobrou para proteger a parte do sistema que realmente pode causar dano se quebrar. Saber decidir o que merece um teste rigoroso é tão importante quanto saber escrever o teste em si.

## Conceito

A decisão de o que testar deveria ser guiada por uma pergunta simples: se isso quebrar, qual é o impacto para quem usa o sistema? Uma mudança num cálculo de cobrança, numa regra de autenticação ou numa migração de dados tem alto risco - um erro silencioso ali pode custar dinheiro, expor dados ou derrubar a confiança no produto. Já uma mudança de texto num rótulo de botão tem risco baixíssimo: um teste ali raramente compensa o tempo investido.

Pense em risco como um seguro: você não contrata a cobertura mais cara para todos os seus bens, contrata proporcionalmente ao que perderia se algo desse errado. Uma função que calcula juros merece testes que cobrem casos de borda (valor zero, valor negativo, arredondamento); uma função que apenas formata uma data para exibição talvez precise só de um teste simples, ou nenhum, se o comportamento já é coberto por outro teste de integração.

Na prática, isso significa fazer duas perguntas antes de escrever qualquer teste: que comportamento essa mudança pode quebrar sem que ninguém perceba na hora, e o que acontece com o usuário se isso quebrar em produção. A resposta a essas perguntas dita o nível de esforço - não uma regra fixa como "toda função precisa de teste" nem "só testo se for fácil".

## Exemplo prático

Imagine duas mudanças no mesmo dia: uma altera a lógica que decide se um aluno passou de nível num curso (afeta progresso e possivelmente cobrança de certificado), outra ajusta o espaçamento de um card na tela de perfil. A primeira merece testes cobrindo os limites exatos da aprovação, casos de empate e entradas inválidas - porque um erro silencioso ali afeta a experiência e a credibilidade do produto. A segunda não precisa de teste automatizado algum; uma checagem visual rápida já é suficiente, e insistir em testá-la formalmente só adiciona manutenção sem retorno.

## Erro comum

O equívoco mais comum tem duas faces opostas: de um lado, pular testes porque a mudança "parece simples" - muitas vezes é justamente aí que um efeito colateral inesperado passa despercebido; do outro, testar exaustivamente cada função isolada, incluindo casos que nunca ocorreriam na prática, o que infla a suíte de testes sem aumentar a proteção real do sistema.

## Resumo

Escolha o que testar pelo comportamento que pode quebrar e pelo impacto que isso teria no usuário - não pelo tamanho da mudança nem pela facilidade de escrever o teste.""",
                        concept="O teste certo protege o comportamento que pode quebrar.",
                        correct="Pelo comportamento que pode quebrar e pelo impacto no usuário",
                        wrong_a="Sempre escrever o maior teste possível",
                        wrong_b="Nunca testar se a mudança parece simples",
                    ),
                    LessonSeed(
                        title="Resumo de entrega",
                        description="Comunique o que mudou, como validou e o que ficou fora.",
                        content="""## Introdução

Depois que o código funciona, ainda falta uma etapa que muita gente trata como formalidade: comunicar o que foi feito. Um resumo de entrega mal escrito obriga quem revisa a reler todo o diff do zero para entender o que mudou e o que não foi coberto - e isso custa tempo do time inteiro, não só de quem escreveu o código.

## Conceito

Um bom resumo de entrega tem três elementos essenciais: as mudanças feitas (o que foi alterado e por quê, em linguagem que alguém sem o contexto completo consiga entender), as validações realizadas (que testes rodaram, que cenários foram checados manualmente) e os limites conhecidos (o que não foi coberto, o que ficou de fora do escopo, riscos que ainda existem). Esses três pontos juntos dão a quem revisa exatamente o que precisa para decidir se aprova, pede ajuste ou testa algo específico.

Um resumo de entrega funciona como o relatório de um exame médico: não basta dizer "está tudo bem" - o laudo precisa dizer o que foi examinado, o que os resultados mostraram e o que não foi avaliado nesse exame específico. Um relatório que só diz "normal" sem detalhar o que foi olhado obriga o próximo profissional a repetir o exame do zero para confiar no resultado.

Escrever esse resumo bem não significa despejar todos os detalhes internos da implementação - significa priorizar: o que importa para a decisão de quem revisa vem primeiro, e detalhes técnicos profundos ficam disponíveis mas não obrigatórios de ler.

## Exemplo prático

Compare dois resumos para a mesma entrega. Mal escrito: "Terminei a task, tudo funcionando." Bem escrito: "Adicionei validação de e-mail duplicado no cadastro. Testes unitários cobrindo e-mail já existente, e-mail inválido e caso de sucesso - todos passando, cobertura do service em 100%. Não testei o fluxo de recuperação de senha porque não foi alterado nesta entrega; ele continua usando a validação antiga." O segundo permite que quem revisa saiba exatamente o que checar e o que confiar sem reexaminar.

## Erro comum

O erro mais frequente é escrever um resumo genérico do tipo "está pronto" ou "fiz o que foi pedido", sem detalhar mudanças, validações ou limites - isso transfere para quem revisa todo o trabalho de descobrir sozinho o que realmente foi feito e o que ainda precisa de atenção.

## Resumo

Um resumo de entrega útil registra o que mudou, como foi validado e quais são os limites conhecidos - isso é o que permite que outra pessoa confie e revise o trabalho com rapidez.""",
                        concept="Um bom resumo registra mudanças, validações e limites conhecidos.",
                        correct="Mudanças feitas, validações e limites conhecidos",
                        wrong_a="Apenas uma frase dizendo que está pronto",
                        wrong_b="Todos os detalhes internos sem priorizar nada",
                    ),
                ),
            ),
        ),
    ),
    TrackSeed(
        title="AI Engineering",
        description="Projete sistemas com agentes, ferramentas, avaliação e observabilidade.",
        difficulty="advanced",
        estimated_hours=9,
        icon="workflow",
        order=5,
        modules=(
            ModuleSeed(
                title="Agents e ferramentas",
                description="Entenda agentes como loops de decisão com ferramentas.",
                lessons=(
                    LessonSeed(
                        title="O que torna um fluxo agente",
                        description="Diferencie chamada única de loop com decisão.",
                        content="""## Introdução

Quando você projeta um sistema de IA, a primeira decisão de arquitetura é também a mais fácil de errar: isso precisa ser um agente ou basta uma chamada ao modelo? Confundir os dois leva a sistemas engessados (que quebram no primeiro passo inesperado) ou a agentes desnecessariamente complexos para tarefas simples. Entender o que de fato caracteriza um fluxo agente evita as duas armadilhas.

## Conceito

Uma chamada única a um modelo - por mais longo e detalhado que seja o prompt - é uma via de mão única: você manda uma entrada, recebe uma saída, e o modelo nunca sabe se aquela saída funcionou. Não importa quantas instruções você empilhe no prompt: se não existe um retorno de informação sobre o resultado da ação, não há agente, há só um gerador de texto sofisticado.

Um agente, por definição, é um loop: ele observa o estado atual do mundo (ou da tarefa), decide uma próxima ação com base nesse estado, executa a ação - geralmente usando uma ferramenta - e volta a observar o resultado antes de decidir o próximo passo. É esse ciclo de observação-decisão-ação, repetido até que um critério de parada seja satisfeito, que transforma um modelo de linguagem em algo capaz de resolver tarefas que não cabem em uma única resposta.

Pense na diferença entre pedir a um estagiário "escreva um relatório sobre X" e dizer "aqui está uma pasta de arquivos, um acesso à internet e uma meta: descubra o que está causando a queda de vendas". No primeiro caso, uma resposta encerra a tarefa. No segundo, a pessoa precisa investigar, checar o que encontrou, ajustar a hipótese e repetir - exatamente o comportamento que distingue um agente de uma resposta fixa.

## Exemplo prático

Imagine um agente encarregado de corrigir um bug relatado por um usuário. Ele primeiro lê o log de erro (observação), decide abrir o arquivo indicado no stack trace (ação), lê o conteúdo (nova observação), decide que a causa é uma variável não inicializada, aplica a correção (ação), roda os testes automatizados (ação) e observa se passaram. Se falharem, ele volta a investigar. Cada ciclo usa o resultado do anterior para decidir o próximo passo - não existe um roteiro fixo escrito de antemão.

## Erro comum

O equívoco mais comum é achar que "agente" é sinônimo de "prompt bem elaborado" ou de salvar uma resposta pronta para reaproveitar depois. Um prompt longo, por mais sofisticado, ainda produz uma única saída sem verificar se ela funcionou - e uma resposta salva em arquivo é estática por definição. Nenhum dos dois observa resultados nem decide próximos passos, então nenhum dos dois é, de fato, um agente.

## Resumo

O que torna um fluxo "agente" não é o tamanho do prompt nem a sofisticação da resposta, e sim a existência de um loop real de observação, decisão e ação que se repete até a tarefa estar resolvida.""",
                        concept="Um agente combina objetivo, estado, ferramentas e critério de parada.",
                        correct="Um loop que observa resultados e decide próximas ações",
                        wrong_a="Um prompt muito longo sem ferramentas",
                        wrong_b="Uma resposta fixa salva em arquivo",
                    ),
                    LessonSeed(
                        title="Ferramentas com contratos claros",
                        description="Defina entradas, saídas e erros das ferramentas.",
                        content="""## Introdução

Um agente só é tão confiável quanto as ferramentas que ele usa. Se você já viu um agente "alucinar" um resultado ou travar em um loop de tentativas sem sentido, é bem provável que o problema não estivesse no modelo, mas no desenho da ferramenta que ele estava tentando usar. Projetar ferramentas com contratos claros é o que separa um agente previsível de um imprevisível.

## Conceito

Um "contrato" de ferramenta é a promessa que ela faz ao agente: dado este conjunto de parâmetros, de tipos e formatos definidos, você receberá de volta este tipo específico de resultado, ou um erro explícito e legível quando algo dá errado. É exatamente como um contrato entre empresas: ele não descreve vagamente "vamos prestar um serviço", ele especifica entregáveis, prazos e o que acontece em caso de descumprimento. Ferramentas sem esse nível de precisão obrigam o agente a "adivinhar" o que aconteceu, e modelos de linguagem são péssimos em admitir incerteza sobre isso - eles tendem a seguir em frente como se tudo tivesse dado certo.

Dois elementos são essenciais nesse contrato. Primeiro, o nome e os parâmetros da ferramenta precisam comunicar exatamente o que ela faz e o que espera receber - um nome como "buscar pedido por identificador" deixa claro o propósito e a entrada esperada, enquanto um nome genérico como "processar" não diz nada sobre o que "processar" significa nem que formato de dado deve receber. Segundo, a resposta precisa ser previsível e estruturada: sucesso e falha devem ter formatos distintos e reconhecíveis, para que o agente consiga decidir corretamente o próximo passo - tentar de novo, escolher outra ferramenta ou informar o usuário.

## Exemplo prático

Compare duas versões da mesma funcionalidade. Uma ferramenta mal definida, algo como "fazer coisa com um dado de entrada", recebe uma string livre, tenta interpretar a intenção internamente e, se não conseguir, retorna simplesmente uma resposta vazia, sem sinalizar erro. O agente não tem como saber se a tarefa foi concluída com sucesso e resultou em "nada a mostrar" ou se falhou silenciosamente. Já uma ferramenta bem definida, como "consultar estoque por código do produto", que devolve claramente se o produto está disponível e em que quantidade, ou um erro específico de "produto não encontrado", deixa explícito o que entra, o que sai em caso de sucesso e qual é o formato do erro. O agente consegue reagir de forma diferente para cada caso, em vez de tratar tudo como a mesma ambiguidade.

## Erro comum

Um erro frequente é achar que dar um nome genérico e flexível à ferramenta (do tipo "faz tudo") economiza trabalho de design. Na prática, isso só transfere a ambiguidade para dentro da ferramenta, onde o agente não tem visibilidade nenhuma, e falhas silenciosas ali são muito mais difíceis de depurar do que um parâmetro obrigatório faltando.

## Resumo

Uma ferramenta confiável para um agente não é a mais flexível, é a que tem parâmetros e respostas bem definidos - isso é o que permite ao agente decidir com segurança o que fazer a seguir.""",
                        concept="Ferramentas boas possuem nome claro, parâmetros e resultado previsível.",
                        correct="Parâmetros e respostas bem definidos",
                        wrong_a="Nome genérico como fazer_coisa",
                        wrong_b="Erros silenciosos",
                        lesson_type=LessonType.CHALLENGE,
                    ),
                ),
            ),
            ModuleSeed(
                title="Evaluation",
                description="Meça qualidade de respostas e fluxos de IA.",
                lessons=(
                    LessonSeed(
                        title="Rubricas simples",
                        description="Defina critérios antes de avaliar uma resposta.",
                        content="""## Introdução

Depois que um sistema de IA está no ar, a pergunta inevitável é: como saber se as respostas dele são boas? "Parece bom" não escala, não é reproduzível entre pessoas diferentes e não aponta o que exatamente melhorar. Rubricas resolvem esse problema transformando uma sensação subjetiva em um processo de avaliação que qualquer pessoa da equipe pode aplicar do mesmo jeito.

## Conceito

Uma rubrica de avaliação é uma lista de critérios explícitos e verificáveis contra os quais uma resposta de IA é julgada, geralmente com uma pontuação simples para cada item. Em vez de perguntar "essa resposta foi boa?", você pergunta "essa resposta cobriu os pontos certos? Ela seguiu o formato esperado? Ela evitou o erro que já vimos antes?" - perguntas específicas o suficiente para que duas pessoas diferentes cheguem à mesma conclusão avaliando a mesma resposta.

Isso é parecido com a diferença entre pedir a um professor para "dar uma nota geral" a uma redação e dar a ele uma grade de correção com pontos específicos: argumentação, coesão, uso de exemplos. A nota isolada some sem deixar rastro do motivo; a rubrica revela exatamente onde o texto falhou e onde foi bem. O mesmo vale para avaliar a saída de um modelo: uma "impressão geral de qualidade" não indica se o problema está no tom, na precisão factual ou na estrutura da resposta - critérios explícitos indicam.

Rubricas também têm um efeito colateral importante: elas tornam a avaliação auditável e comparável ao longo do tempo. Se você mudar o prompt ou trocar de modelo, pode rodar o mesmo conjunto de critérios e comparar resultados de forma justa, em vez de confiar na memória de "parece que melhorou".

## Exemplo prático

Para um assistente que responde dúvidas de suporte técnico, uma rubrica simples de três critérios poderia ser: a resposta identificou corretamente a causa do problema relatado; a resposta incluiu um passo a passo acionável, e não só uma explicação genérica; a resposta evitou prometer algo que o produto não faz. Cada critério é binário e checável por qualquer revisor, sem depender de gosto pessoal.

## Erro comum

Um equívoco comum é achar que rubricas "engessam" a avaliação ou substituem o julgamento humano - na verdade elas fazem o oposto: dão à pessoa revisora uma base objetiva para discordar ou concordar com fundamento, em vez de eliminar a revisão. Rubricas não tornam a avaliação mais misteriosa nem tiram o humano do processo; elas dão a esse humano critérios claros para trabalhar.

## Resumo

O valor de uma rubrica está em avaliar respostas por critérios explícitos e reproduzíveis, não em substituir julgamento humano nem em complicar o processo de revisão.""",
                        concept="Rubricas transformam qualidade em critérios explícitos.",
                        correct="Avaliar respostas por critérios explícitos",
                        wrong_a="Deixar prompts mais misteriosos",
                        wrong_b="Impedir qualquer revisão humana",
                    ),
                    LessonSeed(
                        title="Casos de teste de IA",
                        description="Monte exemplos representativos para comparar modelos.",
                        content="""## Introdução

Testar um sistema de IA só com o exemplo mais fácil que você consegue imaginar é como testar um carro apenas em estrada reta e sem trânsito: você aprova algo que nunca foi de fato desafiado. Montar um conjunto de casos de teste representativo é o que permite detectar problemas antes que o usuário final os encontre.

## Conceito

Um conjunto de avaliação bem construído não busca cobrir "tudo", busca cobrir os tipos de situação que realmente revelam se o sistema funciona. Isso normalmente significa combinar pelo menos três categorias: um caso comum (o cenário que a maioria dos usuários vai de fato encontrar no dia a dia), um caso limite (uma situação nas bordas do que o sistema deveria conseguir lidar, uma entrada incomum, ambígua ou no limite do escopo) e um caso problemático (um cenário que já causou falha antes, ou que você sabe ser particularmente difícil para o modelo).

A lógica é parecida com a de um piloto de provas testando um carro: ele não dirige só na estrada tranquila em que o carro claramente funciona bem - ele testa a curva fechada (caso limite) e recria exatamente a situação em que um carro anterior falhou (caso problemático). Testar só o caminho fácil dá uma falsa sensação de segurança; testar só os casos difíceis, por outro lado, também distorce a avaliação, porque não reflete o uso real.

Cada categoria cumpre um papel diferente: o caso comum garante que você não quebrou o básico ao fazer uma mudança; o caso limite revela se o sistema generaliza além do óbvio; o caso problemático garante que erros já identificados no passado não voltem a acontecer, funcionando como um teste de regressão para os pontos mais frágeis conhecidos do sistema.

## Exemplo prático

Para um agente que classifica e-mails de suporte por categoria, um conjunto de três casos poderia ser: caso comum, um e-mail claro pedindo reembolso, com todas as informações necessárias; caso limite, um e-mail que menciona reembolso e também um problema técnico não resolvido, exigindo decidir qual categoria prevalece; caso problemático, um e-mail sarcástico que no passado já foi classificado erroneamente como "elogio" por causa do tom aparentemente positivo. Rodar os três a cada mudança no sistema revela problemas que um único exemplo fácil jamais mostraria.

## Erro comum

O erro mais comum é montar o conjunto de teste só com os exemplos que o sistema já resolve bem, porque isso "passa" nos testes e dá uma falsa confiança. O oposto, não ter nenhum caso fixo e testar sempre com exemplos improvisados na hora, é igualmente problemático, porque impede comparar resultados de forma consistente ao longo do tempo.

## Resumo

Um bom conjunto de avaliação combina deliberadamente um caso comum, um caso limite e um caso problemático - é essa combinação, e não a quantidade de exemplos, que revela se um sistema de IA realmente funciona.""",
                        concept="Um bom conjunto inclui casos comuns, limites e problemas históricos.",
                        correct="Um caso comum, um caso limite e um caso problemático",
                        wrong_a="Somente o exemplo mais fácil",
                        wrong_b="Nenhum caso fixo, apenas impressão subjetiva",
                        lesson_type=LessonType.CHALLENGE,
                    ),
                ),
            ),
        ),
    ),
)


def _practice_content(
    title: str,
    description: str,
    concept: str,
    action: str,
    wrong_a: str,
    wrong_b: str,
) -> str:
    return f"""## O que e

{title} e uma pratica aplicada para transformar conhecimento de IA em decisao, execucao e revisao. Nesta atividade, voce nao esta apenas decorando um termo: voce esta aprendendo a reconhecer quando a pratica faz sentido, como aplicar em um fluxo real e quais erros evitar.

## Objetivo

{description} Ao final desta atividade, voce deve conseguir explicar o conceito em linguagem simples, escolher quando usar, aplicar um procedimento basico e reconhecer as limitacoes.

## Conceito central

{concept}

## Quando usar

Use esta pratica quando a decisao depender de clareza, rastreabilidade ou reducao de risco. Ela e especialmente util quando existe ambiguidade no pedido, impacto em outras pessoas, necessidade de validar uma resposta de IA, ou quando um agente precisa agir sobre codigo, dados, documentos ou politicas.

Nao use como ritual automatico para qualquer tarefa trivial. Se a mudanca for pequena, reversivel e sem impacto, um checklist leve pode bastar.

## Como usar

{action}

Uma forma pratica de executar:

1. Defina o resultado esperado em uma frase.
2. Liste o contexto minimo que a IA ou a pessoa precisa saber.
3. Escolha um criterio verificavel de sucesso.
4. Execute em um passo pequeno.
5. Revise o resultado antes de avançar para o proximo passo.

## Exemplo pratico

Antes de pedir para a IA executar, descreva o resultado esperado, o contexto minimo e o criterio que define sucesso. Em seguida, valide a resposta contra esse criterio, ajustando o pedido em ciclos curtos.

Exemplo de comando mental: "Eu sei o que quero, sei por que isso importa, sei como validar e sei qual erro eu quero evitar." Se uma dessas respostas estiver vazia, ainda falta contexto.

## Limitacoes

Esta pratica nao substitui julgamento humano, teste real ou revisao de seguranca. Ela tambem nao funciona bem quando o objetivo esta vago, quando os dados de entrada sao ruins, ou quando a pessoa tenta usar IA para pular uma decisao que deveria ser assumida pelo time.

Duas armadilhas comuns nesta atividade:

- {wrong_a}
- {wrong_b}

## Boas praticas

- Prefira exemplos concretos a definicoes abstratas.
- Valide uma resposta antes de construir outra etapa em cima dela.
- Separe fatos observados de suposicoes.
- Registre decisoes quando elas afetarem proximas pessoas ou proximas tarefas.
- Use feedback curto e especifico para iterar.

## Atividade pratica

Escolha uma situacao real do seu trabalho e aplique esta pratica em tres linhas:

1. Contexto: qual problema voce esta tentando resolver?
2. Acao: qual passo pequeno voce vai executar agora?
3. Validacao: como voce sabe que o resultado ficou correto?

## Resumo

Voce conclui esta etapa quando consegue dizer o que e, para que serve, quando usar, como aplicar, quais limitacoes existem e qual boa pratica reduz o risco principal."""


def _lesson(
    *,
    title: str,
    description: str,
    concept: str,
    correct: str,
    wrong_a: str,
    wrong_b: str,
    action: str,
    lesson_type: LessonType = LessonType.QUIZ,
) -> LessonSeed:
    return LessonSeed(
        title=title,
        description=description,
        content=_practice_content(title, description, concept, action, wrong_a, wrong_b),
        concept=concept,
        correct=correct,
        wrong_a=wrong_a,
        wrong_b=wrong_b,
        lesson_type=lesson_type,
    )


def _module(title: str, description: str, first: LessonSeed, second: LessonSeed) -> ModuleSeed:
    return ModuleSeed(title=title, description=description, lessons=(first, second))


TRACKS = TRACKS + (
    TrackSeed(
        title="Claude Code: Spec Driven Development",
        description="Transforme requisitos em specs, criterios e tarefas executaveis com Claude Code.",
        difficulty="intermediate",
        estimated_hours=4,
        icon="file-check-2",
        order=6,
        modules=(
            _module(
                "Especificacao antes do codigo",
                "Comece pela intencao, nao pelo diff.",
                _lesson(
                    title="Spec minima",
                    description="Defina objetivo, escopo e criterio de sucesso antes de implementar.",
                    concept="Uma boa spec descreve comportamento observavel, restricoes e fora de escopo.",
                    correct="Objetivo, comportamento esperado, restricoes e fora de escopo",
                    wrong_a="Pedir para codar direto sem criterio de aceite",
                    wrong_b="Escrever uma ideia vaga sem exemplos",
                    action="Escreva uma spec curta com problema, usuarios afetados, comportamento esperado e criterios de aceite verificaveis.",
                ),
                _lesson(
                    title="Critérios de aceite executaveis",
                    description="Converta expectativas em checks que podem ser testados.",
                    concept="Criterios de aceite bons podem virar teste, checklist ou validacao manual objetiva.",
                    correct="Usuario nao-admin e redirecionado para o dashboard",
                    wrong_a="A experiencia deve ficar melhor",
                    wrong_b="O codigo precisa estar bonito",
                    action="Para cada criterio, pergunte: como vou saber que passou sem depender de opiniao?",
                    lesson_type=LessonType.CHALLENGE,
                ),
            ),
            _module(
                "Da spec ao plano",
                "Quebre a spec em passos pequenos para o agente executar.",
                _lesson(
                    title="Plano por risco",
                    description="Ordene tarefas pelo que precisa ser descoberto primeiro.",
                    concept="Um plano bom reduz incerteza antes de editar areas sensiveis.",
                    correct="Ler contratos e testes antes de alterar o service",
                    wrong_a="Alterar todos os arquivos de uma vez",
                    wrong_b="Comecar por refatoracao visual sem entender a regra",
                    action="Peça ao Claude Code para listar arquivos provaveis, riscos e validacoes antes de tocar no codigo.",
                ),
                _lesson(
                    title="Definition of done da spec",
                    description="Feche a entrega com validacao e limites conhecidos.",
                    concept="Uma spec so termina quando mudanca, teste e limite conhecido estao registrados.",
                    correct="Resumo com mudancas, validacoes e pendencias",
                    wrong_a="Apenas dizer que esta pronto",
                    wrong_b="Nao registrar testes que falharam",
                    action="Ao final, compare o diff com cada criterio de aceite e registre o que foi validado.",
                ),
            ),
        ),
    ),
    TrackSeed(
        title="Claude Code: Vault com Obsidian",
        description="Use um vault como memoria viva de produto, decisoes e backlog.",
        difficulty="beginner",
        estimated_hours=4,
        icon="book-open",
        order=7,
        modules=(
            _module(
                "Vault como fonte de verdade",
                "Organize notas para orientar agentes e desenvolvimento.",
                _lesson(
                    title="Mapa do vault",
                    description="Separe visao, roadmap, tasks, ADRs e conteudo.",
                    concept="Um vault util tem areas claras e links entre decisao, tarefa e implementacao.",
                    correct="Vision, roadmap, tasks, ADRs e conteudo conectados",
                    wrong_a="Notas soltas sem dono nem data",
                    wrong_b="Guardar tudo somente no chat",
                    action="Crie uma nota indice que diga onde cada tipo de informacao deve viver.",
                ),
                _lesson(
                    title="Backlog acionavel",
                    description="Transforme notas em tasks que um agente consegue executar.",
                    concept="Uma task acionavel tem contexto, criterio de aceite, arquivos provaveis e status.",
                    correct="Contexto, aceite, dependencias e status",
                    wrong_a="Uma frase solta como melhorar learning",
                    wrong_b="Um texto longo sem proxima acao",
                    action="Revise cada task perguntando: um agente conseguiria comecar sem me chamar?",
                ),
            ),
            _module(
                "Sincronia entre vault e repo",
                "Evite que documentacao e codigo contem historias diferentes.",
                _lesson(
                    title="Atualizacao pos-entrega",
                    description="Atualize status depois de validar codigo.",
                    concept="O vault deve registrar o que esta done, parcial, local ou pendente.",
                    correct="Marcar Done/Parcial/local com data e evidencia",
                    wrong_a="Marcar como concluido antes de testar",
                    wrong_b="Apagar pendencias para parecer pronto",
                    action="Depois de cada entrega, atualize tasks e roadmap com data, evidencias e lacunas.",
                ),
                _lesson(
                    title="ADR curta",
                    description="Registre decisoes que mudam arquitetura ou produto.",
                    concept="ADR boa explica contexto, decisao, alternativas e consequencias.",
                    correct="Contexto, decisao, alternativas e consequencias",
                    wrong_a="Somente a decisao sem motivo",
                    wrong_b="Discussao longa sem conclusao",
                    action="Quando uma decisao afetar proximas tasks, escreva uma ADR curta no vault.",
                ),
            ),
        ),
    ),
    TrackSeed(
        title="Claude Code: Skills",
        description="Crie habilidades reutilizaveis para workflows recorrentes com Codex/Claude.",
        difficulty="intermediate",
        estimated_hours=4,
        icon="sparkles",
        order=8,
        modules=(
            _module(
                "Quando criar uma skill",
                "Identifique workflows que merecem virar instrucao reutilizavel.",
                _lesson(
                    title="Sinal de repeticao",
                    description="Reconheca quando uma tarefa repetida precisa de skill.",
                    concept="Skills valem quando um processo tem passos recorrentes, criterios e ferramentas especificas.",
                    correct="Workflow recorrente com passos e criterios claros",
                    wrong_a="Uma duvida pontual de uma unica vez",
                    wrong_b="Um prompt solto sem validacao",
                    action="Liste tarefas repetidas e marque quais exigem o mesmo checklist toda vez.",
                ),
                _lesson(
                    title="Escopo da skill",
                    description="Defina gatilho, entradas e saida esperada.",
                    concept="Uma skill boa diz quando usar, como agir e como validar o resultado.",
                    correct="Gatilho, passos e validacao",
                    wrong_a="Instrucoes genericas para qualquer coisa",
                    wrong_b="Somente uma lista de preferencias",
                    action="Escreva a skill como um procedimento que outro agente seguiria sem contexto extra.",
                ),
            ),
            _module(
                "Qualidade da skill",
                "Teste se a skill realmente muda o comportamento.",
                _lesson(
                    title="Checklist de execucao",
                    description="Transforme conhecimento em passos verificaveis.",
                    concept="A skill deve reduzir ambiguidade, nao apenas inspirar o agente.",
                    correct="Passos verificaveis e criterios de parada",
                    wrong_a="Texto motivacional sem procedimento",
                    wrong_b="Mandar o agente ser cuidadoso",
                    action="Converta cada recomendacao em uma acao observavel.",
                ),
                _lesson(
                    title="Evolucao da skill",
                    description="Atualize a skill quando encontrar uma falha recorrente.",
                    concept="Skills devem evoluir a partir de erros reais e padroes descobertos.",
                    correct="Adicionar regra apos erro recorrente validado",
                    wrong_a="Reescrever tudo a cada uso",
                    wrong_b="Nunca revisar a skill",
                    action="Quando um workflow falhar, registre a causa e ajuste a skill com um passo novo.",
                ),
            ),
        ),
    ),
    TrackSeed(
        title="Claude Code: TDD",
        description="Use testes para guiar mudancas pequenas, seguras e verificaveis.",
        difficulty="intermediate",
        estimated_hours=4,
        icon="flask-conical",
        order=9,
        modules=(
            _module(
                "Teste antes da mudanca",
                "Use falhas controladas para orientar o agente.",
                _lesson(
                    title="Red primeiro",
                    description="Escreva ou ajuste um teste que falha pelo motivo certo.",
                    concept="TDD com IA comeca comprovando a lacuna antes de pedir a implementacao.",
                    correct="Criar teste que falha pelo comportamento ausente",
                    wrong_a="Implementar tudo e so depois ver se passa",
                    wrong_b="Apagar teste dificil",
                    action="Peça ao agente para escrever o teste, rodar e explicar por que falhou.",
                ),
                _lesson(
                    title="Green minimo",
                    description="Implemente o menor codigo que satisfaz o teste.",
                    concept="O passo verde deve resolver o comportamento testado sem refatorar o mundo.",
                    correct="Mudanca pequena que faz o teste passar",
                    wrong_a="Refatoracao ampla antes de passar o teste",
                    wrong_b="Mockar tudo para esconder a falha",
                    action="Depois do teste vermelho, limite o agente a menor alteracao coerente.",
                ),
            ),
            _module(
                "Refatoracao segura",
                "Melhore com protecao depois do verde.",
                _lesson(
                    title="Refactor com rede",
                    description="Refatore somente com testes passando.",
                    concept="Refatorar depois do verde separa mudanca de comportamento de limpeza interna.",
                    correct="Refatorar mantendo testes verdes",
                    wrong_a="Mudar comportamento durante limpeza",
                    wrong_b="Refatorar sem rodar teste",
                    action="Peça resumo do que e comportamento e do que e limpeza antes de aceitar o diff.",
                ),
                _lesson(
                    title="Teste de regressao",
                    description="Capture bugs corrigidos para eles nao voltarem.",
                    concept="Bug corrigido sem teste pode voltar invisivel na proxima mudanca.",
                    correct="Adicionar caso que falhava antes da correcao",
                    wrong_a="Confiar apenas na memoria do time",
                    wrong_b="Testar so o caminho feliz",
                    action="Para cada bug, crie um teste que provaria a falha original.",
                    lesson_type=LessonType.CHALLENGE,
                ),
            ),
        ),
    ),
    TrackSeed(
        title="Claude Code: Markdown e Docs",
        description="Escreva documentacao tecnica clara, navegavel e util para agentes.",
        difficulty="beginner",
        estimated_hours=4,
        icon="file-text",
        order=10,
        modules=(
            _module(
                "Markdown pratico",
                "Use Markdown como interface de pensamento e entrega.",
                _lesson(
                    title="Estrutura escaneavel",
                    description="Organize docs com titulos, listas e exemplos curtos.",
                    concept="Markdown bom permite encontrar decisao, comando e exemplo sem ler tudo.",
                    correct="Titulos claros, listas curtas e exemplos",
                    wrong_a="Paredao de texto sem hierarquia",
                    wrong_b="Decoracao visual sem conteudo",
                    action="Reescreva docs para que uma pessoa ache comando, contexto e status em segundos.",
                ),
                _lesson(
                    title="Docs para agentes",
                    description="Escreva instrucoes que uma IA consegue executar.",
                    concept="Docs para agentes precisam de comandos, caminhos, criterios e limites.",
                    correct="Caminhos, comandos e criterios verificaveis",
                    wrong_a="Preferencias vagas sem exemplo",
                    wrong_b="Historico longo sem proxima acao",
                    action="Inclua exemplos de comando e diga quando nao aplicar aquela instrucao.",
                ),
            ),
            _module(
                "Manutencao de docs",
                "Mantenha documentacao sincronizada com o sistema.",
                _lesson(
                    title="Doc perto do codigo",
                    description="Atualize docs junto da mudanca que altera comportamento.",
                    concept="Documentacao confiavel muda no mesmo ciclo da funcionalidade.",
                    correct="Atualizar doc no mesmo PR da mudanca",
                    wrong_a="Documentar meses depois",
                    wrong_b="Criar doc duplicada em outro lugar",
                    action="Ao fechar uma task, revise se README, vault ou specs foram afetados.",
                ),
                _lesson(
                    title="Exemplo vivo",
                    description="Prefira exemplos que refletem o uso real.",
                    concept="Exemplo vivo reduz interpretacao errada e acelera onboarding.",
                    correct="Exemplo copiado do fluxo real",
                    wrong_a="Exemplo artificial que nunca roda",
                    wrong_b="Somente descricao abstrata",
                    action="Troque explicacoes longas por um exemplo pequeno e realista.",
                ),
            ),
        ),
    ),
    TrackSeed(
        title="Claude Code: CONTEXT.md",
        description="Use CONTEXT.md para orientar agentes sobre estado atual e decisoes vivas.",
        difficulty="intermediate",
        estimated_hours=4,
        icon="map",
        order=11,
        modules=(
            _module(
                "Contexto operacional",
                "Explique o estado atual sem reabrir toda a historia.",
                _lesson(
                    title="O que entra no CONTEXT.md",
                    description="Registre objetivo atual, restricoes e comandos uteis.",
                    concept="CONTEXT.md deve responder onde estamos, o que importa agora e como validar.",
                    correct="Objetivo atual, restricoes, comandos e riscos",
                    wrong_a="Toda a historia do projeto desde o inicio",
                    wrong_b="Somente links sem resumo",
                    action="Escreva um contexto que um agente consiga ler em menos de dois minutos.",
                ),
                _lesson(
                    title="Contexto temporario",
                    description="Separe contexto vivo de documentacao permanente.",
                    concept="CONTEXT.md e para estado corrente; decisoes permanentes viram ADR ou docs oficiais.",
                    correct="Estado corrente no CONTEXT; decisao duradoura em ADR",
                    wrong_a="Misturar tudo numa nota eterna",
                    wrong_b="Nunca remover contexto antigo",
                    action="Ao terminar uma fase, promova decisoes permanentes e limpe o contexto obsoleto.",
                ),
            ),
            _module(
                "Uso com agentes",
                "Faca o agente respeitar contexto antes de agir.",
                _lesson(
                    title="Leitura obrigatoria",
                    description="Instrua a IA a ler contexto antes de planejar.",
                    concept="O agente deve conhecer restricoes atuais antes de sugerir alteracoes.",
                    correct="Ler CONTEXT.md antes de propor plano",
                    wrong_a="Ignorar contexto e aplicar receita generica",
                    wrong_b="Perguntar tudo de novo ao usuario",
                    action="Inclua no workflow: leia CONTEXT.md, resuma restricoes e so entao aja.",
                ),
                _lesson(
                    title="Atualizacao no fechamento",
                    description="Atualize contexto quando o estado mudar.",
                    concept="Contexto desatualizado e pior que ausencia de contexto.",
                    correct="Registrar novo status e remover pendencia resolvida",
                    wrong_a="Deixar instrucoes antigas conflitantes",
                    wrong_b="Duplicar informacao em varios lugares",
                    action="No final da entrega, ajuste CONTEXT.md com status e proximos passos reais.",
                ),
            ),
        ),
    ),
    TrackSeed(
        title="Claude Code: CLAUDE.md",
        description="Defina regras persistentes para agentes trabalharem no repositorio.",
        difficulty="intermediate",
        estimated_hours=4,
        icon="scroll-text",
        order=12,
        modules=(
            _module(
                "Contrato do repositorio",
                "Transforme convencoes em instrucoes persistentes.",
                _lesson(
                    title="Regras do projeto",
                    description="Documente comandos, arquitetura e limites.",
                    concept="CLAUDE.md deve ensinar como trabalhar neste repo especifico.",
                    correct="Comandos, arquitetura, padroes e limites",
                    wrong_a="Conselhos genericos sobre programacao",
                    wrong_b="Instrucoes que contradizem o codigo",
                    action="Liste comandos reais, estrutura de pastas e regras que evitam erros recorrentes.",
                ),
                _lesson(
                    title="Instrucao verificavel",
                    description="Evite regras impossiveis de checar.",
                    concept="Uma instrucao boa e observavel no diff ou na validacao.",
                    correct="Use apply_patch para edicoes manuais",
                    wrong_a="Seja brilhante sempre",
                    wrong_b="Faca do jeito bonito",
                    action="Reescreva preferencias como comportamentos observaveis.",
                ),
            ),
            _module(
                "Evolucao do CLAUDE.md",
                "Mantenha regras fortes e poucas.",
                _lesson(
                    title="Menos e melhor",
                    description="Evite transformar CLAUDE.md em um deposito infinito.",
                    concept="Regras demais competem entre si e reduzem obediencia.",
                    correct="Poucas regras de alto impacto",
                    wrong_a="Adicionar toda opiniao pessoal",
                    wrong_b="Duplicar README inteiro",
                    action="Antes de adicionar regra, pergunte qual erro real ela evita.",
                ),
                _lesson(
                    title="Regra depois do erro",
                    description="Atualize instrucoes com base em falhas observadas.",
                    concept="O melhor CLAUDE.md nasce de erros recorrentes, nao de suposicoes.",
                    correct="Adicionar regra que previne falha repetida",
                    wrong_a="Adicionar regra sem caso concreto",
                    wrong_b="Nunca revisar instrucoes antigas",
                    action="Quando o agente errar duas vezes o mesmo padrao, transforme isso em regra.",
                ),
            ),
        ),
    ),
    TrackSeed(
        title="Claude Code: Plan Mode",
        description="Use Plan Mode para investigar, negociar escopo e reduzir risco antes da edicao.",
        difficulty="intermediate",
        estimated_hours=4,
        icon="list-checks",
        order=13,
        modules=(
            _module(
                "Quando planejar",
                "Use planejamento quando a mudanca tem incerteza real.",
                _lesson(
                    title="Sinal de incerteza",
                    description="Identifique quando agir direto e arriscado.",
                    concept="Plan Mode vale quando contexto, escopo ou risco ainda nao estao claros.",
                    correct="Investigar antes quando escopo ou risco estao incertos",
                    wrong_a="Planejar longamente uma mudanca trivial",
                    wrong_b="Editar primeiro e entender depois",
                    action="Antes de codar, classifique o risco: baixo, medio ou alto, e planeje proporcionalmente.",
                ),
                _lesson(
                    title="Pergunta desbloqueadora",
                    description="Pergunte so quando a resposta muda a implementacao.",
                    concept="Boa pergunta reduz risco; pergunta ruim transfere trabalho para o usuario.",
                    correct="Perguntar quando ha decisao de produto bloqueante",
                    wrong_a="Pedir confirmacao para qualquer detalhe obvio",
                    wrong_b="Adivinhar decisao sensivel",
                    action="Formule perguntas curtas que expliquem o impacto de cada caminho.",
                ),
            ),
            _module(
                "Plano executavel",
                "Saia do plano com proximos passos claros.",
                _lesson(
                    title="Checklist de execucao",
                    description="Transforme investigacao em passos pequenos.",
                    concept="Plano util tem ordem, validacao e pontos de risco.",
                    correct="Passos ordenados com validacao",
                    wrong_a="Lista vaga de ideias",
                    wrong_b="Plano sem criterio de parada",
                    action="Finalize o plano com arquivos provaveis, validacoes e primeiro passo.",
                ),
                _lesson(
                    title="Atualizar plano",
                    description="Revise o plano quando descobrir algo novo.",
                    concept="Plano e ferramenta viva, nao promessa rigida.",
                    correct="Ajustar plano apos nova evidencia",
                    wrong_a="Seguir plano errado por orgulho",
                    wrong_b="Mudar sem registrar motivo",
                    action="Quando a exploracao mudar a rota, registre o motivo antes de seguir.",
                ),
            ),
        ),
    ),
    TrackSeed(
        title="Machine Learning",
        description="Aprenda fundamentos praticos de dados, modelos, treino e avaliacao.",
        difficulty="intermediate",
        estimated_hours=6,
        icon="brain-circuit",
        order=14,
        modules=(
            _module(
                "Fundamentos de modelos",
                "Entenda dados, features e generalizacao.",
                _lesson(
                    title="Dados antes do modelo",
                    description="Avalie qualidade dos dados antes de escolher algoritmo.",
                    concept="Modelo bom depende de dados representativos, rotulos confiaveis e objetivo claro.",
                    correct="Verificar dados, rotulos e objetivo antes do algoritmo",
                    wrong_a="Escolher o modelo mais famoso primeiro",
                    wrong_b="Ignorar vieses da base",
                    action="Descreva origem, cobertura, rotulos e lacunas da base antes de treinar.",
                ),
                _lesson(
                    title="Treino e generalizacao",
                    description="Diferencie memorizar treino de funcionar em dados novos.",
                    concept="Generalizacao e desempenho consistente fora dos exemplos usados no treino.",
                    correct="Avaliar em dados separados do treino",
                    wrong_a="Medir somente acerto no conjunto treinado",
                    wrong_b="Aumentar complexidade sem validar",
                    action="Separe treino, validacao e teste antes de comparar modelos.",
                ),
            ),
            _module(
                "Avaliacao de ML",
                "Escolha metricas que combinam com o problema.",
                _lesson(
                    title="Metrica certa",
                    description="Use metricas alinhadas ao custo do erro.",
                    concept="A melhor metrica depende do tipo de erro mais caro para o negocio.",
                    correct="Escolher metrica pelo custo de falso positivo/negativo",
                    wrong_a="Usar acuracia sempre",
                    wrong_b="Otimizar metrica que ninguem entende",
                    action="Mapeie o custo de cada erro antes de escolher precision, recall ou acuracia.",
                ),
                _lesson(
                    title="Baseline",
                    description="Compare modelos contra uma referencia simples.",
                    concept="Sem baseline, nao da para saber se o modelo realmente agrega valor.",
                    correct="Comparar com regra simples ou modelo anterior",
                    wrong_a="Celebrar qualquer numero isolado",
                    wrong_b="Trocar modelo sem comparacao",
                    action="Crie uma regra simples e so aceite modelo que supere essa referencia.",
                    lesson_type=LessonType.CHALLENGE,
                ),
            ),
        ),
    ),
    TrackSeed(
        title="Governança de IA",
        description="Gerencie riscos, politicas, auditoria e responsabilidades em sistemas de IA.",
        difficulty="advanced",
        estimated_hours=6,
        icon="shield-check",
        order=15,
        modules=(
            _module(
                "Politicas e risco",
                "Defina onde IA pode ou nao pode decidir.",
                _lesson(
                    title="Classificacao de risco",
                    description="Separe casos de baixo, medio e alto impacto.",
                    concept="Governanca comeca classificando impacto, reversibilidade e pessoas afetadas.",
                    correct="Classificar por impacto, reversibilidade e alcance",
                    wrong_a="Liberar todos os usos por padrao",
                    wrong_b="Bloquear IA sem analisar caso",
                    action="Para cada caso de uso, defina risco, responsavel e aprovacao necessaria.",
                ),
                _lesson(
                    title="Human in the loop",
                    description="Decida quando revisao humana e obrigatoria.",
                    concept="Quanto maior o dano potencial, mais forte deve ser o controle humano.",
                    correct="Exigir revisao humana em decisoes de alto impacto",
                    wrong_a="Deixar a IA aprovar tudo sozinha",
                    wrong_b="Revisar manualmente ate rascunho simples",
                    action="Crie uma matriz: autonomia permitida, revisao obrigatoria e bloqueios.",
                ),
            ),
            _module(
                "Auditoria e transparencia",
                "Registre decisoes para investigar incidentes.",
                _lesson(
                    title="Log de decisao",
                    description="Guarde entradas, saidas, versoes e responsaveis.",
                    concept="Auditoria exige rastrear o que foi decidido, por qual modelo e com qual contexto.",
                    correct="Registrar entrada, saida, modelo, versao e usuario",
                    wrong_a="Salvar so a resposta final",
                    wrong_b="Nao manter historico por conveniencia",
                    action="Defina quais campos minimos cada decisao automatizada precisa registrar.",
                ),
                _lesson(
                    title="Politica comunicavel",
                    description="Escreva regras que equipes conseguem seguir.",
                    concept="Politica boa e clara o suficiente para orientar decisao no dia a dia.",
                    correct="Regras claras com exemplos permitidos e proibidos",
                    wrong_a="Documento juridico impossivel de aplicar",
                    wrong_b="Politica verbal sem registro",
                    action="Para cada regra, inclua um exemplo permitido e um proibido.",
                ),
            ),
        ),
    ),
    TrackSeed(
        title="CyberSecurity IA",
        description="Proteja sistemas com IA contra prompt injection, vazamento e abuso.",
        difficulty="advanced",
        estimated_hours=6,
        icon="lock-keyhole",
        order=16,
        modules=(
            _module(
                "Ameacas em IA",
                "Entenda ataques especificos contra sistemas com modelos.",
                _lesson(
                    title="Prompt injection",
                    description="Reconheca instrucoes maliciosas escondidas em dados.",
                    concept="Prompt injection tenta fazer o modelo obedecer ao atacante em vez do sistema.",
                    correct="Tratar conteudo externo como dado nao confiavel",
                    wrong_a="Confiar em qualquer texto lido pelo modelo",
                    wrong_b="Remover todas as instrucoes do sistema",
                    action="Separe claramente instrucao confiavel de conteudo externo nao confiavel.",
                ),
                _lesson(
                    title="Vazamento de dados",
                    description="Evite expor segredos, contexto interno e dados pessoais.",
                    concept="Modelos podem revelar informacao sensivel se contexto e ferramentas forem permissivos.",
                    correct="Aplicar minimo privilegio ao contexto e as ferramentas",
                    wrong_a="Enviar todos os dados para melhorar resposta",
                    wrong_b="Guardar segredos em prompts",
                    action="Revise quais dados entram no prompt e remova o que nao e necessario.",
                ),
            ),
            _module(
                "Defesas praticas",
                "Reduza superficie de ataque com controles verificaveis.",
                _lesson(
                    title="Ferramentas seguras",
                    description="Limite o que agentes podem executar.",
                    concept="Agentes precisam de permissoes minimas, logs e confirmacao para acoes sensiveis.",
                    correct="Permissao minima, log e confirmacao em acao sensivel",
                    wrong_a="Dar acesso irrestrito por conveniencia",
                    wrong_b="Esconder erros para parecer seguro",
                    action="Classifique ferramentas por risco e exija confirmacao nas destrutivas.",
                ),
                _lesson(
                    title="Teste adversarial",
                    description="Teste o sistema tentando quebrar suas regras.",
                    concept="Seguranca de IA precisa de casos maliciosos, nao so caminhos felizes.",
                    correct="Testar prompt injection, exfiltracao e abuso de ferramenta",
                    wrong_a="Testar apenas perguntas normais",
                    wrong_b="Confiar que o modelo sempre recusara",
                    action="Monte uma suite pequena de prompts adversariais e rode a cada mudanca.",
                    lesson_type=LessonType.CHALLENGE,
                ),
            ),
        ),
    ),
    TrackSeed(
        title="Harness Engineering",
        description="Projete ambientes, contexto, ferramentas e loops de feedback que tornam agentes de IA confiaveis em trabalho real.",
        difficulty="beginner",
        estimated_hours=8,
        icon="workflow",
        order=17,
        modules=(
            _module(
                "Iniciante - O sistema ao redor do modelo",
                "Entenda o que e um harness e por que o modelo sozinho nao entrega um agente confiavel.",
                _lesson(
                    title="Modelo, agente e harness",
                    description="Separe a capacidade do modelo da infraestrutura que permite agir.",
                    concept="O harness conecta o modelo a contexto, ferramentas, estado, limites e verificacao para transformar respostas em trabalho executavel.",
                    correct="Combinar modelo, contexto, ferramentas, estado, limites e verificacao",
                    wrong_a="Tratar um prompt longo como todo o sistema",
                    wrong_b="Medir qualidade apenas pela fluencia da resposta",
                    action="Desenhe o caminho entre a intencao do usuario, a decisao do modelo, a execucao de uma ferramenta e a verificacao do resultado.",
                ),
                _lesson(
                    title="O loop observar, agir e verificar",
                    description="Aprenda o ciclo minimo de execucao de um agente.",
                    concept="Um agente confiavel observa o estado atual, escolhe uma acao limitada, executa e verifica a evidencia antes de continuar.",
                    correct="Observar o estado, agir com limites e verificar a evidencia",
                    wrong_a="Executar todas as etapas sem olhar resultados intermediarios",
                    wrong_b="Declarar sucesso porque a ferramenta nao retornou erro",
                    action="Para uma tarefa simples, registre qual evidencia deve existir antes e depois de cada acao do agente.",
                    lesson_type=LessonType.CHALLENGE,
                ),
            ),
            _module(
                "Basico - Contexto, ferramentas e guardrails",
                "Torne o ambiente legivel para o agente e limite suas acoes de forma verificavel.",
                _lesson(
                    title="Contexto como mapa",
                    description="Entregue ao agente informacao relevante sem lotar a janela de contexto.",
                    concept="Contexto eficaz oferece um mapa curto para fontes de verdade locais, versionadas e descobertas sob demanda.",
                    correct="Usar um mapa curto que aponta para documentacao e contratos versionados",
                    wrong_a="Colocar toda a documentacao em uma unica instrucao gigante",
                    wrong_b="Depender de decisoes guardadas somente em chats e na memoria da equipe",
                    action="Crie um indice curto do repositorio com links para arquitetura, regras de dominio, comandos e criterios de conclusao.",
                ),
                _lesson(
                    title="Ferramentas e guardrails",
                    description="Desenhe interfaces de ferramenta claras, restritas e observaveis.",
                    concept="Ferramentas seguras usam contratos claros, menor privilegio, saidas estruturadas e confirmacao proporcional ao risco.",
                    correct="Aplicar contratos, menor privilegio, saida estruturada e confirmacao por risco",
                    wrong_a="Dar acesso amplo para evitar qualquer bloqueio",
                    wrong_b="Esconder falhas da ferramenta e pedir ao modelo para tentar novamente",
                    action="Classifique cada ferramenta por leitura, escrita reversivel ou acao destrutiva e defina controles para cada classe.",
                    lesson_type=LessonType.CHALLENGE,
                ),
            ),
            _module(
                "Intermediario - Feedback, avaliacoes e observabilidade",
                "Converta falhas recorrentes em sinais, testes e melhorias permanentes do harness.",
                _lesson(
                    title="Loops de feedback executaveis",
                    description="Faça o ambiente devolver sinais objetivos para o agente corrigir o proprio trabalho.",
                    concept="Testes, linters, tipos e validacoes de dominio transformam expectativas humanas em feedback rapido e acionavel.",
                    correct="Transformar expectativas em checks rapidos, locais e acionaveis",
                    wrong_a="Repetir o mesmo prompt esperando um resultado diferente",
                    wrong_b="Deixar toda verificacao para a revisao humana final",
                    action="Escolha uma regra importante e transforme-a em um teste ou check que informe o arquivo, a causa e a correcao esperada.",
                ),
                _lesson(
                    title="Evals e observabilidade",
                    description="Meça qualidade e diagnostique onde o sistema falha.",
                    concept="Uma avaliacao util separa falhas de modelo, contexto, ferramenta e runtime e acompanha qualidade, custo, latencia e seguranca.",
                    correct="Medir resultados e atribuir falhas ao componente correto do sistema",
                    wrong_a="Avaliar apenas se a resposta final parece boa",
                    wrong_b="Trocar o modelo sempre que uma execucao falhar",
                    action="Monte um conjunto pequeno de tarefas reais com criterio de sucesso, traces e categorias de falha para comparar mudancas no harness.",
                    lesson_type=LessonType.CHALLENGE,
                ),
            ),
            _module(
                "Avancado - Orquestracao e confiabilidade",
                "Projete execucoes longas, paralelas e seguras sem perder estado, controle ou eficiencia.",
                _lesson(
                    title="Estado, retomada e orquestracao",
                    description="Coordene tarefas longas e multiplos agentes com artefatos duraveis.",
                    concept="Orquestracao confiavel divide trabalho por fronteiras claras, persiste progresso e permite retomada idempotente apos interrupcoes.",
                    correct="Persistir estado, definir ownership e tornar a retomada idempotente",
                    wrong_a="Confiar que toda a execucao cabera em uma unica conversa",
                    wrong_b="Executar agentes paralelos editando o mesmo escopo sem coordenacao",
                    action="Projete um fluxo com checkpoint, criterio de handoff, ownership de arquivos e estrategia de recuperacao para uma tarefa longa.",
                ),
                _lesson(
                    title="Confiabilidade em producao",
                    description="Equilibre autonomia, seguranca, qualidade, latencia e custo.",
                    concept="Um harness de producao usa isolamento, budgets, timeouts, retries seletivos, circuit breakers e escalonamento humano baseado em risco.",
                    correct="Combinar isolamento, budgets, timeouts e escalonamento proporcional ao risco",
                    wrong_a="Aplicar retry infinito a qualquer erro",
                    wrong_b="Maximizar autonomia sem limite de custo ou impacto",
                    action="Defina SLOs e uma politica de falha para cada etapa: repetir, degradar, pausar, reverter ou escalar para uma pessoa.",
                    lesson_type=LessonType.CHALLENGE,
                ),
            ),
        ),
    ),
)


def _backend_ai_lesson(title: str, objective: str) -> LessonSeed:
    normalized = title.casefold()
    if title.startswith("Faça como eu fiz"):
        lesson_type = LessonType.LAB
    elif title.startswith("Para saber mais"):
        lesson_type = LessonType.READING
    elif title == "O que aprendemos" or title == "Encerramento":
        lesson_type = LessonType.QUIZ
    elif any(
        keyword in normalized
        for keyword in (
            "implementando",
            "implementação",
            "escrevendo testes",
            "garantindo",
            "avaliando",
            "desenvolvendo",
            "refatorando",
            "otimização",
            "otimizando",
            "isolamento",
        )
    ):
        lesson_type = LessonType.CHALLENGE
    else:
        lesson_type = LessonType.QUIZ

    concept = f"{objective} Nesta missão, o foco prático é {title.lower()}."
    return _lesson(
        title=title,
        description=f"Aplique {title.lower()} em um cenário de desenvolvimento back-end assistido por IA.",
        concept=concept,
        correct="Definir o resultado esperado, fornecer contexto verificável e validar a implementação",
        wrong_a="Aceitar a primeira geração da IA sem executar testes ou revisar decisões",
        wrong_b="Misturar arquitetura, implementação e infraestrutura sem critérios de aceite",
        action=(
            f"Construa um pequeno artefato sobre '{title}' e registre contexto, decisão, evidência "
            "de validação e melhoria encontrada."
        ),
        lesson_type=lesson_type,
    )


def _backend_ai_module(
    title: str, description: str, objective: str, lesson_titles: tuple[str, ...]
) -> ModuleSeed:
    return ModuleSeed(
        title=title,
        description=description,
        lessons=tuple(
            _backend_ai_lesson(lesson_title, objective) for lesson_title in lesson_titles
        ),
    )


TRACKS = TRACKS + (
    TrackSeed(
        title="Desenvolvimento Back-end com IA: Fundamentos Práticos",
        description="Planeje, teste, automatize e entregue aplicações back-end completas com apoio de IA, de ambientes isolados à containerização.",
        difficulty="intermediate",
        estimated_hours=12,
        icon="server-cog",
        order=18,
        modules=(
            _backend_ai_module(
                "Fundamentos, ambiente e contexto",
                "Prepare uma base segura, reproduzível e legível para pessoas e agentes de IA.",
                "Ambientes isolados e regras explícitas reduzem ambiguidade, deriva arquitetural e falhas difíceis de reproduzir.",
                (
                    "Por que base sólida importa mais com IA",
                    "Preparando o ambiente",
                    "Configurando regras e contexto para a IA",
                    "Faça como eu fiz: API Meetup",
                    "Decisões de arquitetura",
                    "Avaliando a segurança de portfólios digitais",
                    "Implementando Dev Containers",
                    "Facilitando o Onboarding com Dev Containers",
                    "Definindo regras para o desenvolvimento de um projeto",
                    "Para saber mais: modo auto no Cursor",
                    "O que aprendemos",
                ),
            ),
            _backend_ai_module(
                "Planejamento e scaffold da aplicação",
                "Converta requisitos em arquitetura e em um esqueleto back-end executável.",
                "Plan Mode e scaffold orientado por contratos permitem validar entidades, DTOs e camadas antes de aprofundar a implementação.",
                (
                    "O que é Plan Mode e por que usar",
                    "Scaffold pom.xml, configuração e entidades",
                    "Esqueleto completo do Repository ao Controller",
                    "Faça como eu fiz: Planejamento e scaffold API",
                    "Planejamento estratégico para otimização de recompensas",
                    "Gerenciamento de tarefas em uma plataforma social",
                    "Estrutura de classes para otimização de publicação de podcasts",
                    "Uso de DTOs para melhorar a comunicação entre serviços",
                    "Gerenciamento de exceções em serviços de streaming",
                    "Para saber mais: identity vs UUID na geração de ID",
                    "O que aprendemos",
                ),
            ),
            _backend_ai_module(
                "TDD e implementação guiada por testes",
                "Use testes como especificações executáveis para serviços, regras e controladores.",
                "No desenvolvimento assistido por IA, testes escritos primeiro delimitam comportamento, casos extremos e critérios objetivos de conclusão.",
                (
                    "Escrevendo testes para o CRUD de Eventos",
                    "Escrevendo testes para Inscrições e Cancelamento",
                    "Implementação do EventoService guiada pelos testes",
                    "Implementação do InscricaoService e validação final",
                    "Implementação de controllers",
                    "Faça como eu fiz: serviços TDD",
                    "Implementando TDD na criação de organogramas",
                    "Garantindo a segurança em transações financeiras com TDD",
                    "Garantindo a segurança dos dispositivos inteligentes",
                    "Gerenciamento de eventos em um aplicativo",
                    "Garantindo a integridade dos controladores",
                    "Para saber mais: acompanhar o steering no desenvolvimento com IA",
                    "O que aprendemos",
                ),
            ),
            _backend_ai_module(
                "Skills, workflows e qualidade contínua",
                "Automatize tarefas recorrentes, revisão, refatoração, Git e documentação.",
                "Skills e workflows eficazes transformam padrões de engenharia em procedimentos reutilizáveis, verificáveis e econômicos em contexto.",
                (
                    "Criando workflows e automações com IA",
                    "Refatoração assistida e IA como revisor",
                    "Git e documentação com IA",
                    "Faça como eu fiz: workflow com skills",
                    "Implementando skills para otimizar o atendimento ao cliente",
                    "Implementando revisão de código",
                    "Desenvolvendo um workflow",
                    "Refatorando o sistema de pedidos",
                    "Organizando commits semânticos em uma rede social",
                    "Para saber mais: entendendo o consumo de tokens",
                    "O que aprendemos",
                ),
            ),
            _backend_ai_module(
                "Docker, segurança e portabilidade",
                "Containerize a aplicação e otimize build, execução, rede e configuração.",
                "Containers confiáveis combinam imagens mínimas, builds reproduzíveis, menor privilégio, configuração externa e isolamento de rede.",
                (
                    "Containerização e Docker",
                    "Encerramento",
                    "Faça como eu fiz: containerização otimizada",
                    "Otimização de imagens Docker",
                    "Implementando práticas de segurança",
                    "Gerenciamento de variáveis de ambiente",
                    "Isolamento de rede",
                    "Otimizando a entrega de pacotes com Docker",
                    "Para saber mais: otimização do cache no docker build",
                    "O que aprendemos",
                ),
            ),
        ),
    ),
)


def _cowork_lesson(title: str, objective: str) -> LessonSeed:
    normalized = title.casefold()
    if title.startswith("Faça como eu fiz"):
        lesson_type = LessonType.LAB
    elif title.startswith("Para saber mais"):
        lesson_type = LessonType.READING
    elif title.startswith("O que aprendemos") or title == "Conclusão":
        lesson_type = LessonType.QUIZ
    elif any(
        keyword in normalized
        for keyword in (
            "criando",
            "orquestrando",
            "gerenciamento",
            "tomada de decisão",
            "eficiência",
            "gerando relatórios",
        )
    ):
        lesson_type = LessonType.CHALLENGE
    else:
        lesson_type = LessonType.QUIZ

    return _lesson(
        title=title,
        description=f"Pratique {title.lower()} em uma operação real com Claude Cowork.",
        concept=f"{objective} O foco desta missão é {title.lower()}.",
        correct="Definir objetivo, contexto, responsabilidades e evidências antes de executar",
        wrong_a="Delegar tudo sem limites, critérios ou revisão humana",
        wrong_b="Usar vários agentes sem separar escopo e responsabilidade",
        action=(
            f"Simule '{title}' com um objetivo mensurável, entradas confiáveis, entregável claro "
            "e uma etapa final de revisão."
        ),
        lesson_type=lesson_type,
    )


def _cowork_module(
    title: str, description: str, objective: str, lesson_titles: tuple[str, ...]
) -> ModuleSeed:
    return ModuleSeed(
        title=title,
        description=description,
        lessons=tuple(_cowork_lesson(lesson_title, objective) for lesson_title in lesson_titles),
    )


_cowork_modules = (
    _cowork_module(
        "Fundamentos da operação com Cowork",
        "Prepare o ambiente e escolha quando usar automação simples ou múltiplos agentes.",
        "Uma operação confiável começa com ambiente preparado, contexto suficiente e uma escolha consciente do grau de autonomia.",
        (
            "Preparando o ambiente",
            "Rotina comum de uma pessoa gestora",
            "Automação simples vs. Operação multiagente",
            "Tomada de decisão com assistente virtual",
            "Para saber mais: janela de contexto em LLMs",
            "Faça como eu fiz: otimizar projetos",
            "O que aprendemos-",
        ),
    ),
    _cowork_module(
        "PMO multiagente",
        "Crie um agente de PMO, paralelize tarefas e incorpore feedback sem perder contexto.",
        "Agentes paralelos precisam de escopos independentes, artefatos compartilhados e um processo explícito de integração de resultados.",
        (
            "Criando nosso agente de PMO",
            "Rodando vários agentes em paralelo",
            "Entendendo a janela de contexto",
            "Gerenciamento de projetos de integração",
            "Para saber mais: integração de feedback",
            "Faça como eu fiz: criar agente PMO",
            "O que aprendemos-",
        ),
    ),
    _cowork_module(
        "Criação e orquestração de agentes",
        "Defina agentes especializados, conecte responsabilidades e diferencie skills de agentes.",
        "Um agente tem objetivo, contexto, ferramentas e autonomia; a orquestração coordena contratos, dependências e handoffs entre especialistas.",
        (
            "Criando agentes manualmente",
            "Criando agentes para otimizar a gestão de inventários",
            "Orquestrando nossos agentes",
            "Skills vs. Agentes",
            "Para saber mais: anatomia de um agente de IA",
            "Faça como eu fiz: criar e orquestrar agentes",
            "O que aprendemos-",
        ),
    ),
    _cowork_module(
        "Análise de dados e relatórios",
        "Combine interpretação por IA com processamento determinístico em Python e HTML.",
        "Análises confiáveis separam cálculo reproduzível em código da interpretação contextual realizada pelo modelo.",
        (
            "Geração de relatórios",
            "Economizando com Python",
            "Para saber mais: por que Python-",
            "Eficiência na análise de dados",
            "Gerando relatórios HTML",
            "Para saber mais: separação de tarefas determinísticas e interpretativas",
            "Faça como eu fiz: análise NPS Onboard",
            "O que aprendemos-",
        ),
    ),
    _cowork_module(
        "Claude no Chrome",
        "Leve o Claude ao fluxo visual do navegador com supervisão e contexto.",
        "A integração no navegador permite observar e agir em interfaces, mas exige confirmação proporcional ao impacto de cada ação.",
        (
            "Claude no Chrome",
            "Para saber mais: integração visual do Claude",
            "Faça como eu fiz: usar Claude no Chrome",
            "O que aprendemos-",
            "Conclusão",
        ),
    ),
)


def _gemini_workspace_lesson(title: str, objective: str) -> LessonSeed:
    normalized = title.casefold()
    if title.startswith("Laboratório"):
        lesson_type = LessonType.LAB
    elif title.startswith("Leitura"):
        lesson_type = LessonType.READING
    elif title.startswith("Desafio") or any(
        keyword in normalized
        for keyword in ("analisando", "criando", "automatizando", "projetando", "validando")
    ):
        lesson_type = LessonType.CHALLENGE
    else:
        lesson_type = LessonType.QUIZ

    return _lesson(
        title=title,
        description=f"Use o Gemini para {title.lower()} com qualidade, segurança e revisão humana.",
        concept=f"{objective} Nesta missão, você praticará {title.lower()}.",
        correct="Definir objetivo, contexto, formato de saída e critérios de verificação",
        wrong_a="Enviar dados sensíveis sem confirmar política, acesso ou necessidade",
        wrong_b="Publicar a primeira resposta sem conferir fontes, cálculos ou contexto",
        action=(
            f"Execute um cenário de '{title}', compare a saída com a fonte original e registre "
            "o que precisou de revisão humana."
        ),
        lesson_type=lesson_type,
    )


def _gemini_workspace_module(
    title: str, description: str, objective: str, lesson_titles: tuple[str, ...]
) -> ModuleSeed:
    return ModuleSeed(
        title=title,
        description=description,
        lessons=tuple(
            _gemini_workspace_lesson(lesson_title, objective) for lesson_title in lesson_titles
        ),
    )


_gemini_workspace_track = TrackSeed(
    title="Gemini no Google Workspace: produtividade com IA",
    description="Use Gemini com texto, imagem, áudio e vídeo para criar, colaborar, analisar dados e automatizar rotinas no Google Workspace com senso crítico.",
    difficulty="beginner",
    estimated_hours=10,
    icon="gem",
    order=19,
    modules=(
        _gemini_workspace_module(
            "Fundamentos e uso consciente",
            "Entenda como o Gemini responde, quais recursos dependem de plano e como manter controle humano.",
            "Autonomia produtiva começa entendendo capacidades, limitações, disponibilidade e responsabilidade sobre a saída gerada.",
            (
                "Como o Gemini processa contexto e gera respostas",
                "Conhecendo a interface e o painel lateral no Workspace",
                "Planos, idiomas e recursos disponíveis",
                "Alucinações, vieses e limites da resposta",
                "Privacidade e dados corporativos no Workspace",
                "Desafio: decidir quando usar, revisar ou não usar IA",
            ),
        ),
        _gemini_workspace_module(
            "Prompts e multimodalidade",
            "Combine instruções claras com texto, imagens, áudio, vídeo e arquivos de referência.",
            "Prompts eficazes descrevem papel, tarefa, contexto, restrições, formato e evidência esperada, adaptados à modalidade usada.",
            (
                "Anatomia de um prompt aplicável ao trabalho",
                "Iteração: do primeiro rascunho à entrega confiável",
                "Analisando texto e documentos longos",
                "Analisando imagens, áudio e vídeo",
                "Criando resumos, relatórios e insights de negócio",
                "Laboratório: briefing multimodal com critérios de qualidade",
            ),
        ),
        _gemini_workspace_module(
            "Gmail, Calendar e Chat",
            "Reduza trabalho operacional em comunicação, agenda e acompanhamento de equipes.",
            "Comunicação assistida por IA deve preservar intenção, tom, fatos, destinatários e compromissos antes do envio.",
            (
                "Resumindo conversas e encontrando decisões no Gmail",
                "Escrevendo e refinando e-mails com tom adequado",
                "Extraindo ações, responsáveis e prazos",
                "Organizando agenda e preparação de reuniões",
                "Criando sínteses e comunicados para o Google Chat",
                "Desafio: transformar uma caixa de entrada em plano de ação",
            ),
        ),
        _gemini_workspace_module(
            "Docs e Drive",
            "Produza documentos consistentes e encontre conhecimento em fontes corporativas.",
            "Documentos úteis conectam fontes autorizadas, estrutura adequada ao público e revisão factual antes do compartilhamento.",
            (
                "Criando documentos a partir de um briefing",
                "Reescrevendo com clareza, concisão e tom",
                "Resumindo arquivos e referências do Google Drive",
                "Usando modelos de estilo e formato como referência",
                "Criando imagens e elementos visuais no Docs",
                "Laboratório: relatório executivo baseado em fontes do Drive",
            ),
        ),
        _gemini_workspace_module(
            "Slides, Meet e Vids",
            "Transforme ideias e reuniões em narrativas, apresentações e conteúdos audiovisuais.",
            "Uma boa entrega multimídia separa mensagem, evidência, narrativa e recursos visuais, sem confundir estética com precisão.",
            (
                "Planejando a narrativa de uma apresentação",
                "Criando e editando slides com Gemini",
                "Gerando imagens e recursos visuais responsáveis",
                "Capturando notas, decisões e próximos passos no Meet",
                "Criando roteiros, voz e vídeo no Google Vids",
                "Desafio: reunião, resumo executivo e apresentação final",
            ),
        ),
        _gemini_workspace_module(
            "Sheets, Forms e decisões com dados",
            "Organize informações, detecte padrões e transforme dados em decisões verificáveis.",
            "Análise responsável usa dados limpos, perguntas explícitas, cálculos conferidos e distinção entre evidência e interpretação.",
            (
                "Preparando dados antes de pedir uma análise",
                "Criando tabelas, fórmulas e preenchimentos inteligentes",
                "Analisando tendências e gerando insights no Sheets",
                "Usando a função de IA para classificar e resumir dados",
                "Criando formulários e sintetizando respostas abertas",
                "Laboratório: painel de decisão com dados verificáveis",
            ),
        ),
        _gemini_workspace_module(
            "Automações e agentes sem código",
            "Conecte ferramentas, regras e agentes para automatizar fluxos colaborativos com governança.",
            "Agentes corporativos precisam de gatilho, fontes autorizadas, passos observáveis, limites, tratamento de falhas e responsável humano.",
            (
                "Do prompt isolado ao fluxo de trabalho",
                "Criando automações no Google Workspace Studio",
                "Projetando agentes com passos, ferramentas e fontes",
                "Conectando Gmail, Drive e ferramentas corporativas",
                "Validando segurança, custo e qualidade de uma automação",
                "Desafio final: agente de produtividade sem código",
            ),
        ),
    ),
)


def _gemini_assistant_lesson(title: str, objective: str) -> LessonSeed:
    normalized = title.casefold()
    if title.startswith("Mão na massa"):
        lesson_type = LessonType.LAB
    elif title.startswith("Para saber mais"):
        lesson_type = LessonType.READING
    elif any(
        keyword in normalized
        for keyword in (
            "utilizando",
            "personalizando",
            "criando",
            "implementando",
            "inovando",
            "buscando",
            "adicionando",
            "gerenciamento",
            "produzindo",
            "validando",
        )
    ):
        lesson_type = LessonType.CHALLENGE
    else:
        lesson_type = LessonType.QUIZ

    return _lesson(
        title=title,
        description=f"Explore {title.lower()} no Gemini com um resultado prático e verificável.",
        concept=f"{objective} O foco desta missão é {title.lower()}.",
        correct="Fornecer contexto, objetivo, referências e formato esperado, depois revisar a saída",
        wrong_a="Confiar em toda resposta porque foi gerada por um modelo mais avançado",
        wrong_b="Usar recursos pagos ou conectados sem conferir plano, permissões e dados envolvidos",
        action=(
            f"Realize um exercício de '{title}', registre o prompt usado, compare o resultado com "
            "uma fonte confiável e refine pelo menos uma vez."
        ),
        lesson_type=lesson_type,
    )


def _gemini_assistant_module(
    title: str, description: str, objective: str, lesson_titles: tuple[str, ...]
) -> ModuleSeed:
    return ModuleSeed(
        title=title,
        description=description,
        lessons=tuple(
            _gemini_assistant_lesson(lesson_title, objective) for lesson_title in lesson_titles
        ),
    )


_gemini_assistant_track = TrackSeed(
    title="Gemini: Domine o assistente de IA do Google",
    description="Domine IA generativa e Prompt Engineering com Gemini para pesquisar, criar imagens, prototipar, integrar serviços e personalizar assistentes.",
    difficulty="beginner",
    estimated_hours=11,
    icon="bot",
    order=20,
    modules=(
        _gemini_assistant_module(
            "Primeiros passos e projeto prático",
            "Entenda modelos de linguagem e comece um e-commerce geek com texto e imagens.",
            "A base do uso produtivo está em compreender o modelo, preparar o ambiente e transformar uma necessidade real em prompts iterativos.",
            (
                "Apresentação",
                "Preparando o ambiente",
                "Visão geral do Gemini",
                "O que são e como funcionam os modelos de linguagem",
                "Começando o projeto do curso",
                "Mão na massa: e-commerce geek",
                "Utilizando IA para otimizar descrições de produtos",
                "Usando o Gemini para análise e criação",
                "Gerando as primeiras imagens",
                "O que aprendemos-",
            ),
        ),
        _gemini_assistant_module(
            "Pesquisa profunda: do insight ao conteúdo multimídia",
            "Use instruções persistentes, arquivos e Deep Research para produzir conteúdo fundamentado.",
            "Pesquisa profunda exige um plano editável, seleção consciente de fontes, comparação de evidências e transformação responsável do relatório.",
            (
                "Apresentando os System Prompts",
                "Trabalhando com arquivos",
                "Personalizando interações com clientes",
                "Deep Research para pesquisa profunda",
                "Mão na massa: configurar prompts Gemini",
                "Para saber mais: extração e comparação de grandes volumes de dados",
                "Utilizando busca profunda para otimizar a gestão de contatos",
                "O que aprendemos-",
            ),
        ),
        _gemini_assistant_module(
            "Criação visual e desenvolvimento com IA",
            "Crie imagens refinadas e transforme ideias em protótipos funcionais no Canvas.",
            "Criação visual eficaz combina referências, composição, consistência, iteração e avaliação de segurança antes de publicar.",
            (
                "Nano Banana: criando modelos e imagens refinadas",
                "Canvas: transformando ideias em um site, sem programar",
                "Inovando na apresentação de produtos",
                "Mão na massa: criar site com Canvas",
                "Para saber mais: a influência do contexto no comportamento da IA",
                "Inovando com IA generativa na experiência de pessoas usuárias",
                "O que aprendemos-",
            ),
        ),
        _gemini_assistant_module(
            "Gemini no ecossistema Google",
            "Conecte Gmail, Drive, Agenda, tarefas e YouTube para buscar e agir com contexto.",
            "Integrações úteis respeitam permissões, minimizam dados compartilhados e pedem confirmação antes de criar ou alterar informações.",
            (
                "Resumindo e-mails do Gmail",
                "Integração de serviços para melhorar a eficiência operacional",
                "Buscando arquivos específicos no Google Drive",
                "Mão na massa: integrar Google Workspace",
                "Adicionando compromissos à Agenda",
                "Gerenciamento de tarefas",
                "Resumindo vídeo do YouTube",
                "Para saber mais: uso do SynthID",
                "O que aprendemos-",
            ),
        ),
        _gemini_assistant_module(
            "Gems: personalizando o seu assistente de IA",
            "Crie versões especializadas do Gemini com instruções, exemplos e arquivos de referência.",
            "Uma Gem confiável delimita papel, público, regras, conhecimento de apoio, exemplos e situações em que deve pedir ajuda.",
            (
                "Introdução às Gems",
                "Implementando Gems para otimizar descrições de produtos",
                "Criando uma Gem de texto e com base em PDF",
                "Mão na massa: criar Gem de correção",
                "Aprimorando a comunicação interna com Gems",
                "Para saber mais: organização de few-shots",
                "O que aprendemos-",
            ),
        ),
        _gemini_assistant_module(
            "Raciocínio e mídia avançada",
            "Escolha níveis de raciocínio e produza vídeo respeitando planos, limites e procedência.",
            "Recursos avançados consomem mais tempo e cota; devem ser escolhidos pelo risco e complexidade da tarefa, não por novidade.",
            (
                "Quando usar pensamento padrão, estendido ou Deep Think",
                "Deep Think: raciocínio paralelo e disponibilidade no plano Ultra",
                "Produzindo vídeos com Veo 3 e Veo 3.1",
                "Planejando cenas, áudio e continuidade visual",
                "Validando procedência, SynthID e uso responsável de mídia",
                "Desafio final: campanha multimídia para o e-commerce geek",
            ),
        ),
    ),
)


def _sales_gemini_lesson(title: str, objective: str) -> LessonSeed:
    normalized = title.casefold()
    if title.startswith("Faça como eu fiz"):
        lesson_type = LessonType.LAB
    elif title.startswith("O que aprendemos") or title == "Conclusão do curso":
        lesson_type = LessonType.QUIZ
    elif any(
        keyword in normalized
        for keyword in (
            "criando",
            "rapport",
            "investigação",
            "persuas",
            "objeções",
            "prospecção",
            "propostas",
            "apresentação de impacto",
            "otimização",
            "inteligência",
            "agente",
            "priorizando",
            "workshop",
            "personalizando",
        )
    ):
        lesson_type = LessonType.CHALLENGE
    else:
        lesson_type = LessonType.QUIZ

    return _lesson(
        title=title,
        description=f"Aplique {title.lower()} em uma situação comercial simulada com o Gemini.",
        concept=f"{objective} Nesta missão, o foco é {title.lower()}.",
        correct="Ancorar a resposta em dados do cliente, objetivo comercial, regras e evidências",
        wrong_a="Inventar urgência, dados ou benefícios para aumentar a chance de conversão",
        wrong_b="Automatizar mensagens em escala sem segmentação, consentimento ou revisão",
        action=(
            f"Conduza um roleplay de '{title}' com persona, contexto, objetivo, objeção e critério "
            "de sucesso; depois revise fatos, ética e adequação da abordagem."
        ),
        lesson_type=lesson_type,
    )


def _sales_gemini_module(
    title: str, description: str, objective: str, lesson_titles: tuple[str, ...]
) -> ModuleSeed:
    return ModuleSeed(
        title=title,
        description=description,
        lessons=tuple(_sales_gemini_lesson(item, objective) for item in lesson_titles),
    )


_sales_gemini_track = TrackSeed(
    title="Estratégia de vendas e Gemini: Construa agentes comerciais inteligentes",
    description="Crie Gems e agentes para prospecção, diagnóstico, CRM, propostas, negociação e treinamento comercial com ética e evidências.",
    difficulty="intermediate",
    estimated_hours=8,
    icon="handshake",
    order=21,
    modules=(
        _sales_gemini_module(
            "Fundamentos do agente comercial",
            "Prepare o Gemini e construa uma primeira Gem com comunicação e limites claros.",
            "Um agente comercial confiável combina persona, tarefa, contexto, formato, conhecimento autorizado e regras éticas.",
            (
                "Apresentação",
                "Preparando o ambiente: Google Gemini e prompts do curso",
                "Criando o primeiro Gem",
                "Estratégias de comunicação",
                "Ética e refinamento",
                "Faça como eu fiz na aula: configurando o Gem",
                "O que aprendemos-",
            ),
        ),
        _sales_gemini_module(
            "Persuasão e abordagem consultiva com IA",
            "Pratique rapport digital, diagnóstico, perguntas e tratamento responsável de objeções.",
            "Venda consultiva usa escuta, contexto e perguntas para compreender necessidades; persuasão não deve manipular nem ocultar informação.",
            (
                "Técnica de rapport com IA",
                "Investigação profunda e diagnóstico de dificuldades",
                "Perguntas persuasivas",
                "Estratégias de persuasão para aumentar vendas",
                "Objeções",
                "Faça como eu fiz na aula: Rapport digital",
                "O que aprendemos-",
            ),
        ),
        _sales_gemini_module(
            "Prospecção, propostas e apresentações",
            "Segmente contas e transforme diagnóstico em proposta e narrativa de valor.",
            "Prospecção eficaz conecta perfil, sinal, problema e hipótese de valor; propostas devem ser específicas, verificáveis e adequadas ao cliente.",
            (
                "Prospecção",
                "Estratégias de prospecção",
                "Propostas",
                "Apresentação de impacto",
                "Otimização e escala",
                "Faça como eu fiz na aula: prospecção e propostas",
                "O que aprendemos-",
            ),
        ),
        _sales_gemini_module(
            "Inteligência de CRM e treinamento",
            "Use dados comerciais para priorizar contas e simular conversas de venda.",
            "Decisões de CRM precisam de critérios transparentes, dados atualizados, explicações e revisão humana antes de afetar clientes.",
            (
                "Inteligência de dados",
                "IA como aliada analítica",
                "Agente de CRM",
                "Priorizando contas com risco no CRM",
                "Workshop de vendas",
                "Faça como eu fiz na aula: criar e usar agentes",
                "O que aprendemos-",
            ),
        ),
        _sales_gemini_module(
            "Qualidade e personalização de agentes",
            "Crie prompts reutilizáveis, experiências personalizadas e controles contra alucinação.",
            "Agentes sustentáveis têm instruções testáveis, fontes explícitas, exemplos, recusa segura, métricas e ciclos de melhoria.",
            (
                "Boas práticas na criação de agentes",
                "Gem para criação de prompts",
                "Personalizando experiências",
                "O que aprendemos-",
                "Conclusão do curso",
            ),
        ),
    ),
)


def _workspace_communication_lesson(title: str, objective: str) -> LessonSeed:
    normalized = title.casefold()
    if title.startswith("Faça como eu fiz"):
        lesson_type = LessonType.LAB
    elif title.startswith("Para saber mais"):
        lesson_type = LessonType.READING
    elif title.startswith("O que aprendemos") or title == "Conclusão":
        lesson_type = LessonType.QUIZ
    elif any(
        keyword in normalized
        for keyword in (
            "estruturando",
            "análise",
            "aprimorando",
            "organização",
            "execução",
            "criando",
            "colaboração",
            "design",
            "integração",
            "comunicação eficaz",
            "automatizado",
            "busca avançada",
            "organizando",
        )
    ):
        lesson_type = LessonType.CHALLENGE
    else:
        lesson_type = LessonType.QUIZ

    return _lesson(
        title=title,
        description=f"Pratique {title.lower()} usando Gemini no Google Workspace.",
        concept=f"{objective} Nesta missão, você trabalhará {title.lower()}.",
        correct="Usar contexto autorizado, objetivo explícito, formato esperado e revisão antes de compartilhar",
        wrong_a="Permitir que a IA envie, mova ou publique conteúdo sem confirmação",
        wrong_b="Copiar respostas sem conferir fatos, permissões, tom ou destinatários",
        action=(
            f"Execute um cenário de '{title}', revise a saída contra a fonte original e confirme "
            "permissões, destinatários e próximos passos."
        ),
        lesson_type=lesson_type,
    )


def _workspace_communication_module(
    title: str, description: str, objective: str, lesson_titles: tuple[str, ...]
) -> ModuleSeed:
    return ModuleSeed(
        title=title,
        description=description,
        lessons=tuple(_workspace_communication_lesson(item, objective) for item in lesson_titles),
    )


_workspace_communication_track = TrackSeed(
    title="Gemini no Google Workspace: Comunicação, criação e organização com IA",
    description="Transforme e-mails em ações, crie documentos e apresentações, automatize reuniões e organize conhecimento com Gemini no Workspace.",
    difficulty="beginner",
    estimated_hours=12,
    icon="messages-square",
    order=22,
    modules=(
        _workspace_communication_module(
            "Fundamentos e configuração",
            "Prepare o ambiente, conheça o assistente lateral e escreva prompts seguros e eficazes.",
            "Uma boa experiência no Workspace começa com configuração, privacidade, estrutura de prompt e equilíbrio entre contexto e concisão.",
            (
                "Apresentação",
                "Preparando o ambiente",
                "O assistente na barra lateral",
                "Segurança e privacidade",
                "Estrutura de prompts",
                "Estruturando prompts para organogramas empresariais",
                "Mobile e configurações iniciais",
                "Faça como eu fiz: usar o Gemini no Workspace",
                "Para saber mais: equilíbrio entre detalhes e concisão",
                "O que aprendemos-",
            ),
        ),
        _workspace_communication_module(
            "Gmail: da comunicação à execução",
            "Resuma, traduza e transforme mensagens em tarefas e respostas adequadas ao contexto.",
            "Comunicação assistida deve preservar intenção, cultura, fatos, compromissos e revisão humana antes do envio.",
            (
                "Análise e resumo inteligente",
                "Tradução e adaptação cultural",
                "Aprimorando a comunicação com clientes internacionais na Hermex Log",
                "Resposta assistida",
                "Organização inteligente",
                "Do e-mail para a execução",
                "Faça como eu fiz: Gmail com Gemini",
                "Para saber mais: criação de Gems para respostas automatizadas",
                "O que aprendemos-",
            ),
        ),
        _workspace_communication_module(
            "Docs: estrutura, escrita e colaboração",
            "Supere a página em branco, personalize documentos e refine conteúdo com a equipe.",
            "Documentos confiáveis combinam briefing, fontes, estrutura adequada ao público, edição iterativa e comparação final.",
            (
                "Estrutura e escrita: o fim da página em branco",
                "Contexto e inserção de conteúdo inteligente",
                "Edição e refinamento",
                "Criando um manual de boas-vindas para novos artistas na Playcatch",
                "Colaboração inteligente",
                "Análise comparativa e finalização",
                "Faça como eu fiz: manual onboarding",
                "Para saber mais: pop-up de revisão no Google Docs",
                "O que aprendemos-",
            ),
        ),
        _workspace_communication_module(
            "Slides: narrativa e design generativo",
            "Transforme documentos em apresentações multimodais com notas e integração a reuniões.",
            "Apresentações eficazes conectam objetivo, público, narrativa, evidência, design e fala sem sacrificar precisão.",
            (
                "Do Docs para o Slides",
                "Adaptação de conteúdo",
                "Design generativo",
                "Criatividade com modelo multimodal",
                "Speaker Notes",
                "Integração com Meet",
                "Faça como eu fiz: slides interativos",
                "O que aprendemos-",
            ),
        ),
        _workspace_communication_module(
            "Meet e Agenda: reuniões integradas",
            "Planeje, conduza e documente reuniões com acessibilidade, áudio e automação.",
            "Automação de reuniões precisa informar participantes, respeitar controles do anfitrião e converter notas em decisões e responsáveis.",
            (
                "Agendamento inteligente",
                "Setup prévio",
                "Controle audiovisual",
                "Ferramentas avançadas",
                "Comunicação eficaz em reuniões logísticas",
                "O pós-reunião automatizado",
                "Faça como eu fiz: reunião integrada",
                "Para saber mais: recursos de áudio no Meet",
                "O que aprendemos-",
            ),
        ),
        _workspace_communication_module(
            "Drive: busca, organização e ciclo completo",
            "Encontre, organize e conecte documentos com permissões e fontes verificáveis.",
            "Gestão de conhecimento exige nomenclatura, estrutura simples, busca com fontes, permissões mínimas e confirmação antes de mover arquivos.",
            (
                "O ciclo completo",
                "Busca avançada",
                "Organização e controle",
                "Organizando portfólios de desenvolvedores",
                "Segurança e interação",
                "Faça como eu fiz: integração Gemini",
                "Para saber mais: IA e organização de documentos",
                "Conclusão",
                "O que aprendemos-",
            ),
        ),
    ),
)


TRACKS = TRACKS + (
    _gemini_workspace_track,
    _gemini_assistant_track,
    _sales_gemini_track,
    _workspace_communication_track,
)


CLAUDE_CODE_CHAPTER_TRACK_TITLES = (
    "Claude Code: Spec Driven Development",
    "Claude Code: Vault com Obsidian",
    "Claude Code: Skills",
    "Claude Code: TDD",
    "Claude Code: Markdown e Docs",
    "Claude Code: CONTEXT.md",
    "Claude Code: CLAUDE.md",
    "Claude Code: Plan Mode",
)


def _as_chapter_module(track: TrackSeed) -> ModuleSeed:
    lessons = tuple(lesson for module in track.modules for lesson in module.lessons)
    return ModuleSeed(
        title=track.title.removeprefix("Claude Code: "),
        description=track.description,
        lessons=lessons,
    )


_claude_code_chapters = tuple(
    _as_chapter_module(track) for track in TRACKS if track.title in CLAUDE_CODE_CHAPTER_TRACK_TITLES
)


_TRACK_CAPSTONES = {
    "Fundamentos de IA": (
        "Auditoria de uma resposta de IA",
        "Projeto final: decisão assistida com fontes e limites",
        "Demonstre que sabe separar fluência, evidência, incerteza e responsabilidade humana.",
    ),
    "Claude Chat": (
        "Diagnóstico de uma conversa improdutiva",
        "Projeto final: biblioteca de prompts para uma rotina real",
        "Construa conversas reutilizáveis com contexto, exemplos, critérios e revisão.",
    ),
    "Claude Cowork": (
        "Diagnóstico de uma operação multiagente",
        "Projeto final: PMO com agentes, dados e handoffs",
        "Projete uma operação com responsabilidades claras, estado compartilhado e validação final.",
    ),
    "Claude Code": (
        "Diagnóstico de um repositório para agentes",
        "Projeto final: entrega end-to-end com testes e documentação",
        "Conduza uma mudança completa, da leitura do contexto à revisão do diff e evidências.",
    ),
    "AI Engineering": (
        "Diagnóstico de falhas em um sistema de IA",
        "Projeto final: pipeline com avaliação e observabilidade",
        "Integre modelo, dados, guardrails, métricas e feedback em uma solução verificável.",
    ),
    "Machine Learning": (
        "Diagnóstico de dados, métricas e generalização",
        "Projeto final: experimento reproduzível de Machine Learning",
        "Documente hipótese, baseline, divisão de dados, métrica, resultado e limitações.",
    ),
    "Governança de IA": (
        "Diagnóstico de risco e responsabilidade",
        "Projeto final: política operacional para um caso de IA",
        "Defina classificação de risco, controles humanos, auditoria e resposta a incidentes.",
    ),
    "CyberSecurity IA": (
        "Diagnóstico de superfície de ataque",
        "Projeto final: threat model e suíte adversarial",
        "Mapeie ativos, ameaças, permissões, ataques e defesas testáveis para um agente.",
    ),
    "Harness Engineering": (
        "Diagnóstico do harness e de seus pontos cegos",
        "Projeto final: harness observável e recuperável",
        "Projete contexto, ferramentas, estado, evals, isolamento e estratégia de recuperação.",
    ),
    "Desenvolvimento Back-end com IA: Fundamentos Práticos": (
        "Diagnóstico arquitetural e de qualidade",
        "Projeto final: API testada, documentada e containerizada",
        "Entregue uma API completa com contratos, TDD, automações, segurança e Docker.",
    ),
    "Gemini no Google Workspace: produtividade com IA": (
        "Diagnóstico de uma rotina no Workspace",
        "Projeto final: fluxo produtivo com dados e agente sem código",
        "Conecte comunicação, documentos, análise e automação com permissões e revisão humana.",
    ),
    "Gemini: Domine o assistente de IA do Google": (
        "Diagnóstico de prompt, fonte e modalidade",
        "Projeto final: campanha multimodal com Gem especializada",
        "Combine pesquisa, imagem, Canvas, integrações e mídia com procedência verificável.",
    ),
    "Estratégia de vendas e Gemini: Construa agentes comerciais inteligentes": (
        "Diagnóstico de um funil comercial assistido por IA",
        "Projeto final: agente comercial com CRM e roleplay",
        "Crie um agente ético para prospectar, diagnosticar, propor, negociar e aprender com feedback.",
    ),
    "Gemini no Google Workspace: Comunicação, criação e organização com IA": (
        "Diagnóstico de comunicação e conhecimento",
        "Projeto final: ciclo Gmail, Docs, Slides, Meet e Drive",
        "Converta uma demanda em comunicação, documento, apresentação, reunião e arquivo organizado.",
    ),
}


def _track_capstone(track: TrackSeed) -> ModuleSeed:
    challenge_title, lab_title, objective = _TRACK_CAPSTONES[track.title]
    return ModuleSeed(
        title="Projeto integrador",
        description=objective,
        lessons=(
            _lesson(
                title=challenge_title,
                description="Identifique lacunas, riscos e critérios antes de construir a solução final.",
                concept=objective,
                correct="Mapear contexto, riscos, evidências e critérios de sucesso antes da execução",
                wrong_a="Começar pela ferramenta sem esclarecer o problema",
                wrong_b="Avaliar apenas se a saída parece convincente",
                action="Produza um diagnóstico priorizado com evidências e plano de validação.",
                lesson_type=LessonType.CHALLENGE,
            ),
            _lesson(
                title=lab_title,
                description="Integre os conhecimentos da trilha em uma entrega demonstrável.",
                concept=objective,
                correct="Entregar artefato, testes, evidências, limitações e próximos passos",
                wrong_a="Apresentar somente uma resposta gerada pela IA",
                wrong_b="Ocultar falhas ou decisões que ainda precisam de validação",
                action="Construa a entrega final e registre como outra pessoa pode verificar o resultado.",
                lesson_type=LessonType.LAB,
            ),
        ),
    )


TRACKS = tuple(
    replace(
        track,
        description="Aprenda Claude Code por capitulos praticos: leitura, testes, specs, vault, skills, docs, contexto e plan mode.",
        estimated_hours=40,
        order=order,
        modules=track.modules + _claude_code_chapters + (_track_capstone(track),),
    )
    if track.title == "Claude Code"
    else (
        replace(
            track,
            description="Use Claude Cowork para planejar operações, coordenar agentes, analisar dados e automatizar trabalho no navegador.",
            estimated_hours=9,
            modules=track.modules + _cowork_modules + (_track_capstone(track),),
            order=order,
        )
        if track.title == "Claude Cowork"
        else replace(track, modules=track.modules + (_track_capstone(track),), order=order)
    )
    for order, track in enumerate(
        (track for track in TRACKS if track.title not in CLAUDE_CODE_CHAPTER_TRACK_TITLES),
        start=1,
    )
)


def _replace_quizzes_with_active_practice(track: TrackSeed) -> TrackSeed:
    """Converte quizzes genéricos em práticas com intenções cognitivas distintas."""
    activity_cycle = (
        LessonType.CHECKLIST,
        LessonType.CHALLENGE,
        LessonType.FREE_ANSWER,
    )
    activity_index = 0
    modules: list[ModuleSeed] = []
    for module in track.modules:
        lessons: list[LessonSeed] = []
        for lesson in module.lessons:
            if lesson.lesson_type == LessonType.QUIZ:
                lesson = replace(
                    lesson,
                    lesson_type=activity_cycle[activity_index % len(activity_cycle)],
                    xp=max(lesson.xp, 35),
                )
                activity_index += 1
            lessons.append(lesson)
        modules.append(replace(module, lessons=tuple(lessons)))
    return replace(track, modules=tuple(modules))


TRACKS = tuple(_replace_quizzes_with_active_practice(track) for track in TRACKS)
TRACKS = tuple(
    replace(
        track,
        description=(
            "Formação-base do ecossistema Workspace. Domine produtividade, dados e automações "
            "antes de avançar para a especialização em comunicação e operações."
        ),
    )
    if track.title == "Gemini no Google Workspace: produtividade com IA"
    else replace(
        track,
        description=(
            "Especialização aplicada que continua a formação de produtividade com fluxos "
            "integrados de Gmail, Docs, Slides, Meet, Agenda e Drive."
        ),
    )
    if track.title == "Gemini no Google Workspace: Comunicação, criação e organização com IA"
    else track
    for track in TRACKS
)


SCHOOL_TITLE = "Vértice Academy"
SCHOOL_SLUG = "claude-academy"
SCHOOL_DESCRIPTION = "Formações práticas em IA, produtividade, engenharia e negócios digitais."
SCHOOL_ICON = "graduation-cap"


async def _get_track(session: AsyncSession, title: str) -> Track | None:
    result = await session.execute(
        select(Track).where(Track.title == _with_portuguese_accents(title))
    )
    return result.scalar_one_or_none()


async def _deactivate_split_claude_code_tracks(session: AsyncSession) -> list[str]:
    tracks = await session.scalars(
        select(Track).where(
            Track.title.in_(CLAUDE_CODE_CHAPTER_TRACK_TITLES),
            Track.deleted_at.is_(None),
            Track.is_active.is_(True),
        )
    )
    deactivated: list[str] = []
    for track in tracks:
        track.is_active = False
        deactivated.append(track.title)
    return deactivated


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
    track.title = _with_portuguese_accents(track_data.title)
    track.description = _with_portuguese_accents(track_data.description)
    track.difficulty = track_data.difficulty
    track.estimated_hours = _estimated_track_hours(track_data)
    track.icon = track_data.icon
    track.order = track_data.order
    track.is_active = True


async def _create_track(session: AsyncSession, school: School, track_data: TrackSeed) -> Track:
    track = Track(
        school_id=school.id,
        title=_with_portuguese_accents(track_data.title),
        description=_with_portuguese_accents(track_data.description),
        difficulty=track_data.difficulty,
        estimated_hours=_estimated_track_hours(track_data),
        icon=track_data.icon,
        order=track_data.order,
        is_active=True,
    )
    session.add(track)
    await session.flush()
    return track


async def _upsert_module(
    session: AsyncSession, track: Track, order: int, module_data: ModuleSeed
) -> Module:
    """Localiza um módulo existente por (track_id, order) ou cria um novo.

    Casar por posição (não por título) é o que permite atualizar o texto de um
    módulo já existente mesmo quando o título em si muda (ex.: correção de
    acentuação), preservando o id do registro e suas dependências (levels,
    lessons, etc).
    """
    module = await session.scalar(
        select(Module).where(Module.track_id == track.id, Module.order == order)
    )
    if module is None:
        module = Module(
            track_id=track.id,
            title=_with_portuguese_accents(module_data.title),
            description=_with_portuguese_accents(module_data.description),
            order=order,
            is_active=True,
        )
        session.add(module)
        await session.flush()
    else:
        module.title = _with_portuguese_accents(module_data.title)
        module.description = _with_portuguese_accents(module_data.description)
        module.is_active = True
    return module


async def _upsert_level(session: AsyncSession, module: Module, module_data: ModuleSeed) -> Level:
    """Localiza o nível 1 de um módulo (module_id, level_number) ou cria um novo."""
    total_xp = sum(lesson.xp for lesson in module_data.lessons)
    level = await session.scalar(
        select(Level).where(Level.module_id == module.id, Level.level_number == 1)
    )
    title = _with_portuguese_accents(f"Fase - {module_data.title}")
    description = _with_portuguese_accents(
        f"Fase progressiva de {module_data.title}: cada atividade libera uma camada "
        "de teoria, prática guiada, limitações e boas práticas."
    )
    estimated_minutes = sum(_estimated_lesson_minutes(lesson) for lesson in module_data.lessons)
    if level is None:
        level = Level(
            module_id=module.id,
            title=title,
            description=description,
            level_number=1,
            estimated_minutes=estimated_minutes,
            xp=total_xp,
            required_xp=0,
        )
        session.add(level)
        await session.flush()
    else:
        level.title = title
        level.description = description
        level.estimated_minutes = estimated_minutes
        level.xp = total_xp
    return level


async def _upsert_lesson(
    session: AsyncSession,
    level: Level,
    track_data: TrackSeed,
    order: int,
    lesson_data: LessonSeed,
) -> Lesson:
    """Localiza uma missão existente por (level_id, order) ou cria uma nova."""
    lesson = await session.scalar(
        select(Lesson).where(Lesson.level_id == level.id, Lesson.order == order)
    )
    content = _with_portuguese_accents(lesson_data.content)
    estimated_minutes = _estimated_lesson_minutes(lesson_data)
    if lesson is None:
        lesson = Lesson(
            level_id=level.id,
            title=_with_portuguese_accents(lesson_data.title),
            description=_with_portuguese_accents(lesson_data.description),
            content=content,
            estimated_minutes=estimated_minutes,
            difficulty=track_data.difficulty,
            lesson_type=lesson_data.lesson_type,
            order=order,
            xp=lesson_data.xp,
            ai_corrected=False,
        )
        session.add(lesson)
        await session.flush()
    else:
        lesson.title = _with_portuguese_accents(lesson_data.title)
        lesson.description = _with_portuguese_accents(lesson_data.description)
        lesson.content = content
        lesson.estimated_minutes = estimated_minutes
        lesson.difficulty = track_data.difficulty
        lesson.lesson_type = lesson_data.lesson_type
        lesson.xp = lesson_data.xp
    return lesson


async def _upsert_question(
    session: AsyncSession, lesson: Lesson, question_order: int, question_data: QuestionSeed
) -> Question:
    """Localiza a questão única de uma missão (lesson_id, order=1) ou cria uma nova."""
    question = await session.scalar(
        select(Question).where(Question.lesson_id == lesson.id, Question.order == question_order)
    )
    if question is None:
        question = Question(
            lesson_id=lesson.id,
            question=_with_portuguese_accents(question_data.question),
            question_type=question_data.question_type,
            explanation=(
                _with_portuguese_accents(question_data.explanation)
                if question_data.explanation is not None
                else None
            ),
            points=question_data.points,
            order=question_order,
        )
        session.add(question)
        await session.flush()
    else:
        question.question = _with_portuguese_accents(question_data.question)
        question.question_type = question_data.question_type
        question.explanation = (
            _with_portuguese_accents(question_data.explanation)
            if question_data.explanation is not None
            else None
        )
        question.points = question_data.points
        question.deleted_at = None
    return question


async def _upsert_alternatives(
    session: AsyncSession, question: Question, question_data: QuestionSeed
) -> None:
    """Localiza cada alternativa por (question_id, order) ou cria uma nova."""
    for alt_order, alternative_data in enumerate(question_data.alternatives, start=1):
        alternative = await session.scalar(
            select(Alternative).where(
                Alternative.question_id == question.id, Alternative.order == alt_order
            )
        )
        if alternative is None:
            session.add(
                Alternative(
                    question_id=question.id,
                    text=_with_portuguese_accents(alternative_data.text),
                    is_correct=alternative_data.is_correct,
                    feedback=_with_portuguese_accents(alternative_data.feedback),
                    order=alt_order,
                )
            )
        else:
            alternative.text = _with_portuguese_accents(alternative_data.text)
            alternative.is_correct = alternative_data.is_correct
            alternative.feedback = _with_portuguese_accents(alternative_data.feedback)
            alternative.deleted_at = None

    extra_alternatives = await session.scalars(
        select(Alternative).where(
            Alternative.question_id == question.id,
            Alternative.order > len(question_data.alternatives),
            Alternative.deleted_at.is_(None),
        )
    )
    now = datetime.now(UTC)
    for alternative in extra_alternatives:
        alternative.deleted_at = now


def _default_questions_for_lesson(lesson_data: LessonSeed) -> tuple[QuestionSeed, ...]:
    """Gera um bloco de pratica curto, no estilo Duolingo, para cada missao."""
    if lesson_data.questions:
        return lesson_data.questions

    questions = (
        QuestionSeed(
            question=f"Qual princípio orienta a missão '{lesson_data.title}'-",
            question_type=QuestionType.MULTIPLE_CHOICE,
            explanation=lesson_data.concept,
            alternatives=(
                AlternativeSeed(
                    lesson_data.correct,
                    True,
                    "Correto. Essa resposta segue o conceito principal da missao.",
                ),
                AlternativeSeed(
                    lesson_data.wrong_a,
                    False,
                    "Ainda nao. Essa alternativa cria uma expectativa errada para a ferramenta.",
                ),
                AlternativeSeed(
                    lesson_data.wrong_b,
                    False,
                    "Nao e a melhor opcao para este contexto. Compare com o objetivo da missao.",
                ),
            ),
        ),
        QuestionSeed(
            question=f"Em qual decisão prática o conceito de '{lesson_data.title}' foi aplicado corretamente-",
            question_type=QuestionType.MULTIPLE_CHOICE,
            explanation="Aplicar um conceito exige transformá-lo em uma decisão observável.",
            alternatives=(
                AlternativeSeed(
                    lesson_data.correct,
                    True,
                    "Isso mesmo. A escolha traduz o conceito em uma ação adequada.",
                ),
                AlternativeSeed(
                    lesson_data.wrong_b,
                    False,
                    "Essa decisão ignora o critério trabalhado na missão.",
                ),
                AlternativeSeed(
                    "Agir sem contexto e conferir apenas depois",
                    False,
                    "Aplicação responsável começa antes da execução.",
                ),
            ),
        ),
        QuestionSeed(
            question=f"Um resultado falhou durante '{lesson_data.title}'. Qual diagnóstico identifica a causa mais provável-",
            question_type=QuestionType.MULTIPLE_CHOICE,
            explanation=(
                "Nesta etapa, tambem importa reconhecer o que parece plausivel, mas leva a um uso ruim."
            ),
            alternatives=(
                AlternativeSeed(
                    lesson_data.wrong_a,
                    True,
                    "Boa leitura. Esta e uma armadilha comum nesta etapa.",
                ),
                AlternativeSeed(
                    lesson_data.correct,
                    False,
                    "Essa e a boa pratica, nao a armadilha.",
                ),
                AlternativeSeed(
                    f"Aplicar o conceito de '{lesson_data.title}' com contexto claro",
                    False,
                    "Isso aponta para aplicacao correta, nao para o erro a evitar.",
                ),
            ),
        ),
        QuestionSeed(
            question=f"Depois de identificar o erro em '{lesson_data.title}', qual correção deve vir primeiro-",
            question_type=QuestionType.MULTIPLE_CHOICE,
            explanation=(
                "A resposta certa e a que transforma o conceito em uma acao observavel, nao so em teoria."
            ),
            alternatives=(
                AlternativeSeed(
                    lesson_data.correct,
                    True,
                    "Perfeito. Essa escolha transforma o conceito em comportamento pratico.",
                ),
                AlternativeSeed(
                    lesson_data.wrong_a,
                    False,
                    "Ainda nao. Essa escolha tende a causar retrabalho ou confianca excessiva.",
                ),
                AlternativeSeed(
                    lesson_data.wrong_b,
                    False,
                    "Nao desta vez. Essa opcao foge do criterio principal da missao.",
                ),
            ),
        ),
    )

    if lesson_data.lesson_type != LessonType.CHALLENGE:
        return questions

    return questions + (
        QuestionSeed(
            question="Organize as etapas do desafio na sequencia mais confiavel.",
            question_type=QuestionType.DRAG_AND_DROP,
            explanation=(
                "Desafios reais ficam mais seguros quando voce entende o contexto, executa uma "
                "acao limitada e valida a evidencia antes de encerrar."
            ),
            points=3,
            alternatives=(
                AlternativeSeed(
                    "Entender o contexto e definir o resultado observavel",
                    True,
                    "Comece tornando a intencao e o criterio de sucesso explicitos.",
                ),
                AlternativeSeed(
                    "Executar a menor acao segura que produz evidencia",
                    True,
                    "Uma acao limitada reduz risco e acelera o feedback.",
                ),
                AlternativeSeed(
                    "Verificar o resultado e registrar o que foi aprendido",
                    True,
                    "A verificacao fecha o loop e melhora a proxima execucao.",
                ),
            ),
        ),
    )


async def _sync_track_content(session: AsyncSession, track: Track, track_data: TrackSeed) -> None:
    """Sincroniza toda a árvore aninhada (módulo -> nível -> missão -> questão ->
    alternativa) de uma trilha, já exista a trilha ou tenha acabado de ser criada.

    Casar cada nível da hierarquia por posição (order / level_number), e não por
    título, garante que os textos já gravados no banco sejam atualizados quando o
    conteúdo definido acima mudar (por exemplo, uma correção de acentuação), sem
    recriar registros e sem quebrar referências externas como
    user_lesson_progress.lesson_id.
    """
    for module_order, module_data in enumerate(track_data.modules, start=1):
        module = await _upsert_module(session, track, module_order, module_data)
        level = await _upsert_level(session, module, module_data)

        for lesson_order, lesson_data in enumerate(module_data.lessons, start=1):
            lesson = await _upsert_lesson(session, level, track_data, lesson_order, lesson_data)
            questions = _default_questions_for_lesson(lesson_data)
            for question_order, question_data in enumerate(questions, start=1):
                question = await _upsert_question(session, lesson, question_order, question_data)
                await _upsert_alternatives(session, question, question_data)

            extra_questions = await session.scalars(
                select(Question).where(
                    Question.lesson_id == lesson.id,
                    Question.order > len(questions),
                    Question.deleted_at.is_(None),
                )
            )
            now = datetime.now(UTC)
            for question in extra_questions:
                question.deleted_at = now


async def seed(session: AsyncSession) -> None:
    created_tracks = 0
    updated_tracks: list[str] = []
    deactivated_tracks: list[str] = []
    school = await _get_or_create_school(session)

    for track_data in TRACKS:
        existing_track = await _get_track(session, track_data.title)
        if existing_track is not None:
            existing_track.school_id = school.id
            _update_track_metadata(existing_track, track_data)
            track = existing_track
            updated_tracks.append(track_data.title)
        else:
            track = await _create_track(session, school, track_data)
            created_tracks += 1

        await _sync_track_content(session, track, track_data)

    deactivated_tracks = await _deactivate_split_claude_code_tracks(session)

    await session.commit()

    print(f"Trilhas criadas: {created_tracks}")
    if updated_tracks:
        print(
            "Trilhas já existentes atualizadas (metadados e conteúdo): " + ", ".join(updated_tracks)
        )
    if deactivated_tracks:
        print("Trilhas Claude Code separadas desativadas: " + ", ".join(deactivated_tracks))


async def main() -> None:
    async with AsyncSessionLocal() as session:
        await seed(session)


if __name__ == "__main__":
    asyncio.run(main())
