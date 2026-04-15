import { useEffect, useState } from "react";
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
import type { PatchApproval, PatchCreate } from "@/features/patches/types";

function getStatusVariant(status: PatchApproval["approval_status"]) {
  if (status === "approved") return "ok";
  if (status === "rejected") return "error";
  return "warn";
}

export function PatchApprovalsPage() {
  const [patches, setPatches] = useState<PatchApproval[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [actingPatchId, setActingPatchId] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [pendingDelete, setPendingDelete] = useState<PatchApproval | null>(null);
  const [form, setForm] = useState<PatchCreate>({
    id: "",
    target: "Windows Servers",
    severity: "important",
    machines: 1,
    release_date: new Date().toISOString().slice(0, 10),
  });

  useEffect(() => {
    let active = true;

    async function load() {
      try {
        const response = await fetchPatchApprovals();
        if (!active) return;
        setPatches(response);
      } catch (err) {
        if (!active) return;
        setError(err instanceof Error ? err.message : "Falha ao carregar aprovacoes.");
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    }

    void load();

    return () => {
      active = false;
    };
  }, []);

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
        ? await updatePatch(editingId, { ...form, machines: Number(form.machines) })
        : await createPatch({ ...form, machines: Number(form.machines) });

      setPatches((current) =>
        [...current.filter((item) => item.id !== editingId && item.id !== patch.id), patch].sort(
          (a, b) => b.release_date.localeCompare(a.release_date),
        ),
      );
      setEditingId(null);
      setForm({
        id: "",
        target: "Windows Servers",
        severity: "important",
        machines: 1,
        release_date: new Date().toISOString().slice(0, 10),
      });
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Falha ao salvar o patch.");
    } finally {
      setIsSubmitting(false);
    }
  }

  function handleEditPatch(patch: PatchApproval) {
    setEditingId(patch.id);
    setActionError(null);
    setForm({
      id: patch.id,
      target: patch.target,
      severity: patch.severity,
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
        setForm({
          id: "",
          target: "Windows Servers",
          severity: "important",
          machines: 1,
          release_date: new Date().toISOString().slice(0, 10),
        });
      }
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Falha ao excluir o patch.");
    } finally {
      setPendingDelete(null);
    }
  }

  return (
    <div className="split-grid">
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
          <span className="muted">
            {loading
              ? "Carregando da API..."
              : `${patches.filter((patch) => patch.approval_status === "pending").length} itens pendentes`}
          </span>
        </div>
        {error ? (
          <p className="muted" style={{ marginTop: 0, marginBottom: 16 }}>
            {error}. Verifique se a API esta ativa em `http://localhost:8000`.
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
              <th>Escopo</th>
              <th>Severidade</th>
              <th>Status</th>
              <th>Maquinas</th>
              <th>Lancamento</th>
              <th>Revisao</th>
              <th>Acoes</th>
            </tr>
          </thead>
          <tbody>
            {!loading && patches.length === 0 ? (
              <tr>
                <td colSpan={8} className="muted">
                  Nenhum patch aguardando aprovacao.
                </td>
              </tr>
            ) : null}
            {patches.map((patch) => (
              <tr key={patch.id}>
                <td className="code">{patch.id}</td>
                <td>{patch.target}</td>
                <td>{patch.severity}</td>
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
              <option>Finance Workstations</option>
            </select>
          </label>
          <label>
            <span className="field-label">Severidade</span>
            <select
              className="select"
              value={form.severity}
              onChange={(event) =>
                setForm((current) => ({
                  ...current,
                  severity: event.target.value as PatchCreate["severity"],
                }))
              }
            >
              <option value="critical">critical</option>
              <option value="important">important</option>
              <option value="optional">optional</option>
            </select>
          </label>
          <label>
            <span className="field-label">Maquinas afetadas</span>
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
            {editingId ? (
              <button
                className="btn"
                onClick={() => {
                  setEditingId(null);
                  setActionError(null);
                  setForm({
                    id: "",
                    target: "Windows Servers",
                    severity: "important",
                    machines: 1,
                    release_date: new Date().toISOString().slice(0, 10),
                  });
                }}
                type="button"
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
