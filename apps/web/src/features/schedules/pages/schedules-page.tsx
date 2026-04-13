import { useEffect, useState } from "react";
import {
  createSchedule,
  deleteSchedule,
  fetchSchedules,
  updateSchedule,
} from "@/features/schedules/api";
import { ActionMenu } from "@/components/common/action-menu";
import { ConfirmModal } from "@/components/common/confirm-modal";
import type { ScheduleCreate, ScheduleItem } from "@/features/schedules/types";

export function SchedulesPage() {
  const [schedules, setSchedules] = useState<ScheduleItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [pendingDelete, setPendingDelete] = useState<ScheduleItem | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [form, setForm] = useState<ScheduleCreate>({
    name: "",
    scope: "Ubuntu Production",
    cron_label: "Toda quarta, 02:00",
    reboot_policy: "Somente se necessario",
  });

  useEffect(() => {
    let active = true;

    async function load() {
      try {
        const response = await fetchSchedules();
        if (!active) return;
        setSchedules(response);
      } catch (err) {
        if (!active) return;
        setError(err instanceof Error ? err.message : "Falha ao carregar agendamentos.");
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

  async function handleSubmitSchedule(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFormError(null);
    setIsSubmitting(true);

    try {
      const schedule = editingId
        ? await updateSchedule(editingId, form)
        : await createSchedule(form);
      setSchedules((current) =>
        [...current.filter((item) => item.id !== schedule.id), schedule].sort((a, b) =>
          a.name.localeCompare(b.name),
        ),
      );
      setForm({
        name: "",
        scope: "Ubuntu Production",
        cron_label: "Toda quarta, 02:00",
        reboot_policy: "Somente se necessario",
      });
      setEditingId(null);
    } catch (err) {
      setFormError(
        err instanceof Error
          ? err.message
          : editingId
            ? "Falha ao atualizar agendamento."
            : "Falha ao criar agendamento.",
      );
    } finally {
      setIsSubmitting(false);
    }
  }

  function handleEditSchedule(schedule: ScheduleItem) {
    setEditingId(schedule.id);
    setForm({
      name: schedule.name,
      scope: schedule.scope,
      cron_label: schedule.cron_label,
      reboot_policy: schedule.reboot_policy,
    });
    setFormError(null);
  }

  async function handleDeleteSchedule(schedule: ScheduleItem) {
    try {
      await deleteSchedule(schedule.id);
      setSchedules((current) => current.filter((item) => item.id !== schedule.id));
      if (editingId === schedule.id) {
        setEditingId(null);
        setForm({
          name: "",
          scope: "Ubuntu Production",
          cron_label: "Toda quarta, 02:00",
          reboot_policy: "Somente se necessario",
        });
      }
    } catch (err) {
      setFormError(err instanceof Error ? err.message : "Falha ao remover agendamento.");
    } finally {
      setPendingDelete(null);
    }
  }

  return (
    <div className="split-grid">
      <ConfirmModal
        open={pendingDelete !== null}
        title="Excluir agendamento"
        description={
          pendingDelete
            ? `Deseja realmente excluir o agendamento "${pendingDelete.name}"? Esta acao remove a politica cadastrada.`
            : ""
        }
        confirmLabel="Excluir"
        onCancel={() => setPendingDelete(null)}
        onConfirm={() => {
          if (pendingDelete) {
            void handleDeleteSchedule(pendingDelete);
          }
        }}
      />
      <section className="panel section">
        <div className="section-header">
          <h2 className="section-title">Agendamentos ativos</h2>
          <span className="muted">
            {loading ? "Carregando da API..." : `${schedules.length} politicas ativas`}
          </span>
        </div>
        {error ? (
          <p className="muted" style={{ marginTop: 0, marginBottom: 16 }}>
            {error}. Verifique se a API esta ativa em `http://localhost:8000`.
          </p>
        ) : null}
        <div className="list">
          {!loading && schedules.length === 0 ? (
            <div className="list-item">
              <div className="muted">Nenhum agendamento configurado.</div>
            </div>
          ) : null}
          {schedules.map((schedule) => (
            <div key={schedule.id} className="list-item">
              <div>
                <div style={{ fontWeight: 700 }}>{schedule.name}</div>
                <div className="muted" style={{ marginTop: 4 }}>
                  {schedule.scope}
                </div>
                <div style={{ marginTop: 10 }}>
                  <ActionMenu
                    label={`Abrir acoes do agendamento ${schedule.name}`}
                    items={[
                      {
                        label: "Editar",
                        onSelect: () => handleEditSchedule(schedule),
                      },
                      {
                        label: "Remover",
                        onSelect: () => setPendingDelete(schedule),
                        tone: "danger",
                      },
                    ]}
                  />
                </div>
              </div>
              <div style={{ textAlign: "right" }}>
                <div className="code">{schedule.cron_label}</div>
                <div className="muted" style={{ marginTop: 4 }}>
                  {schedule.reboot_policy}
                </div>
              </div>
            </div>
          ))}
        </div>
      </section>

      <section className="panel section">
        <div className="section-header">
          <h2 className="section-title">Nova janela de manutencao</h2>
          <span className="muted">
            {editingId ? "Edicao persistida no banco" : "Persistencia real no banco"}
          </span>
        </div>
        <form className="form-grid" onSubmit={handleSubmitSchedule}>
          <label>
            <span className="field-label">Nome</span>
            <input
              className="input"
              value={form.name}
              onChange={(event) => setForm((current) => ({ ...current, name: event.target.value }))}
              placeholder="Ex.: Linux Production Weekly"
            />
          </label>
          <label>
            <span className="field-label">Escopo</span>
            <select
              className="select"
              value={form.scope}
              onChange={(event) => setForm((current) => ({ ...current, scope: event.target.value }))}
            >
              <option>Ubuntu Production</option>
              <option>Windows Servers</option>
              <option>Finance Workstations</option>
            </select>
          </label>
          <label>
            <span className="field-label">Descricao da janela</span>
            <input
              className="input"
              value={form.cron_label}
              onChange={(event) =>
                setForm((current) => ({ ...current, cron_label: event.target.value }))
              }
              placeholder="Ex.: Toda quarta, 02:00"
            />
          </label>
          <label>
            <span className="field-label">Politica de reboot</span>
            <select
              className="select"
              value={form.reboot_policy}
              onChange={(event) =>
                setForm((current) => ({ ...current, reboot_policy: event.target.value }))
              }
            >
              <option>Somente se necessario</option>
              <option>Sempre reiniciar</option>
              <option>Nunca reiniciar</option>
            </select>
          </label>
          {formError ? (
            <p className="muted" style={{ margin: 0, color: "#ff9fb0" }}>
              {formError}
            </p>
          ) : null}
          <div style={{ display: "flex", gap: 10 }}>
            <button className="btn btn-primary" type="submit" disabled={isSubmitting}>
              {isSubmitting ? "Salvando..." : editingId ? "Salvar alteracoes" : "Criar agendamento"}
            </button>
            {editingId ? (
              <button
                className="btn"
                type="button"
                onClick={() => {
                  setEditingId(null);
                  setForm({
                    name: "",
                    scope: "Ubuntu Production",
                    cron_label: "Toda quarta, 02:00",
                    reboot_policy: "Somente se necessario",
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
