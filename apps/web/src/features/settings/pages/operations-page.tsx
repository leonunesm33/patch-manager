import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ActionMenu } from "@/components/common/action-menu";
import { StatCard } from "@/components/common/stat-card";
import { StatusBadge } from "@/components/common/status-badge";
import { formatDateTimeSaoPaulo } from "@/lib/datetime";
import { fetchDashboard } from "@/features/dashboard/api";
import type { DashboardResponse } from "@/features/dashboard/types";
import {
  approvePendingEnrollment,
  fetchConnectedAgents,
  fetchRecentAgentCommands,
  fetchPendingEnrollments,
  fetchRejectedEnrollments,
  fetchRevokedAgents,
  reopenRejectedEnrollment,
  rejectPendingEnrollment,
  requestConnectedAgentReboot,
  requeueRevokedAgent,
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
  const [connectedAgents, setConnectedAgents] = useState<ConnectedAgent[]>([]);
  const [pendingEnrollments, setPendingEnrollments] = useState<PendingAgentEnrollment[]>([]);
  const [rejectedEnrollments, setRejectedEnrollments] = useState<RejectedAgentEnrollment[]>([]);
  const [revokedAgents, setRevokedAgents] = useState<RevokedAgent[]>([]);
  const [recentCommands, setRecentCommands] = useState<AgentCommandHistoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionLoadingId, setActionLoadingId] = useState<string | null>(null);
  const [selectedPendingAgents, setSelectedPendingAgents] = useState<string[]>([]);
  const [selectedRebootAgents, setSelectedRebootAgents] = useState<string[]>([]);

  async function load() {
    const [
      dashboardResult,
      connectedResult,
      pendingResult,
      rejectedResult,
      revokedResult,
      commandsResult,
    ] = await Promise.allSettled([
      fetchDashboard(),
      fetchConnectedAgents(),
      fetchPendingEnrollments(),
      fetchRejectedEnrollments(),
      fetchRevokedAgents(),
      fetchRecentAgentCommands(),
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
    setActionLoadingId(agentId);
    try {
      await approvePendingEnrollment(agentId);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Falha ao aprovar o agente.");
    } finally {
      setActionLoadingId(null);
    }
  }

  async function handleReject(agentId: string) {
    setError(null);
    setActionLoadingId(agentId);
    try {
      await rejectPendingEnrollment(agentId);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Falha ao rejeitar o agente.");
    } finally {
      setActionLoadingId(null);
    }
  }

  async function handleRequeue(agentId: string) {
    setError(null);
    setActionLoadingId(agentId);
    try {
      await requeueRevokedAgent(agentId);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Falha ao reabrir a aprovacao do agente.");
    } finally {
      setActionLoadingId(null);
    }
  }

  async function handleReopenRejected(agentId: string) {
    setError(null);
    setActionLoadingId(agentId);
    try {
      await reopenRejectedEnrollment(agentId);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Falha ao reabrir a aprovacao do agente rejeitado.");
    } finally {
      setActionLoadingId(null);
    }
  }

  async function handleReboot(agentId: string) {
    setError(null);
    setActionLoadingId(agentId);
    try {
      await requestConnectedAgentReboot(agentId);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Falha ao solicitar reboot do host.");
    } finally {
      setActionLoadingId(null);
    }
  }

  async function handleBulkApprove() {
    if (selectedPendingAgents.length === 0) return;
    setError(null);
    setActionLoadingId("bulk-approve");
    try {
      await Promise.all(selectedPendingAgents.map((agentId) => approvePendingEnrollment(agentId)));
      setSelectedPendingAgents([]);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Falha ao aprovar os agentes selecionados.");
    } finally {
      setActionLoadingId(null);
    }
  }

  async function handleBulkReject() {
    if (selectedPendingAgents.length === 0) return;
    setError(null);
    setActionLoadingId("bulk-reject");
    try {
      await Promise.all(selectedPendingAgents.map((agentId) => rejectPendingEnrollment(agentId)));
      setSelectedPendingAgents([]);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Falha ao rejeitar os agentes selecionados.");
    } finally {
      setActionLoadingId(null);
    }
  }

  async function handleBulkReboot() {
    if (selectedRebootAgents.length === 0) return;
    setError(null);
    setActionLoadingId("bulk-reboot");
    try {
      await Promise.all(selectedRebootAgents.map((agentId) => requestConnectedAgentReboot(agentId)));
      setSelectedRebootAgents([]);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Falha ao solicitar reboot para os hosts selecionados.");
    } finally {
      setActionLoadingId(null);
    }
  }

  const windowsAgents = connectedAgents.filter((agent) => agent.platform.toLowerCase() === "windows");
  const rebootAgents = connectedAgents.filter((agent) => agent.reboot_required);

  return (
    <div>
      <section className="hero">
        <h1 className="hero-title">Acoes operacionais</h1>
        <p className="hero-copy">
          Esta area concentra as pendencias que exigem decisao rapida: reboot, aprovacao de agentes,
          reintegracao e acompanhamento do pool Windows.
        </p>
      </section>

      {error ? (
        <section className="panel section">
          <div className="section-title">Falha ao carregar operacao</div>
          <p className="muted" style={{ marginTop: 8 }}>
            {error}
          </p>
        </section>
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

      <section className="content-grid">
        <section className="panel section">
          <div className="section-header">
            <h2 className="section-title">Hosts com reboot pendente</h2>
            <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
              <span className="muted">{rebootAgents.length} hosts</span>
              <button
                className="btn"
                disabled={selectedRebootAgents.length === 0 || actionLoadingId === "bulk-reboot"}
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
                      onChange={(event) =>
                        setSelectedRebootAgents((current) =>
                          event.target.checked
                            ? [...current, agent.agent_id]
                            : current.filter((item) => item !== agent.agent_id),
                        )
                      }
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

      <section className="content-grid">
        <section className="panel section">
          <div className="section-header">
            <h2 className="section-title">Agentes aguardando aprovacao</h2>
            <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
              <span className="muted">{pendingEnrollments.length} itens</span>
              <button
                className="btn"
                disabled={selectedPendingAgents.length === 0 || actionLoadingId === "bulk-approve"}
                onClick={() => void handleBulkApprove()}
                type="button"
              >
                Aprovar em lote
              </button>
              <button
                className="btn"
                disabled={selectedPendingAgents.length === 0 || actionLoadingId === "bulk-reject"}
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
            {pendingEnrollments.map((agent) => (
              <div key={agent.agent_id} className="list-item">
                <div>
                  <label style={{ display: "flex", alignItems: "center", gap: 10, fontWeight: 700 }}>
                    <input
                      checked={selectedPendingAgents.includes(agent.agent_id)}
                      onChange={(event) =>
                        setSelectedPendingAgents((current) =>
                          event.target.checked
                            ? [...current, agent.agent_id]
                            : current.filter((item) => item !== agent.agent_id),
                        )
                      }
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
        </section>

        <section className="panel section">
          <div className="section-header">
            <h2 className="section-title">Agentes rejeitados</h2>
            <span className="muted">{rejectedEnrollments.length} itens</span>
          </div>
          <div className="list">
            {rejectedEnrollments.length === 0 ? (
              <div className="list-item">
                <div className="muted">Nenhum agente rejeitado agora.</div>
              </div>
            ) : null}
            {rejectedEnrollments.map((agent) => (
              <div key={agent.agent_id} className="list-item">
                <div>
                  <div style={{ fontWeight: 700 }}>{agent.hostname}</div>
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
        </section>

        <section className="panel section">
          <div className="section-header">
            <h2 className="section-title">Agentes revogados</h2>
            <span className="muted">{revokedAgents.length} itens</span>
          </div>
          <div className="list">
            {revokedAgents.length === 0 ? (
              <div className="list-item">
                <div className="muted">Nenhum agente revogado no momento.</div>
              </div>
            ) : null}
            {revokedAgents.map((agent) => (
              <div key={agent.agent_id} className="list-item">
                <div>
                  <div style={{ fontWeight: 700 }}>{agent.hostname ?? agent.agent_id}</div>
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
          {recentCommands.map((command) => (
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
      </section>
    </div>
  );
}
