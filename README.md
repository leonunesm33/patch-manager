# Patch Manager

Base inicial de uma solucao de Patch Manager para Linux e Windows.

## Estrutura

- `apps/web`: frontend React + Vite + TypeScript
- `apps/api`: backend FastAPI mockado
- `apps/agent-linux`: estrutura inicial do agente Linux
- `apps/agent-windows`: estrutura inicial do agente Windows
- `infra/compose`: infraestrutura local com PostgreSQL e Redis
- `docs`: documentacao de apoio

## Como comecar

### Frontend

```bash
cd apps/web
npm install
npm run dev
```

### Backend

```bash
cd apps/api
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Infra

```bash
docker compose -f infra/compose/docker-compose.yml up -d
```
