# Patch Manager API

## Setup local

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

## Rodar a API

```bash
uvicorn app.main:app --reload --port 8000
```

## Migrations

```bash
alembic upgrade head
```

Para criar uma nova migration:

```bash
alembic revision -m "descricao_da_migration"
```

## Seed inicial

```bash
python -m app.seed
```

Credenciais iniciais apos o seed:

- usuario: `admin`
- senha: `admin123`
- a senha inicial deve ser trocada no primeiro login quando `SEED_ADMIN_FORCE_PASSWORD_CHANGE=true`
