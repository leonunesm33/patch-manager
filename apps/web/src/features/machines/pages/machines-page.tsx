import { useEffect, useState } from "react";
import {
  createMachine,
  deleteMachine,
  fetchMachineOperationalDetails,
  fetchMachines,
  updateMachine,
} from "@/features/machines/api";
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
  const [showFilters, setShowFilters] = useState(false);
  const [showMachineForm, setShowMachineForm] = useState(false);
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
      group: "",
      status: "online",
      pending_patches: 0,
      risk: "important",
    });
  }

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
  const activeFilterCount = [
    searchTerm.trim().length > 0,
    platformFilter !== "all",
    statusFilter !== "all",
    managementFilter !== "all",
  ].filter(Boolean).length;
  const shouldShowOperationalDetails = detailsLoading || detailsError || machineDetails;

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
            <button className="btn" onClick={() => setShowFilters((current) => !current)} type="button">
              {showFilters ? "Ocultar filtros" : activeFilterCount > 0 ? `Filtros (${activeFilterCount})` : "Filtros"}
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
                <td style={{ fontWeight: 700 }}>{machine.name}</td>
                <td className="code">{machine.ip}</td>
                <td>{machine.platform}</td>
                <td>{machine.environment}</td>
                <td>{machine.group}</td>
                <td>
                  {machine.pending_patches > 0 ? (
                    <button
                      className="btn"
                      onClick={() =>
                        navigate(`/patches?machine_id=${encodeURIComponent(machine.id)}&approval_status=pending`)
                      }
                      type="button"
                    >
                      {machine.pending_patches} pendentes
                    </button>
                  ) : (
                    <span className="muted">0</span>
                  )}
                </td>
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
    </div>
  );
}
