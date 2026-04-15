import { useEffect, useState } from "react";
import {
  createMachine,
  deleteMachine,
  fetchMachines,
  updateMachine,
} from "@/features/machines/api";
import { ActionMenu } from "@/components/common/action-menu";
import { ConfirmModal } from "@/components/common/confirm-modal";
import type { Machine, MachineCreate } from "@/features/machines/types";
import { StatusBadge } from "@/components/common/status-badge";
import { formatDateTimeSaoPaulo } from "@/lib/datetime";

function getVariant(status: string) {
  if (status === "online") return "ok";
  if (status === "warning") return "warn";
  return "error";
}

export function MachinesPage() {
  const [machines, setMachines] = useState<Machine[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [pendingDelete, setPendingDelete] = useState<Machine | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [form, setForm] = useState<MachineCreate>({
    name: "",
    ip: "",
    platform: "Windows",
    group: "",
    status: "online",
    pending_patches: 0,
    risk: "important",
  });

  useEffect(() => {
    let active = true;

    async function load() {
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

    void load();

    return () => {
      active = false;
    };
  }, []);

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
        setEditingId(null);
        setForm({
          name: "",
          ip: "",
          platform: "Windows",
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
      <section className="panel section">
        <div className="section-header">
          <h2 className="section-title">Inventario de maquinas</h2>
          <span className="muted">
            {loading ? "Carregando da API..." : `${machines.length} maquinas carregadas`}
          </span>
        </div>

        {error ? (
          <p className="muted" style={{ marginTop: 0, marginBottom: 16 }}>
            {error}. Verifique se a API esta ativa em `http://localhost:8000`.
          </p>
        ) : null}

        <table className="table">
          <thead>
            <tr>
              <th>Host</th>
              <th>IP</th>
              <th>Plataforma</th>
              <th>Grupo</th>
              <th>Patches pendentes</th>
              <th>Ultimo check-in</th>
              <th>Status</th>
              <th>Acoes</th>
            </tr>
          </thead>
          <tbody>
            {!loading && machines.length === 0 ? (
              <tr>
                <td colSpan={7} className="muted">
                  Nenhuma maquina encontrada.
                </td>
              </tr>
            ) : null}
            {machines.map((machine) => (
              <tr key={machine.id}>
                <td style={{ fontWeight: 700 }}>{machine.name}</td>
                <td className="code">{machine.ip}</td>
                <td>{machine.platform}</td>
                <td>{machine.group}</td>
                <td>{machine.pending_patches}</td>
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
