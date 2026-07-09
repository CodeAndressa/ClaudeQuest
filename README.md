# ClaudeQuest

Plataforma de aprendizagem gamificada para formar profissionais no uso prático do
ecossistema Claude — Chat, Cowork, Code, Prompt Engineering, MCP, Skills, Subagents e Hooks.

A documentação de produto, arquitetura, banco de dados e decisões (ADRs) vive no
Vault do Obsidian em `G:\Meu Drive\Obsidian\ClaudeLinguo` — esse repositório é
apenas a implementação. Em caso de dúvida sobre uma regra de negócio, o Vault é
a fonte de verdade, não este README.

## Stack

| Camada | Tecnologias |
|---|---|
| Backend | Python 3.13, FastAPI, SQLAlchemy 2 (async), Alembic, Pydantic v2, PyJWT, Argon2, Structlog |
| Frontend | React 19, TypeScript, Vite, TailwindCSS v4, shadcn/ui, TanStack Query, Zustand, React Hook Form + Zod, Framer Motion, i18next, React Router |
| Banco | SQLite (arquivo local, sem serviço/Docker) |
| Testes | Pytest (backend), Vitest + Testing Library (frontend), Playwright (e2e) |
| CI/CD | GitHub Actions, Vercel (frontend) |

Ver [`ADR-011`](../../ClaudeLinguo/14%20-%20Decisions%20\(ADRs\)/ADR-011-Initial-Setup-Decisions.md.md)
para o histórico das decisões de infraestrutura tomadas na configuração inicial
(nome do produto, estrutura de pastas, hospedagem, gerenciador de dependências).

## Estrutura do repositório

```
ClaudeQuest/
  backend/     API FastAPI, organizada por domínio (Clean Architecture + DDD Lite)
  frontend/    SPA React, organizada por feature
  docs/        Documentação técnica específica da implementação
  scripts/     Scripts utilitários de desenvolvimento
  .github/     Workflows de CI
```

## Setup local

Pré-requisitos: Python 3.13+, [uv](https://docs.astral.sh/uv/), Node 22+.
Não é necessário Docker — o banco é um arquivo SQLite local, criado automaticamente
pelo Alembic (ver ADR sobre a troca de PostgreSQL para SQLite).

```bash
cp .env.example .env

# Backend — roda em http://localhost:8002
cd backend
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --port 8002

# Usuário admin de demonstração (necessário: não existe tela de cadastro — ver ADR-011)
uv run python scripts/seed_demo_data.py
# admin@claudequest.dev / ClaudeQuest#2026

# Conteúdo de demonstração da trilha "Claude Chat" (Track → Module → Level → Lesson → Question)
uv run python scripts/seed_learning_content.py

# Frontend — roda em http://localhost:5180 (proxy de /api para o backend)
cd frontend
npm install
npm run dev
```

> A porta padrão do Vite (5173) foi trocada para **5180** neste projeto para evitar
> conflito com outros projetos locais da mesma máquina.

## Testes

A suíte de testes do backend usa um arquivo SQLite **separado** do banco de
desenvolvimento (`claudequest_test.db`, ver `TEST_DATABASE_URL` no `.env.example`) —
nunca rode os testes apontando para o mesmo arquivo que o Alembic gerencia. Ambos os
arquivos `.db` são criados automaticamente (o de teste, pelo fixture `db_engine`; o de
dev, pelo `alembic upgrade head`) e nunca são versionados (ver `.gitignore`).

Cada domínio do backend mantém seus próprios testes em `app/domains/<dominio>/tests/`;
testes de infraestrutura compartilhada (config, logging, middlewares) ficam em `backend/tests/`.

```bash
# Backend — cobertura mínima de 90% (Services/Repositories exigem 100% quando existirem)
cd backend && uv run pytest --cov

# Frontend — unitários
cd frontend && npm run test:coverage

# Frontend — end-to-end (sobe o próprio dev server automaticamente)
cd frontend && npm run test:e2e
```

## Qualidade de código

```bash
cd backend && uv run ruff check . && uv run mypy app && uv run bandit -r app -q --exclude '*/tests/*,*/test_*'
cd frontend && npm run lint && npm run typecheck && npm run format:check
```

## Domínios implementados

| Domínio | Endpoints | Status |
|---|---|---|
| `auth` | login, refresh, logout, me, forgot-password, reset-password | Completo (AUTH-001/002/003) |
| `users`, `organizations` | (sem endpoints próprios ainda) | Schema mínimo para suportar auth |
| `learning` | `GET /learning/tracks`, `GET /learning/tracks/{id}` | Somente leitura (LEARN-001 a 006 parciais — ver backlog no Vault) |
| `gamification` | `GET /gamification/me`, `POST /gamification/xp` | Cálculo e persistência de XP (GAME-001 parcial — ver backlog no Vault) |

## Deploy

- **Frontend**: Vercel (`frontend/vercel.json`), framework Vite.
- **Backend**: ainda não implantado — por decisão registrada na ADR-011, o FOUND-001
  entrega apenas o ambiente local; a hospedagem do backend (Render/Neon) fica para
  uma tarefa de deploy dedicada, quando as credenciais estiverem disponíveis.
