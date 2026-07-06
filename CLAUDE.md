# ClaudeQuest — instruções para sessões de Claude Code neste repositório

## Fonte de verdade

Este repositório é só código. Toda regra de negócio, requisito de produto,
arquitetura e decisão vive no Vault do Obsidian em
`G:\Meu Drive\Obsidian\ClaudeLinguo`. Antes de implementar qualquer feature nova:

1. Leia a documentação relacionada no Vault (Vision, PRD, Functional Specification,
   Architecture, Database, Backend, Frontend, e o épico correspondente em
   `13 - Roadmap` e no backlog `tasks.md.md`).
2. Se encontrar inconsistência entre documentos, não implemente — reporte e aguarde decisão.
3. Ao terminar uma feature, atualize a documentação do Vault (ADR se houve decisão nova,
   status no backlog, roadmap se o escopo mudou).

## Convenções deste repositório

- **Backend organizado por domínio**, não por camada técnica: cada domínio
  (`auth`, `learning`, `gamification`, ...) reúne router, service, repository,
  schema, model e testes. Ver ADR-011.
- **Fluxo de request obrigatório**: Router → Service → Repository → Database.
  Regra de negócio só em Service. Nunca em Router ou Repository.
- **Todo modelo ORM** herda de `app.database.base.AuditedModel` (UUID PK, soft
  delete, colunas de auditoria — nunca redeclarar essas colunas manualmente).
- **Toda resposta de API** usa o envelope padrão (`app.shared.schemas.SuccessResponse`
  / `ErrorResponse`). Nunca retornar um objeto solto.
- **Erros**: lançar `app.shared.errors.AppError`, nunca capturar `Exception` fora do
  middleware único em `app.middlewares.error_handler`.
- **Frontend organizado por feature** em `src/features/*`, nunca por tipo de arquivo.
  Dados remotos sempre via TanStack Query (nunca `fetch` direto em componente);
  Zustand é só para estado de UI (tema, sessão, idioma).
- **i18n obrigatório**: toda string visível ao usuário vem de `src/i18n/locales/{pt-BR,en-US,es-ES}`.
  Nenhuma string fixa na UI.
- **Cobertura de testes**: mínimo 90% em qualquer camada; Services e Repositories do
  backend, quando existirem, devem chegar a 100%.
- **Nunca** usar `TODO`, `FIXME`, código temporário ou mock definitivo.

## Portas e ambiente local

- Backend: `localhost:8002` (prefixo de API `/api/v1`).
- Frontend (Vite dev server): `localhost:5180` — porta não-padrão, ver README.
- Postgres: `localhost:5432` via `docker compose up -d db`.

## Comandos úteis

```bash
# Backend
cd backend && uv run uvicorn app.main:app --reload --port 8002
cd backend && uv run pytest --cov
cd backend && uv run ruff check . && uv run mypy app && uv run bandit -r app

# Frontend
cd frontend && npm run dev
cd frontend && npm run test:coverage
cd frontend && npm run lint && npm run typecheck
```
