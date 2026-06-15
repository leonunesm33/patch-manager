import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ActionMenu } from "@/components/common/action-menu";
import { Pagination, usePagination } from "@/components/common/pagination";
import { StatCard } from "@/components/common/stat-card";
import { StatusBadge } from "@/components/common/status-badge";
import { formatDateTimeSaoPaulo } from "@/lib/datetime";
import { fetchDashboard } from "@/features/dashboard/api";
import type { DashboardResponse } from "@/features/dashboard/types";
import {
  fetchPatchJobs,
  processPatchJobs,
  runPatchCycle,
} from "@/features/reports/api";
import type {
  PatchCycleRunResponse,
  PatchJobItem,
  PatchJobProcessResponse,
} from "@/features/reports/types";
import {
  approvePendingEnrollment,
  fetchConnectedAgents,
  fetchRecentAgentCommands,
  fetchPendingEnrollments,
  fetchRejectedEnrollments,
  fetchRevokedAgents,
  reintegrateConnectedAgent,
  reopenRejectedEnrollment,
  rejectPendingEnrollment,
  requestConnectedAgentReboot,
  requeueRevokedAgent,
  revokeConnectedAgent,
} from "@/features/settings/api";
import type {
  AgentCommandHistoryItem,
  ConnectedAgent,
  PendingAgentEnrollment,
  RejectedAgentEnrollment,
  RevokedAgent,
} from "@/features/settings/types";

export function OperationsPage() {
  const navigate = useNavigate();
  const [dashboard, setDashboard] = useState<DashboardResponse | null>(null);
  const [patchJobs, setPatchJobs] = useState<PatchJobItem[]>([]);
  const [connectedAgents, setConnectedAgents] = useState<ConnectedAgent[]>([]);
  const [pendingEnrollments, setPendingEnrollments] = useState<PendingAgentEnrollment[]>([]);
  const [rejectedEnrollments, setRejectedEnrollments] = useState<RejectedAgentEnrollment[]>([]);
  const [revokedAgents, setRevokedAgents] = useState<RevokedAgent[]>([]);
  const [recentCommands, setRecentCommands] = useState<AgentCommandHistoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionFeedback, setActionFeedback] = useState<{ tone: "ok" | "warn" | "error"; message: string } | null>(null);
  const [actionLoadingId, setActionLoadingId] = useState<string | null>(null);
  const [cycleResult, setCycleResult] = useState<PatchCycleRunResponse | null>(null);
  const [processResult, setProcessResult] = useState<PatchJobProcessResponse | null>(null);
  const [selectedPendingAgents, setSelectedPendingAgents] = useState<string[]>([]);
  const [selectedRebootAgents, setSelectedRebootAgents] = useState<string[]>([]);
  const [selectedConnectedAgents, setSelectedConnectedAgents] = useState<string[]>([]);
  const [selectedRejectedAgents, setSelectedRejectedAgents] = useState<string[]>([]);
  const [selectedRevokedAgents, setSelectedRevokedAgents] = useState<string[]>([]);

  async function load() {
    const [
      dashboardResult,
      connectedResult,
      pendingResult,
      rejectedResult,
      revokedResult,
      commandsResult,
      jobsResult,
    ] = await Promise.allSettled([
      fetchDashboard(),
      fetchConnectedAgents(),
      fetchPendingEnrollments(),
      fetchRejectedEnrollments(),
      fetchRevokedAgents(),
      fetchRecentAgentCommands(),
      fetchPatchJobs(),
    ]);

    if (dashboardResult.status === "fulfilled") {
      setDashboard(dashboardResult.value);
    }

    if (connectedResult.status === "fulfilled") {
      setConnectedAgents(connectedResult.value);
    }

    if (pendingResult.status === "fulfilled") {
      setPendingEnrollments(pendingResult.value);
    }

    if (rejectedResult.status === "fulfilled") {
      setRejectedEnrollments(rejectedResult.value);
    }

    if (revokedResult.status === "fulfilled") {
      setRevokedAgents(revokedResult.value);
    }

    if (commandsResult.status === "fulfilled") {
      setRecentCommands(commandsResult.value);
    }

    if (jobsResult.status === "fulfilled") {
      setPatchJobs(jobsResult.value);
    }
  }

  useEffect(() => {
    let active = true;

    async function run() {
      try {
        await load();
      } catch (err) {
        if (!active) return;
        setError(err instanceof Error ? err.message : "Falha ao carregar a operacao.");
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    }

    void run();

    return () => {
      active = false;
    };
  }, []);

  async function handleApprove(agentId: string) {
    setError(null);
    setActionFeedback(null);
    setActionLoadingId(agentId);
    try {
      await approvePendingEnrollment(agentId);
      await load();
      setActionFeedback({ tone: "ok", message: "Agente aprovado com sucesso." });
    } catch (err) {
      setActionFeedback({ tone: "error", message: err instanceof Error ? err.message : "Falha ao aprovar o agente." });
    } finally {
      setActionLoadingId(null);
    }
  }

  async function handleReject(agentId: string) {
    setError(null);
    setActionFeedback(null);
    setActionLoadingId(agentId);
    try {
      await rejectPendingEnrollment(agentId);
      await load();
      setActionFeedback({ tone: "ok", message: "Agente rejeitado com sucesso." });
    } catch (err) {
      setActionFeedback({ tone: "error", message: err instanceof Error ? err.message : "Falha ao rejeitar o agente." });
    } finally {
      setActionLoadingId(null);
    }
  }

  async function handleRequeue(agentId: string) {
    setError(null);
    setActionFeedback(null);
    setActionLoadingId(agentId);
    try {
      await requeueRevokedAgent(agentId);
      await load();
      setActionFeedback({ tone: "ok", message: "Aprovacao reaberta para o agente revogado." });
    } catch (err) {
      setActionFeedback({ tone: "error", message: err instanceof Error ? err.message : "Falha ao reabrir a aprovacao do agente." });
    } finally {
      setActionLoadingId(null);
    }
  }

  async function handleReopenRejected(agentId: string) {
    setError(null);
    setActionFeedback(null);
    setActionLoadingId(agentId);
    try {
      await reopenRejectedEnrollment(agentId);
      await load();
      setActionFeedback({ tone: "ok", message: "Aprovacao reaberta para o agente rejeitado." });
    } catch (err) {
      setActionFeedback({ tone: "error", message: err instanceof Error ? err.message : "Falha ao reabrir a aprovacao do agente rejeitado." });
    } finally {
      setActionLoadingId(null);
    }
  }

  async function handleReboot(agentId: string) {
    setError(null);
    setActionFeedback(null);
    setActionLoadingId(agentId);
    try {
      await requestConnectedAgentReboot(agentId);
      await load();
      setActionFeedback({ tone: "ok", message: "Solicitacao de reboot enviada para o agente." });
    } catch (err) {
      setActionFeedback({ tone: "error", message: err instanceof Error ? err.message : "Falha ao solicitar reboot do host." });
    } finally {
      setActionLoadingId(null);
    }
  }

  async function handleReintegrateConnected(agentId: string) {
    setError(null);
    setActionFeedback(null);
    setActionLoadingId(agentId);
    try {
      await reintegrateConnectedAgent(agentId);
      await load();
      setActionFeedback({ tone: "ok", message: "Reintegracao solicitada para o agente conectado." });
    } catch (err) {
      setActionFeedback({ tone: "error", message: err instanceof Error ? err.message : "Falha ao reintegrar o agente conectado." });
    } finally {
      setActionLoadingId(null);
    }
  }

  async function handleRevokeConnected(agentId: string) {
    setError(null);
    setActionFeedback(null);
    setActionLoadingId(agentId);
    try {
      await revokeConnectedAgent(agentId);
      await load();
      setActionFeedback({ tone: "ok", message: "Agente conectado revogado com sucesso." });
    } catch (err) {
      setActionFeedback({ tone: "error", message: err instanceof Error ? err.message : "Falha ao revogar o agente conectado." });
    } finally {
      setActionLoadingId(null);
    }
  }

  async function handleBulkApprove() {
    if (selectedPendingAgents.length === 0) {
      setActionFeedback({ tone: "warn", message: "Selecione ao menos um agente pendente para aprovar em lote." });
      return;
    }
    setError(null);
    setActionFeedback(null);
    setActionLoadingId("bulk-approve");
    try {
      await Promise.all(selectedPendingAgents.map((agentId) => approvePendingEnrollment(agentId)));
      setSelectedPendingAgents([]);
      await load();
      setActionFeedback({ tone: "ok", message: "Agentes pendentes aprovados em lote com sucesso." });
    } catch (err) {
      setActionFeedback({ tone: "error", message: err instanceof Error ? err.message : "Falha ao aprovar os agentes selecionados." });
    } finally {
      setActionLoadingId(null);
    }
  }

  async function handleBulkReject() {
    if (selectedPendingAgents.length === 0) {
      setActionFeedback({ tone: "warn", message: "Selecione ao menos um agente pendente para rejeitar em lote." });
      return;
    }
    setError(null);
    setActionFeedback(null);
    setActionLoadingId("bulk-reject");
    try {
      await Promise.all(selectedPendingAgents.map((agentId) => rejectPendingEnrollment(agentId)));
      setSelectedPendingAgents([]);
      await load();
      setActionFeedback({ tone: "ok", message: "Agentes pendentes rejeitados em lote com sucesso." });
    } catch (err) {
      setActionFeedback({ tone: "error", message: err instanceof Error ? err.message : "Falha ao rejeitar os agentes selecionados." });
    } finally {
      setActionLoadingId(null);
    }
  }

  async function handleBulkReboot() {
    if (selectedRebootAgents.length === 0) {
      setActionFeedback({ tone: "warn", message: "Selecione ao menos um host com reboot pendente." });
      return;
    }
    setError(null);
    setActionFeedback(null);
    setActionLoadingId("bulk-reboot");
    try {
      await Promise.all(selectedRebootAgents.map((agentId) => requestConnectedAgentReboot(agentId)));
      setSelectedRebootAgents([]);
      await load();
      setActionFeedback({ tone: "ok", message: "Solicitacao de reboot enviada para os hosts selecionados." });
    } catch (err) {
      setActionFeedback({ tone: "error", message: err instanceof Error ? err.message : "Falha ao solicitar reboot para os hosts selecionados." });
    } finally {
      setActionLoadingId(null);
    }
  }

  async function handleBulkReopenRejected() {
    if (selectedRejectedAgents.length === 0) {
      setActionFeedback({ tone: "warn", message: "Selecione ao menos um agente rejeitado para reabrir em lote." });
      return;
    }
    setError(null);
    setActionFeedback(null);
    setActionLoadingId("bulk-reopen-rejected");
    try {
      await Promise.all(selectedRejectedAgents.map((agentId) => reopenRejectedEnrollment(agentId)));
      setSelectedRejectedAgents([]);
      await load();
      setActionFeedback({ tone: "ok", message: "Aprovacao reaberta para os agentes rejeitados selecionados." });
    } catch (err) {
      setActionFeedback({ tone: "error", message: err instanceof Error ? err.message : "Falha ao reabrir os agentes rejeitados selecionados." });
    } finally {
      setActionLoadingId(null);
    }
  }

  async function handleBulkRequeueRevoked() {
    if (selectedRevokedAgents.length === 0) {
      setActionFeedback({ tone: "warn", message: "Selecione ao menos um agente revogado para reabrir em lote." });
      return;
    }
    setError(null);
    setActionFeedback(null);
    setActionLoadingId("bulk-requeue-revoked");
    try {
      await Promise.all(selectedRevokedAgents.map((agentId) => requeueRevokedAgent(agentId)));
      setSelectedRevokedAgents([]);
      await load();
      setActionFeedback({ tone: "ok", message: "Aprovacao reaberta para os agentes revogados selecionados." });
    } catch (err) {
      setActionFeedback({ tone: "error", message: err instanceof Error ? err.message : "Falha ao reabrir os agentes revogados selecionados." });
    } finally {
      setActionLoadingId(null);
    }
  }

  async function handleBulkReintegrateConnected() {
    if (selectedConnectedAgents.length === 0) {
      setActionFeedback({ tone: "warn", message: "Selecione ao menos um agente conectado para reintegrar em lote." });
      return;
    }
    setError(null);
    setActionFeedback(null);
    setActionLoadingId("bulk-reintegrate");
    try {
      await Promise.all(selectedConnectedAgents.map((agentId) => reintegrateConnectedAgent(agentId)));
      setSelectedConnectedAgents([]);
      await load();
      setActionFeedback({ tone: "ok", message: "Reintegracao solicitada para os agentes conectados selecionados." });
    } catch (err) {
      setActionFeedback({ tone: "error", message: err instanceof Error ? err.message : "Falha ao reintegrar os agentes conectados selecionados." });
    } finally {
      setActionLoadingId(null);
    }
  }

  async function handleBulkRevokeConnected() {
    if (selectedConnectedAgents.length === 0) {
      setActionFeedback({ tone: "warn", message: "Selecione ao menos um agente conectado para revogar em lote." });
      return;
    }
    setError(null);
    setActionFeedback(null);
    setActionLoadingId("bulk-revoke");
    try {
      await Promise.all(selectedConnectedAgents.map((agentId) => revokeConnectedAgent(agentId)));
      setSelectedConnectedAgents([]);
      await load();
      setActionFeedback({ tone: "ok", message: "Agentes conectados revogados em lote com sucesso." });
    } catch (err) {
      setActionFeedback({ tone: "error", message: err instanceof Error ? err.message : "Falha ao revogar os agentes conectados selecionados." });
    } finally {
      setActionLoadingId(null);
    }
  }

  async function handleRunPatchCycle() {
    setError(null);
    setActionFeedback(null);
    setActionLoadingId("run-patch-cycle");
    try {
      const response = await runPatchCycle();
      setCycleResult(response);
      await load();
      setActionFeedback({
        tone: response.jobs_enqueued > 0 || response.reboot_commands_enqueued > 0 ? "ok" : "warn",
        message:
          response.jobs_enqueued > 0 || response.reboot_commands_enqueued > 0
            ? `${response.jobs_enqueued} jobs e ${response.reboot_commands_enqueued} comandos de reboot enfileirados.`
            : "Ciclo executado, mas nada novo foi enfileirado.",
      });
    } catch (err) {
      setActionFeedback({ tone: "error", message: err instanceof Error ? err.message : "Falha ao gerar jobs agora." });
    } finally {
      setActionLoadingId(null);
    }
  }

  async function handleProcessPatchQueue() {
    setError(null);
    setActionFeedback(null);
    setActionLoadingId("process-patch-queue");
    try {
      const response = await processPatchJobs();
      setProcessResult(response);
      await load();
      setActionFeedback({
        tone: response.failed_executions > 0 ? "warn" : "ok",
        message: `${response.jobs_started} jobs iniciados, ${response.jobs_processed} processados e ${response.failed_executions} falhas.`,
      });
    } catch (err) {
      setActionFeedback({ tone: "error", message: err instanceof Error ? err.message : "Falha ao processar a fila." });
    } finally {
      setActionLoadingId(null);
    }
  }

  const windowsAgents = connectedAgents.filter((agent) => agent.platform.toLowerCase() === "windows");
  const rebootAgents = connectedAgents.filter((agent) => agent.reboot_required);
  const pendingPatchJobs = patchJobs.filter((job) => job.status === "pending");
  const runningPatchJobs = patchJobs.filter((job) => job.status === "running");
  const failedPatchJobs = patchJobs.filter((job) => job.status === "failed");
  const connectedPagination = usePagination(connectedAgents);
  const pendingEnrollPagination = usePagination(pendingEnrollments);
  const rejectedEnrollPagination = usePagination(rejectedEnrollments);
  const revokedPagination = usePagination(revokedAgents);
  const commandsPagination = usePagination(recentCommands);

  return (
    <div>
      {error ? (
        <section className="panel section">
          <div className="section-title">Falha ao carregar operacao</div>
          <p className="muted" style={{ marginTop: 8 }}>
            {error}
          </p>
        </section>
      ) : null}
      {actionFeedback ? (
        <div className={`inline-feedback inline-feedback-${actionFeedback.tone}`}>
          {actionFeedback.message}
        </div>
      ) : null}

      {loading ? (
        <section className="panel section">
          <div className="section-title">Carregando visao operacional...</div>
        </section>
      ) : (
        <section className="cards-grid">
          <StatCard
            label="Acoes pendentes"
            value={String(dashboard?.pending_actions.length ?? 0)}
            detail="itens que pedem resposta do time"
            tone="#ffc542"
          />
          <StatCard
            label="Reboot pendente"
            value={String(rebootAgents.length)}
            detail="hosts Linux aguardando decisao pos-patch"
            tone="#ff8a3d"
          />
          <StatCard
            label="Agentes pendentes"
            value={String(pendingEnrollments.length)}
            detail="hosts aguardando aprovacao ou rejeicao"
            tone="#00d4ff"
          />
          <StatCard
            label="Agentes rejeitados"
            value={String(rejectedEnrollments.length)}
            detail="hosts rejeitados aguardando nova decisao"
            tone="#ff6b6b"
          />
          <StatCard
            label="Agentes Windows"
            value={String(windowsAgents.length)}
            detail="pool conectado para inventario e StartScan controlado"
            tone="#00e5a0"
          />
        </section>
      )}

      <section className="panel section">
        <div className="section-header">
          <h2 className="section-title">Pendencias prioritarias</h2>
          <span className="muted">{dashboard?.pending_actions.length ?? 0} itens</span>
        </div>
        <div className="list">
          {(dashboard?.pending_actions ?? []).length === 0 ? (
            <div className="list-item">
              <div className="muted">Nenhuma pendencia prioritaria neste momento.</div>
            </div>
          ) : null}
          {(dashboard?.pending_actions ?? []).map((item) => (
            <div key={`${item.action_type}-${item.title}`} className="list-item">
              <div>
                <div style={{ fontWeight: 700 }}>{item.title}</div>
                <div className="muted" style={{ marginTop: 4 }}>
                  {item.detail}
                </div>
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                <StatusBadge
                  variant={
                    item.severity === "error"
                      ? "error"
                      : item.severity === "warn"
                        ? "warn"
                        : "ok"
                  }
                >
                  {item.severity}
                </StatusBadge>
                <button
                  className="btn"
                  onClick={() =>
                    navigate(
                      item.action_type === "failed_jobs"
                        ? "/reports"
                        : item.action_type === "agent_approval"
                          ? "/settings"
                          : "/dashboard",
                    )
                  }
                  type="button"
                >
                  Abrir
                </button>
              </div>
            </div>
          ))}
        </div>
      </section>

      <section className="panel section">
        <div className="section-header">
          <div>
            <h2 className="section-title">Controle da fila de patches</h2>
            <span className="muted">
              Acionamento manual do scheduler e worker para diagnostico ou execucao assistida.
            </span>
          </div>
          <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
            <button
              className="btn"
              disabled={actionLoadingId === "run-patch-cycle"}
              onClick={() => void handleRunPatchCycle()}
              type="button"
            >
              {actionLoadingId === "run-patch-cycle" ? "Gerando..." : "Gerar jobs agora"}
            </button>
            <button
              className="btn btn-primary"
              disabled={actionLoadingId === "process-patch-queue"}
              onClick={() => void handleProcessPatchQueue()}
              type="button"
            >
              {actionLoadingId === "process-patch-queue" ? "Processando..." : "Executar proximo ciclo"}
            </button>
          </div>
        </div>
        <div className="stats-mini-grid">
          <div className="list-item">
            <div>
              <div className="eyebrow">Fila</div>
              <div style={{ fontSize: 28, fontWeight: 800 }}>{pendingPatchJobs.length}</div>
              <div className="muted">jobs pendentes</div>
            </div>
          </div>
          <div className="list-item">
            <div>
              <div className="eyebrow">Execucao</div>
              <div style={{ fontSize: 28, fontWeight: 800 }}>{runningPatchJobs.length}</div>
              <div className="muted">jobs em andamento</div>
            </div>
          </div>
          <div className="list-item">
            <div>
              <div className="eyebrow">Falhas</div>
              <div style={{ fontSize: 28, fontWeight: 800 }}>{failedPatchJobs.length}</div>
              <div className="muted">jobs com erro recente</div>
            </div>
          </div>
        </div>
        {cycleResult ? (
          <div className="list-item" style={{ marginTop: 12 }}>
            <div>
              <div style={{ fontWeight: 700 }}>Ultimo ciclo de geracao</div>
              <div className="muted" style={{ marginTop: 4 }}>
                {cycleResult.approved_patches} patches aprovados, {cycleResult.schedules_matched} agendas combinadas,{" "}
                {cycleResult.jobs_enqueued} jobs e {cycleResult.reboot_commands_enqueued} comandos de reboot.
              </div>
            </div>
          </div>
        ) : null}
        {processResult ? (
          <div className="list-item" style={{ marginTop: 12 }}>
            <div>
              <div style={{ fontWeight: 700 }}>Ultimo ciclo de processamento</div>
              <div className="muted" style={{ marginTop: 4 }}>
                {processResult.pending_jobs_before} jobs aguardavam, {processResult.jobs_started} iniciaram,{" "}
                {processResult.jobs_processed} foram processados e {processResult.failed_executions} falharam.
              </div>
            </div>
          </div>
        ) : null}
      </section>

      <section className="content-grid">
        <section className="panel section">
          <div className="section-header">
            <h2 className="section-title">Hosts com reboot pendente</h2>
            <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
              <span className="muted">{rebootAgents.length} hosts</span>
              <button
                className="btn"
                disabled={actionLoadingId === "bulk-reboot"}
                onClick={() => void handleBulkReboot()}
                type="button"
              >
                Solicitar reboot em lote
              </button>
            </div>
          </div>
          <div className="list">
            {rebootAgents.length === 0 ? (
              <div className="list-item">
                <div className="muted">Nenhum host aguardando reboot.</div>
              </div>
            ) : null}
            {rebootAgents.map((agent) => (
              <div key={agent.agent_id} className="list-item">
                <div>
                  <label style={{ display: "flex", alignItems: "center", gap: 10, fontWeight: 700 }}>
                    <input
                      checked={selectedRebootAgents.includes(agent.agent_id)}
                      onChange={(event) => {
                        setActionFeedback(null);
                        setSelectedRebootAgents((current) =>
                          event.target.checked
                            ? [...current, agent.agent_id]
                            : current.filter((item) => item !== agent.agent_id),
                        );
                      }}
                      type="checkbox"
                    />
                    {agent.hostname}
                  </label>
                  <div className="muted" style={{ marginTop: 4 }}>
                    {agent.platform} - {agent.primary_ip ?? "n/d"}
                  </div>
                  <div className="muted" style={{ marginTop: 4 }}>
                      Ultimo heartbeat em {formatDateTimeSaoPaulo(agent.last_seen_at)}
                  </div>
                </div>
                <button className="btn" onClick={() => navigate("/settings")} type="button">
                  Ver politica
                </button>
                <ActionMenu
                  items={[
                    {
                      label: "Solicitar reboot",
                      disabled: actionLoadingId === agent.agent_id,
                      onSelect: () => void handleReboot(agent.agent_id),
                    },
                  ]}
                />
              </div>
            ))}
          </div>
        </section>

        <section className="panel section">
          <div className="section-header">
            <h2 className="section-title">Pool Windows conectado</h2>
            <span className="muted">{windowsAgents.length} agentes</span>
          </div>
          <div className="list">
            {windowsAgents.length === 0 ? (
              <div className="list-item">
                <div className="muted">Nenhum agente Windows conectado no momento.</div>
              </div>
            ) : null}
            {windowsAgents.map((agent) => (
              <div key={agent.agent_id} className="list-item">
                <div>
                  <div style={{ fontWeight: 700 }}>{agent.hostname}</div>
                  <div className="muted" style={{ marginTop: 4 }}>
                    Modo {agent.execution_mode ?? "unknown"} - {agent.os_name} {agent.os_version}
                  </div>
                  <div className="muted" style={{ marginTop: 4 }}>
                    {agent.installed_update_count ?? agent.installed_packages ?? 0} updates instalados -{" "}
                    {agent.upgradable_packages ?? 0} pendentes
                  </div>
                  {agent.pending_update_summary ? (
                    <div className="muted" style={{ marginTop: 4 }}>
                      Pendencias: {agent.pending_update_summary}
                    </div>
                  ) : null}
                  {agent.windows_update_source ? (
                    <div className="muted" style={{ marginTop: 4 }}>
                      Fonte: {agent.windows_update_source}
                    </div>
                  ) : null}
                </div>
                <button className="btn" onClick={() => navigate("/settings")} type="button">
                  Ajustar politica
                </button>
              </div>
            ))}
          </div>
        </section>
      </section>

      <section className="panel section">
        <div className="section-header">
          <h2 className="section-title">Agentes conectados</h2>
          <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
            <span className="muted">{connectedAgents.length} itens</span>
            <button
              className="btn"
              disabled={actionLoadingId === "bulk-reintegrate"}
              onClick={() => void handleBulkReintegrateConnected()}
              type="button"
            >
              Reintegrar em lote
            </button>
            <button
              className="btn"
              disabled={actionLoadingId === "bulk-revoke"}
              onClick={() => void handleBulkRevokeConnected()}
              type="button"
            >
              Revogar em lote
            </button>
          </div>
        </div>
        <div className="list">
          {connectedAgents.length === 0 ? (
            <div className="list-item">
              <div className="muted">Nenhum agente conectado agora.</div>
            </div>
          ) : null}
          {connectedPagination.pageItems.map((agent) => (
            <div key={agent.agent_id} className="list-item">
              <div>
                <label style={{ display: "flex", alignItems: "center", gap: 10, fontWeight: 700 }}>
                  <input
                    checked={selectedConnectedAgents.includes(agent.agent_id)}
                    onChange={(event) => {
                      setActionFeedback(null);
                      setSelectedConnectedAgents((current) =>
                        event.target.checked
                          ? [...current, agent.agent_id]
                          : current.filter((item) => item !== agent.agent_id),
                      );
                    }}
                    type="checkbox"
                  />
                  {agent.hostname}
                </label>
                <div className="muted" style={{ marginTop: 4 }}>
                  {agent.platform} - {agent.primary_ip ?? "n/d"}
                </div>
                <div className="muted" style={{ marginTop: 4 }}>
                  {agent.post_patch_state
                    ? `pos-patch: ${agent.post_patch_state}`
                    : `modo ${agent.execution_mode ?? "unknown"}`}
                </div>
              </div>
              <ActionMenu
                items={[
                  {
                    label: "Forcar reintegracao",
                    disabled: actionLoadingId === agent.agent_id,
                    onSelect: () => void handleReintegrateConnected(agent.agent_id),
                  },
                  {
                    label: "Revogar agente",
                    disabled: actionLoadingId === agent.agent_id,
                    onSelect: () => void handleRevokeConnected(agent.agent_id),
                    tone: "danger",
                  },
                ]}
              />
            </div>
          ))}
        </div>
        <Pagination
          page={connectedPagination.page}
          totalPages={connectedPagination.totalPages}
          from={connectedPagination.from}
          to={connectedPagination.to}
          total={connectedPagination.total}
          onPageChange={connectedPagination.setPage}
        />
      </section>

      <section className="content-grid">
        <section className="panel section">
          <div className="section-header">
            <h2 className="section-title">Agentes aguardando aprovacao</h2>
            <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
              <span className="muted">{pendingEnrollments.length} itens</span>
              <button
                className="btn"
                disabled={actionLoadingId === "bulk-approve"}
                onClick={() => void handleBulkApprove()}
                type="button"
              >
                Aprovar em lote
              </button>
              <button
                className="btn"
                disabled={actionLoadingId === "bulk-reject"}
                onClick={() => void handleBulkReject()}
                type="button"
              >
                Rejeitar em lote
              </button>
            </div>
          </div>
          <div className="list">
            {pendingEnrollments.length === 0 ? (
              <div className="list-item">
                <div className="muted">Nenhum agente pendente agora.</div>
              </div>
            ) : null}
            {pendingEnrollPagination.pageItems.map((agent) => (
              <div key={agent.agent_id} className="list-item">
                <div>
                  <label style={{ display: "flex", alignItems: "center", gap: 10, fontWeight: 700 }}>
                    <input
                    checked={selectedPendingAgents.includes(agent.agent_id)}
                    onChange={(event) => {
                      setActionFeedback(null);
                      setSelectedPendingAgents((current) =>
                        event.target.checked
                          ? [...current, agent.agent_id]
                          : current.filter((item) => item !== agent.agent_id),
                      );
                    }}
                    type="checkbox"
                  />
                    {agent.hostname}
                  </label>
                  <div className="muted" style={{ marginTop: 4 }}>
                    {agent.platform} - {agent.primary_ip}
                  </div>
                  <div className="muted" style={{ marginTop: 4 }}>
                    Solicitado em {formatDateTimeSaoPaulo(agent.requested_at)}
                  </div>
                </div>
                <ActionMenu
                  items={[
                    {
                      label: "Aprovar",
                      disabled: actionLoadingId === agent.agent_id,
                      onSelect: () => void handleApprove(agent.agent_id),
                    },
                    {
                      label: "Rejeitar",
                      disabled: actionLoadingId === agent.agent_id,
                      onSelect: () => void handleReject(agent.agent_id),
                      tone: "danger",
                    },
                  ]}
                />
              </div>
            ))}
          </div>
          <Pagination
            page={pendingEnrollPagination.page}
            totalPages={pendingEnrollPagination.totalPages}
            from={pendingEnrollPagination.from}
            to={pendingEnrollPagination.to}
            total={pendingEnrollPagination.total}
            onPageChange={pendingEnrollPagination.setPage}
          />
        </section>

        <section className="panel section">
          <div className="section-header">
            <h2 className="section-title">Agentes rejeitados</h2>
            <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
              <span className="muted">{rejectedEnrollments.length} itens</span>
              <button
                className="btn"
                disabled={actionLoadingId === "bulk-reopen-rejected"}
                onClick={() => void handleBulkReopenRejected()}
                type="button"
              >
                Reabrir em lote
              </button>
            </div>
          </div>
          <div className="list">
            {rejectedEnrollments.length === 0 ? (
              <div className="list-item">
                <div className="muted">Nenhum agente rejeitado agora.</div>
              </div>
            ) : null}
            {rejectedEnrollPagination.pageItems.map((agent) => (
              <div key={agent.agent_id} className="list-item">
                <div>
                  <label style={{ display: "flex", alignItems: "center", gap: 10, fontWeight: 700 }}>
                    <input
                    checked={selectedRejectedAgents.includes(agent.agent_id)}
                    onChange={(event) => {
                      setActionFeedback(null);
                      setSelectedRejectedAgents((current) =>
                        event.target.checked
                          ? [...current, agent.agent_id]
                          : current.filter((item) => item !== agent.agent_id),
                      );
                    }}
                    type="checkbox"
                  />
                    {agent.hostname}
                  </label>
                  <div className="muted" style={{ marginTop: 4 }}>
                    {agent.platform} - {agent.primary_ip}
                  </div>
                  <div className="muted" style={{ marginTop: 4 }}>
                    Solicitado em {formatDateTimeSaoPaulo(agent.requested_at)}
                  </div>
                </div>
                <ActionMenu
                  items={[
                    {
                      label: "Reabrir aprovacao",
                      disabled: actionLoadingId === agent.agent_id,
                      onSelect: () => void handleReopenRejected(agent.agent_id),
                    },
                  ]}
                />
              </div>
            ))}
          </div>
          <Pagination
            page={rejectedEnrollPagination.page}
            totalPages={rejectedEnrollPagination.totalPages}
            from={rejectedEnrollPagination.from}
            to={rejectedEnrollPagination.to}
            total={rejectedEnrollPagination.total}
            onPageChange={rejectedEnrollPagination.setPage}
          />
        </section>

        <section className="panel section">
          <div className="section-header">
            <h2 className="section-title">Agentes revogados</h2>
            <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
              <span className="muted">{revokedAgents.length} itens</span>
              <button
                className="btn"
                disabled={actionLoadingId === "bulk-requeue-revoked"}
                onClick={() => void handleBulkRequeueRevoked()}
                type="button"
              >
                Reabrir em lote
              </button>
            </div>
          </div>
          <div className="list">
            {revokedAgents.length === 0 ? (
              <div className="list-item">
                <div className="muted">Nenhum agente revogado no momento.</div>
              </div>
            ) : null}
            {revokedPagination.pageItems.map((agent) => (
              <div key={agent.agent_id} className="list-item">
                <div>
                  <label style={{ display: "flex", alignItems: "center", gap: 10, fontWeight: 700 }}>
                    <input
                    checked={selectedRevokedAgents.includes(agent.agent_id)}
                    onChange={(event) => {
                      setActionFeedback(null);
                      setSelectedRevokedAgents((current) =>
                        event.target.checked
                          ? [...current, agent.agent_id]
                          : current.filter((item) => item !== agent.agent_id),
                      );
                    }}
                    type="checkbox"
                  />
                    {agent.hostname ?? agent.agent_id}
                  </label>
                  <div className="muted" style={{ marginTop: 4 }}>
                    {agent.platform} - {agent.primary_ip ?? "n/d"}
                  </div>
                  <div className="muted" style={{ marginTop: 4 }}>
                    Ultimo registro{" "}
                    {agent.last_known_at
                          ? formatDateTimeSaoPaulo(agent.last_known_at)
                      : "indisponivel"}
                  </div>
                </div>
                <ActionMenu
                  items={[
                    {
                      label: "Reabrir aprovacao",
                      disabled: actionLoadingId === agent.agent_id,
                      onSelect: () => void handleRequeue(agent.agent_id),
                    },
                  ]}
                />
              </div>
            ))}
          </div>
          <Pagination
            page={revokedPagination.page}
            totalPages={revokedPagination.totalPages}
            from={revokedPagination.from}
            to={revokedPagination.to}
            total={revokedPagination.total}
            onPageChange={revokedPagination.setPage}
          />
        </section>
      </section>

      <section className="panel section">
        <div className="section-header">
          <h2 className="section-title">Historico de comandos operacionais</h2>
          <span className="muted">{recentCommands.length} comandos recentes</span>
        </div>
        <div className="list">
          {recentCommands.length === 0 ? (
            <div className="list-item">
              <div className="muted">Nenhum comando operacional emitido ainda.</div>
            </div>
          ) : null}
          {commandsPagination.pageItems.map((command) => (
            <div key={command.id} className="list-item">
              <div>
                <div style={{ fontWeight: 700 }}>
                  {command.command_type} - {command.agent_id}
                </div>
                <div className="muted" style={{ marginTop: 4 }}>
                    solicitado por {command.requested_by} em {formatDateTimeSaoPaulo(command.created_at)}
                </div>
                {command.message ? (
                  <div className="muted" style={{ marginTop: 4 }}>
                    {command.message}
                  </div>
                ) : null}
              </div>
              <StatusBadge
                variant={
                  command.status === "failed"
                    ? "error"
                    : command.status === "completed"
                      ? "ok"
                      : "warn"
                }
              >
                {command.status}
              </StatusBadge>
            </div>
          ))}
        </div>
        <Pagination
          page={commandsPagination.page}
          totalPages={commandsPagination.totalPages}
          from={commandsPagination.from}
          to={commandsPagination.to}
          total={commandsPagination.total}
          onPageChange={commandsPagination.setPage}
        />
      </section>
    </div>
  );
}
