import { useEffect, useState } from "react";
import {
  createMachine,
  deleteMachine,
  fetchMachineOperationalDetails,
  fetchMachines,
  updateMachine,
} from "@/features/machines/api";
import {
  reintegrateConnectedAgent,
  requestConnectedAgentReboot,
  revokeConnectedAgent,
} from "@/features/settings/api";
import { ActionMenu } from "@/components/common/action-menu";
import { ConfirmModal } from "@/components/common/confirm-modal";
import { MachineOperationalDetailsPanel } from "@/features/machines/components/machine-operational-details-panel";
import type { Machine, MachineCreate, MachineOperationalDetails } from "@/features/machines/types";
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
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [pendingDelete, setPendingDelete] = useState<Machine | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [inventoryAgentId, setInventoryAgentId] = useState<string | null>(null);
  const [machineDetails, setMachineDetails] = useState<MachineOperationalDetails | null>(null);
  const [detailsLoading, setDetailsLoading] = useState(false);
  const [detailsError, setDetailsError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState("");
  const [platformFilter, setPlatformFilter] = useState("all");
  const [statusFilter, setStatusFilter] = useState("all");
  const [managementFilter, setManagementFilter] = useState("all");
  const [selectedMachineIds, setSelectedMachineIds] = useState<string[]>([]);
  const [batchAction, setBatchAction] = useState<"reboot" | "reintegrate" | "revoke" | null>(null);
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

  useEffect(() => {
    let active = true;

    async function loadMachines() {
      try {
        const response = await fetchMachines();
        if (!active) return;
        setMachines(response);
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

    return () => {
      active = false;
    };
  }, []);

  async function loadMachines() {
    const response = await fetchMachines();
    setMachines(response);
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
      setForm({
        name: "",
        ip: "",
        platform: "Windows",
        environment: "production",
        group: "",
        status: "online",
        pending_patches: 0,
        risk: "important",
      });
      setEditingId(null);
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
      setSelectedMachineIds((current) => current.filter((item) => item !== machine.id));
      if (editingId === machine.id) {
        setEditingId(null);
        setForm({
          name: "",
          ip: "",
          platform: "Windows",
          environment: "production",
          group: "",
          status: "online",
          pending_patches: 0,
          risk: "important",
        });
      }
    } catch (err) {
      setFormError(err instanceof Error ? err.message : "Falha ao remover maquina.");
    } finally {
      setPendingDelete(null);
    }
  }

  async function handleBatchAction() {
    if (!batchAction) return;
    const selectedManagedAgentIds = machines
      .filter((machine) => selectedMachineIds.includes(machine.id) && machine.id.startsWith("agent-"))
      .map((machine) => machine.id.replace(/^agent-/, ""));

    if (selectedManagedAgentIds.length === 0) {
      setBatchAction(null);
      return;
    }

    setFormError(null);
    setIsSubmitting(true);
    try {
      if (batchAction === "reboot") {
        await Promise.all(selectedManagedAgentIds.map((agentId) => requestConnectedAgentReboot(agentId)));
      } else if (batchAction === "reintegrate") {
        await Promise.all(selectedManagedAgentIds.map((agentId) => reintegrateConnectedAgent(agentId)));
      } else {
        await Promise.all(selectedManagedAgentIds.map((agentId) => revokeConnectedAgent(agentId)));
      }
      setSelectedMachineIds([]);
      setBatchAction(null);
      await loadMachines();
    } catch (err) {
      setFormError(
        err instanceof Error ? err.message : "Falha ao executar a acao em lote nas maquinas selecionadas.",
      );
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleOpenInventory(machine: Machine) {
    if (!machine.id.startsWith("agent-")) return;
    void handleOpenOperationalDetails(machine);
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
  const selectedMachines = filteredMachines.filter((machine) => selectedMachineIds.includes(machine.id));
  const selectedManagedMachines = selectedMachines.filter((machine) => machine.id.startsWith("agent-"));
  const allFilteredSelected =
    filteredMachines.length > 0 && filteredMachines.every((machine) => selectedMachineIds.includes(machine.id));

  return (
    <div className="split-grid">
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
        open={batchAction !== null}
        title={
          batchAction === "reboot"
            ? "Solicitar reboot em lote?"
            : batchAction === "reintegrate"
              ? "Reintegrar agentes em lote?"
              : "Revogar agentes em lote?"
        }
        description={
          batchAction === "reboot"
            ? `${selectedManagedMachines.length} hosts gerenciados receberao uma solicitacao de reboot.`
            : batchAction === "reintegrate"
              ? `${selectedManagedMachines.length} hosts gerenciados voltarao para o fluxo de aprovacao do agente.`
              : `${selectedManagedMachines.length} hosts gerenciados perderao a credencial atual do agente.`
        }
        confirmLabel={
          batchAction === "reboot"
            ? "Solicitar reboot"
            : batchAction === "reintegrate"
              ? "Reintegrar"
              : "Revogar"
        }
        confirmDisabled={isSubmitting || selectedManagedMachines.length === 0}
        onCancel={() => setBatchAction(null)}
        onConfirm={() => void handleBatchAction()}
      />
      <section className="panel section">
        <div className="section-header">
          <h2 className="section-title">Inventario de maquinas</h2>
          <span className="muted">
            {loading ? "Carregando da API..." : `${filteredMachines.length} de ${machines.length} maquinas visiveis`}
          </span>
        </div>

        {error ? (
          <p className="muted" style={{ marginTop: 0, marginBottom: 16 }}>
            {error}. Verifique se a API esta ativa em `http://localhost:8000`.
          </p>
        ) : null}

        <div className="form-grid" style={{ marginBottom: 16 }}>
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

        <div style={{ display: "flex", gap: 10, alignItems: "center", justifyContent: "space-between", marginBottom: 16, flexWrap: "wrap" }}>
          <div className="muted">
            {selectedMachines.length === 0
              ? "Nenhuma maquina selecionada"
              : `${selectedMachines.length} maquinas selecionadas, ${selectedManagedMachines.length} gerenciadas por agente`}
          </div>
          <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
            <button
              className="btn"
              disabled={selectedManagedMachines.length === 0}
              onClick={() => setBatchAction("reboot")}
              type="button"
            >
              Reboot em lote
            </button>
            <button
              className="btn"
              disabled={selectedManagedMachines.length === 0}
              onClick={() => setBatchAction("reintegrate")}
              type="button"
            >
              Reintegrar em lote
            </button>
            <button
              className="btn"
              disabled={selectedManagedMachines.length === 0}
              onClick={() => setBatchAction("revoke")}
              type="button"
            >
              Revogar em lote
            </button>
            <button
              className="btn"
              disabled={selectedMachineIds.length === 0}
              onClick={() => setSelectedMachineIds([])}
              type="button"
            >
              Limpar selecao
            </button>
          </div>
        </div>

        <table className="table">
          <thead>
            <tr>
              <th>
                <input
                  aria-label="Selecionar todas as maquinas filtradas"
                  checked={allFilteredSelected}
                  onChange={(event) =>
                    setSelectedMachineIds((current) => {
                      if (event.target.checked) {
                        return Array.from(new Set([...current, ...filteredMachines.map((machine) => machine.id)]));
                      }
                      return current.filter((id) => !filteredMachines.some((machine) => machine.id === id));
                    })
                  }
                  type="checkbox"
                />
              </th>
              <th>Host</th>
              <th>IP</th>
              <th>Plataforma</th>
              <th>Ambiente</th>
              <th>Grupo</th>
              <th>Patches pendentes</th>
              <th>Pos-patch</th>
              <th>Ultimo check-in</th>
              <th>Status</th>
              <th>Acoes</th>
            </tr>
          </thead>
          <tbody>
            {!loading && filteredMachines.length === 0 ? (
              <tr>
                <td colSpan={10} className="muted">
                  Nenhuma maquina encontrada com os filtros atuais.
                </td>
              </tr>
            ) : null}
            {filteredMachines.map((machine) => (
              <tr key={machine.id}>
                <td>
                  <input
                    aria-label={`Selecionar maquina ${machine.name}`}
                    checked={selectedMachineIds.includes(machine.id)}
                    onChange={(event) =>
                      setSelectedMachineIds((current) =>
                        event.target.checked
                          ? [...current, machine.id]
                          : current.filter((item) => item !== machine.id),
                      )
                    }
                    type="checkbox"
                  />
                </td>
                <td style={{ fontWeight: 700 }}>{machine.name}</td>
                <td className="code">{machine.ip}</td>
                <td>{machine.platform}</td>
                <td>{machine.environment}</td>
                <td>{machine.group}</td>
                <td>{machine.pending_patches}</td>
                <td>
                  {machine.post_patch_state ? (
                    <div style={{ display: "grid", gap: 6 }}>
                      <StatusBadge variant={getPostPatchVariant(machine.post_patch_state)}>
                        {machine.post_patch_state}
                      </StatusBadge>
                      {machine.post_patch_message ? (
                        <div className="muted" style={{ maxWidth: 220 }}>
                          {machine.post_patch_message}
                        </div>
                      ) : null}
                      {machine.reboot_scheduled_at ? (
                        <div className="muted">
                          reboot em {formatDateTimeSaoPaulo(machine.reboot_scheduled_at)}
                        </div>
                      ) : null}
                      {machine.last_apply_at ? (
                        <div className="muted">
                          ultimo apply em {formatDateTimeSaoPaulo(machine.last_apply_at)}
                        </div>
                      ) : null}
                    </div>
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
                        label: "Ver inventario detalhado",
                        disabled: !machine.id.startsWith("agent-"),
                        onSelect: () => void handleOpenInventory(machine),
                      },
                      {
                        label: "Ver detalhes operacionais",
                        onSelect: () => void handleOpenOperationalDetails(machine),
                      },
                      {
                        label: "Abrir pagina do host",
                        onSelect: () => navigate(`/machines/${machine.id}`),
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
      </section>
      <MachineOperationalDetailsPanel
        details={machineDetails}
        error={detailsError}
        inventoryAgentId={inventoryAgentId}
        loading={detailsLoading}
      />

      <section className="panel section">
        <div className="section-header">
          <h2 className="section-title">Registrar maquina</h2>
          <span className="muted">
            {editingId ? "Edicao autenticada" : "Cadastro inicial autenticado"}
          </span>
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
            <input
              className="input"
              value={form.group}
              onChange={(event) => setForm((current) => ({ ...current, group: event.target.value }))}
              placeholder="Ex.: App Servers"
            />
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
            <p className="muted" style={{ margin: 0, color: "#ff9fb0" }}>
              {formError}
            </p>
          ) : null}
          <div style={{ display: "flex", gap: 10 }}>
            <button className="btn btn-primary" type="submit" disabled={isSubmitting}>
              {isSubmitting ? "Salvando..." : editingId ? "Salvar alteracoes" : "Registrar maquina"}
            </button>
            {editingId ? (
              <button
                className="btn"
                type="button"
                onClick={() => {
                  setEditingId(null);
                  setForm({
                    name: "",
                    ip: "",
                    platform: "Windows",
                    environment: "production",
                    group: "",
                    status: "online",
                    pending_patches: 0,
                    risk: "important",
                  });
                  setFormError(null);
                }}
              >
                Cancelar
              </button>
            ) : null}
          </div>
        </form>
      </section>
    </div>
  );
}
