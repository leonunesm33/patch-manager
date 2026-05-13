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
  if (severity === "high" || severity === "important") return "warn";
  return "ok";
}

function getSeverityLabel(severity: string) {
  const labels: Record<string, string> = {
    low: "baixo",
    medium: "medio",
    high: "alto",
    critical: "critico",
    important: "alto",
    optional: "baixo",
  };
  return labels[severity] ?? severity;
}

function getCategoryLabel(category: string) {
  const labels: Record<string, string> = {
    security: "seguranca",
    bugfix: "bug",
    feature: "funcional",
    stability: "estabilidade",
    other: "outros",
  };
  return labels[category] ?? category;
}

export function PatchApprovalsPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const machineIdFilter = searchParams.get("machine_id") ?? "";
  const approvalStatusFilter = searchParams.get("approval_status") ?? "";
  const [patches, setPatches] = useState<PatchApproval[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [actingPatchId, setActingPatchId] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [pendingDelete, setPendingDelete] = useState<PatchApproval | null>(null);
  const [showPatchForm, setShowPatchForm] = useState(false);
  const [form, setForm] = useState<PatchCreate>({
    id: "",
    target: "Windows Servers",
    severity: "high",
    category: "security",
    machines: 1,
    release_date: new Date().toISOString().slice(0, 10),
  });
  const hasSidePanel = showPatchForm || editingId !== null;

  function resetPatchForm() {
    setEditingId(null);
    setShowPatchForm(false);
    setActionError(null);
    setForm({
      id: "",
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
        approvalStatus: approvalStatusFilter || undefined,
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
  }, [machineIdFilter, approvalStatusFilter]);

  function clearFilters() {
    setSearchParams({});
  }

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
        current
          .map((patch) => (patch.id === updatedPatch.id ? updatedPatch : patch))
          .filter((patch) => !approvalStatusFilter || patch.approval_status === approvalStatusFilter),
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
        ? await updatePatch(editingId, { ...form, machines: Number(form.machines) })
        : await createPatch({ ...form, machines: Number(form.machines) });

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

  return (
    <div className={hasSidePanel ? "split-grid" : "single-panel-grid"}>
      <ConfirmModal
        open={pendingDelete !== null}
        title="Excluir patch"
        description={
          pendingDelete
            ? `Deseja realmente excluir o patch "${pendingDelete.id}"? Esta acao remove o item da fila de aprovacao.`
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
          <h2 className="section-title">Fila de aprovacoes</h2>
          <div style={{ display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap" }}>
            <span className="muted">
              {loading
                ? "Carregando da API..."
                : `${patches.filter((patch) => patch.approval_status === "pending").length} pendentes`}
            </span>
            <button
              className="btn btn-primary"
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
        {(machineIdFilter || approvalStatusFilter) ? (
          <div className="list-item subtle-filter-panel" style={{ marginBottom: 16 }}>
            <div>
              <div style={{ fontWeight: 700 }}>Filtro ativo</div>
              <div className="muted" style={{ marginTop: 4 }}>
                {machineIdFilter ? `Maquina: ${machineIdFilter}` : "Todas as maquinas"}
                {approvalStatusFilter ? ` - status: ${approvalStatusFilter}` : ""}
              </div>
            </div>
            <button className="btn" onClick={clearFilters} type="button">
              Limpar filtro
            </button>
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
          <tbody>
            {!loading && patches.length === 0 ? (
              <tr>
                <td colSpan={8} className="muted">
                  Nenhum patch encontrado para o filtro atual.
                </td>
              </tr>
            ) : null}
            {patches.map((patch) => (
              <tr key={patch.id}>
                <td>
                  <div className="code">{patch.id}</div>
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
                        disabled: actingPatchId === patch.id,
                      },
                      {
                        label: actingPatchId === patch.id ? "Salvando..." : "Rejeitar",
                        onSelect: () => void handlePatchDecision(patch.id, "rejected"),
                        disabled: actingPatchId === patch.id,
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
            ))}
          </tbody>
        </table>
      </section>

      {showPatchForm || editingId ? (
      <section className="panel section">
        <div className="section-header">
          <h2 className="section-title">Registrar patch</h2>
          <span className="muted">
            {editingId ? "Edicao persistida no banco" : "Cadastro autenticado"}
          </span>
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
              <option value="high">alto</option>
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
              <option value="bugfix">bug</option>
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
            <button className="btn btn-primary" disabled={isSubmitting} type="submit">
              {isSubmitting ? "Salvando..." : editingId ? "Salvar alteracoes" : "Registrar patch"}
            </button>
            <button className="btn" onClick={resetPatchForm} type="button">
              Fechar
            </button>
          </div>
        </form>
      </section>
      ) : null}
    </div>
  );
}
