import { useEffect, useRef, useState } from "react";
import {
  createMachine,
  createMachineGroup,
  deleteMachine,
  deleteMachineGroup,
  fetchMachineGroups,
  fetchMachineOperationalDetails,
  fetchMachines,
  forceReidentifyConnectedAgent,
  resolveIdentityConflict,
  updateMachine,
} from "@/features/machines/api";
import { ActionMenu } from "@/components/common/action-menu";
import { ConfirmModal } from "@/components/common/confirm-modal";
import { InfoHint } from "@/components/common/info-hint";
import {
  requestConnectedAgentUpgrade,
  requestConnectedAgentsBatchUpgrade,
} from "@/features/settings/api";
import { MachineOperationalDetailsPanel } from "@/features/machines/components/machine-operational-details-panel";
import type {
  Machine,
  MachineCreate,
  MachineGroup,
  MachineOperationalDetails,
} from "@/features/machines/types";
import { Pagination, usePagination } from "@/components/common/pagination";
import { StatusBadge } from "@/components/common/status-badge";
import { formatDateTimeSaoPaulo } from "@/lib/datetime";
import { useNavigate } from "react-router-dom";

function getVariant(status: string) {
  if (status === "online") return "ok";
  if (status === "warning") return "warn";
  return "error";
}

function getPostPatchVariant(state: string | null) {
  if (state === "reboot-scheduled" || state === "apply-completed" || state === "reboot-cleared") {
    return "ok";
  }
  if (state === "reboot-required") return "warn";
  if (state === "apply-failed") return "error";
  return "warn";
}

export function MachinesPage() {
  const navigate = useNavigate();
  const [machines, setMachines] = useState<Machine[]>([]);
  const [groups, setGroups] = useState<MachineGroup[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [pendingDelete, setPendingDelete] = useState<Machine | null>(null);
  const [pendingReidentify, setPendingReidentify] = useState<Machine | null>(null);
  const [reidentifyConfirmation, setReidentifyConfirmation] = useState("");
  const [pendingGroupDelete, setPendingGroupDelete] = useState<MachineGroup | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [groupFeedback, setGroupFeedback] = useState<string | null>(null);
  const [inventoryAgentId, setInventoryAgentId] = useState<string | null>(null);
  const [machineDetails, setMachineDetails] = useState<MachineOperationalDetails | null>(null);
  const [detailsLoading, setDetailsLoading] = useState(false);
  const [detailsError, setDetailsError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState("");
  const [platformFilter, setPlatformFilter] = useState("all");
  const [statusFilter, setStatusFilter] = useState("all");
  const [managementFilter, setManagementFilter] = useState("all");
  const [showFilters, setShowFilters] = useState(false);
  const [selectedMachineIds, setSelectedMachineIds] = useState<Set<string>>(new Set());
  const [upgradeFeedback, setUpgradeFeedback] = useState<string | null>(null);
  const [showGroupManager, setShowGroupManager] = useState(false);
  const [showMachineForm, setShowMachineForm] = useState(false);
  const [groupForm, setGroupForm] = useState({ name: "", description: "" });
  const [form, setForm] = useState<MachineCreate>({
    name: "",
    ip: "",
    platform: "Windows",
    environment: "production",
    group: "",
    status: "online",
    pending_patches: 0,
    risk: "important",
  });

  function resetMachineForm() {
    setEditingId(null);
    setShowMachineForm(false);
    setFormError(null);
    setForm({
      name: "",
      ip: "",
      platform: "Windows",
      environment: "production",
      group: groups[0]?.name ?? "",
      status: "online",
      pending_patches: 0,
      risk: "important",
    });
  }

  useEffect(() => {
    let active = true;

    async function loadMachines() {
      try {
        const [machineResponse, groupResponse] = await Promise.all([
          fetchMachines(),
          fetchMachineGroups(),
        ]);
        if (!active) return;
        setMachines(machineResponse);
        setGroups(groupResponse);
      } catch (err) {
        if (!active) return;
        setError(err instanceof Error ? err.message : "Falha ao carregar maquinas.");
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    }

    void loadMachines();

    const intervalId = setInterval(() => {
      if (!active) return;
      Promise.all([fetchMachines(), fetchMachineGroups()])
        .then(([machineResponse, groupResponse]) => {
          if (!active) return;
          setMachines(machineResponse);
          setGroups(groupResponse);
        })
        .catch(() => { /* falha silenciosa no polling */ });
    }, 30000);

    return () => {
      active = false;
      clearInterval(intervalId);
    };
  }, []);

  async function loadMachines() {
    const [machineResponse, groupResponse] = await Promise.all([
      fetchMachines(),
      fetchMachineGroups(),
    ]);
    setMachines(machineResponse);
    setGroups(groupResponse);
  }

  async function handleSubmitMachine(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFormError(null);
    setIsSubmitting(true);

    try {
      const payload = {
        ...form,
        pending_patches: Number(form.pending_patches),
      };
      const machine = editingId
        ? await updateMachine(editingId, payload)
        : await createMachine(payload);
      setMachines((current) =>
        [...current.filter((item) => item.id !== machine.id), machine].sort((a, b) =>
          a.name.localeCompare(b.name),
        ),
      );
      resetMachineForm();
    } catch (err) {
      setFormError(
        err instanceof Error
          ? err.message
          : editingId
            ? "Falha ao atualizar maquina."
            : "Falha ao registrar maquina.",
      );
    } finally {
      setIsSubmitting(false);
    }
  }

  function handleEditMachine(machine: Machine) {
    setEditingId(machine.id);
    setShowMachineForm(true);
    setForm({
      name: machine.name,
      ip: machine.ip,
      platform: machine.platform,
      environment: machine.environment,
      group: machine.group,
      status: machine.status,
      pending_patches: machine.pending_patches,
      risk: machine.risk,
    });
    setFormError(null);
  }

  async function handleDeleteMachine(machine: Machine) {
    try {
      await deleteMachine(machine.id);
      setMachines((current) => current.filter((item) => item.id !== machine.id));
      if (editingId === machine.id) {
        resetMachineForm();
      }
    } catch (err) {
      setFormError(err instanceof Error ? err.message : "Falha ao remover maquina.");
    } finally {
      setPendingDelete(null);
    }
  }

  async function handleCreateGroup(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setGroupFeedback(null);
    try {
      const group = await createMachineGroup({
        name: groupForm.name,
        description: groupForm.description || null,
      });
      setGroups((current) =>
        [...current.filter((item) => item.id !== group.id), group].sort((a, b) =>
          a.name.localeCompare(b.name),
        ),
      );
      setGroupForm({ name: "", description: "" });
      setGroupFeedback(`Grupo ${group.name} criado.`);
    } catch (err) {
      setGroupFeedback(err instanceof Error ? err.message : "Falha ao criar grupo.");
    }
  }

  async function handleDeleteGroup(group: MachineGroup) {
    try {
      await deleteMachineGroup(group.id);
      setGroups((current) => current.filter((item) => item.id !== group.id));
      setGroupFeedback(`Grupo ${group.name} removido.`);
    } catch (err) {
      setGroupFeedback(err instanceof Error ? err.message : "Falha ao remover grupo.");
    } finally {
      setPendingGroupDelete(null);
    }
  }

  async function handleOpenOperationalDetails(machine: Machine) {
    setDetailsLoading(true);
    setDetailsError(null);
    try {
      const response = await fetchMachineOperationalDetails(machine.id);
      setMachineDetails(response);
      if (machine.id.startsWith("agent-")) {
        setInventoryAgentId(machine.id.replace(/^agent-/, ""));
      } else {
        setInventoryAgentId(null);
      }
    } catch (err) {
      setMachineDetails(null);
      setDetailsError(err instanceof Error ? err.message : "Falha ao carregar os detalhes operacionais.");
    } finally {
      setDetailsLoading(false);
    }
  }

  async function handleUpgradeAgent(machine: Machine) {
    const agentId = machine.id.replace(/^agent-/, "");
    try {
      await requestConnectedAgentUpgrade(agentId);
      setUpgradeFeedback(`Upgrade solicitado para ${machine.name}. O agente reiniciara em instantes.`);
      setTimeout(() => setUpgradeFeedback(null), 6000);
    } catch (err) {
      setUpgradeFeedback(err instanceof Error ? err.message : "Falha ao solicitar upgrade.");
      setTimeout(() => setUpgradeFeedback(null), 6000);
    }
  }

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

  async function handleForceReidentify(machine: Machine) {
    const agentId = machine.id.replace(/^agent-/, "");
    try {
      const response = await forceReidentifyConnectedAgent(
        agentId,
        "identity_oscillation_shared_agent_id",
      );
      setUpgradeFeedback(
        `Comando ${response.command_id} enfileirado. O host que reivindicar este comando para a identidade ${response.old_agent_id} migrara para ${response.new_agent_id}.`,
      );
      setTimeout(() => setUpgradeFeedback(null), 10000);
      if (machineDetails?.machine.id === machine.id) {
        setMachineDetails(await fetchMachineOperationalDetails(machine.id));
      }
    } catch (err) {
      setUpgradeFeedback(
        err instanceof Error ? err.message : "Falha ao forcar reidentificacao.",
      );
      setTimeout(() => setUpgradeFeedback(null), 10000);
    } finally {
      setPendingReidentify(null);
      setReidentifyConfirmation("");
    }
  }

  async function handleBatchUpgrade() {
    const agentIds = Array.from(selectedMachineIds)
      .filter((id) => id.startsWith("agent-"))
      .map((id) => id.replace(/^agent-/, ""));
    if (agentIds.length === 0) return;
    try {
      const result = await requestConnectedAgentsBatchUpgrade(agentIds);
      setUpgradeFeedback(`Upgrade solicitado para ${result.queued} agente(s). Os agentes reiniciarao em instantes.`);
      setSelectedMachineIds(new Set());
      setTimeout(() => setUpgradeFeedback(null), 6000);
    } catch (err) {
      setUpgradeFeedback(err instanceof Error ? err.message : "Falha ao solicitar upgrade em lote.");
      setTimeout(() => setUpgradeFeedback(null), 6000);
    }
  }

  const filteredMachines = machines.filter((machine) => {
    const normalizedSearch = searchTerm.trim().toLowerCase();
    const matchesSearch =
      normalizedSearch.length === 0 ||
      machine.name.toLowerCase().includes(normalizedSearch) ||
      machine.ip.toLowerCase().includes(normalizedSearch) ||
      machine.group.toLowerCase().includes(normalizedSearch) ||
      machine.environment.toLowerCase().includes(normalizedSearch) ||
      machine.platform.toLowerCase().includes(normalizedSearch);
    const matchesPlatform =
      platformFilter === "all" || machine.platform.toLowerCase() === platformFilter.toLowerCase();
    const matchesStatus = statusFilter === "all" || machine.status === statusFilter;
    const isManaged = machine.id.startsWith("agent-");
    const matchesManagement =
      managementFilter === "all" ||
      (managementFilter === "managed" && isManaged) ||
      (managementFilter === "manual" && !isManaged);
    return matchesSearch && matchesPlatform && matchesStatus && matchesManagement;
  });

  const availablePlatforms = Array.from(new Set(machines.map((machine) => machine.platform))).sort((a, b) =>
    a.localeCompare(b),
  );
  const activeFilterCount = [
    searchTerm.trim().length > 0,
    platformFilter !== "all",
    statusFilter !== "all",
    managementFilter !== "all",
  ].filter(Boolean).length;
  const shouldShowOperationalDetails = detailsLoading || detailsError || machineDetails;
  const machinesPagination = usePagination(filteredMachines);

  const selectableIds = filteredMachines
    .filter((m) => m.id.startsWith("agent-"))
    .map((m) => m.id);
  const selectedCount = selectableIds.filter((id) => selectedMachineIds.has(id)).length;
  const selectAllChecked = selectableIds.length > 0 && selectedCount === selectableIds.length;
  const selectAllIndeterminate = selectedCount > 0 && selectedCount < selectableIds.length;
  const selectAllRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (selectAllRef.current) {
      selectAllRef.current.indeterminate = selectAllIndeterminate;
    }
  }, [selectAllIndeterminate]);

  function handleSelectAll() {
    if (selectAllChecked || selectAllIndeterminate) {
      setSelectedMachineIds((current) => {
        const next = new Set(current);
        selectableIds.forEach((id) => next.delete(id));
        return next;
      });
    } else {
      setSelectedMachineIds((current) => {
        const next = new Set(current);
        selectableIds.forEach((id) => next.add(id));
        return next;
      });
    }
  }

  return (
    <div className="single-panel-grid">
      <ConfirmModal
        open={pendingDelete !== null}
        title="Excluir maquina"
        description={
          pendingDelete
            ? `Deseja realmente excluir a maquina "${pendingDelete.name}"? Esta acao remove o registro da lista atual.`
            : ""
        }
        confirmLabel="Excluir"
        onCancel={() => setPendingDelete(null)}
        onConfirm={() => {
          if (pendingDelete) {
            void handleDeleteMachine(pendingDelete);
          }
        }}
      />
      <ConfirmModal
        open={pendingReidentify !== null}
        title="Forcar reidentificacao do proximo host"
        description={
          pendingReidentify
            ? `Esta acao NAO seleciona o host ${pendingReidentify.name}. Ela afeta o host fisico que reivindicar este comando na fila compartilhada do agent_id; a API rejeita a acao enquanto houver outro comando pendente. Repita somente depois que um novo enrollment aparecer e for aprovado; pode ser necessario repetir ate todos os clones migrarem.`
            : ""
        }
        confirmLabel="Enfileirar para o proximo host"
        confirmDisabled={
          !pendingReidentify ||
          reidentifyConfirmation !== pendingReidentify.id.replace(/^agent-/, "")
        }
        onCancel={() => {
          setPendingReidentify(null);
          setReidentifyConfirmation("");
        }}
        onConfirm={() => {
          if (pendingReidentify) {
            void handleForceReidentify(pendingReidentify);
          }
        }}
      >
        <label>
          <span className="field-label">
            Digite o agent_id para confirmar que entendeu a semantica iterativa
          </span>
          <input
            className="input"
            autoComplete="off"
            value={reidentifyConfirmation}
            onChange={(event) => setReidentifyConfirmation(event.target.value)}
            placeholder={pendingReidentify?.id.replace(/^agent-/, "") ?? ""}
          />
        </label>
      </ConfirmModal>
      <ConfirmModal
        open={pendingGroupDelete !== null}
        title="Excluir grupo"
        description={
          pendingGroupDelete
            ? `Deseja remover o grupo "${pendingGroupDelete.name}"? As maquinas nao serao excluidas.`
            : ""
        }
        confirmLabel="Excluir"
        onCancel={() => setPendingGroupDelete(null)}
        onConfirm={() => {
          if (pendingGroupDelete) {
            void handleDeleteGroup(pendingGroupDelete);
          }
        }}
      />
      {showGroupManager ? (
        <div className="modal-backdrop" role="dialog" aria-modal="true" aria-label="Grupos de maquinas">
          <div className="modal-card modal-card-form">
            <div className="modal-header">
              <div>
                <p className="eyebrow">Organizacao</p>
                <h3 className="modal-title">Grupos de maquinas</h3>
                <p className="modal-copy">
                  Crie e remova grupos usados para organizar maquinas e direcionar agendamentos.
                </p>
              </div>
              <button className="btn" type="button" onClick={() => setShowGroupManager(false)}>
                Fechar
              </button>
            </div>

            <form className="form-grid" onSubmit={handleCreateGroup}>
              <label>
                <span className="field-label">Nome do grupo</span>
                <input
                  className="input"
                  value={groupForm.name}
                  onChange={(event) => setGroupForm((current) => ({ ...current, name: event.target.value }))}
                  placeholder="Ex.: Workstations Financeiro"
                />
              </label>
              <label>
                <span className="field-label">Descricao</span>
                <input
                  className="input"
                  value={groupForm.description}
                  onChange={(event) =>
                    setGroupForm((current) => ({ ...current, description: event.target.value }))
                  }
                  placeholder="Opcional"
                />
              </label>
              <button className="btn btn-primary btn-primary-uniform" type="submit">
                Criar grupo
              </button>
            </form>

            {groupFeedback ? <p className="muted">{groupFeedback}</p> : null}

            <div className="list" style={{ marginTop: 16 }}>
              {groups.length === 0 ? (
                <div className="list-item">
                  <div className="muted">Nenhum grupo cadastrado.</div>
                </div>
              ) : null}
              {groups.map((group) => (
                <div className="list-item" key={group.id}>
                  <div>
                    <div style={{ fontWeight: 700 }}>{group.name}</div>
                    <div className="muted" style={{ marginTop: 4 }}>
                      {group.description || "Sem descricao"}
                    </div>
                  </div>
                  <button className="btn btn-danger" type="button" onClick={() => setPendingGroupDelete(group)}>
                    Remover
                  </button>
                </div>
              ))}
            </div>
          </div>
        </div>
      ) : null}
      {shouldShowOperationalDetails ? (
        <div className="modal-backdrop" role="dialog" aria-modal="true" aria-label="Detalhes operacionais da maquina">
          <div className="modal-card modal-card-wide">
            <div className="modal-toolbar">
              <button
                className="btn"
                onClick={() => {
                  setMachineDetails(null);
                  setDetailsError(null);
                  setDetailsLoading(false);
                  setInventoryAgentId(null);
                }}
                type="button"
              >
                Fechar
              </button>
            </div>
            <div className="modal-body-scroll">
              <MachineOperationalDetailsPanel
                details={machineDetails}
                error={detailsError}
                hideInventoryEmptyState
                hideInventoryHeader
                inventoryAgentId={inventoryAgentId}
                loading={detailsLoading}
              />
            </div>
          </div>
        </div>
      ) : null}
      {showMachineForm || editingId ? (
        <div className="modal-backdrop" role="dialog" aria-modal="true" aria-label="Formulario da maquina">
          <div className="modal-card modal-card-form">
            <div className="modal-header">
              <div>
                <p className="eyebrow">{editingId ? "Edicao" : "Cadastro"}</p>
                <h3 className="modal-title">{editingId ? "Editar maquina" : "Registrar maquina"}</h3>
                <p className="modal-copy">
                  {editingId
                    ? "Atualize os dados do host mantendo o inventario visivel ao fundo."
                    : "Inclua uma maquina manual sem deslocar a tela para a lateral."}
                </p>
              </div>
              <button className="btn" type="button" onClick={resetMachineForm}>
                Fechar
              </button>
            </div>
            <form className="form-grid" onSubmit={handleSubmitMachine}>
              <label>
                <span className="field-label">Hostname</span>
                <input
                  className="input"
                  value={form.name}
                  onChange={(event) => setForm((current) => ({ ...current, name: event.target.value }))}
                  placeholder="Ex.: SRV-APP-01"
                />
              </label>
              <label>
                <span className="field-label">IP</span>
                <input
                  className="input"
                  value={form.ip}
                  onChange={(event) => setForm((current) => ({ ...current, ip: event.target.value }))}
                  placeholder="10.0.0.15"
                />
              </label>
              <label>
                <span className="field-label">Plataforma</span>
                <select
                  className="select"
                  value={form.platform}
                  onChange={(event) =>
                    setForm((current) => ({ ...current, platform: event.target.value }))
                  }
                >
                  <option>Windows</option>
                  <option>Ubuntu</option>
                  <option>Debian</option>
                  <option>RHEL</option>
                </select>
              </label>
              <label>
                <span className="field-label">Ambiente</span>
                <select
                  className="select"
                  value={form.environment}
                  onChange={(event) =>
                    setForm((current) => ({ ...current, environment: event.target.value }))
                  }
                >
                  <option value="production">production</option>
                  <option value="homolog">homolog</option>
                  <option value="development">development</option>
                </select>
              </label>
              <label>
                <span className="field-label">Grupo</span>
                <select
                  className="select"
                  value={form.group}
                  onChange={(event) => setForm((current) => ({ ...current, group: event.target.value }))}
                >
                  {groups.length === 0 ? (
                    <option value="" disabled>
                      Nenhum grupo cadastrado
                    </option>
                  ) : (
                    groups.map((group) => (
                      <option key={group.id} value={group.name}>
                        {group.name}
                      </option>
                    ))
                  )}
                  {form.group && !groups.some((group) => group.name === form.group) ? (
                    <option value={form.group}>{form.group}</option>
                  ) : null}
                </select>
              </label>
              <label>
                <span className="field-label">Status</span>
                <select
                  className="select"
                  value={form.status}
                  onChange={(event) =>
                    setForm((current) => ({
                      ...current,
                      status: event.target.value as MachineCreate["status"],
                    }))
                  }
                >
                  <option value="online">online</option>
                  <option value="warning">warning</option>
                  <option value="offline">offline</option>
                </select>
              </label>
              <label>
                <span className="field-label">Patches pendentes</span>
                <input
                  className="input"
                  type="number"
                  min="0"
                  value={form.pending_patches}
                  onChange={(event) =>
                    setForm((current) => ({
                      ...current,
                      pending_patches: Number(event.target.value),
                    }))
                  }
                />
              </label>
              <label>
                <span className="field-label">Risco</span>
                <select
                  className="select"
                  value={form.risk}
                  onChange={(event) =>
                    setForm((current) => ({
                      ...current,
                      risk: event.target.value as MachineCreate["risk"],
                    }))
                  }
                >
                  <option value="critical">critical</option>
                  <option value="important">important</option>
                  <option value="optional">optional</option>
                </select>
              </label>
              {formError ? (
                <p className="form-error">{formError}</p>
              ) : null}
              <div style={{ display: "flex", gap: 10 }}>
                <button className="btn btn-primary btn-primary-uniform" type="submit" disabled={isSubmitting}>
                  {isSubmitting ? "Salvando..." : editingId ? "Salvar alteracoes" : "Registrar maquina"}
                </button>
                <button className="btn" type="button" onClick={resetMachineForm}>
                  Cancelar
                </button>
              </div>
            </form>
          </div>
        </div>
      ) : null}
      <section className="panel section">
        <div className="section-header">
          <h2 className="section-title">Inventario de maquinas</h2>
          <div style={{ display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap" }}>
            <span className="muted">
              {loading ? "Carregando da API..." : `${filteredMachines.length} de ${machines.length} maquinas`}
            </span>
            {selectedMachineIds.size > 0 ? (
              <>
                <span className="muted">{selectedMachineIds.size} selecionadas</span>
                <button
                  className="btn btn-primary btn-primary-uniform"
                  onClick={() => void handleBatchUpgrade()}
                  type="button"
                >
                  Atualizar agentes selecionados
                </button>
                <button className="btn" onClick={() => setSelectedMachineIds(new Set())} type="button">
                  Limpar selecao
                </button>
              </>
            ) : null}
            <button className="btn" onClick={() => void loadMachines()} type="button">
              Atualizar
            </button>
            <button className="btn" onClick={() => setShowFilters((current) => !current)} type="button">
              {showFilters ? "Ocultar filtros" : activeFilterCount > 0 ? `Filtros (${activeFilterCount})` : "Filtros"}
            </button>
            <button className="btn" onClick={() => setShowGroupManager(true)} type="button">
              Grupos
            </button>
            <button
              className="btn btn-primary btn-primary-uniform"
              onClick={() => {
                resetMachineForm();
                setShowMachineForm(true);
              }}
              type="button"
            >
              Nova maquina
            </button>
          </div>
        </div>
        {upgradeFeedback ? (
          <p className="muted" style={{ marginBottom: 8 }}>{upgradeFeedback}</p>
        ) : null}

        {error ? (
          <p className="muted" style={{ marginTop: 0, marginBottom: 16 }}>
            {error}. Verifique se a API esta ativa em `http://localhost:8000`.
          </p>
        ) : null}

        {showFilters ? (
        <div className="form-grid subtle-filter-panel" style={{ marginBottom: 16 }}>
          <label>
            <span className="field-label">Busca</span>
            <input
              className="input"
              placeholder="Host, IP, grupo ou plataforma"
              value={searchTerm}
              onChange={(event) => setSearchTerm(event.target.value)}
            />
          </label>
          <label>
            <span className="field-label">Plataforma</span>
            <select
              className="select"
              value={platformFilter}
              onChange={(event) => setPlatformFilter(event.target.value)}
            >
              <option value="all">todas</option>
              {availablePlatforms.map((platform) => (
                <option key={platform} value={platform}>
                  {platform}
                </option>
              ))}
            </select>
          </label>
          <label>
            <span className="field-label">Status</span>
            <select
              className="select"
              value={statusFilter}
              onChange={(event) => setStatusFilter(event.target.value)}
            >
              <option value="all">todos</option>
              <option value="online">online</option>
              <option value="warning">warning</option>
              <option value="offline">offline</option>
            </select>
          </label>
          <label>
            <span className="field-label">Origem</span>
            <select
              className="select"
              value={managementFilter}
              onChange={(event) => setManagementFilter(event.target.value)}
            >
              <option value="all">todas</option>
              <option value="managed">gerenciadas por agente</option>
              <option value="manual">cadastro manual</option>
            </select>
          </label>
        </div>
        ) : null}

        <table className="table">
          <thead>
            <tr>
              <th style={{ width: 32 }}>
                <input
                  type="checkbox"
                  ref={selectAllRef}
                  checked={selectAllChecked}
                  onChange={handleSelectAll}
                  disabled={selectableIds.length === 0}
                  aria-label="Selecionar todas as maquinas gerenciadas"
                  title="Selecionar todas as maquinas gerenciadas"
                />
              </th>
              <th>Host</th>
              <th>IP</th>
              <th>Plataforma</th>
              <th>SO</th>
              <th>Grupo</th>
              <th>
                Patches pendentes{" "}
                <InfoHint text="Total de patches pendentes / quantos desses são de segurança ou severidade crítica." />
              </th>
              <th>Pos-patch</th>
              <th>Ultimo check-in</th>
              <th>Status</th>
              <th>Acoes</th>
            </tr>
          </thead>
          <tbody>
            {!loading && filteredMachines.length === 0 ? (
              <tr>
                <td colSpan={11} className="muted">
                  Nenhuma maquina encontrada com os filtros atuais.
                </td>
              </tr>
            ) : null}
            {machinesPagination.pageItems.map((machine) => (
              <tr key={machine.id}>
                <td>
                  {machine.id.startsWith("agent-") ? (
                    <input
                      type="checkbox"
                      checked={selectedMachineIds.has(machine.id)}
                      onChange={(event) => {
                        setSelectedMachineIds((current) => {
                          const next = new Set(current);
                          if (event.target.checked) {
                            next.add(machine.id);
                          } else {
                            next.delete(machine.id);
                          }
                          return next;
                        });
                      }}
                      aria-label={`Selecionar ${machine.name}`}
                    />
                  ) : null}
                </td>
                <td style={{ fontWeight: 700 }}>
                  {machine.name}
                  {machine.identity_conflict_oscillation_detected_at ? (
                    <span
                      title={`Possivel identidade duplicada: fingerprint alternando entre ${machine.hardware_fingerprint ?? "?"} e ${machine.identity_conflict_fingerprint ?? "?"}. Detectado em ${formatDateTimeSaoPaulo(machine.identity_conflict_oscillation_detected_at)}. Requer revisao manual.`}
                      style={{ marginLeft: 6 }}
                    >
                      <StatusBadge variant="error">possivel identidade duplicada</StatusBadge>
                    </span>
                  ) : machine.identity_conflict_detected_at ? (
                    <span
                      title={`Fingerprint esperado: ${machine.hardware_fingerprint ?? "?"} | visto: ${machine.identity_conflict_fingerprint ?? "?"} em ${formatDateTimeSaoPaulo(machine.identity_conflict_detected_at)}`}
                      style={{ marginLeft: 6 }}
                    >
                      <StatusBadge variant="error">conflito de identidade</StatusBadge>
                    </span>
                  ) : null}
                </td>
                <td className="code">{machine.ip}</td>
                <td>{machine.platform}</td>
                <td>{machine.os_release ?? <span className="muted">-</span>}</td>
                <td>{machine.group}</td>
                <td>
                  {machine.pending_patches > 0 ? (
                    <button
                      className="btn"
                      onClick={() =>
                        navigate(`/patches?machine_id=${encodeURIComponent(machine.id)}&approval_status=pending&machine_name=${encodeURIComponent(machine.name)}`)
                      }
                      title="total / segurança e críticos"
                      type="button"
                    >
                      {machine.pending_patches}/{machine.pending_security_critical_patches}
                    </button>
                  ) : (
                    <span className="muted">0/0</span>
                  )}
                </td>
                <td>
                  {machine.post_patch_state ? (
                    <span
                      title={[
                        machine.post_patch_message,
                        machine.reboot_scheduled_at ? `reboot em ${formatDateTimeSaoPaulo(machine.reboot_scheduled_at)}` : null,
                        machine.last_apply_at ? `apply em ${formatDateTimeSaoPaulo(machine.last_apply_at)}` : null,
                      ].filter(Boolean).join(" | ") || undefined}
                    >
                      <StatusBadge variant={getPostPatchVariant(machine.post_patch_state)}>
                        {machine.post_patch_state}
                      </StatusBadge>
                    </span>
                  ) : (
                    <span className="muted">sem estado</span>
                  )}
                </td>
                <td className="code">{formatDateTimeSaoPaulo(machine.last_check_in)}</td>
                <td>
                  <StatusBadge variant={getVariant(machine.status)}>
                    {machine.status}
                  </StatusBadge>
                </td>
                <td>
                  <ActionMenu
                    label={`Abrir acoes da maquina ${machine.name}`}
                    items={[
                      {
                        label: "Ver detalhes",
                        onSelect: () => void handleOpenOperationalDetails(machine),
                      },
                      {
                        label: "Abrir pagina do host",
                        onSelect: () => navigate(`/machines/${machine.id}`),
                      },
                      {
                        label: "Atualizar agente",
                        disabled: !machine.id.startsWith("agent-"),
                        onSelect: () => void handleUpgradeAgent(machine),
                      },
                      ...(machine.identity_conflict_oscillation_detected_at
                        ? [
                            {
                              label: "Forcar reidentificacao (proximo host a conectar)",
                              onSelect: () => {
                                setReidentifyConfirmation("");
                                setPendingReidentify(machine);
                              },
                              tone: "danger" as const,
                            },
                          ]
                        : []),
                      {
                        label: "Resolver conflito de identidade",
                        disabled: !machine.identity_conflict_detected_at,
                        onSelect: () => void handleResolveIdentityConflict(machine),
                      },
                      {
                        label: "Editar",
                        onSelect: () => handleEditMachine(machine),
                      },
                      {
                        label: "Remover",
                        onSelect: () => setPendingDelete(machine),
                        tone: "danger",
                      },
                    ]}
                  />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        <Pagination
          page={machinesPagination.page}
          totalPages={machinesPagination.totalPages}
          from={machinesPagination.from}
          to={machinesPagination.to}
          total={machinesPagination.total}
          onPageChange={machinesPagination.setPage}
        />
      </section>
    </div>
  );
}
