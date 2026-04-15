import { useEffect, useState } from "react";
import { ActionMenu } from "@/components/common/action-menu";
import { ConfirmModal } from "@/components/common/confirm-modal";
import { StatusBadge } from "@/components/common/status-badge";
import { formatDateTimeSaoPaulo } from "@/lib/datetime";
import {
  approvePendingEnrollment,
  downloadOperationalEventsCsv,
  fetchConnectedAgents,
  fetchPendingEnrollments,
  fetchRejectedEnrollments,
  fetchRevokedAgents,
  fetchStoppedAgents,
  fetchSchedulerStatus,
  fetchSettings,
  startScheduler,
  stopScheduler,
  reintegrateConnectedAgent,
  requeueRevokedAgent,
  reopenRejectedEnrollment,
  rejectPendingEnrollment,
  requestConnectedAgentReboot,
  revokeConnectedAgent,
  updateBootstrapToken,
  updateLinuxExecutionMode,
} from "@/features/settings/api";
import type {
  ConnectedAgent,
  ExecutionSettings,
  PendingAgentEnrollment,
  RejectedAgentEnrollment,
  RevokedAgent,
  SchedulerStatusResponse,
  SettingsResponse,
  StoppedAgent,
} from "@/features/settings/types";

export function SettingsPage() {
  const [connectedAgents, setConnectedAgents] = useState<ConnectedAgent[]>([]);
  const [pendingEnrollments, setPendingEnrollments] = useState<PendingAgentEnrollment[]>([]);
  const [rejectedEnrollments, setRejectedEnrollments] = useState<RejectedAgentEnrollment[]>([]);
  const [revokedAgents, setRevokedAgents] = useState<RevokedAgent[]>([]);
  const [stoppedAgents, setStoppedAgents] = useState<StoppedAgent[]>([]);
  const [settings, setSettings] = useState<SettingsResponse | null>(null);
  const [schedulerStatus, setSchedulerStatus] = useState<SchedulerStatusResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [schedulerLoading, setSchedulerLoading] = useState(false);
  const [executionLoading, setExecutionLoading] = useState(false);
  const [approvalLoadingId, setApprovalLoadingId] = useState<string | null>(null);
  const [bootstrapTokenDraft, setBootstrapTokenDraft] = useState("");
  const [installServerUrlDraft, setInstallServerUrlDraft] = useState("");
  const [bootstrapLoading, setBootstrapLoading] = useState(false);
  const [allowedPatternsDraft, setAllowedPatternsDraft] = useState("");
  const [timeoutDraft, setTimeoutDraft] = useState("900");
  const [rebootGraceDraft, setRebootGraceDraft] = useState("60");
  const [windowsTimeoutDraft, setWindowsTimeoutDraft] = useState("60");
  const [windowsRebootGraceDraft, setWindowsRebootGraceDraft] = useState("60");
  const [confirmRealApplyOpen, setConfirmRealApplyOpen] = useState(false);
  const [eventFilter, setEventFilter] = useState<"all" | "info" | "warn" | "error">("all");
  const [exportLoading, setExportLoading] = useState(false);
  const [agentActionLoadingId, setAgentActionLoadingId] = useState<string | null>(null);
  const [confirmAgentAction, setConfirmAgentAction] = useState<
    | {
        type: "revoke" | "reintegrate" | "reboot";
        agent: ConnectedAgent;
      }
    | {
        type: "requeue";
        agent: RevokedAgent;
      }
    | {
        type: "reopen-rejected";
        agent: RejectedAgentEnrollment;
      }
    | null
  >(null);
  const installCommand = settings
    ? `curl -fsSL "${settings.bootstrap.agent_install_server_url}/api/v1/agents/install/linux.sh?server_url=${encodeURIComponent(
        settings.bootstrap.agent_install_server_url,
      )}&bootstrap_token=${encodeURIComponent(settings.bootstrap.agent_bootstrap_token)}" | sudo bash`
    : "";
  const upgradeCommand = settings
    ? `curl -fsSL "${settings.bootstrap.agent_install_server_url}/api/v1/agents/install/linux-upgrade.sh?server_url=${encodeURIComponent(
        settings.bootstrap.agent_install_server_url,
      )}" | sudo bash`
    : "";
  const windowsInstallCommand = settings
    ? `powershell -ExecutionPolicy Bypass -Command "irm '${settings.bootstrap.agent_install_server_url}/api/v1/agents/install/windows.ps1?server_url=${encodeURIComponent(
        settings.bootstrap.agent_install_server_url,
      )}&bootstrap_token=${encodeURIComponent(settings.bootstrap.agent_bootstrap_token)}' | iex"`
    : "";
  const windowsUpgradeCommand = settings
    ? `powershell -ExecutionPolicy Bypass -Command "irm '${settings.bootstrap.agent_install_server_url}/api/v1/agents/install/windows-upgrade.ps1?server_url=${encodeURIComponent(
        settings.bootstrap.agent_install_server_url,
      )}' | iex"`
    : "";
  const realApplyAuditLabel =
    settings?.execution.real_apply_last_enabled_by && settings.execution.real_apply_last_enabled_at
      ? `Ultima habilitacao por ${settings.execution.real_apply_last_enabled_by} em ${formatDateTimeSaoPaulo(
          settings.execution.real_apply_last_enabled_at,
        )}`
      : "Nenhuma habilitacao registrada ainda.";
  const filteredEvents =
    eventFilter === "all"
      ? settings?.events ?? []
      : (settings?.events ?? []).filter((event) => event.severity === eventFilter);
  const lifecycleItems = [
    ...connectedAgents.map((agent) => ({
      id: `connected-${agent.agent_id}`,
      agent_id: agent.agent_id,
      hostname: agent.hostname,
      platform: agent.platform,
      status: "connected" as const,
      detail: `${agent.os_name} ${agent.os_version}`,
      secondary: agent.primary_ip ?? "n/d",
      occurred_at: agent.last_seen_at,
    })),
    ...pendingEnrollments.map((agent) => ({
      id: `pending-${agent.agent_id}`,
      agent_id: agent.agent_id,
      hostname: agent.hostname,
      platform: agent.platform,
      status: "pending" as const,
      detail: `${agent.os_name} ${agent.os_version}`,
      secondary: agent.primary_ip,
      occurred_at: agent.requested_at,
    })),
    ...rejectedEnrollments.map((agent) => ({
      id: `rejected-${agent.agent_id}`,
      agent_id: agent.agent_id,
      hostname: agent.hostname,
      platform: agent.platform,
      status: "rejected" as const,
      detail: `${agent.os_name} ${agent.os_version}`,
      secondary: agent.primary_ip,
      occurred_at: agent.requested_at,
    })),
    ...revokedAgents.map((agent) => ({
      id: `revoked-${agent.agent_id}`,
      agent_id: agent.agent_id,
      hostname: agent.hostname ?? agent.agent_id,
      platform: agent.platform,
      status: "revoked" as const,
      detail: `${agent.os_name ?? "Host"} ${agent.os_version ?? ""}`.trim(),
      secondary: agent.primary_ip ?? "n/d",
      occurred_at: agent.last_known_at ?? null,
    })),
    ...stoppedAgents.map((agent) => ({
      id: `stopped-${agent.agent_id}`,
      agent_id: agent.agent_id,
      hostname: agent.hostname ?? agent.agent_id,
      platform: agent.platform,
      status: "stopped" as const,
      detail: `${agent.os_name ?? "Host"} ${agent.os_version ?? ""}`.trim(),
      secondary: agent.primary_ip ?? "n/d",
      occurred_at: agent.last_seen_at ?? null,
    })),
  ].sort((left, right) => {
    const leftTime = left.occurred_at ? new Date(left.occurred_at).getTime() : 0;
    const rightTime = right.occurred_at ? new Date(right.occurred_at).getTime() : 0;
    return rightTime - leftTime;
  });

  function getLifecycleVariant(status: (typeof lifecycleItems)[number]["status"]) {
    if (status === "connected") return "ok";
    if (status === "pending") return "warn";
    if (status === "stopped") return "warn";
    if (status === "rejected") return "error";
    return "error";
  }

  useEffect(() => {
    let active = true;

    async function load() {
      try {
        const [settingsResponse, schedulerResponse, agentsResponse, enrollmentsResponse, rejectedResponse, revokedResponse, stoppedResponse] = await Promise.all([
          fetchSettings(),
          fetchSchedulerStatus(),
          fetchConnectedAgents(),
          fetchPendingEnrollments(),
          fetchRejectedEnrollments(),
          fetchRevokedAgents(),
          fetchStoppedAgents(),
        ]);
        if (!active) return;
        setSettings(settingsResponse);
        setBootstrapTokenDraft(settingsResponse.bootstrap.agent_bootstrap_token);
        setInstallServerUrlDraft(settingsResponse.bootstrap.agent_install_server_url);
        setAllowedPatternsDraft(settingsResponse.execution.allowed_package_patterns.join(", "));
        setTimeoutDraft(String(settingsResponse.execution.apt_apply_timeout_seconds));
        setRebootGraceDraft(String(settingsResponse.execution.reboot_grace_minutes));
        setWindowsTimeoutDraft(String(settingsResponse.execution.windows_command_timeout_seconds));
        setWindowsRebootGraceDraft(String(settingsResponse.execution.windows_reboot_grace_minutes));
        setSchedulerStatus(schedulerResponse);
        setConnectedAgents(agentsResponse);
        setPendingEnrollments(enrollmentsResponse);
        setRejectedEnrollments(rejectedResponse);
        setRevokedAgents(revokedResponse);
        setStoppedAgents(stoppedResponse);
      } catch (err) {
        if (!active) return;
        setError(err instanceof Error ? err.message : "Falha ao carregar configuracoes.");
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

  async function handleSchedulerToggle() {
    setError(null);
    setSchedulerLoading(true);

    try {
      const response = schedulerStatus?.running ? await stopScheduler() : await startScheduler();
      setSchedulerStatus(response);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Falha ao atualizar o scheduler.");
    } finally {
      setSchedulerLoading(false);
    }
  }

  async function handleExecutionModeChange(mode: ExecutionSettings["linux_agent_mode"]) {
    setError(null);
    setExecutionLoading(true);

    try {
      const response = await updateLinuxExecutionMode(mode, undefined, {
        real_apply_enabled: settings?.execution.real_apply_enabled,
        allow_security_only: settings?.execution.allow_security_only,
        allowed_package_patterns: settings?.execution.allowed_package_patterns,
        apt_apply_timeout_seconds: settings?.execution.apt_apply_timeout_seconds,
      });
      setSettings((current) =>
        current
          ? {
              ...current,
              execution: response,
            }
          : current,
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Falha ao atualizar o modo do agente Linux.");
    } finally {
      setExecutionLoading(false);
    }
  }

  async function handleExecutionGuardrailsSave() {
    if (!settings) return;

    setError(null);
    setExecutionLoading(true);
    try {
      const response = await updateLinuxExecutionMode(settings.execution.linux_agent_mode, undefined, {
        real_apply_enabled: settings.execution.real_apply_enabled,
        allow_security_only: settings.execution.allow_security_only,
        allowed_package_patterns: allowedPatternsDraft
          .split(",")
          .map((item) => item.trim())
          .filter(Boolean),
        apt_apply_timeout_seconds: Number(timeoutDraft),
        reboot_policy: settings.execution.reboot_policy,
        reboot_grace_minutes: Number(rebootGraceDraft),
        windows_scan_apply_enabled: settings.execution.windows_scan_apply_enabled,
        windows_download_install_enabled: settings.execution.windows_download_install_enabled,
        windows_command_timeout_seconds: Number(windowsTimeoutDraft),
        windows_reboot_policy: settings.execution.windows_reboot_policy,
        windows_reboot_grace_minutes: Number(windowsRebootGraceDraft),
      });
      setSettings((current) =>
        current
          ? {
              ...current,
              execution: response,
            }
          : current,
      );
      setAllowedPatternsDraft(response.allowed_package_patterns.join(", "));
      setTimeoutDraft(String(response.apt_apply_timeout_seconds));
      setRebootGraceDraft(String(response.reboot_grace_minutes));
      setWindowsTimeoutDraft(String(response.windows_command_timeout_seconds));
      setWindowsRebootGraceDraft(String(response.windows_reboot_grace_minutes));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Falha ao atualizar os guardrails de execucao.");
    } finally {
      setExecutionLoading(false);
    }
  }

  function handleRealApplyToggle() {
    if (!settings) return;

    if (!settings.execution.real_apply_enabled) {
      setConfirmRealApplyOpen(true);
      return;
    }

    setSettings((current) =>
      current
        ? {
            ...current,
            execution: {
              ...current.execution,
              real_apply_enabled: false,
            },
          }
        : current,
    );
  }

  function confirmEnableRealApply() {
    setSettings((current) =>
      current
        ? {
            ...current,
            execution: {
              ...current.execution,
              real_apply_enabled: true,
            },
          }
        : current,
    );
    setConfirmRealApplyOpen(false);
  }

  async function handleGroupExecutionModeChange(
    machineGroup: string,
    mode: ExecutionSettings["linux_agent_mode"],
  ) {
    setError(null);
    setExecutionLoading(true);

    try {
      const response = await updateLinuxExecutionMode(mode, machineGroup);
      setSettings((current) =>
        current
          ? {
              ...current,
              execution: response,
            }
          : current,
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Falha ao atualizar a politica do grupo Linux.");
    } finally {
      setExecutionLoading(false);
    }
  }

  async function handleApproveEnrollment(agentId: string) {
    setError(null);
    setApprovalLoadingId(agentId);

    try {
      await approvePendingEnrollment(agentId);
      const [agentsResponse, enrollmentsResponse, rejectedResponse] = await Promise.all([
        fetchConnectedAgents(),
        fetchPendingEnrollments(),
        fetchRejectedEnrollments(),
      ]);
      setConnectedAgents(agentsResponse);
      setPendingEnrollments(enrollmentsResponse);
      setRejectedEnrollments(rejectedResponse);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Falha ao aprovar o agente pendente.");
    } finally {
      setApprovalLoadingId(null);
    }
  }

  async function handleRejectEnrollment(agentId: string) {
    setError(null);
    setApprovalLoadingId(agentId);

    try {
      await rejectPendingEnrollment(agentId);
      const [enrollmentsResponse, rejectedResponse] = await Promise.all([
        fetchPendingEnrollments(),
        fetchRejectedEnrollments(),
      ]);
      setPendingEnrollments(enrollmentsResponse);
      setRejectedEnrollments(rejectedResponse);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Falha ao rejeitar o agente pendente.");
    } finally {
      setApprovalLoadingId(null);
    }
  }

  async function handleBootstrapTokenSave() {
    setError(null);
    setBootstrapLoading(true);
    try {
      const response = await updateBootstrapToken(bootstrapTokenDraft, installServerUrlDraft);
      setSettings((current) =>
        current
          ? {
              ...current,
              bootstrap: response,
            }
          : current,
      );
      setBootstrapTokenDraft(response.agent_bootstrap_token);
      setInstallServerUrlDraft(response.agent_install_server_url);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Falha ao atualizar o bootstrap token.");
    } finally {
      setBootstrapLoading(false);
    }
  }

  async function refreshOperationalData() {
    const [
      settingsResult,
      agentsResult,
      enrollmentsResult,
      rejectedResult,
      revokedResult,
      stoppedResult,
    ] = await Promise.allSettled([
      fetchSettings(),
      fetchConnectedAgents(),
      fetchPendingEnrollments(),
      fetchRejectedEnrollments(),
      fetchRevokedAgents(),
      fetchStoppedAgents(),
    ]);

    if (settingsResult.status === "fulfilled") {
      setSettings(settingsResult.value);
      setRebootGraceDraft(String(settingsResult.value.execution.reboot_grace_minutes));
      setWindowsTimeoutDraft(String(settingsResult.value.execution.windows_command_timeout_seconds));
      setWindowsRebootGraceDraft(String(settingsResult.value.execution.windows_reboot_grace_minutes));
    }

    if (agentsResult.status === "fulfilled") {
      setConnectedAgents(agentsResult.value);
    }

    if (enrollmentsResult.status === "fulfilled") {
      setPendingEnrollments(enrollmentsResult.value);
    }

    if (rejectedResult.status === "fulfilled") {
      setRejectedEnrollments(rejectedResult.value);
    }

    if (revokedResult.status === "fulfilled") {
      setRevokedAgents(revokedResult.value);
    }

    if (stoppedResult.status === "fulfilled") {
      setStoppedAgents(stoppedResult.value);
    }
  }

  async function handleConnectedAgentActionConfirm() {
    if (!confirmAgentAction) return;

    setError(null);
    setAgentActionLoadingId(confirmAgentAction.agent.agent_id);
    try {
      if (confirmAgentAction.type === "revoke") {
        await revokeConnectedAgent(confirmAgentAction.agent.agent_id);
      } else if (confirmAgentAction.type === "reintegrate") {
        await reintegrateConnectedAgent(confirmAgentAction.agent.agent_id);
      } else if (confirmAgentAction.type === "reboot") {
        await requestConnectedAgentReboot(confirmAgentAction.agent.agent_id);
      } else if (confirmAgentAction.type === "reopen-rejected") {
        await reopenRejectedEnrollment(confirmAgentAction.agent.agent_id);
      } else {
        await requeueRevokedAgent(confirmAgentAction.agent.agent_id);
      }
      setConfirmAgentAction(null);
      await refreshOperationalData();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Falha ao executar a acao do agente.");
    } finally {
      setAgentActionLoadingId(null);
    }
  }

  async function handleExportEvents() {
    setError(null);
    setExportLoading(true);
    try {
      const content = await downloadOperationalEventsCsv();
      const blob = new Blob([content], { type: "text/csv;charset=utf-8" });
      const url = window.URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = "patch-manager-operational-events.csv";
      anchor.click();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Falha ao exportar os eventos operacionais.");
    } finally {
      setExportLoading(false);
    }
  }

  return (
    <div className="split-grid">
      <section className="panel section">
        <div className="section-header">
          <h2 className="section-title">Politicas de patch</h2>
        </div>
        {error ? (
          <p className="muted" style={{ marginTop: 0, marginBottom: 16 }}>
            {error}. Verifique se a API esta ativa em `http://localhost:8000`.
          </p>
        ) : null}
        {loading ? <p className="muted">Carregando configuracoes...</p> : null}
        {(settings?.policy ?? []).map((item) => (
          <div key={item.label} className="setting-row">
            <div>
              <div style={{ fontWeight: 700 }}>{item.label}</div>
              <div className="muted" style={{ marginTop: 4 }}>
                {item.description}
              </div>
            </div>
            <div className={item.enabled ? "pill-switch on" : "pill-switch"} />
          </div>
        ))}
      </section>

      <section className="panel section">
        <div className="section-header">
          <h2 className="section-title">Notificacoes</h2>
        </div>
        {(settings?.notifications ?? []).map((item) => (
          <div key={item.label} className="setting-row">
            <div>
              <div style={{ fontWeight: 700 }}>{item.label}</div>
              <div className="muted" style={{ marginTop: 4 }}>
                {item.description}
              </div>
            </div>
            <div className={item.enabled ? "pill-switch on" : "pill-switch"} />
          </div>
        ))}
      </section>

      <section className="panel section">
        <div className="section-header">
          <h2 className="section-title">Modo do agente Linux</h2>
          <span className="muted">
            {settings?.execution.linux_agent_mode ?? "dry-run"}
          </span>
        </div>
        <div className="list-item">
          <div>
            <div style={{ fontWeight: 700 }}>Politica de execucao</div>
            <div className="muted" style={{ marginTop: 4 }}>
              `dry-run` valida e inspeciona. `apply` executa a simulacao segura com `apt-get -s`.
            </div>
          </div>
          <div style={{ display: "flex", gap: 10 }}>
            <button
              className={
                settings?.execution.linux_agent_mode === "dry-run" ? "btn btn-primary" : "btn"
              }
              disabled={executionLoading}
              onClick={() => void handleExecutionModeChange("dry-run")}
              type="button"
            >
              Dry-run
            </button>
            <button
              className={
                settings?.execution.linux_agent_mode === "apply" ? "btn btn-primary" : "btn"
              }
              disabled={executionLoading}
              onClick={() => void handleExecutionModeChange("apply")}
              type="button"
            >
              Apply
            </button>
          </div>
        </div>
      </section>

      <section className="panel section">
        <div className="section-header">
          <h2 className="section-title">Guardrails de apply real</h2>
          <span className="muted">
            {settings?.execution.real_apply_enabled ? "habilitado" : "desabilitado"}
          </span>
        </div>
        <div className="list">
          <div className="list-item">
            <div>
              <div style={{ fontWeight: 700 }}>Trilha de habilitacao</div>
              <div className="muted" style={{ marginTop: 4 }}>
                {realApplyAuditLabel}
              </div>
            </div>
          </div>
          <div className="list-item">
            <div>
              <div style={{ fontWeight: 700 }}>Habilitar aplicacao real</div>
              <div className="muted" style={{ marginTop: 4 }}>
                Quando desligado, `apply` continua apenas simulando no host.
              </div>
            </div>
            <button
              className={settings?.execution.real_apply_enabled ? "btn btn-primary" : "btn"}
              disabled={executionLoading}
              onClick={handleRealApplyToggle}
              type="button"
            >
              {settings?.execution.real_apply_enabled ? "Ligado" : "Desligado"}
            </button>
          </div>
          <div className="list-item">
            <div>
              <div style={{ fontWeight: 700 }}>Somente atualizacoes de seguranca</div>
              <div className="muted" style={{ marginTop: 4 }}>
                Restringe apply real a candidatos com indicio de origem security.
              </div>
            </div>
            <button
              className={settings?.execution.allow_security_only ? "btn btn-primary" : "btn"}
              disabled={executionLoading}
              onClick={() =>
                setSettings((current) =>
                  current
                    ? {
                        ...current,
                        execution: {
                          ...current.execution,
                          allow_security_only: !current.execution.allow_security_only,
                        },
                      }
                    : current,
                )
              }
              type="button"
            >
              {settings?.execution.allow_security_only ? "Ligado" : "Desligado"}
            </button>
          </div>
          <div className="list-item" style={{ alignItems: "flex-start", flexDirection: "column" }}>
            <div style={{ fontWeight: 700 }}>Allowlist de pacotes</div>
            <div className="muted" style={{ marginTop: 4 }}>
              Informe padroes separados por virgula, como `openssl,libssl*,curl`.
            </div>
            <input
              className="input"
              onChange={(event) => setAllowedPatternsDraft(event.target.value)}
              style={{ marginTop: 12 }}
              type="text"
              value={allowedPatternsDraft}
            />
          </div>
          <div className="list-item">
            <div>
              <div style={{ fontWeight: 700 }}>Timeout de apply</div>
              <div className="muted" style={{ marginTop: 4 }}>
                Tempo maximo para um `apt-get --only-upgrade install -y`.
              </div>
            </div>
            <input
              className="input"
              onChange={(event) => setTimeoutDraft(event.target.value)}
              style={{ maxWidth: 140 }}
              type="number"
              min="30"
              value={timeoutDraft}
            />
          </div>
          <div className="list-item">
            <div>
              <div style={{ fontWeight: 700 }}>Politica de reboot pos-patch</div>
              <div className="muted" style={{ marginTop: 4 }}>
                Define como o ambiente trata hosts Linux que exigem reboot depois de um apply bem-sucedido.
              </div>
            </div>
            <div style={{ display: "flex", gap: 10 }}>
              {(["manual", "notify", "maintenance-window"] as const).map((policy) => (
                <button
                  key={policy}
                  className={settings?.execution.reboot_policy === policy ? "btn btn-primary" : "btn"}
                  disabled={executionLoading}
                  onClick={() =>
                    setSettings((current) =>
                      current
                        ? {
                            ...current,
                            execution: {
                              ...current.execution,
                              reboot_policy: policy,
                            },
                          }
                        : current,
                    )
                  }
                  type="button"
                >
                  {policy}
                </button>
              ))}
            </div>
          </div>
          <div className="list-item">
            <div>
              <div style={{ fontWeight: 700 }}>Janela de grace para reboot</div>
              <div className="muted" style={{ marginTop: 4 }}>
                Tempo, em minutos, usado pela politica de reboot apos patch aplicado.
              </div>
            </div>
            <input
              className="input"
              onChange={(event) => setRebootGraceDraft(event.target.value)}
              style={{ maxWidth: 140 }}
              type="number"
              min="5"
              value={rebootGraceDraft}
            />
          </div>
          <div style={{ display: "flex", justifyContent: "flex-end" }}>
            <button
              className="btn btn-primary"
              disabled={executionLoading}
              onClick={() => void handleExecutionGuardrailsSave()}
              type="button"
            >
              {executionLoading ? "Salvando..." : "Salvar guardrails"}
            </button>
          </div>
        </div>
      </section>

      <section className="panel section">
        <div className="section-header">
          <h2 className="section-title">Politicas Linux por grupo</h2>
          <span className="muted">
            {(settings?.execution.linux_group_modes.length ?? 0)} grupos
          </span>
        </div>
        <div className="list">
          {(settings?.execution.linux_group_modes ?? []).length === 0 ? (
            <div className="list-item">
              <div className="muted">Nenhum grupo cadastrado ainda.</div>
            </div>
          ) : null}
          {(settings?.execution.linux_group_modes ?? []).map((item) => (
            <div key={item.group_name} className="list-item">
              <div>
                <div style={{ fontWeight: 700 }}>{item.group_name}</div>
                <div className="muted" style={{ marginTop: 4 }}>
                  {item.uses_default
                    ? "Segue a politica global do Linux."
                    : "Override persistido para este grupo."}
                </div>
                <div className="muted" style={{ marginTop: 4 }}>
                  Guardrails efetivos: apply real {settings?.execution.real_apply_enabled ? "ligado" : "desligado"} -
                  security-only {settings?.execution.allow_security_only ? "ligado" : "desligado"} - allowlist{" "}
                  {(settings?.execution.allowed_package_patterns.length ?? 0) > 0
                    ? `${settings?.execution.allowed_package_patterns.length ?? 0} padroes`
                    : "aberta"}{" "}
                  - timeout {settings?.execution.apt_apply_timeout_seconds ?? 900}s
                </div>
              </div>
              <div style={{ display: "flex", gap: 10 }}>
                <button
                  className={item.linux_agent_mode === "dry-run" ? "btn btn-primary" : "btn"}
                  disabled={executionLoading}
                  onClick={() => void handleGroupExecutionModeChange(item.group_name, "dry-run")}
                  type="button"
                >
                  Dry-run
                </button>
                <button
                  className={item.linux_agent_mode === "apply" ? "btn btn-primary" : "btn"}
                  disabled={executionLoading}
                  onClick={() => void handleGroupExecutionModeChange(item.group_name, "apply")}
                  type="button"
                >
                  Apply
                </button>
              </div>
            </div>
          ))}
        </div>
      </section>

      <section className="panel section">
        <div className="section-header">
          <h2 className="section-title">Execucao do agente Windows</h2>
          <span className="muted">
            {settings?.execution.windows_scan_apply_enabled ? "scan apply habilitado" : "somente inventario"}
          </span>
        </div>
        <div className="list">
          <div className="list-item">
            <div>
              <div style={{ fontWeight: 700 }}>StartScan controlado</div>
              <div className="muted" style={{ marginTop: 4 }}>
                Quando ligado, jobs Windows em `apply` podem acionar `UsoClient StartScan` no host.
              </div>
            </div>
            <button
              className={settings?.execution.windows_scan_apply_enabled ? "btn btn-primary" : "btn"}
              disabled={executionLoading}
              onClick={() =>
                setSettings((current) =>
                  current
                    ? {
                        ...current,
                        execution: {
                          ...current.execution,
                          windows_scan_apply_enabled: !current.execution.windows_scan_apply_enabled,
                        },
                      }
                    : current,
                )
              }
              type="button"
            >
              {settings?.execution.windows_scan_apply_enabled ? "Ligado" : "Desligado"}
            </button>
          </div>
          <div className="list-item">
            <div>
              <div style={{ fontWeight: 700 }}>StartDownload e StartInstall</div>
              <div className="muted" style={{ marginTop: 4 }}>
                Quando ligado, o agente Windows vai alem do scan e tenta baixar e instalar updates via `UsoClient`.
              </div>
            </div>
            <button
              className={settings?.execution.windows_download_install_enabled ? "btn btn-primary" : "btn"}
              disabled={executionLoading}
              onClick={() =>
                setSettings((current) =>
                  current
                    ? {
                        ...current,
                        execution: {
                          ...current.execution,
                          windows_download_install_enabled: !current.execution.windows_download_install_enabled,
                        },
                      }
                    : current,
                )
              }
              type="button"
            >
              {settings?.execution.windows_download_install_enabled ? "Ligado" : "Desligado"}
            </button>
          </div>
          <div className="list-item">
            <div>
              <div style={{ fontWeight: 700 }}>Timeout do comando Windows</div>
              <div className="muted" style={{ marginTop: 4 }}>
                Tempo maximo para validacao PowerShell e `StartScan` no agente Windows.
              </div>
            </div>
            <input
              className="input"
              onChange={(event) => setWindowsTimeoutDraft(event.target.value)}
              style={{ maxWidth: 140 }}
              type="number"
              min="15"
              value={windowsTimeoutDraft}
            />
          </div>
          <div className="list-item">
            <div>
              <div style={{ fontWeight: 700 }}>Politica de reboot Windows</div>
              <div className="muted" style={{ marginTop: 4 }}>
                Define como o agente deve tratar reboot pendente apos `StartInstall`.
              </div>
            </div>
            <div style={{ display: "flex", gap: 10, flexWrap: "wrap", justifyContent: "flex-end" }}>
              {(["manual", "notify", "maintenance-window"] as const).map((policy) => (
                <button
                  key={policy}
                  className={settings?.execution.windows_reboot_policy === policy ? "btn btn-primary" : "btn"}
                  disabled={executionLoading}
                  onClick={() =>
                    setSettings((current) =>
                      current
                        ? {
                            ...current,
                            execution: {
                              ...current.execution,
                              windows_reboot_policy: policy,
                            },
                          }
                        : current,
                    )
                  }
                  type="button"
                >
                  {policy}
                </button>
              ))}
            </div>
          </div>
          <div className="list-item">
            <div>
              <div style={{ fontWeight: 700 }}>Janela de reboot Windows</div>
              <div className="muted" style={{ marginTop: 4 }}>
                Em `maintenance-window`, define em quantos minutos o reboot sera agendado.
              </div>
            </div>
            <input
              className="input"
              onChange={(event) => setWindowsRebootGraceDraft(event.target.value)}
              style={{ maxWidth: 140 }}
              type="number"
              min="5"
              value={windowsRebootGraceDraft}
            />
          </div>
          <div style={{ display: "flex", justifyContent: "flex-end" }}>
            <button
              className="btn btn-primary"
              disabled={executionLoading}
              onClick={() => void handleExecutionGuardrailsSave()}
              type="button"
            >
              {executionLoading ? "Salvando..." : "Salvar politica Windows"}
            </button>
          </div>
        </div>
      </section>

      <section className="panel section">
        <div className="section-header">
          <h2 className="section-title">Orquestracao do scheduler</h2>
          {schedulerStatus ? (
            <StatusBadge variant={schedulerStatus.running ? "ok" : "warn"}>
              {schedulerStatus.running ? "Ativo" : "Pausado"}
            </StatusBadge>
          ) : null}
        </div>
        {loading ? <p className="muted">Carregando status do scheduler...</p> : null}
        {schedulerStatus ? (
          <div className="list">
            <div className="list-item">
              <div>
                <div style={{ fontWeight: 700 }}>Intervalo de enfileiramento</div>
                <div className="muted" style={{ marginTop: 4 }}>
                  Enfileira novos jobs a cada {schedulerStatus.enqueue_interval_seconds} segundos.
                </div>
              </div>
              <div className="code">{schedulerStatus.enqueue_interval_seconds}s</div>
            </div>
            <div className="list-item">
              <div>
                <div style={{ fontWeight: 700 }}>Intervalo do worker</div>
                <div className="muted" style={{ marginTop: 4 }}>
                  Processa um job por vez a cada {schedulerStatus.worker_interval_seconds} segundos.
                </div>
              </div>
              <div className="code">{schedulerStatus.worker_interval_seconds}s</div>
            </div>
            <div className="list-item">
              <div>
                <div style={{ fontWeight: 700 }}>Proxima atividade automatica</div>
                <div className="muted" style={{ marginTop: 4 }}>
                  Enfileirador:{" "}
                  {schedulerStatus.next_enqueue_run_at
                  ? formatDateTimeSaoPaulo(schedulerStatus.next_enqueue_run_at)
                    : "sem agenda"}
                </div>
                <div className="muted" style={{ marginTop: 4 }}>
                  Worker:{" "}
                  {schedulerStatus.next_worker_run_at
                  ? formatDateTimeSaoPaulo(schedulerStatus.next_worker_run_at)
                    : "sem agenda"}
                </div>
              </div>
            </div>
            <div className="list-item">
              <div>
                <div style={{ fontWeight: 700 }}>Ultimas execucoes automaticas</div>
                <div className="muted" style={{ marginTop: 4 }}>
                  Enfileirador:{" "}
                  {schedulerStatus.last_enqueue_run_at
                  ? formatDateTimeSaoPaulo(schedulerStatus.last_enqueue_run_at)
                    : "nunca executado"}
                </div>
                <div className="muted" style={{ marginTop: 4 }}>
                  Worker:{" "}
                  {schedulerStatus.last_worker_run_at
                  ? formatDateTimeSaoPaulo(schedulerStatus.last_worker_run_at)
                    : "nunca executado"}
                </div>
              </div>
              {schedulerStatus.last_enqueue_result || schedulerStatus.last_worker_result ? (
                <div className="muted" style={{ textAlign: "right" }}>
                  {schedulerStatus.last_enqueue_result?.jobs_enqueued ?? 0} jobs novos
                  <br />
                  {schedulerStatus.last_worker_result?.jobs_processed ?? 0} jobs concluidos
                </div>
              ) : null}
            </div>
          </div>
        ) : null}
        <div style={{ display: "flex", gap: 10, marginTop: 16 }}>
          <button
            className="btn btn-primary"
            disabled={schedulerLoading}
            onClick={() => void handleSchedulerToggle()}
            type="button"
          >
            {schedulerLoading
              ? "Atualizando..."
              : schedulerStatus?.running
                ? "Pausar scheduler"
                : "Iniciar scheduler"}
          </button>
        </div>
      </section>

      <section className="panel section">
        <div className="section-header">
          <h2 className="section-title">Bootstrap do agente</h2>
          <span className="muted">Token de cadastro inicial</span>
        </div>
        <div className="list-item">
          <div style={{ flex: 1 }}>
            <div style={{ fontWeight: 700 }}>Bootstrap token</div>
            <div className="muted" style={{ marginTop: 4 }}>
              Use este token somente para o primeiro cadastro do host. Depois o agente recebe uma credencial propria.
            </div>
          </div>
          <input
            className="input"
            onChange={(event) => setBootstrapTokenDraft(event.target.value)}
            style={{ maxWidth: 320 }}
            type="text"
            value={bootstrapTokenDraft}
          />
        </div>
        <div className="list-item" style={{ marginTop: 12 }}>
          <div style={{ flex: 1 }}>
            <div style={{ fontWeight: 700 }}>URL publica do servidor</div>
            <div className="muted" style={{ marginTop: 4 }}>
              Base usada para gerar o comando de instalacao remota do agente.
            </div>
          </div>
          <input
            className="input"
            onChange={(event) => setInstallServerUrlDraft(event.target.value)}
            style={{ maxWidth: 320 }}
            type="text"
            value={installServerUrlDraft}
          />
          <button
            className="btn btn-primary"
            disabled={bootstrapLoading}
            onClick={() => void handleBootstrapTokenSave()}
            type="button"
          >
            {bootstrapLoading ? "Salvando..." : "Salvar token"}
          </button>
        </div>
        <div className="list-item" style={{ marginTop: 12, alignItems: "flex-start", flexDirection: "column" }}>
          <div style={{ fontWeight: 700 }}>Instalacao Linux</div>
          <div className="muted" style={{ marginTop: 4 }}>
            Rode este comando no Linux de destino para instalar e iniciar o agente automaticamente.
          </div>
          <code
            style={{
              width: "100%",
              marginTop: 12,
              padding: "12px 14px",
              border: "1px solid var(--border)",
              borderRadius: 12,
              background: "var(--surface-2)",
              color: "var(--text)",
              overflowX: "auto",
              whiteSpace: "pre-wrap",
              wordBreak: "break-all",
            }}
          >
            {installCommand}
          </code>
        </div>
        <div className="list-item" style={{ marginTop: 12, alignItems: "flex-start", flexDirection: "column" }}>
          <div style={{ fontWeight: 700 }}>Atualizacao Linux</div>
          <div className="muted" style={{ marginTop: 4 }}>
            Use este comando em um host que ja tenha o agente instalado. Ele preserva o `.env` e reinicia o servico.
          </div>
          <code
            style={{
              width: "100%",
              marginTop: 12,
              padding: "12px 14px",
              border: "1px solid var(--border)",
              borderRadius: 12,
              background: "var(--surface-2)",
              color: "var(--text)",
              overflowX: "auto",
              whiteSpace: "pre-wrap",
              wordBreak: "break-all",
            }}
          >
            {upgradeCommand}
          </code>
        </div>
        <div className="list-item" style={{ marginTop: 12, alignItems: "flex-start", flexDirection: "column" }}>
          <div style={{ fontWeight: 700 }}>Instalacao Windows</div>
          <div className="muted" style={{ marginTop: 4 }}>
            Rode este comando no PowerShell com privilegio administrativo para instalar o agente Windows e registrar a task automatica.
          </div>
          <code
            style={{
              width: "100%",
              marginTop: 12,
              padding: "12px 14px",
              border: "1px solid var(--border)",
              borderRadius: 12,
              background: "var(--surface-2)",
              color: "var(--text)",
              overflowX: "auto",
              whiteSpace: "pre-wrap",
              wordBreak: "break-all",
            }}
          >
            {windowsInstallCommand}
          </code>
        </div>
        <div className="list-item" style={{ marginTop: 12, alignItems: "flex-start", flexDirection: "column" }}>
          <div style={{ fontWeight: 700 }}>Atualizacao Windows</div>
          <div className="muted" style={{ marginTop: 4 }}>
            Use este comando em um host Windows que ja tenha o agente instalado. Ele preserva o ambiente e reinicia a task.
          </div>
          <code
            style={{
              width: "100%",
              marginTop: 12,
              padding: "12px 14px",
              border: "1px solid var(--border)",
              borderRadius: 12,
              background: "var(--surface-2)",
              color: "var(--text)",
              overflowX: "auto",
              whiteSpace: "pre-wrap",
              wordBreak: "break-all",
            }}
          >
            {windowsUpgradeCommand}
          </code>
        </div>
      </section>

      <section className="panel section">
        <div className="section-header">
          <h2 className="section-title">Ciclo de vida dos agentes</h2>
          <span className="muted">{lifecycleItems.length} registros</span>
        </div>
        <div className="list" style={{ marginBottom: 12 }}>
          <div className="list-item">
            <div>
              <div style={{ fontWeight: 700 }}>Conectados</div>
              <div className="muted" style={{ marginTop: 4 }}>
                Agentes ativos e respondendo heartbeat.
              </div>
            </div>
            <StatusBadge variant="ok">{`${connectedAgents.length}`}</StatusBadge>
          </div>
          <div className="list-item">
            <div>
              <div style={{ fontWeight: 700 }}>Pendentes</div>
              <div className="muted" style={{ marginTop: 4 }}>
                Hosts aguardando aprovacao ou rejeicao.
              </div>
            </div>
            <StatusBadge variant="warn">{`${pendingEnrollments.length}`}</StatusBadge>
          </div>
          <div className="list-item">
            <div>
              <div style={{ fontWeight: 700 }}>Revogados</div>
              <div className="muted" style={{ marginTop: 4 }}>
                Credenciais revogadas e fora do pool ativo.
              </div>
            </div>
            <StatusBadge variant="error">{`${revokedAgents.length}`}</StatusBadge>
          </div>
          <div className="list-item">
            <div>
              <div style={{ fontWeight: 700 }}>Rejeitados</div>
              <div className="muted" style={{ marginTop: 4 }}>
                Enrollments rejeitados aguardando reabertura ou nova tentativa.
              </div>
            </div>
            <StatusBadge variant="error">{`${rejectedEnrollments.length}`}</StatusBadge>
          </div>
          <div className="list-item">
            <div>
              <div style={{ fontWeight: 700 }}>Parados</div>
              <div className="muted" style={{ marginTop: 4 }}>
                Agentes com credencial ativa, mas sem heartbeat recente.
              </div>
            </div>
            <StatusBadge variant="warn">{`${stoppedAgents.length}`}</StatusBadge>
          </div>
        </div>
        <div className="list">
          {lifecycleItems.length === 0 ? (
            <div className="list-item">
              <div className="muted">Nenhum agente conhecido ainda.</div>
            </div>
          ) : null}
          {lifecycleItems.map((item) => (
            <div key={item.id} className="list-item">
              <div>
                <div style={{ fontWeight: 700 }}>
                  {item.hostname} - {item.platform}
                </div>
                <div className="muted" style={{ marginTop: 4 }}>
                  {item.agent_id} - {item.secondary}
                </div>
                <div className="muted" style={{ marginTop: 4 }}>
                  {item.detail}
                </div>
              </div>
              <div style={{ textAlign: "right", display: "grid", gap: 8, justifyItems: "end" }}>
                <StatusBadge variant={getLifecycleVariant(item.status)}>{item.status}</StatusBadge>
                <div className="muted">
                  {item.occurred_at ? formatDateTimeSaoPaulo(item.occurred_at) : "sem data"}
                </div>
              </div>
            </div>
          ))}
        </div>
      </section>

      <section className="panel section">
        <div className="section-header">
          <h2 className="section-title">Agentes pendentes</h2>
          <span className="muted">{pendingEnrollments.length} aguardando aprovacao</span>
        </div>
        <div className="list">
          {pendingEnrollments.length === 0 ? (
            <div className="list-item">
              <div className="muted">Nenhum agente aguardando aprovacao.</div>
            </div>
          ) : null}
          {pendingEnrollments.map((item) => (
            <div key={item.agent_id} className="list-item">
              <div>
                <div style={{ fontWeight: 700 }}>
                  {item.hostname} - {item.platform}
                </div>
                <div className="muted" style={{ marginTop: 4 }}>
                  {item.agent_id} - {item.primary_ip}
                </div>
                <div className="muted" style={{ marginTop: 4 }}>
                  {item.os_name} {item.os_version} - kernel {item.kernel_version}
                </div>
                <div className="muted" style={{ marginTop: 4 }}>
                  Solicitado em {formatDateTimeSaoPaulo(item.requested_at)}
                </div>
              </div>
              <div style={{ display: "flex", gap: 10 }}>
                <button
                  className="btn"
                  disabled={approvalLoadingId === item.agent_id}
                  onClick={() => void handleRejectEnrollment(item.agent_id)}
                  type="button"
                >
                  Rejeitar
                </button>
                <button
                  className="btn btn-primary"
                  disabled={approvalLoadingId === item.agent_id}
                  onClick={() => void handleApproveEnrollment(item.agent_id)}
                  type="button"
                >
                  {approvalLoadingId === item.agent_id ? "Processando..." : "Aprovar"}
                </button>
              </div>
            </div>
          ))}
        </div>
      </section>

      <section className="panel section">
        <div className="section-header">
          <h2 className="section-title">Agentes rejeitados</h2>
          <span className="muted">{rejectedEnrollments.length} enrollments rejeitados</span>
        </div>
        <div className="list">
          {rejectedEnrollments.length === 0 ? (
            <div className="list-item">
              <div className="muted">Nenhum agente rejeitado no momento.</div>
            </div>
          ) : null}
          {rejectedEnrollments.map((agent) => (
            <div key={agent.agent_id} className="list-item">
              <div>
                <div style={{ fontWeight: 700 }}>
                  {agent.hostname} - {agent.platform}
                </div>
                <div className="muted" style={{ marginTop: 4 }}>
                  {agent.agent_id} - {agent.primary_ip}
                </div>
                <div className="muted" style={{ marginTop: 4 }}>
                  {agent.os_name} {agent.os_version} - kernel {agent.kernel_version}
                </div>
                <div className="muted" style={{ marginTop: 4 }}>
                  Rejeitado a partir da solicitacao em {formatDateTimeSaoPaulo(agent.requested_at)}
                </div>
              </div>
              <div style={{ textAlign: "right" }}>
                <StatusBadge variant="error">rejected</StatusBadge>
                <div style={{ marginTop: 10, display: "flex", justifyContent: "flex-end" }}>
                  <ActionMenu
                    label={`Acoes do agente rejeitado ${agent.agent_id}`}
                    items={[
                      {
                        label: "Reabrir aprovacao",
                        disabled: agentActionLoadingId === agent.agent_id,
                        onSelect: () => setConfirmAgentAction({ type: "reopen-rejected", agent }),
                      },
                    ]}
                  />
                </div>
              </div>
            </div>
          ))}
        </div>
      </section>

      <section className="panel section">
        <div className="section-header">
          <h2 className="section-title">Agentes parados</h2>
          <span className="muted">{stoppedAgents.length} sem heartbeat recente</span>
        </div>
        <div className="list">
          {stoppedAgents.length === 0 ? (
            <div className="list-item">
              <div className="muted">Nenhum agente parado no momento.</div>
            </div>
          ) : null}
          {stoppedAgents.map((agent) => (
            <div key={agent.agent_id} className="list-item">
              <div>
                <div style={{ fontWeight: 700 }}>
                  {agent.hostname ?? agent.agent_id} - {agent.platform}
                </div>
                <div className="muted" style={{ marginTop: 4 }}>
                  {agent.agent_id} - {agent.primary_ip ?? "n/d"}
                </div>
                <div className="muted" style={{ marginTop: 4 }}>
                  {agent.os_name ?? "Host"} {agent.os_version ?? ""}
                </div>
                <div className="muted" style={{ marginTop: 4 }}>
                  Ultimo registro: {agent.last_seen_at ? formatDateTimeSaoPaulo(agent.last_seen_at) : "sem data"}
                </div>
              </div>
              <div style={{ textAlign: "right", display: "grid", gap: 8, justifyItems: "end" }}>
                <StatusBadge variant="warn">stopped</StatusBadge>
                <div className="muted">
                  modo {agent.execution_mode ?? "unknown"}
                </div>
              </div>
            </div>
          ))}
        </div>
      </section>

      <section className="panel section">
        <div className="section-header">
          <h2 className="section-title">Agentes revogados</h2>
          <span className="muted">{revokedAgents.length} credenciais revogadas</span>
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
                <div style={{ fontWeight: 700 }}>
                  {agent.hostname ?? agent.agent_id} - {agent.platform}
                </div>
                <div className="muted" style={{ marginTop: 4 }}>
                  {agent.agent_id} - {agent.primary_ip ?? "n/d"}
                </div>
                <div className="muted" style={{ marginTop: 4 }}>
                  {agent.os_name ?? "Host"} {agent.os_version ?? ""}
                </div>
                <div className="muted" style={{ marginTop: 4 }}>
                  Ultimo registro:{" "}
                  {agent.last_known_at ? formatDateTimeSaoPaulo(agent.last_known_at) : "sem data"}
                </div>
              </div>
              <div style={{ textAlign: "right" }}>
                <StatusBadge variant="error">revoked</StatusBadge>
                <div style={{ marginTop: 10, display: "flex", justifyContent: "flex-end" }}>
                  <ActionMenu
                    label={`Acoes do agente revogado ${agent.agent_id}`}
                    items={[
                      {
                        label: "Reabrir aprovacao",
                        disabled: agentActionLoadingId === agent.agent_id,
                        onSelect: () => setConfirmAgentAction({ type: "requeue", agent }),
                      },
                    ]}
                  />
                </div>
              </div>
            </div>
          ))}
        </div>
      </section>

      <section className="panel section">
        <div className="section-header">
          <h2 className="section-title">Agentes conectados</h2>
          <span className="muted">{connectedAgents.length} agentes ativos</span>
        </div>
        <div className="list">
          {connectedAgents.length === 0 ? (
            <div className="list-item">
              <div className="muted">Nenhum agente conectado no momento.</div>
            </div>
          ) : null}
          {connectedAgents.map((agent) => (
            <div key={agent.agent_id} className="list-item">
              <div>
                <div style={{ fontWeight: 700 }}>
                  {agent.hostname} - {agent.platform}
                </div>
                <div className="muted" style={{ marginTop: 4 }}>
                  {agent.os_name} {agent.os_version}
                </div>
                <div className="muted" style={{ marginTop: 4 }}>
                  Kernel {agent.kernel_version} - agente {agent.agent_version}
                </div>
                <div className="muted" style={{ marginTop: 4 }}>
                  Modo {agent.execution_mode ?? "unknown"}
                </div>
                <div className="muted" style={{ marginTop: 4 }}>
                  IP {agent.primary_ip ?? "n/d"} - {agent.package_manager ?? "sem gerenciador"}
                </div>
                <div className="muted" style={{ marginTop: 4 }}>
                  {agent.installed_packages ?? 0} pacotes instalados - {agent.upgradable_packages ?? 0} atualizaveis
                  {agent.reboot_required ? " - reboot pendente" : ""}
                </div>
                {agent.platform.toLowerCase() === "linux" && settings ? (
                  <div className="muted" style={{ marginTop: 4 }}>
                    Guardrails ativos: apply real {settings.execution.real_apply_enabled ? "ligado" : "desligado"} -
                    security-only {settings.execution.allow_security_only ? "ligado" : "desligado"} - allowlist{" "}
                    {settings.execution.allowed_package_patterns.length > 0
                      ? `${settings.execution.allowed_package_patterns.length} padroes`
                      : "aberta"}{" "}
                    - timeout {settings.execution.apt_apply_timeout_seconds}s
                  </div>
                ) : null}
                {agent.platform.toLowerCase() === "windows" && settings ? (
                  <div className="muted" style={{ marginTop: 4 }}>
                    Guardrails ativos: StartScan {settings.execution.windows_scan_apply_enabled ? "ligado" : "desligado"} -
                    Download/Install {settings.execution.windows_download_install_enabled ? "ligado" : "desligado"} -
                    timeout {settings.execution.windows_command_timeout_seconds}s - reboot{" "}
                    {settings.execution.windows_reboot_policy} ({settings.execution.windows_reboot_grace_minutes} min)
                  </div>
                ) : null}
              </div>
              <div style={{ textAlign: "right" }}>
                <StatusBadge variant="ok">online</StatusBadge>
                <div className="muted" style={{ marginTop: 8 }}>
                  {formatDateTimeSaoPaulo(agent.last_seen_at)}
                </div>
                <div style={{ marginTop: 10, display: "flex", justifyContent: "flex-end" }}>
                  <ActionMenu
                    label={`Acoes do agente ${agent.agent_id}`}
                    items={[
                      ...(agent.platform.toLowerCase() === "linux"
                        ? [
                            {
                              label: "Solicitar reboot",
                              disabled: agentActionLoadingId === agent.agent_id,
                              onSelect: () => setConfirmAgentAction({ type: "reboot", agent }),
                            },
                          ]
                        : []),
                      {
                        label: "Forcar reintegracao",
                        disabled: agentActionLoadingId === agent.agent_id,
                        onSelect: () => setConfirmAgentAction({ type: "reintegrate", agent }),
                      },
                      {
                        label: "Revogar agente",
                        disabled: agentActionLoadingId === agent.agent_id,
                        onSelect: () => setConfirmAgentAction({ type: "revoke", agent }),
                        tone: "danger",
                      },
                    ]}
                  />
                </div>
              </div>
            </div>
          ))}
        </div>
      </section>
      <section className="panel section">
        <div className="section-header">
          <h2 className="section-title">Eventos operacionais</h2>
          <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
            <span className="muted">{filteredEvents.length} eventos visiveis</span>
            <button
              className="btn"
              disabled={exportLoading}
              onClick={() => void handleExportEvents()}
              type="button"
            >
              {exportLoading ? "Exportando..." : "Exportar CSV"}
            </button>
          </div>
        </div>
        <div style={{ display: "flex", gap: 10, marginBottom: 14 }}>
          {(["all", "info", "warn", "error"] as const).map((filter) => (
            <button
              key={filter}
              className={eventFilter === filter ? "btn btn-primary" : "btn"}
              onClick={() => setEventFilter(filter)}
              type="button"
            >
              {filter === "all" ? "Todos" : filter}
            </button>
          ))}
        </div>
        <div className="list">
          {filteredEvents.length === 0 ? (
            <div className="list-item">
              <div className="muted">Nenhum evento operacional registrado ainda.</div>
            </div>
          ) : null}
          {filteredEvents.map((event) => (
            <div key={`${event.occurred_at}-${event.event_type}-${event.summary}`} className="list-item">
              <div>
                <div style={{ fontWeight: 700 }}>{event.summary}</div>
                <div className="muted" style={{ marginTop: 4 }}>
                  {event.actor} - {formatDateTimeSaoPaulo(event.occurred_at)}
                </div>
              </div>
              <div style={{ textAlign: "right", display: "grid", gap: 8, justifyItems: "end" }}>
                <StatusBadge
                  variant={
                    event.severity === "error"
                      ? "error"
                      : event.severity === "warn"
                        ? "warn"
                        : "ok"
                  }
                >
                  {event.severity}
                </StatusBadge>
                <div className="muted">{event.event_type}</div>
              </div>
            </div>
          ))}
        </div>
      </section>
      <ConfirmModal
        open={confirmRealApplyOpen}
        title="Habilitar apply real no Linux?"
        description="Isso libera execucao real de `apt-get --only-upgrade install -y` quando um job Linux estiver em modo apply. So siga depois de revisar a allowlist, o timeout e se esse ambiente esta realmente pronto para homologacao controlada."
        confirmLabel="Habilitar apply real"
        cancelLabel="Manter bloqueado"
        onCancel={() => setConfirmRealApplyOpen(false)}
        onConfirm={confirmEnableRealApply}
      />
      <ConfirmModal
        open={confirmAgentAction !== null}
        title={
          confirmAgentAction?.type === "revoke"
            ? "Revogar este agente?"
            : confirmAgentAction?.type === "reintegrate"
              ? "Forcar reintegracao deste agente?"
              : confirmAgentAction?.type === "reboot"
                ? "Solicitar reboot manual deste host?"
              : confirmAgentAction?.type === "reopen-rejected"
                ? "Reabrir aprovacao deste agente rejeitado?"
              : "Reabrir aprovacao deste agente?"
        }
        description={
          confirmAgentAction?.type === "revoke"
            ? `O agente ${confirmAgentAction.agent.agent_id} perdera a credencial atual e precisara passar por novo fluxo operacional para voltar.`
            : confirmAgentAction?.type === "reintegrate"
              ? `O agente ${confirmAgentAction?.agent.agent_id} sera desconectado e voltara para a fila de aprovacao usando o bootstrap configurado.`
              : confirmAgentAction?.type === "reboot"
                ? `O agente ${confirmAgentAction?.agent.agent_id} recebera um comando operacional para agendar reboot manual do host.`
              : confirmAgentAction?.type === "reopen-rejected"
                ? `O agente ${confirmAgentAction?.agent.agent_id} voltara para a fila de aprovacao a partir do estado rejeitado.`
              : `O agente ${confirmAgentAction?.agent.agent_id} voltara para a fila de aprovacao a partir do estado revogado.`
        }
        confirmLabel={
          confirmAgentAction?.type === "revoke"
            ? "Revogar agente"
            : confirmAgentAction?.type === "reintegrate"
              ? "Forcar reintegracao"
              : confirmAgentAction?.type === "reboot"
                ? "Solicitar reboot"
              : confirmAgentAction?.type === "reopen-rejected"
                ? "Reabrir aprovacao"
              : "Reabrir aprovacao"
        }
        cancelLabel="Cancelar"
        confirmDisabled={agentActionLoadingId === confirmAgentAction?.agent.agent_id}
        onCancel={() => setConfirmAgentAction(null)}
        onConfirm={() => void handleConnectedAgentActionConfirm()}
      />
    </div>
  );
}
