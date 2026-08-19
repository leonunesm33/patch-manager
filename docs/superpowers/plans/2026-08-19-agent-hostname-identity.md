# Sincronização de Hostname e Detecção de Conflito de Identidade — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fazer o Patch Manager manter o hostname sempre atualizado no cadastro de máquinas e detectar (sem corrigir silenciosamente) colisões de identidade quando um agente clonado de um template reporta um fingerprint de hardware diferente do já registrado.

**Architecture:** Três camadas independentemente testáveis: (1) API — `MachineModel` ganha `hardware_fingerprint`/`identity_conflict_*`, `submit_agent_inventory` passa a sincronizar `name` a cada ciclo e a comparar fingerprints, um novo endpoint resolve conflitos; (2) Agentes Linux e Windows coletam um identificador de hardware por VM e o enviam no payload de inventário já existente; (3) instaladores passam a gerar `agent_id` como UUID aleatório em vez de derivar do hostname; (4) painel exibe o aviso de conflito e a ação de resolução.

**Tech Stack:** FastAPI + SQLAlchemy + Alembic + Postgres (API), Python 3 stdlib (agentes Linux/Windows), React + TypeScript (painel), Docker Compose no WSL para testes locais.

## Global Constraints

- Spec de referência: `docs/superpowers/specs/2026-08-19-agent-hostname-identity-design.md`.
- Agentes já instalados não são migrados/re-enrollados — mudanças de `agent_id` valem só para instalações novas.
- Nenhuma coluna nova é `NOT NULL`; nada exige backfill manual.
- Commits partem do WSL (regra do `CLAUDE.md` do projeto). Rebuild dos containers `api`/`web` é necessário após mudanças em `apps/api`/`apps/web` (`sudo docker compose up -d --build api web` em `infra/compose`).
- Repositório: `~/projetos/patch-manager` no WSL (acessível também via `\\wsl.localhost\Ubuntu-24.04\home\leonardo\projetos\patch-manager`).

---

### Task 1: Colunas de fingerprint e conflito de identidade em `MachineModel` + migration

**Files:**
- Modify: `apps/api/app/models/machine.py`
- Create: `apps/api/alembic/versions/20260819_0031_agent_hardware_fingerprint.py`

**Interfaces:**
- Produces: `MachineModel.hardware_fingerprint: str | None`, `MachineModel.identity_conflict_fingerprint: str | None`, `MachineModel.identity_conflict_detected_at: datetime | None` — consumidos pela Task 2 (lógica do endpoint) e pela Task 3 (endpoint de resolução).

- [ ] **Step 1: Adicionar as três colunas ao modelo**

Conteúdo atual de `apps/api/app/models/machine.py` (26 linhas) — substituir pelo conteúdo completo abaixo:

```python
from datetime import datetime

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class MachineModel(Base):
    __tablename__ = "machines"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), index=True)
    ip: Mapped[str] = mapped_column(String(45))
    platform: Mapped[str] = mapped_column(String(50))
    environment: Mapped[str] = mapped_column(String(32), default="production", nullable=False)
    group: Mapped[str] = mapped_column("group_name", String(120), index=True)
    status: Mapped[str] = mapped_column(String(30))
    pending_patches: Mapped[int] = mapped_column(Integer, default=0)
    last_check_in: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    risk: Mapped[str] = mapped_column(String(30))
    hardware_fingerprint: Mapped[str | None] = mapped_column(String(255), nullable=True)
    identity_conflict_fingerprint: Mapped[str | None] = mapped_column(String(255), nullable=True)
    identity_conflict_detected_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
```

- [ ] **Step 2: Criar a migration**

Criar `apps/api/alembic/versions/20260819_0031_agent_hardware_fingerprint.py`:

```python
"""add hardware fingerprint and identity conflict columns to machines

Servidores nascem de templates com hostname provisorio e sao renomeados
durante o provisionamento. Se o agente for instalado (enrollado) antes do
hostname final, o agent_id derivado do hostname pode colidir entre clones.
Estas colunas permitem detectar essa colisao via um fingerprint de hardware
enviado pelo agente a cada inventario, sem corrigir silenciosamente.

Revision ID: 20260819_0031
Revises: 20260714_0030
Create Date: 2026-08-19 00:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260819_0031"
down_revision = "20260714_0030"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("machines", sa.Column("hardware_fingerprint", sa.String(255), nullable=True))
    op.add_column(
        "machines", sa.Column("identity_conflict_fingerprint", sa.String(255), nullable=True)
    )
    op.add_column(
        "machines",
        sa.Column("identity_conflict_detected_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("machines", "identity_conflict_detected_at")
    op.drop_column("machines", "identity_conflict_fingerprint")
    op.drop_column("machines", "hardware_fingerprint")
```

- [ ] **Step 3: Rodar a migration no ambiente de testes (Docker Compose no WSL) e verificar as colunas**

Run:
```bash
wsl -e bash -c "cd ~/projetos/patch-manager/infra/compose && sudo docker compose up -d --build api"
```
Expected: build conclui sem erro; o log do container `api` mostra `alembic upgrade head` rodando a nova revisão `20260819_0031` (verificar com `sudo docker compose logs --tail=50 api`).

Run:
```bash
wsl -e bash -c "cd ~/projetos/patch-manager/infra/compose && sudo docker compose exec db psql -U patchmanager -d patchmanager -c '\d machines'"
```
Expected: saída lista `hardware_fingerprint`, `identity_conflict_fingerprint` e `identity_conflict_detected_at` como colunas nullable da tabela `machines`.

- [ ] **Step 4: Commit**

```bash
wsl -e bash -c "cd ~/projetos/patch-manager && git add apps/api/app/models/machine.py apps/api/alembic/versions/20260819_0031_agent_hardware_fingerprint.py && git commit -m 'feat(api): add hardware fingerprint and identity conflict columns to machines'"
```

---

### Task 2: Sincronizar hostname e detectar conflito de fingerprint em `submit_agent_inventory`

**Files:**
- Modify: `apps/api/app/schemas/agent.py:37-55` (`AgentInventoryRequest`)
- Modify: `apps/api/app/schemas/machine.py:8-24` (`Machine`)
- Modify: `apps/api/app/api/v1/agents.py:1-30` (imports/logger) e `apps/api/app/api/v1/agents.py:1419-1443` (`submit_agent_inventory`)
- Create: `apps/api/requirements-dev.txt`
- Create: `apps/api/app/tests/__init__.py`
- Create: `apps/api/app/tests/conftest.py`
- Create: `apps/api/app/tests/test_agents_inventory.py`

**Interfaces:**
- Consumes: `MachineModel.hardware_fingerprint`/`identity_conflict_fingerprint`/`identity_conflict_detected_at` (Task 1).
- Produces: `AgentInventoryRequest.hardware_fingerprint: str | None`; `Machine.hardware_fingerprint/identity_conflict_fingerprint/identity_conflict_detected_at`; `conftest.py` fixtures `db_session` e `client` reutilizados pela Task 3.

Não existe infraestrutura de teste no `apps/api` hoje (`apps/api/app/tests/` está vazio, sem `conftest.py`, sem `pytest`/`httpx` em `requirements.txt`). Este task cria essa infraestrutura pela primeira vez, usando SQLite em memória (via `Base.metadata.create_all`, sem depender do Alembic) e overrides de dependências do FastAPI — não requer o Postgres do Docker Compose para rodar.

- [ ] **Step 1: Criar `requirements-dev.txt`**

```
-r requirements.txt
pytest==8.3.3
httpx==0.27.2
```

- [ ] **Step 2: Instalar as dependências de teste no venv local**

Run:
```bash
wsl -e bash -c "cd ~/projetos/patch-manager/apps/api && source .venv/bin/activate && pip install -r requirements-dev.txt"
```
Expected: instala `pytest` e `httpx` sem erro (se o `.venv` ainda não existir, criar antes com `python3 -m venv .venv`).

- [ ] **Step 3: Criar `apps/api/app/tests/__init__.py`** (vazio, só para consistência de pacote)

```python
```

- [ ] **Step 4: Criar `apps/api/app/tests/conftest.py`**

```python
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_agent_identity, get_db
from app.core.database import Base
from app.main import app
from app.models.agent_credential import AgentCredentialModel

TEST_AGENT_ID = "linux-test-01"


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    testing_session_local = sessionmaker(
        bind=engine, autoflush=False, autocommit=False, expire_on_commit=False
    )
    session = testing_session_local()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture()
def client(db_session):
    def override_get_db():
        yield db_session

    def override_get_agent_identity():
        return AgentCredentialModel(
            agent_id=TEST_AGENT_ID,
            platform="linux",
            description="test agent",
            key_hash="unused-in-tests",
            is_active=True,
        )

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_agent_identity] = override_get_agent_identity
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
```

- [ ] **Step 5: Escrever os testes que falham (ainda sem a implementação)**

Criar `apps/api/app/tests/test_agents_inventory.py`:

```python
from app.tests.conftest import TEST_AGENT_ID


def _base_payload(**overrides):
    payload = {
        "agent_id": TEST_AGENT_ID,
        "platform": "linux",
        "hostname": "tpl-provisorio-01",
        "primary_ip": "10.0.0.5",
        "package_manager": "apt",
        "installed_packages": 100,
        "upgradable_packages": 0,
        "reboot_required": False,
        "os_name": "Linux",
        "os_version": "1",
        "kernel_version": "6.8.0",
        "agent_version": "0.2.0",
        "execution_mode": "dry-run",
    }
    payload.update(overrides)
    return payload


def _post_inventory(client, **overrides):
    return client.post("/api/v1/agents/inventory", json=_base_payload(**overrides))


def _get_machine(db_session):
    from app.models.machine import MachineModel

    return db_session.get(MachineModel, f"agent-{TEST_AGENT_ID}")


def test_creates_machine_with_hostname_and_fingerprint(client, db_session):
    response = _post_inventory(client, hardware_fingerprint="uuid-aaa")
    assert response.status_code == 200

    machine = _get_machine(db_session)
    assert machine.name == "tpl-provisorio-01"
    assert machine.hardware_fingerprint == "uuid-aaa"
    assert machine.identity_conflict_fingerprint is None
    assert machine.identity_conflict_detected_at is None


def test_hostname_rename_updates_name_without_conflict(client, db_session):
    _post_inventory(client, hostname="tpl-provisorio-01", hardware_fingerprint="uuid-aaa")

    _post_inventory(client, hostname="srv-web-03", hardware_fingerprint="uuid-aaa")

    machine = _get_machine(db_session)
    assert machine.name == "srv-web-03"
    assert machine.identity_conflict_fingerprint is None
    assert machine.identity_conflict_detected_at is None


def test_different_fingerprint_flags_conflict_but_still_updates_name(client, db_session):
    _post_inventory(client, hostname="srv-web-03", hardware_fingerprint="uuid-aaa")

    _post_inventory(client, hostname="srv-web-03-clone", hardware_fingerprint="uuid-bbb")

    machine = _get_machine(db_session)
    assert machine.name == "srv-web-03-clone"
    assert machine.hardware_fingerprint == "uuid-aaa"
    assert machine.identity_conflict_fingerprint == "uuid-bbb"
    assert machine.identity_conflict_detected_at is not None


def test_backfills_fingerprint_when_machine_had_none(client, db_session):
    _post_inventory(client, hostname="srv-legado-01")

    machine = _get_machine(db_session)
    assert machine.hardware_fingerprint is None

    _post_inventory(client, hostname="srv-legado-01", hardware_fingerprint="uuid-ccc")

    machine = _get_machine(db_session)
    assert machine.hardware_fingerprint == "uuid-ccc"
    assert machine.identity_conflict_fingerprint is None


def test_missing_fingerprint_never_triggers_conflict(client, db_session):
    _post_inventory(client, hostname="srv-antigo-01", hardware_fingerprint="uuid-ddd")

    _post_inventory(client, hostname="srv-antigo-01")

    machine = _get_machine(db_session)
    assert machine.hardware_fingerprint == "uuid-ddd"
    assert machine.identity_conflict_fingerprint is None


def test_repeat_report_same_hostname_and_fingerprint_is_noop(client, db_session):
    _post_inventory(client, hostname="srv-estavel-01", hardware_fingerprint="uuid-eee")

    _post_inventory(client, hostname="srv-estavel-01", hardware_fingerprint="uuid-eee")

    machine = _get_machine(db_session)
    assert machine.name == "srv-estavel-01"
    assert machine.hardware_fingerprint == "uuid-eee"
    assert machine.identity_conflict_fingerprint is None
    assert machine.identity_conflict_detected_at is None
```

- [ ] **Step 6: Rodar os testes e confirmar que falham**

Run:
```bash
wsl -e bash -c "cd ~/projetos/patch-manager/apps/api && source .venv/bin/activate && python -m pytest app/tests/test_agents_inventory.py -v"
```
Expected: FAIL nos testes 2, 3 e 4 (o `name` não é atualizado e não há lógica de conflito ainda) — porque `AgentInventoryRequest` ainda não aceita `hardware_fingerprint` (o campo extra é ignorado silenciosamente pelo Pydantic, então nenhuma `AttributeError` ocorre, mas os asserts de `hardware_fingerprint`/`identity_conflict_*` falham). O teste 1 e o teste 5 podem passar mesmo antes da implementação — o objetivo aqui é confirmar que os testes 2, 3 e 4 falham pela razão certa (name não atualiza / conflito não é detectado).

- [ ] **Step 7: Adicionar `hardware_fingerprint` ao schema de request**

Em `apps/api/app/schemas/agent.py`, na classe `AgentInventoryRequest` (linhas 37-55), adicionar o campo após `primary_ip`:

```python
class AgentInventoryRequest(BaseModel):
    agent_id: str
    platform: str
    hostname: str
    primary_ip: str
    hardware_fingerprint: str | None = None
    package_manager: str
    installed_packages: int
    upgradable_packages: int
    reboot_required: bool
    installed_update_count: int | None = None
    pending_update_summary: str | None = None
    windows_update_source: str | None = None
    os_name: str
    os_version: str
    kernel_version: str
    agent_version: str
    execution_mode: str
    pending_updates: list[AgentInventoryEntryPayload] = []
    installed_updates: list[AgentInventoryEntryPayload] = []
```

- [ ] **Step 8: Expor os campos novos no schema de resposta `Machine`**

Em `apps/api/app/schemas/machine.py`, na classe `Machine` (linhas 8-24), adicionar os três campos:

```python
class Machine(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    ip: str
    platform: str
    environment: str
    group: str
    status: str
    pending_patches: int
    last_check_in: datetime
    risk: str
    hardware_fingerprint: str | None = None
    identity_conflict_fingerprint: str | None = None
    identity_conflict_detected_at: datetime | None = None
    post_patch_state: str | None = None
    post_patch_message: str | None = None
    last_apply_at: datetime | None = None
    reboot_scheduled_at: datetime | None = None
```

- [ ] **Step 9: Adicionar logger ao topo de `agents.py`**

Em `apps/api/app/api/v1/agents.py`, primeira linha do arquivo, adicionar antes do `from hashlib import sha1` existente:

```python
import logging
from hashlib import sha1
import json
import secrets
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Annotated
```

Localizar as duas linhas finais do bloco de imports do arquivo:

```python
from app.services.settings_service import SettingsService
router = APIRouter()
```

E substituir por:

```python
from app.services.settings_service import SettingsService

logger = logging.getLogger(__name__)
router = APIRouter()
```

- [ ] **Step 10: Corrigir a sincronização de hostname e adicionar a lógica de fingerprint**

Em `apps/api/app/api/v1/agents.py`, localizar o bloco `if machine is None: ... else: ...` (linhas 1419-1443 no arquivo atual) e substituir por:

```python
    if machine is None:
        machine_repository.add(
            MachineModel(
                id=managed_machine_id,
                name=payload.hostname,
                ip=payload.primary_ip,
                platform="Ubuntu" if payload.platform.lower() == "linux" else payload.platform.title(),
                environment="production",
                group="Agent Managed",
                status="online",
                pending_patches=payload.upgradable_packages,
                last_check_in=datetime.now(UTC),
                risk=risk,
                hardware_fingerprint=payload.hardware_fingerprint,
            )
        )
    else:
        machine.name = payload.hostname
        machine.ip = payload.primary_ip
        machine.platform = "Ubuntu" if payload.platform.lower() == "linux" else payload.platform.title()
        machine.environment = machine.environment or "production"
        machine.group = "Agent Managed"
        machine.status = "online"
        machine.pending_patches = payload.upgradable_packages
        machine.last_check_in = datetime.now(UTC)
        machine.risk = risk
        if payload.hardware_fingerprint:
            if machine.hardware_fingerprint is None:
                machine.hardware_fingerprint = payload.hardware_fingerprint
            elif machine.hardware_fingerprint != payload.hardware_fingerprint:
                machine.identity_conflict_fingerprint = payload.hardware_fingerprint
                machine.identity_conflict_detected_at = datetime.now(UTC)
                logger.warning(
                    "Identity conflict detected for machine %s: expected fingerprint %s, saw %s",
                    managed_machine_id,
                    machine.hardware_fingerprint,
                    payload.hardware_fingerprint,
                )
        machine_repository.update(machine)
```

- [ ] **Step 11: Rodar os testes de novo e confirmar que passam**

Run:
```bash
wsl -e bash -c "cd ~/projetos/patch-manager/apps/api && source .venv/bin/activate && python -m pytest app/tests/test_agents_inventory.py -v"
```
Expected: 6 passed.

- [ ] **Step 12: Commit**

```bash
wsl -e bash -c "cd ~/projetos/patch-manager && git add apps/api/requirements-dev.txt apps/api/app/tests apps/api/app/schemas/agent.py apps/api/app/schemas/machine.py apps/api/app/api/v1/agents.py && git commit -m 'feat(api): sync hostname every inventory cycle and detect hardware fingerprint conflicts'"
```

---

### Task 3: Endpoint de resolução de conflito de identidade

**Files:**
- Modify: `apps/api/app/api/v1/machines.py`
- Create: `apps/api/app/tests/test_machines_identity_conflict.py`

**Interfaces:**
- Consumes: `MachineModel.identity_conflict_fingerprint`/`identity_conflict_detected_at` (Task 1); fixtures `db_session`/`client` de `apps/api/app/tests/conftest.py` (Task 2).
- Produces: `POST /api/v1/machines/{machine_id}/resolve-identity-conflict` → `Machine` (mesmo schema de resposta usado pelos demais endpoints de `machines.py`).

- [ ] **Step 1: Escrever o teste que falha**

Criar `apps/api/app/tests/test_machines_identity_conflict.py`:

```python
from datetime import UTC, datetime

from app.api.deps import require_operator
from app.main import app
from app.models.machine import MachineModel


def _seed_machine_with_conflict(db_session) -> MachineModel:
    machine = MachineModel(
        id="agent-linux-clone-01",
        name="srv-clonado-01",
        ip="10.0.0.9",
        platform="Ubuntu",
        environment="production",
        group="Agent Managed",
        status="online",
        pending_patches=0,
        last_check_in=datetime.now(UTC),
        risk="optional",
        hardware_fingerprint="uuid-original",
        identity_conflict_fingerprint="uuid-conflitante",
        identity_conflict_detected_at=datetime.now(UTC),
    )
    db_session.add(machine)
    db_session.commit()
    return machine


def test_resolve_identity_conflict_accepts_latest_fingerprint_as_baseline(client, db_session):
    _seed_machine_with_conflict(db_session)
    app.dependency_overrides[require_operator] = lambda: None

    response = client.post("/api/v1/machines/agent-linux-clone-01/resolve-identity-conflict")

    assert response.status_code == 200
    body = response.json()
    assert body["hardware_fingerprint"] == "uuid-conflitante"
    assert body["identity_conflict_fingerprint"] is None
    assert body["identity_conflict_detected_at"] is None

    del app.dependency_overrides[require_operator]


def test_resolve_identity_conflict_404_when_machine_missing(client):
    app.dependency_overrides[require_operator] = lambda: None

    response = client.post("/api/v1/machines/does-not-exist/resolve-identity-conflict")

    assert response.status_code == 404

    del app.dependency_overrides[require_operator]
```

- [ ] **Step 2: Rodar e confirmar que falha**

Run:
```bash
wsl -e bash -c "cd ~/projetos/patch-manager/apps/api && source .venv/bin/activate && python -m pytest app/tests/test_machines_identity_conflict.py -v"
```
Expected: FAIL com `404 Not Found` (rota ainda não existe) nos dois testes.

- [ ] **Step 3: Implementar o endpoint**

Em `apps/api/app/api/v1/machines.py`, adicionar logo após a função `update_machine` (a que termina em `return Machine.model_validate(machine)`, antes do `@router.delete("/{machine_id}"...)`):

```python
@router.post("/{machine_id}/resolve-identity-conflict", response_model=Machine)
def resolve_machine_identity_conflict(
    machine_id: str,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[UserResponse, Depends(require_operator)],
) -> Machine:
    repository = MachineRepository(db)
    machine = repository.get_by_id(machine_id)
    if machine is None:
        raise HTTPException(status_code=404, detail="Machine not found")

    if machine.identity_conflict_fingerprint is not None:
        machine.hardware_fingerprint = machine.identity_conflict_fingerprint
    machine.identity_conflict_fingerprint = None
    machine.identity_conflict_detected_at = None

    machine = repository.update(machine)
    return Machine.model_validate(machine)
```

- [ ] **Step 4: Rodar de novo e confirmar que passa**

Run:
```bash
wsl -e bash -c "cd ~/projetos/patch-manager/apps/api && source .venv/bin/activate && python -m pytest app/tests/ -v"
```
Expected: todos os 8 testes (6 de `test_agents_inventory.py` + 2 novos) passam.

- [ ] **Step 5: Commit**

```bash
wsl -e bash -c "cd ~/projetos/patch-manager && git add apps/api/app/api/v1/machines.py apps/api/app/tests/test_machines_identity_conflict.py && git commit -m 'feat(api): add endpoint to resolve machine identity conflicts'"
```

---

### Task 4: Coleta de fingerprint de hardware no agente Linux

**Files:**
- Modify: `apps/agent-linux/agent/inventory.py`
- Modify: `apps/agent-linux/deploy/install-linux-agent-guided.sh` (sudoers)
- Modify: `apps/api/app/api/v1/agents.py` (bloco sudoers do instalador Linux gerado pela API, linhas ~326-330)
- Create: `apps/agent-linux/agent/tests/test_inventory_fingerprint.py`

**Interfaces:**
- Produces: chave `"hardware_fingerprint"` no dict retornado por `collect_inventory()` — consumida automaticamente por `send_inventory()` em `main.py` via `**inventory` (nenhuma mudança necessária em `main.py`).

O usuário `patchmanager` (não-root) roda o agente; `/sys/class/dmi/id/product_uuid` só é legível por root na maioria das distros. Por isso a leitura é feita via `sudo cat`, e é necessário liberar esse comando específico no sudoers — mesmo padrão já usado para `shutdown`/`apt-get`.

- [ ] **Step 1: Escrever o teste que falha**

Criar `apps/agent-linux/agent/tests/__init__.py` (vazio):

```python
```

Criar `apps/agent-linux/agent/tests/test_inventory_fingerprint.py`:

```python
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from inventory import _collect_hardware_fingerprint  # noqa: E402


def test_override_env_var_takes_precedence(monkeypatch):
    monkeypatch.setenv("PATCH_MANAGER_FINGERPRINT_OVERRIDE", "forced-uuid-123")
    assert _collect_hardware_fingerprint() == "forced-uuid-123"


def test_returns_none_when_no_override_and_sudo_fails(monkeypatch):
    monkeypatch.delenv("PATCH_MANAGER_FINGERPRINT_OVERRIDE", raising=False)
    monkeypatch.setattr("inventory._run", lambda *args, **kwargs: "")
    assert _collect_hardware_fingerprint() is None
```

- [ ] **Step 2: Rodar e confirmar que falha**

Run:
```bash
wsl -e bash -c "cd ~/projetos/patch-manager/apps/agent-linux/agent && python3 -m pytest tests/test_inventory_fingerprint.py -v"
```
Expected: FAIL com `ImportError: cannot import name '_collect_hardware_fingerprint'`.

- [ ] **Step 3: Implementar a coleta**

Em `apps/agent-linux/agent/inventory.py`, adicionar `import os` já existe; adicionar a função abaixo logo após a definição de `_count_lines` (antes do comentário `# PackageKit/Cockpit priority`):

```python
def _collect_hardware_fingerprint() -> str | None:
    override = os.getenv("PATCH_MANAGER_FINGERPRINT_OVERRIDE", "").strip()
    if override:
        return override
    output = _run(["sudo", "cat", "/sys/class/dmi/id/product_uuid"])
    return output.strip() or None
```

E em `collect_inventory()` (final da função), adicionar a chave ao dict retornado:

```python
    return {
        "hostname": hostname,
        "primary_ip": primary_ip,
        "hardware_fingerprint": _collect_hardware_fingerprint(),
        "package_manager": package_manager,
        "installed_packages": installed_packages,
        "upgradable_packages": upgradable_packages,
        "reboot_required": reboot_required,
        "installed_update_count": len(installed_updates),
        "pending_update_summary": "; ".join(item["title"] for item in pending_updates[:3]),
        "pending_updates": pending_updates,
        "installed_updates": installed_updates,
        "os_name": platform.system(),
        "os_version": platform.version(),
        "kernel_version": platform.release(),
        "agent_version": agent_version,
        "execution_mode": execution_mode,
    }
```

- [ ] **Step 4: Rodar de novo e confirmar que passa**

Run:
```bash
wsl -e bash -c "cd ~/projetos/patch-manager/apps/agent-linux/agent && python3 -m pytest tests/test_inventory_fingerprint.py -v"
```
Expected: 2 passed.

- [ ] **Step 5: Liberar a leitura do UUID via sudoers no instalador guiado**

Confirmado: `install-linux-agent-guided.sh` (161 linhas) não escreve nenhum arquivo em `/etc/sudoers.d/` hoje — só o instalador gerado pela API faz isso. Adicionar um bloco novo, restrito só à permissão necessária para este recurso (não replicar `shutdown`/`apt-get` aqui, já que este script nunca concedeu isso e não é parte do escopo desta mudança). Inserir logo após o bloco `sudo chown -R patchmanager:patchmanager "${INSTALL_ROOT}" /var/log/patch-manager` (linha 152) e antes de `sudo systemctl daemon-reload` (linha 153):

```bash
sudo chown -R patchmanager:patchmanager "${INSTALL_ROOT}" /var/log/patch-manager

sudo tee /etc/sudoers.d/patch-manager-fingerprint > /dev/null <<'SUDOERS_EOF'
patchmanager ALL=(root) NOPASSWD: /bin/cat /sys/class/dmi/id/product_uuid
SUDOERS_EOF
sudo chmod 440 /etc/sudoers.d/patch-manager-fingerprint

sudo systemctl daemon-reload
```

- [ ] **Step 6: Liberar a mesma permissão no instalador gerado pela API**

Em `apps/api/app/api/v1/agents.py`, no bloco do instalador Linux gerado dinamicamente (por volta da linha 326-330 mostrada na investigação), alterar:

```python
sudo tee /etc/sudoers.d/patch-manager > /dev/null <<'SUDOERS_EOF'
patchmanager ALL=(root) NOPASSWD: /usr/sbin/shutdown
patchmanager ALL=(root) NOPASSWD: /usr/bin/apt-get
patchmanager ALL=(root) NOPASSWD: /bin/cat /sys/class/dmi/id/product_uuid
SUDOERS_EOF
sudo chmod 440 /etc/sudoers.d/patch-manager
```

- [ ] **Step 7: Commit**

```bash
wsl -e bash -c "cd ~/projetos/patch-manager && git add apps/agent-linux/agent/inventory.py apps/agent-linux/agent/tests apps/agent-linux/deploy/install-linux-agent-guided.sh apps/api/app/api/v1/agents.py && git commit -m 'feat(agent-linux): collect hardware fingerprint via sudo-gated sysfs read'"
```

---

### Task 5: Coleta de fingerprint de hardware no agente Windows

**Files:**
- Modify: `apps/agent-windows/agent/inventory.py`
- Create: `apps/agent-windows/agent/tests/test_inventory_fingerprint.py`

**Interfaces:**
- Produces: chave `"hardware_fingerprint"` no dict retornado por `collect_inventory()` — consumida automaticamente por `send_inventory()` em `main.py` via `**inventory` (nenhuma mudança necessária em `main.py`).

O serviço Windows do agente roda como LocalSystem (instalado via `sc.exe`/`install`), que já tem acesso total a WMI/CIM — não há necessidade de nenhuma permissão extra, diferente do Linux.

- [ ] **Step 1: Escrever o teste que falha**

Criar `apps/agent-windows/agent/tests/__init__.py` (vazio):

```python
```

Criar `apps/agent-windows/agent/tests/test_inventory_fingerprint.py`:

```python
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from inventory import _collect_hardware_fingerprint  # noqa: E402


def test_override_env_var_takes_precedence(monkeypatch):
    monkeypatch.setenv("PATCH_MANAGER_FINGERPRINT_OVERRIDE", "forced-uuid-456")
    assert _collect_hardware_fingerprint() == "forced-uuid-456"


def test_returns_none_when_no_override_and_powershell_fails(monkeypatch):
    monkeypatch.delenv("PATCH_MANAGER_FINGERPRINT_OVERRIDE", raising=False)
    monkeypatch.setattr("inventory._run_powershell_json", lambda script: None)
    assert _collect_hardware_fingerprint() is None
```

- [ ] **Step 2: Rodar e confirmar que falha**

Run:
```powershell
cd apps\agent-windows\agent
python -m pytest tests\test_inventory_fingerprint.py -v
```
Expected: FAIL com `ImportError: cannot import name '_collect_hardware_fingerprint'`.

- [ ] **Step 3: Implementar a coleta**

Em `apps/agent-windows/agent/inventory.py`, adicionar `import os` ao topo (junto com os imports existentes `json`, `platform`, `socket`, `subprocess`):

```python
import json
import os
import platform
import socket
import subprocess
```

Adicionar a função abaixo logo após `_run_powershell_json` (antes de `_collect_windows_update_metrics`):

```python
def _collect_hardware_fingerprint() -> str | None:
    override = os.getenv("PATCH_MANAGER_FINGERPRINT_OVERRIDE", "").strip()
    if override:
        return override
    data = _run_powershell_json(
        "Get-CimInstance Win32_ComputerSystemProduct | "
        "Select-Object @{Name='uuid';Expression={$_.UUID}} | ConvertTo-Json -Compress"
    )
    if data is None:
        return None
    value = data.get("uuid")
    return str(value).strip() or None if value else None
```

E em `collect_inventory()` (final da função), adicionar a chave ao dict retornado:

```python
    return {
        "hostname": hostname,
        "primary_ip": primary_ip,
        "hardware_fingerprint": _collect_hardware_fingerprint(),
        "package_manager": "windows-update",
        "installed_packages": windows_metrics["installed_update_count"],
        "upgradable_packages": windows_metrics["upgradable_packages"],
        "reboot_required": windows_metrics["reboot_required"],
        "installed_update_count": windows_metrics["installed_update_count"],
        "pending_update_summary": windows_metrics["pending_update_summary"],
        "windows_update_source": windows_metrics["windows_update_source"],
        "pending_updates": windows_metrics["pending_updates"],
        "installed_updates": windows_metrics["installed_updates"],
        "os_name": platform.system(),
        "os_version": platform.version(),
        "kernel_version": platform.release(),
        "agent_version": agent_version,
        "execution_mode": execution_mode,
    }
```

- [ ] **Step 4: Rodar de novo e confirmar que passa**

Run:
```powershell
cd apps\agent-windows\agent
python -m pytest tests\test_inventory_fingerprint.py -v
```
Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
wsl -e bash -c "cd ~/projetos/patch-manager && git add apps/agent-windows/agent/inventory.py apps/agent-windows/agent/tests && git commit -m 'feat(agent-windows): collect hardware fingerprint via WMI ComputerSystemProduct UUID'"
```

---

### Task 6: `agent_id` gerado como UUID aleatório em vez de derivado do hostname

**Files:**
- Modify: `apps/agent-linux/deploy/install-linux-agent-guided.sh:112-116`
- Modify: `apps/api/app/api/v1/agents.py:283-285` (gerador do instalador Linux)
- Modify: `apps/api/app/api/v1/agents.py:481` (gerador do instalador Windows)

**Interfaces:**
- Nenhuma mudança de interface — o formato de `agent_id` (`linux-<algo>` / `windows-<algo>`) e o mecanismo de override (`--agent-id` no script guiado) são preservados; só a fonte do `<algo>` muda de hostname para UUID.

Este task não tem teste automatizado próprio (é geração de texto de shell/PowerShell) — a verificação é executar os scripts gerados e confirmar que o `agent_id` produzido é um UUID e que o enroll continua funcionando (Step 4).

- [ ] **Step 1: Script guiado Linux**

Em `apps/agent-linux/deploy/install-linux-agent-guided.sh`, substituir (linhas 112-116):

```bash
if [[ -z "${AGENT_ID}" ]]; then
  AGENT_ID="linux-$(cat /proc/sys/kernel/random/uuid 2>/dev/null || uuidgen)"
fi
```

(Mantém o comportamento de permitir `--agent-id` explícito, já garantido pelo `if [[ -z "${AGENT_ID}" ]]` existente — só troca a fonte do valor default de hostname para UUID.)

- [ ] **Step 2: Instalador Linux gerado pela API**

Em `apps/api/app/api/v1/agents.py`, no texto do script gerado (por volta da linha 283-285), substituir:

```python
HOSTNAME_VALUE="$(hostname -s 2>/dev/null || hostname)"
AGENT_ID="linux-$(cat /proc/sys/kernel/random/uuid 2>/dev/null || uuidgen)"
```

(Remove a dependência do hostname; `HOSTNAME_VALUE` deixa de ser necessária — remover a linha, não deixar variável não usada.)

- [ ] **Step 3: Instalador Windows gerado pela API**

Em `apps/api/app/api/v1/agents.py`, no texto do script gerado (linha 481), substituir:

```powershell
$AgentId = "windows-$([guid]::NewGuid().ToString('N'))"
```

- [ ] **Step 4: Validar manualmente que os scripts gerados continuam funcionando**

Run (no ambiente de teste do WSL, contra a central local subida pelo Docker Compose):
```bash
wsl -e bash -c "curl -k -s https://localhost/api/v1/agents/install/linux.sh?server_url=https%3A%2F%2Flocalhost -o /tmp/linux-install-test.sh && grep -A1 'AGENT_ID=' /tmp/linux-install-test.sh"
```
Expected: a linha `AGENT_ID="linux-$(...)"` aparece com a nova lógica baseada em UUID, sem referência a `HOSTNAME_VALUE`.

- [ ] **Step 5: Commit**

```bash
wsl -e bash -c "cd ~/projetos/patch-manager && git add apps/agent-linux/deploy/install-linux-agent-guided.sh apps/api/app/api/v1/agents.py && git commit -m 'feat(agents): generate agent_id as random UUID instead of hostname-derived to avoid template clone collisions'"
```

---

### Task 7: Painel — aviso de conflito de identidade e ação de resolução

**Files:**
- Modify: `apps/web/src/features/machines/types.ts:1-16`
- Modify: `apps/web/src/features/machines/api.ts`
- Modify: `apps/web/src/features/machines/pages/machines-page.tsx`

**Interfaces:**
- Consumes: `Machine.hardware_fingerprint`/`identity_conflict_fingerprint`/`identity_conflict_detected_at` (já expostos pela API na Task 2); `POST /machines/{id}/resolve-identity-conflict` (Task 3).
- Produces: `resolveIdentityConflict(machineId: string): Promise<Machine>` em `api.ts`, consumido pelo handler novo em `machines-page.tsx`.

Sem teste automatizado de frontend (o projeto não tem suíte de testes de componentes hoje) — a verificação é visual, via `npm run build` + inspeção manual no navegador contra a central local.

- [ ] **Step 1: Adicionar os campos ao tipo `Machine`**

Em `apps/web/src/features/machines/types.ts`, substituir o tipo `Machine` (linhas 1-16):

```typescript
export type Machine = {
  id: string;
  name: string;
  ip: string;
  platform: string;
  environment: string;
  group: string;
  status: "online" | "warning" | "offline";
  pending_patches: number;
  last_check_in: string;
  risk: "critical" | "important" | "optional";
  hardware_fingerprint: string | null;
  identity_conflict_fingerprint: string | null;
  identity_conflict_detected_at: string | null;
  post_patch_state: string | null;
  post_patch_message: string | null;
  last_apply_at: string | null;
  reboot_scheduled_at: string | null;
};
```

- [ ] **Step 2: Adicionar a função de API**

Em `apps/web/src/features/machines/api.ts`, adicionar após `updateMachine`:

```typescript
export function resolveIdentityConflict(machineId: string) {
  return http<Machine>(`/machines/${machineId}/resolve-identity-conflict`, {
    method: "POST",
  });
}
```

- [ ] **Step 3: Importar a nova função e o tipo de aviso na página de máquinas**

Em `apps/web/src/features/machines/pages/machines-page.tsx`, no bloco de imports (linhas 1-28), adicionar `resolveIdentityConflict` ao import existente de `@/features/machines/api`:

```typescript
import {
  createMachine,
  createMachineGroup,
  deleteMachine,
  deleteMachineGroup,
  fetchMachineGroups,
  fetchMachineOperationalDetails,
  fetchMachines,
  resolveIdentityConflict,
  updateMachine,
} from "@/features/machines/api";
```

- [ ] **Step 4: Adicionar o handler de resolução**

Em `apps/web/src/features/machines/pages/machines-page.tsx`, logo após a função `handleUpgradeAgent` (que usa o padrão de `upgradeFeedback` + `setTimeout`), adicionar:

```typescript
  async function handleResolveIdentityConflict(machine: Machine) {
    try {
      const updated = await resolveIdentityConflict(machine.id);
      setMachines((current) => current.map((item) => (item.id === updated.id ? updated : item)));
      setUpgradeFeedback(`Conflito de identidade resolvido para ${machine.name}.`);
      setTimeout(() => setUpgradeFeedback(null), 6000);
    } catch (err) {
      setUpgradeFeedback(
        err instanceof Error ? err.message : "Falha ao resolver conflito de identidade.",
      );
      setTimeout(() => setUpgradeFeedback(null), 6000);
    }
  }
```

- [ ] **Step 5: Exibir o aviso na tabela e adicionar a ação no menu**

Em `apps/web/src/features/machines/pages/machines-page.tsx`, na célula do nome da máquina (linha 788: `<td style={{ fontWeight: 700 }}>{machine.name}</td>`), substituir por:

```typescript
                <td style={{ fontWeight: 700 }}>
                  {machine.name}
                  {machine.identity_conflict_detected_at ? (
                    <span
                      title={`Fingerprint esperado: ${machine.hardware_fingerprint ?? "?"} | visto: ${machine.identity_conflict_fingerprint ?? "?"} em ${formatDateTimeSaoPaulo(machine.identity_conflict_detected_at)}`}
                      style={{ marginLeft: 6 }}
                    >
                      <StatusBadge variant="error">conflito de identidade</StatusBadge>
                    </span>
                  ) : null}
                </td>
```

E no array `items` do `ActionMenu` dessa mesma linha (após o item `"Atualizar agente"`, antes de `"Editar"`), adicionar:

```typescript
                      {
                        label: "Resolver conflito de identidade",
                        disabled: !machine.identity_conflict_detected_at,
                        onSelect: () => void handleResolveIdentityConflict(machine),
                      },
```

- [ ] **Step 6: Build e verificação manual**

Run:
```bash
wsl -e bash -c "cd ~/projetos/patch-manager/apps/web && npm run build"
```
Expected: build conclui sem erros de TypeScript.

Run:
```bash
wsl -e bash -c "cd ~/projetos/patch-manager/infra/compose && sudo docker compose up -d --build web"
```
Abrir `https://localhost/machines` no navegador, confirmar que a tabela carrega normalmente (sem badge de conflito, já que nenhuma máquina real tem conflito ainda nesse ambiente).

- [ ] **Step 7: Commit**

```bash
wsl -e bash -c "cd ~/projetos/patch-manager && git add apps/web/src/features/machines/types.ts apps/web/src/features/machines/api.ts apps/web/src/features/machines/pages/machines-page.tsx && git commit -m 'feat(web): show identity conflict warning and resolution action on machines list'"
```
