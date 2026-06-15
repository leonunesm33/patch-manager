import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import {
  approvePatch,
  createPatch,
  deletePatch,
  fetchPatchApprovals,
  rejectPatch,
  updatePatch,
} from "@/features/patches/api";
import { ActionMenu } from "@/components/common/action-menu";
import { ConfirmModal } from "@/components/common/confirm-modal";
import { StatusBadge } from "@/components/common/status-badge";
import { formatDateTimeSaoPaulo } from "@/lib/datetime";
import type { PatchApproval, PatchCategory, PatchCreate, PatchSeverity } from "@/features/patches/types";

function getStatusVariant(status: PatchApproval["approval_status"]) {
  if (status === "approved") return "ok";
  if (status === "rejected") return "error";
  return "warn";
}

function getSeverityVariant(severity: string) {
  if (severity === "critical") return "error";
  if (severity === "important" || severity === "high") return "warn";
  if (severity === "moderate") return "warn";
  return "ok";
}

function getSeverityLabel(severity: string) {
  const labels: Record<string, string> = {
    low: "baixo",
    medium: "medio",
    moderate: "moderado",
    high: "alto",
    critical: "critico",
    important: "alto",
    optional: "baixo",
    unknown: "desconhecido",
  };
  return labels[severity] ?? severity;
}

function getCategoryLabel(category: string) {
  const labels: Record<string, string> = {
    security: "seguranca",
    bugfix: "bug fix",
    enhancement: "melhoria",
    driver: "driver",
    firmware: "firmware",
    feature: "funcional",
    stability: "estabilidade",
    other: "outros",
    unknown: "geral",
    normal: "normal",
  };
  return labels[category] ?? category;
}

export function PatchApprovalsPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const machineIdFilter = searchParams.get("machine_id") ?? "";
  const approvalStatusFilter = searchParams.get("approval_status") ?? "";
  const severityFilter = searchParams.get("severity") ?? "";
  const categoryFilter = searchParams.get("category") ?? "";
  const platformFilter = searchParams.get("platform") ?? "";
  const [patches, setPatches] = useState<PatchApproval[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [actingPatchId, setActingPatchId] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [pendingDelete, setPendingDelete] = useState<PatchApproval | null>(null);
  const [showPatchForm, setShowPatchForm] = useState(false);
  const [showFilters, setShowFilters] = useState(false);
  const [form, setForm] = useState<PatchCreate>({
    id: "",
    display_name: "",
    target: "Windows Servers",
    severity: "high",
    category: "security",
    machines: 1,
    release_date: new Date().toISOString().slice(0, 10),
  });

  function resetPatchForm() {
    setEditingId(null);
    setShowPatchForm(false);
    setActionError(null);
    setForm({
      id: "",
      display_name: "",
      target: "Windows Servers",
      severity: "high",
      category: "security",
      machines: 1,
      release_date: new Date().toISOString().slice(0, 10),
    });
  }

  async function loadPatches() {
    setLoading(true);
    try {
      const response = await fetchPatchApprovals({
        machineId: machineIdFilter || undefined,
      });
      setPatches(response);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Falha ao carregar aprovacoes.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadPatches();
  }, [machineIdFilter]);

  function clearFilters() {
    setSearchParams({});
  }

  function updateFilter(key: string, value: string) {
    const nextParams = new URLSearchParams(searchParams);
    if (value) {
      nextParams.set(key, value);
    } else {
      nextParams.delete(key);
    }
    setSearchParams(nextParams);
  }

  function patchMatchesPlatform(patch: PatchApproval, platform: string) {
    if (!platform) return true;
    const normalizedPlatform = platform.toLowerCase();
    if (patch.target.toLowerCase().includes(normalizedPlatform)) return true;
    return patch.affected_machines.some((machine) =>
      machine.platform.toLowerCase().includes(normalizedPlatform),
    );
  }

  function patchMatchesFilters(patch: PatchApproval) {
    return (
      (!approvalStatusFilter || patch.approval_status === approvalStatusFilter) &&
      (!severityFilter || patch.severity === severityFilter) &&
      (!categoryFilter || patch.category === categoryFilter) &&
      patchMatchesPlatform(patch, platformFilter)
    );
  }

  function uniqueValues(values: string[]) {
    return Array.from(new Set(values.filter(Boolean))).sort((a, b) => a.localeCompare(b));
  }

  const filteredPatches = patches.filter(patchMatchesFilters);
  const pendingPatches = filteredPatches.filter((patch) => patch.approval_status === "pending");
  const managedPatches = filteredPatches.filter((patch) => patch.approval_status !== "pending");
  const categoryOptions = uniqueValues(patches.map((patch) => patch.category));
  const severityOptions = uniqueValues(patches.map((patch) => patch.severity));
  const platformOptions = uniqueValues(
    patches.flatMap((patch) => [
      ...patch.affected_machines.map((machine) => machine.platform),
      patch.target.toLowerCase().includes("windows") ? "Windows" : "",
      patch.target.toLowerCase().includes("linux") || patch.target.toLowerCase().includes("ubuntu") ? "Linux" : "",
    ]),
  );
  const hasActiveFilters = Boolean(
    machineIdFilter || approvalStatusFilter || severityFilter || categoryFilter || platformFilter,
  );

  async function handlePatchDecision(
    patchId: string,
    decision: PatchApproval["approval_status"],
  ) {
    setActionError(null);
    setActingPatchId(patchId);

    try {
      const updatedPatch =
        decision === "approved" ? await approvePatch(patchId) : await rejectPatch(patchId);
      setPatches((current) =>
        current.map((patch) => (patch.id === updatedPatch.id ? updatedPatch : patch)),
      );
    } catch (err) {
      setActionError(
        err instanceof Error ? err.message : "Falha ao atualizar o status do patch.",
      );
    } finally {
      setActingPatchId(null);
    }
  }

  async function handleSubmitPatch(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setActionError(null);
    setIsSubmitting(true);

    try {
      const patch = editingId
        ? await updatePatch(editingId, { ...form, display_name: form.display_name || form.id, machines: Number(form.machines) })
        : await createPatch({ ...form, display_name: form.display_name || form.id, machines: Number(form.machines) });

      setPatches((current) =>
        [...current.filter((item) => item.id !== editingId && item.id !== patch.id), patch].sort(
          (a, b) => b.release_date.localeCompare(a.release_date),
        ),
      );
      setEditingId(null);
      setShowPatchForm(false);
      resetPatchForm();
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Falha ao salvar o patch.");
    } finally {
      setIsSubmitting(false);
    }
  }

  function handleEditPatch(patch: PatchApproval) {
    setEditingId(patch.id);
    setShowPatchForm(true);
    setActionError(null);
    setForm({
      id: patch.id,
      display_name: patch.display_name || patch.id,
      target: patch.target,
      severity: patch.severity,
      category: patch.category,
      machines: patch.machines,
      release_date: patch.release_date,
    });
  }

  async function handleDeletePatch(patch: PatchApproval) {
    try {
      await deletePatch(patch.id);
      setPatches((current) => current.filter((item) => item.id !== patch.id));
      if (editingId === patch.id) {
        setEditingId(null);
        setShowPatchForm(false);
        resetPatchForm();
      }
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Falha ao excluir o patch.");
    } finally {
      setPendingDelete(null);
    }
  }

  function renderPatchRows(items: PatchApproval[], emptyMessage: string) {
    if (!loading && items.length === 0) {
      return (
        <tr>
          <td colSpan={8} className="muted">
            {emptyMessage}
          </td>
        </tr>
      );
    }

    return items.map((patch) => (
      <tr key={patch.id}>
        <td>
          <div style={{ fontWeight: 700 }}>{patch.display_name || patch.id}</div>
          <div className="muted" style={{ marginTop: 4 }}>
            ID: <span className="code">{patch.id}</span>
          </div>
          <div className="muted" style={{ marginTop: 4 }}>
            {patch.target}
          </div>
        </td>
        <td>{getCategoryLabel(patch.category)}</td>
        <td>
          <StatusBadge variant={getSeverityVariant(patch.severity)}>
            {getSeverityLabel(patch.severity)}
          </StatusBadge>
        </td>
        <td>
          <StatusBadge variant={getStatusVariant(patch.approval_status)}>
            {patch.approval_status}
          </StatusBadge>
        </td>
        <td>{patch.machines}</td>
        <td className="code">{patch.release_date}</td>
        <td className="muted">
          {patch.reviewed_by
            ? `${patch.reviewed_by} - ${patch.reviewed_at ? formatDateTimeSaoPaulo(patch.reviewed_at) : "sem horario"}`
            : "Aguardando decisao"}
        </td>
        <td>
          <ActionMenu
            label={`Abrir acoes do patch ${patch.id}`}
            items={[
              {
                label: actingPatchId === patch.id ? "Salvando..." : "Aprovar",
                onSelect: () => void handlePatchDecision(patch.id, "approved"),
                disabled: actingPatchId === patch.id || patch.approval_status === "approved",
              },
              {
                label: actingPatchId === patch.id ? "Salvando..." : "Rejeitar",
                onSelect: () => void handlePatchDecision(patch.id, "rejected"),
                disabled: actingPatchId === patch.id || patch.approval_status === "rejected",
                tone: "danger",
              },
              {
                label: "Editar",
                onSelect: () => handleEditPatch(patch),
              },
              {
                label: "Remover",
                onSelect: () => setPendingDelete(patch),
                tone: "danger",
              },
            ]}
          />
        </td>
      </tr>
    ));
  }

  function renderPatchTable(items: PatchApproval[], emptyMessage: string) {
    return (
      <table className="table">
        <thead>
          <tr>
            <th>Patch</th>
            <th>Categoria</th>
            <th>Criticidade</th>
            <th>Status</th>
            <th>Maquinas afetadas</th>
            <th>Lancamento</th>
            <th>Revisao</th>
            <th>Acoes</th>
          </tr>
        </thead>
        <tbody>{renderPatchRows(items, emptyMessage)}</tbody>
      </table>
    );
  }

  return (
    <div className="single-panel-grid">
      <ConfirmModal
        open={pendingDelete !== null}
        title="Excluir patch"
        description={
          pendingDelete
            ? `Deseja realmente excluir o patch "${pendingDelete.display_name || pendingDelete.id}"? Esta acao remove o item da fila de aprovacao.`
            : ""
        }
        confirmLabel="Excluir"
        onCancel={() => setPendingDelete(null)}
        onConfirm={() => {
          if (pendingDelete) {
            void handleDeletePatch(pendingDelete);
          }
        }}
      />
      <section className="panel section">
        <div className="section-header">
          <h2 className="section-title">Patches pendentes</h2>
          <div style={{ display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap" }}>
            <span className="muted">
              {loading
                ? "Carregando da API..."
                : `${pendingPatches.length} pendentes`}
            </span>
            <button className="btn" onClick={() => setShowFilters((current) => !current)} type="button">
              Filtros
            </button>
            <button
              className="btn btn-primary btn-primary-uniform"
              onClick={() => {
                resetPatchForm();
                setShowPatchForm(true);
              }}
              type="button"
            >
              Novo patch
            </button>
          </div>
        </div>
        {showFilters ? (
          <div className="list-item subtle-filter-panel" style={{ marginBottom: 16, alignItems: "stretch" }}>
            <div style={{ display: "grid", gap: 12, width: "100%" }}>
              <div>
                <div style={{ fontWeight: 700 }}>Filtros</div>
                <div className="muted" style={{ marginTop: 4 }}>
                  {machineIdFilter
                    ? `Maquina filtrada: ${machineIdFilter}`
                    : "Use os filtros disponiveis para reduzir a fila sem esconder o contexto."}
                </div>
              </div>
              <div
                style={{
                  display: "grid",
                  gap: 12,
                  gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
                }}
              >
                <label>
                  <span className="field-label">Status</span>
                  <select
                    className="select"
                    value={approvalStatusFilter}
                    onChange={(event) => updateFilter("approval_status", event.target.value)}
                  >
                    <option value="">Todos</option>
                    <option value="pending">Pendentes</option>
                    <option value="approved">Aprovados</option>
                    <option value="rejected">Rejeitados</option>
                  </select>
                </label>
                <label>
                  <span className="field-label">Criticidade</span>
                  <select
                    className="select"
                    value={severityFilter}
                    onChange={(event) => updateFilter("severity", event.target.value)}
                  >
                    <option value="">Todas</option>
                    {severityOptions.map((severity) => (
                      <option key={severity} value={severity}>
                        {getSeverityLabel(severity)}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  <span className="field-label">Categoria</span>
                  <select
                    className="select"
                    value={categoryFilter}
                    onChange={(event) => updateFilter("category", event.target.value)}
                  >
                    <option value="">Todas</option>
                    {categoryOptions.map((category) => (
                      <option key={category} value={category}>
                        {getCategoryLabel(category)}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  <span className="field-label">Plataforma</span>
                  <select
                    className="select"
                    value={platformFilter}
                    onChange={(event) => updateFilter("platform", event.target.value)}
                  >
                    <option value="">Todas</option>
                    {platformOptions.map((platform) => (
                      <option key={platform} value={platform}>
                        {platform}
                      </option>
                    ))}
                  </select>
                </label>
              </div>
            </div>
            <div style={{ display: "flex", gap: 10, alignItems: "flex-start" }}>
              {hasActiveFilters ? (
                <button className="btn" onClick={clearFilters} type="button">
                  Limpar filtro
                </button>
              ) : null}
              <button className="btn" onClick={() => setShowFilters(false)} type="button">
                Fechar
              </button>
            </div>
          </div>
        ) : null}
        {hasActiveFilters ? (
          <div className="muted" style={{ marginTop: -8, marginBottom: 16 }}>
            {filteredPatches.length} patches encontrados para os filtros atuais.
          </div>
        ) : null}
        {error ? (
          <p className="muted" style={{ marginTop: 0, marginBottom: 16 }}>
            {error}. Verifique se a API esta ativa.
          </p>
        ) : null}
        {actionError ? (
          <p className="muted" style={{ marginTop: 0, marginBottom: 16, color: "#ff9fb0" }}>
            {actionError}
          </p>
        ) : null}
        {renderPatchTable(
          pendingPatches,
          machineIdFilter
            ? "Este host reportou pendencias no resumo, mas ainda nao enviou patches pendentes para o filtro atual."
            : "Nenhum patch pendente para o filtro atual.",
        )}
      </section>

      <section className="panel section">
        <div className="section-header">
          <h2 className="section-title">Patches ja gerenciados</h2>
          <span className="muted">
            {loading ? "Carregando da API..." : `${managedPatches.length} aprovados ou rejeitados`}
          </span>
        </div>
        {renderPatchTable(managedPatches, "Nenhum patch aprovado ou rejeitado para o filtro atual.")}
      </section>

      {showPatchForm || editingId ? (
        <div className="modal-backdrop" role="dialog" aria-modal="true" aria-label="Formulario do patch">
          <div className="modal-card modal-card-form">
            <div className="modal-header">
              <div>
                <p className="eyebrow">{editingId ? "Edicao" : "Cadastro"}</p>
                <h3 className="modal-title">{editingId ? "Editar patch" : "Registrar patch"}</h3>
                <p className="modal-copy">
                  {editingId
                    ? "Atualize criticidade, categoria e escopo sem sair da fila de aprovacoes."
                    : "Inclua um novo patch na fila mantendo a lista principal em contexto."}
                </p>
              </div>
              <button className="btn" onClick={resetPatchForm} type="button">
                Fechar
              </button>
            </div>
            <form className="form-grid" onSubmit={handleSubmitPatch}>
              <label>
                <span className="field-label">Identificador</span>
                <input
                  className="input"
                  value={form.id}
                  onChange={(event) => setForm((current) => ({ ...current, id: event.target.value }))}
                  placeholder="Ex.: KB5034441"
                />
              </label>
              <label>
                <span className="field-label">Nome do patch</span>
                <input
                  className="input"
                  value={form.display_name ?? ""}
                  onChange={(event) =>
                    setForm((current) => ({ ...current, display_name: event.target.value }))
                  }
                  placeholder="Ex.: Intel Driver Update (2.3.20303.5058)"
                />
              </label>
              <label>
                <span className="field-label">Escopo</span>
                <select
                  className="select"
                  value={form.target}
                  onChange={(event) =>
                    setForm((current) => ({ ...current, target: event.target.value }))
                  }
                >
                  <option>Windows Servers</option>
                  <option>Ubuntu Production</option>
                  <option>Linux Production</option>
                  <option>Finance Workstations</option>
                </select>
              </label>
              <label>
                <span className="field-label">Criticidade</span>
                <select
                  className="select"
                  value={form.severity}
                  onChange={(event) =>
                    setForm((current) => ({
                      ...current,
                      severity: event.target.value as PatchSeverity,
                    }))
                  }
                >
                  <option value="low">baixo</option>
                  <option value="medium">medio</option>
                  <option value="moderate">moderado</option>
                  <option value="high">alto</option>
                  <option value="important">importante</option>
                  <option value="critical">critico</option>
                </select>
              </label>
              <label>
                <span className="field-label">Categoria</span>
                <select
                  className="select"
                  value={form.category}
                  onChange={(event) =>
                    setForm((current) => ({
                      ...current,
                      category: event.target.value as PatchCategory,
                    }))
                  }
                >
                  <option value="security">seguranca</option>
                  <option value="bugfix">bug fix</option>
                  <option value="enhancement">melhoria</option>
                  <option value="driver">driver</option>
                  <option value="firmware">firmware</option>
                  <option value="stability">estabilidade</option>
                  <option value="feature">funcional</option>
                  <option value="other">outros</option>
                </select>
              </label>
              <label>
                <span className="field-label">Maquinas afetadas estimadas</span>
                <input
                  className="input"
                  min="1"
                  type="number"
                  value={form.machines}
                  onChange={(event) =>
                    setForm((current) => ({
                      ...current,
                      machines: Number(event.target.value),
                    }))
                  }
                />
              </label>
              <label>
                <span className="field-label">Data de lancamento</span>
                <input
                  className="input"
                  type="date"
                  value={form.release_date}
                  onChange={(event) =>
                    setForm((current) => ({ ...current, release_date: event.target.value }))
                  }
                />
              </label>
              {actionError ? (
                <p className="muted" style={{ margin: 0, color: "#ff9fb0" }}>
                  {actionError}
                </p>
              ) : null}
              <div style={{ display: "flex", gap: 10 }}>
                <button className="btn btn-primary btn-primary-uniform" disabled={isSubmitting} type="submit">
                  {isSubmitting ? "Salvando..." : editingId ? "Salvar alteracoes" : "Registrar patch"}
                </button>
                <button className="btn" onClick={resetPatchForm} type="button">
                  Cancelar
                </button>
              </div>
            </form>
          </div>
        </div>
      ) : null}
    </div>
  );
}
