# ClaudeQuest — Backend

API do ClaudeQuest, construída em FastAPI seguindo Clean Architecture + DDD Lite,
organizada por domínio (ver `docs/` na raiz do repositório para a documentação completa).

## Setup local

```bash
uv sync
cp ../.env.example ../.env
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --port 8002
```

## Testes

```bash
uv run pytest --cov
```
