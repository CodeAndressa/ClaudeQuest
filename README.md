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
| Banco | PostgreSQL 17 |
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

Pré-requisitos: Python 3.13+, [uv](https://docs.astral.sh/uv/), Node 22+, Docker.

```bash
cp .env.example .env

# Banco de dados
docker compose up -d db

# Backend — roda em http://localhost:8002
cd backend
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --port 8002

# Frontend — roda em http://localhost:5180 (proxy de /api para o backend)
cd frontend
npm install
npm run dev
```

> A porta padrão do Vite (5173) foi trocada para **5180** neste projeto para evitar
> conflito com outros projetos locais da mesma máquina.

## Testes

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
cd backend && uv run ruff check . && uv run mypy app && uv run bandit -r app
cd frontend && npm run lint && npm run typecheck && npm run format:check
```

## Deploy

- **Frontend**: Vercel (`frontend/vercel.json`), framework Vite.
- **Backend**: ainda não implantado — por decisão registrada na ADR-011, o FOUND-001
  entrega apenas o ambiente local; a hospedagem do backend (Render/Neon) fica para
  uma tarefa de deploy dedicada, quando as credenciais estiverem disponíveis.
