import { useEffect, useMemo, useState } from "react";
import {
  createSchedule,
  deleteSchedule,
  fetchSchedules,
  toggleScheduleActive,
  updateSchedule,
} from "@/features/schedules/api";
import {
  fetchMachineGroups,
  fetchMachines,
} from "@/features/machines/api";
import { ActionMenu } from "@/components/common/action-menu";
import { ConfirmModal } from "@/components/common/confirm-modal";
import type { Machine, MachineGroup } from "@/features/machines/types";
import type {
  ScheduleCreate,
  ScheduleItem,
  ScheduleRebootPolicy,
  ScheduleRecurrence,
  ScheduleScopeType,
} from "@/features/schedules/types";

const today = new Date().toISOString().slice(0, 10);

const emptyScheduleForm: ScheduleCreate = {
  name: "",
  scope_type: "group",
  scope_value: "",
  install_date: today,
  install_time: "02:00",
  reboot_date: today,
  reboot_time: "03:00",
  recurrence: "weekly",
  reboot_policy: "if-needed",
  is_active: true,
};

const recurrenceLabels: Record<ScheduleRecurrence, string> = {
  once: "unica",
  daily: "diaria",
  weekly: "semanal",
  monthly: "mensal",
};

const scopeLabels: Record<ScheduleScopeType, string> = {
  machine: "Maquina",
  group: "Grupo",
  os: "SO",
};

const rebootLabels: Record<ScheduleRebootPolicy, string> = {
  "if-needed": "Reiniciar se necessario",
  always: "Sempre reiniciar",
  never: "Nao reiniciar",
};

function normalizeScheduleForEdit(schedule: ScheduleItem): ScheduleCreate {
  return {
    name: schedule.name,
    scope_type: schedule.scope_type ?? "group",
    scope_value: schedule.scope_value || schedule.scope,
    install_date: schedule.install_date ?? today,
    install_time: schedule.install_time || "02:00",
    reboot_date: schedule.reboot_date ?? schedule.install_date ?? today,
    reboot_time: schedule.reboot_time ?? "03:00",
    recurrence: schedule.recurrence ?? "weekly",
    reboot_policy: schedule.reboot_policy.toLowerCase().includes("nao")
      ? "never"
      : schedule.reboot_policy.toLowerCase().includes("sempre")
        ? "always"
        : "if-needed",
    is_active: schedule.is_active ?? true,
  };
}

export function SchedulesPage() {
  const [schedules, setSchedules] = useState<ScheduleItem[]>([]);
  const [machines, setMachines] = useState<Machine[]>([]);
  const [groups, setGroups] = useState<MachineGroup[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [pendingDelete, setPendingDelete] = useState<ScheduleItem | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [showScheduleForm, setShowScheduleForm] = useState(false);
  const [form, setForm] = useState<ScheduleCreate>(emptyScheduleForm);

  const machineOptions = useMemo(
    () => machines.map((machine) => ({ value: machine.id, label: `${machine.name} (${machine.platform})` })),
    [machines],
  );
  const groupOptions = useMemo(() => groups.map((group) => group.name), [groups]);

  function firstScopeValue(scopeType: ScheduleScopeType) {
    if (scopeType === "machine") return machineOptions[0]?.value ?? "";
    if (scopeType === "os") return "Windows";
    return groupOptions[0] ?? "";
  }

  function resetScheduleForm() {
    setEditingId(null);
    setShowScheduleForm(false);
    setFormError(null);
    setForm({ ...emptyScheduleForm, scope_value: firstScopeValue("group") });
  }

  async function loadData() {
    setLoading(true);
    try {
      const [scheduleResponse, machineResponse, groupResponse] = await Promise.all([
        fetchSchedules(),
        fetchMachines(),
        fetchMachineGroups(),
      ]);
      setSchedules(scheduleResponse);
      setMachines(machineResponse);
      setGroups(groupResponse);
      setError(null);
      if (!form.scope_value) {
        setForm((current) => ({
          ...current,
          scope_value: groupResponse[0]?.name ?? machineResponse[0]?.id ?? "",
        }));
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Falha ao carregar agendamentos.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadData();
  }, []);

  function handleScopeTypeChange(scopeType: ScheduleScopeType) {
    setForm((current) => ({
      ...current,
      scope_type: scopeType,
      scope_value: firstScopeValue(scopeType),
    }));
  }

  async function handleSubmitSchedule(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFormError(null);
    setIsSubmitting(true);

    try {
      const payload = {
        ...form,
        reboot_date: form.reboot_policy === "never" ? null : form.reboot_date,
        reboot_time: form.reboot_policy === "never" ? null : form.reboot_time,
      };
      const schedule = editingId
        ? await updateSchedule(editingId, payload)
        : await createSchedule(payload);
      setSchedules((current) =>
        [...current.filter((item) => item.id !== schedule.id), schedule].sort((a, b) =>
          a.name.localeCompare(b.name),
        ),
      );
      resetScheduleForm();
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
    setShowScheduleForm(true);
    setForm(normalizeScheduleForEdit(schedule));
    setFormError(null);
  }

  async function handleToggleActive(schedule: ScheduleItem) {
    try {
      const updated = await toggleScheduleActive(schedule.id, !schedule.is_active);
      setSchedules((current) => current.map((item) => (item.id === updated.id ? updated : item)));
    } catch (err) {
      setFormError(err instanceof Error ? err.message : "Falha ao alterar status do agendamento.");
    }
  }

  async function handleDeleteSchedule(schedule: ScheduleItem) {
    try {
      await deleteSchedule(schedule.id);
      setSchedules((current) => current.filter((item) => item.id !== schedule.id));
      if (editingId === schedule.id) {
        resetScheduleForm();
      }
    } catch (err) {
      setFormError(err instanceof Error ? err.message : "Falha ao remover agendamento.");
    } finally {
      setPendingDelete(null);
    }
  }

  return (
    <div className={showScheduleForm || editingId ? "split-grid" : "single-panel-grid"}>
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

      <div className="single-panel-grid">
        <section className="panel section">
          <div className="section-header">
            <h2 className="section-title">Agendamentos</h2>
            <div style={{ display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap" }}>
              <span className="muted">
                {loading ? "Carregando da API..." : `${schedules.filter((s) => s.is_active).length} ativos de ${schedules.length}`}
              </span>
              <button
                className="btn btn-primary btn-primary-uniform"
                onClick={() => {
                  resetScheduleForm();
                  setShowScheduleForm(true);
                }}
                type="button"
              >
                Nova janela
              </button>
            </div>
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
                  <div style={{ opacity: schedule.is_active ? 1 : 0.6 }}>
                    <div style={{ fontWeight: 700, display: "flex", alignItems: "center", gap: 8 }}>
                      {schedule.name}
                      <span
                        style={{
                          fontSize: 11,
                          fontWeight: 600,
                          padding: "2px 7px",
                          borderRadius: 4,
                          background: schedule.is_active ? "var(--color-success, #2d6a2d)" : "var(--color-muted-bg, #333)",
                          color: schedule.is_active ? "#a8f0a8" : "var(--color-muted, #999)",
                        }}
                      >
                        {schedule.is_active ? "Ativo" : "Inativo"}
                      </span>
                    </div>
                    <div className="muted" style={{ marginTop: 4 }}>
                      {scopeLabels[schedule.scope_type] ?? "Escopo"}: {schedule.scope_value || schedule.scope}
                    </div>
                    <div className="muted" style={{ marginTop: 6 }}>
                      Instalacao: {schedule.install_date ? `${schedule.install_date} ` : ""}
                      <span className="code">{schedule.install_time}</span>
                    </div>
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
                          label: schedule.is_active ? "Desativar" : "Ativar",
                          onSelect: () => void handleToggleActive(schedule),
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
                <div style={{ textAlign: "right", opacity: schedule.is_active ? 1 : 0.6 }}>
                  <div className="code">{schedule.cron_label}</div>
                  <div className="muted" style={{ marginTop: 4 }}>
                    Frequencia: {recurrenceLabels[schedule.recurrence] ?? schedule.recurrence}
                  </div>
                  <div className="muted" style={{ marginTop: 4 }}>
                    Reboot: {schedule.reboot_time ? <span className="code">{schedule.reboot_time}</span> : "sem janela"}
                  </div>
                  <div className="muted" style={{ marginTop: 4 }}>
                    {schedule.reboot_policy}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </section>

      </div>

      {showScheduleForm || editingId ? (
        <section className="panel section">
          <div className="section-header">
            <h2 className="section-title">{editingId ? "Editar janela" : "Nova janela"}</h2>
            <button className="btn" type="button" onClick={resetScheduleForm}>
              Fechar
            </button>
          </div>
          <form className="form-grid" onSubmit={handleSubmitSchedule}>
            <label>
              <span className="field-label">Nome</span>
              <input
                className="input"
                value={form.name}
                onChange={(event) => setForm((current) => ({ ...current, name: event.target.value }))}
                placeholder="Ex.: Drivers Windows semanal"
              />
            </label>
            <label>
              <span className="field-label">Tipo de escopo</span>
              <select
                className="select"
                value={form.scope_type}
                onChange={(event) => handleScopeTypeChange(event.target.value as ScheduleScopeType)}
              >
                <option value="machine">Maquina</option>
                <option value="group">Grupo</option>
                <option value="os">SO</option>
              </select>
            </label>
            <label>
              <span className="field-label">Escopo</span>
              <select
                className="select"
                value={form.scope_value}
                onChange={(event) => setForm((current) => ({ ...current, scope_value: event.target.value }))}
              >
                {form.scope_type === "machine"
                  ? machineOptions.map((machine) => (
                      <option key={machine.value} value={machine.value}>
                        {machine.label}
                      </option>
                    ))
                  : null}
                {form.scope_type === "group"
                  ? groupOptions.length > 0
                    ? groupOptions.map((group) => (
                        <option key={group} value={group}>
                          {group}
                        </option>
                      ))
                    : (
                        <option value="" disabled>
                          Nenhum grupo cadastrado
                        </option>
                      )
                  : null}
                {form.scope_type === "os" ? (
                  <>
                    <option value="Windows">Windows</option>
                    <option value="Linux">Linux</option>
                  </>
                ) : null}
              </select>
            </label>
            <label>
              <span className="field-label">Frequencia</span>
              <select
                className="select"
                value={form.recurrence}
                onChange={(event) =>
                  setForm((current) => ({
                    ...current,
                    recurrence: event.target.value as ScheduleRecurrence,
                  }))
                }
              >
                <option value="once">unica</option>
                <option value="daily">diaria</option>
                <option value="weekly">semanal</option>
                <option value="monthly">mensal</option>
              </select>
            </label>
            <label>
              <span className="field-label">Data de instalacao</span>
              <input
                className="input"
                type="date"
                value={form.install_date ?? ""}
                onChange={(event) =>
                  setForm((current) => ({ ...current, install_date: event.target.value || null }))
                }
              />
            </label>
            <label>
              <span className="field-label">Hora de instalacao</span>
              <input
                className="input"
                type="time"
                value={form.install_time}
                onChange={(event) => setForm((current) => ({ ...current, install_time: event.target.value }))}
              />
            </label>
            <label>
              <span className="field-label">Politica de reboot</span>
              <select
                className="select"
                value={form.reboot_policy}
                onChange={(event) =>
                  setForm((current) => ({
                    ...current,
                    reboot_policy: event.target.value as ScheduleRebootPolicy,
                  }))
                }
              >
                <option value="if-needed">Reiniciar se necessario</option>
                <option value="always">Sempre reiniciar</option>
                <option value="never">Nao reiniciar</option>
              </select>
            </label>
            <label>
              <span className="field-label">Data de reboot</span>
              <input
                className="input"
                disabled={form.reboot_policy === "never"}
                type="date"
                value={form.reboot_date ?? ""}
                onChange={(event) =>
                  setForm((current) => ({ ...current, reboot_date: event.target.value || null }))
                }
              />
            </label>
            <label>
              <span className="field-label">Hora de reboot</span>
              <input
                className="input"
                disabled={form.reboot_policy === "never"}
                type="time"
                value={form.reboot_time ?? ""}
                onChange={(event) =>
                  setForm((current) => ({ ...current, reboot_time: event.target.value || null }))
                }
              />
            </label>
            <label style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <input
                type="checkbox"
                checked={form.is_active}
                onChange={(event) => setForm((current) => ({ ...current, is_active: event.target.checked }))}
              />
              <span className="field-label" style={{ margin: 0 }}>Janela ativa</span>
            </label>
            {formError ? (
              <p className="muted" style={{ margin: 0, color: "#ff9fb0" }}>
                {formError}
              </p>
            ) : null}
            <div style={{ display: "flex", gap: 10 }}>
              <button className="btn btn-primary btn-primary-uniform" type="submit" disabled={isSubmitting}>
                {isSubmitting ? "Salvando..." : editingId ? "Salvar alteracoes" : "Criar agendamento"}
              </button>
              <button className="btn" type="button" onClick={resetScheduleForm}>
                Cancelar
              </button>
            </div>
          </form>
        </section>
      ) : null}
    </div>
  );
}
