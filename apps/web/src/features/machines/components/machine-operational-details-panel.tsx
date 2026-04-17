import { useEffect, useMemo, useState } from "react";
import { AgentInventoryDetailPanel } from "@/features/agents/components/agent-inventory-detail-panel";
import type { MachineOperationalDetails } from "@/features/machines/types";
import { StatusBadge } from "@/components/common/status-badge";
import { formatDateTimeSaoPaulo } from "@/lib/datetime";

type MachineOperationalDetailsPanelProps = {
  details: MachineOperationalDetails | null;
  loading: boolean;
  error: string | null;
  inventoryAgentId: string | null;
  title?: string;
};

function getVariant(status: string) {
  if (status === "online") return "ok";
  if (status === "warning") return "warn";
  return "error";
}

function getTimelineItems(details: MachineOperationalDetails) {
  const timeline = [
    ...details.recent_jobs.map((job) => ({
      id: `job-${job.id}`,
      category: "job",
      title: `${job.patch_id} - ${job.status}`,
      detail: `${job.schedule_name} - ${job.platform} - ${job.severity}`,
      message: job.error_message,
      occurredAt: job.finished_at ?? job.started_at ?? job.created_at,
      variant:
        job.status === "failed" ? "error" : job.status === "completed" ? "ok" : "warn",
    })),
    ...details.recent_executions.map((execution) => ({
      id: `execution-${execution.id}`,
      category: "execucao",
      title: `${execution.patch_id} - ${execution.result}`,
      detail: `${execution.schedule_name} - ${execution.platform} - ${execution.severity}`,
      message: `${execution.duration_seconds}s`,
      occurredAt: execution.executed_at,
      variant: execution.result === "applied" ? "ok" : execution.result === "failed" ? "error" : "warn",
    })),
    ...details.recent_commands.map((command) => ({
      id: `command-${command.id}`,
      category: "comando",
      title: `${command.command_type} - ${command.status}`,
      detail: `solicitado por ${command.requested_by}`,
      message: command.message,
      occurredAt: command.finished_at ?? command.created_at,
      variant:
        command.status === "failed" ? "error" : command.status === "completed" ? "ok" : "warn",
    })),
  ];

  return timeline.sort(
    (left, right) =>
      new Date(right.occurredAt).getTime() - new Date(left.occurredAt).getTime(),
  );
}

export function MachineOperationalDetailsPanel({
  details,
  loading,
  error,
  inventoryAgentId,
  title = "Detalhes operacionais do host",
}: MachineOperationalDetailsPanelProps) {
  const [timelinePageSize, setTimelinePageSize] = useState(10);
  const [timelinePage, setTimelinePage] = useState(1);
  const timelineItems = useMemo(() => (details ? getTimelineItems(details) : []), [details]);
  const timelineTotalPages = Math.max(1, Math.ceil(timelineItems.length / timelinePageSize));
  const paginatedTimelineItems = useMemo(
    () => timelineItems.slice((timelinePage - 1) * timelinePageSize, timelinePage * timelinePageSize),
    [timelineItems, timelinePage, timelinePageSize],
  );

  useEffect(() => {
    setTimelinePage(1);
  }, [details?.machine.id, timelinePageSize]);

  useEffect(() => {
    if (timelinePage > timelineTotalPages) {
      setTimelinePage(timelineTotalPages);
    }
  }, [timelinePage, timelineTotalPages]);

  return (
    <div style={{ display: "grid", gap: 18 }}>
      <AgentInventoryDetailPanel
        detail={details?.inventory ?? null}
        error={error && !details ? error : null}
        loading={loading}
        title={
          inventoryAgentId
            ? `Inventario detalhado do host gerenciado por ${inventoryAgentId}`
            : "Inventario detalhado do host"
        }
      />
      <section className="panel section">
        <div className="section-header">
          <h2 className="section-title">{title}</h2>
          <span className="muted">
            {details ? details.machine.name : loading ? "Carregando..." : "Selecione uma maquina"}
          </span>
        </div>
        {error ? (
          <p className="muted" style={{ marginTop: 0, marginBottom: 16 }}>
            {error}
          </p>
        ) : null}
        {loading ? <p className="muted">Carregando detalhes operacionais...</p> : null}
        {!loading && !details ? (
          <p className="muted">
            Abra os detalhes operacionais de uma maquina para ver jobs recentes, execucoes e comandos do agente.
          </p>
        ) : null}
        {details ? (
          <div style={{ display: "grid", gap: 18 }}>
            <div className="list">
              <div className="list-item">
                <div>
                  <div style={{ fontWeight: 700 }}>
                    {details.machine.name} - {details.machine.platform}
                  </div>
                  <div className="muted" style={{ marginTop: 4 }}>
                    {details.machine.group} - {details.machine.ip}
                  </div>
                  {details.agent_id ? (
                    <div className="muted" style={{ marginTop: 4 }}>
                      agente {details.agent_id}
                    </div>
                  ) : null}
                </div>
                <StatusBadge variant={getVariant(details.machine.status)}>
                  {details.machine.status}
                </StatusBadge>
              </div>
            </div>

            <div className="list">
              <div className="list-item">
                <div style={{ fontWeight: 700 }}>Jobs recentes</div>
              </div>
              {details.recent_jobs.length === 0 ? (
                <div className="list-item">
                  <div className="muted">Nenhum job recente para este host.</div>
                </div>
              ) : null}
              {details.recent_jobs.map((job) => (
                <div key={job.id} className="list-item">
                  <div>
                    <div style={{ fontWeight: 700 }}>
                      {job.patch_id} - {job.status}
                    </div>
                    <div className="muted" style={{ marginTop: 4 }}>
                      {job.schedule_name} - {job.platform} - {job.severity}
                    </div>
                    {job.error_message ? (
                      <div className="muted" style={{ marginTop: 4 }}>
                        {job.error_message}
                      </div>
                    ) : null}
                  </div>
                  <div className="muted">{formatDateTimeSaoPaulo(job.created_at)}</div>
                </div>
              ))}
            </div>

            <div className="list">
              <div className="list-item">
                <div style={{ fontWeight: 700 }}>Execucoes recentes</div>
              </div>
              {details.recent_executions.length === 0 ? (
                <div className="list-item">
                  <div className="muted">Nenhuma execucao recente para este host.</div>
                </div>
              ) : null}
              {details.recent_executions.map((execution) => (
                <div key={execution.id} className="list-item">
                  <div>
                    <div style={{ fontWeight: 700 }}>
                      {execution.patch_id} - {execution.result}
                    </div>
                    <div className="muted" style={{ marginTop: 4 }}>
                      {execution.schedule_name} - {execution.platform} - {execution.severity}
                    </div>
                  </div>
                  <div className="muted">{formatDateTimeSaoPaulo(execution.executed_at)}</div>
                </div>
              ))}
            </div>

            <div className="list">
              <div className="list-item">
                <div style={{ fontWeight: 700 }}>Comandos do agente</div>
              </div>
              {details.recent_commands.length === 0 ? (
                <div className="list-item">
                  <div className="muted">Nenhum comando operacional recente para este host.</div>
                </div>
              ) : null}
              {details.recent_commands.map((command) => (
                <div key={command.id} className="list-item">
                  <div>
                    <div style={{ fontWeight: 700 }}>
                      {command.command_type} - {command.status}
                    </div>
                    <div className="muted" style={{ marginTop: 4 }}>
                      solicitado por {command.requested_by}
                    </div>
                    {command.message ? (
                      <div className="muted" style={{ marginTop: 4 }}>
                        {command.message}
                      </div>
                    ) : null}
                  </div>
                  <div className="muted">{formatDateTimeSaoPaulo(command.created_at)}</div>
                </div>
              ))}
            </div>

            <div className="list">
              <div className="list-item" style={{ alignItems: "flex-start" }}>
                <div>
                  <div style={{ fontWeight: 700 }}>Timeline operacional</div>
                  <div className="muted" style={{ marginTop: 4 }}>
                    {timelineItems.length} eventos operacionais recentes para este host
                  </div>
                </div>
                <div style={{ display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap", justifyContent: "flex-end" }}>
                  <label style={{ display: "grid", gap: 6 }}>
                    <span className="field-label">Itens por pagina</span>
                    <select
                      className="select"
                      value={timelinePageSize}
                      onChange={(event) => setTimelinePageSize(Number(event.target.value))}
                    >
                      <option value={5}>5</option>
                      <option value={10}>10</option>
                      <option value={20}>20</option>
                    </select>
                  </label>
                  <div style={{ display: "flex", gap: 8, alignItems: "center", marginTop: 24 }}>
                    <button
                      className="btn"
                      disabled={timelinePage <= 1}
                      onClick={() => setTimelinePage((current) => Math.max(1, current - 1))}
                      type="button"
                    >
                      Anterior
                    </button>
                    <span className="muted">
                      Pagina {timelinePage} de {timelineTotalPages}
                    </span>
                    <button
                      className="btn"
                      disabled={timelinePage >= timelineTotalPages}
                      onClick={() =>
                        setTimelinePage((current) => Math.min(timelineTotalPages, current + 1))
                      }
                      type="button"
                    >
                      Proxima
                    </button>
                  </div>
                </div>
              </div>
              {timelineItems.length === 0 ? (
                <div className="list-item">
                  <div className="muted">Nenhum evento operacional recente para este host.</div>
                </div>
              ) : null}
              {paginatedTimelineItems.map((item) => (
                <div key={item.id} className="list-item">
                  <div>
                    <div style={{ fontWeight: 700 }}>
                      {item.title}
                    </div>
                    <div className="muted" style={{ marginTop: 4 }}>
                      {item.category} - {item.detail}
                    </div>
                    {item.message ? (
                      <div className="muted" style={{ marginTop: 4 }}>
                        {item.message}
                      </div>
                    ) : null}
                  </div>
                  <div style={{ textAlign: "right", display: "grid", gap: 8, justifyItems: "end" }}>
                    <StatusBadge variant={item.variant as "ok" | "warn" | "error"}>
                      {item.category}
                    </StatusBadge>
                    <div className="muted">{formatDateTimeSaoPaulo(item.occurredAt)}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        ) : null}
      </section>
    </div>
  );
}
