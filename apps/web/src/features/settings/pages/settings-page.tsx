import { useEffect, useState, type CSSProperties } from "react";
import { ConfirmModal } from "@/components/common/confirm-modal";
import { StatusBadge } from "@/components/common/status-badge";
import { formatDateTimeSaoPaulo } from "@/lib/datetime";
import {
  fetchSchedulerStatus,
  fetchSettings,
  startScheduler,
  stopScheduler,
  updateBootstrapToken,
  updateLinuxExecutionMode,
} from "@/features/settings/api";
import type {
  ExecutionSettings,
  SchedulerStatusResponse,
  SettingsResponse,
} from "@/features/settings/types";

export function SettingsPage() {
  const [settings, setSettings] = useState<SettingsResponse | null>(null);
  const [schedulerStatus, setSchedulerStatus] = useState<SchedulerStatusResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [schedulerLoading, setSchedulerLoading] = useState(false);
  const [executionLoading, setExecutionLoading] = useState(false);
  const [bootstrapTokenDraft, setBootstrapTokenDraft] = useState("");
  const [installServerUrlDraft, setInstallServerUrlDraft] = useState("");
  const [bootstrapExpiryDaysDraft, setBootstrapExpiryDaysDraft] = useState("30");
  const [bootstrapLoading, setBootstrapLoading] = useState(false);
  const [allowedPatternsDraft, setAllowedPatternsDraft] = useState("");
  const [timeoutDraft, setTimeoutDraft] = useState("900");
  const [rebootGraceDraft, setRebootGraceDraft] = useState("60");
  const [windowsTimeoutDraft, setWindowsTimeoutDraft] = useState("60");
  const [windowsRebootGraceDraft, setWindowsRebootGraceDraft] = useState("60");
  const [confirmRealApplyOpen, setConfirmRealApplyOpen] = useState(false);

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

  useEffect(() => {
    let active = true;

    async function load() {
      try {
        const [settingsResponse, schedulerResponse] = await Promise.all([
          fetchSettings(),
          fetchSchedulerStatus(),
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
        reboot_policy: settings?.execution.reboot_policy,
        reboot_grace_minutes: settings?.execution.reboot_grace_minutes,
        windows_scan_apply_enabled: settings?.execution.windows_scan_apply_enabled,
        windows_download_install_enabled: settings?.execution.windows_download_install_enabled,
        windows_command_timeout_seconds: settings?.execution.windows_command_timeout_seconds,
        windows_reboot_policy: settings?.execution.windows_reboot_policy,
        windows_reboot_grace_minutes: settings?.execution.windows_reboot_grace_minutes,
      });
      setSettings((current) => (current ? { ...current, execution: response } : current));
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
      setSettings((current) => (current ? { ...current, execution: response } : current));
      setAllowedPatternsDraft(response.allowed_package_patterns.join(", "));
      setTimeoutDraft(String(response.apt_apply_timeout_seconds));
      setRebootGraceDraft(String(response.reboot_grace_minutes));
      setWindowsTimeoutDraft(String(response.windows_command_timeout_seconds));
      setWindowsRebootGraceDraft(String(response.windows_reboot_grace_minutes));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Falha ao atualizar as politicas de execucao.");
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
      setSettings((current) => (current ? { ...current, execution: response } : current));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Falha ao atualizar a politica do grupo Linux.");
    } finally {
      setExecutionLoading(false);
    }
  }

  async function handleBootstrapTokenSave() {
    setError(null);
    setBootstrapLoading(true);
    try {
      const expiresInDays = Number(bootstrapExpiryDaysDraft);
      const response = await updateBootstrapToken(
        bootstrapTokenDraft,
        installServerUrlDraft,
        Number.isFinite(expiresInDays) ? expiresInDays : undefined,
      );
      setSettings((current) => (current ? { ...current, bootstrap: response } : current));
      setBootstrapTokenDraft(response.agent_bootstrap_token);
      setInstallServerUrlDraft(response.agent_install_server_url);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Falha ao atualizar o bootstrap token.");
    } finally {
      setBootstrapLoading(false);
    }
  }

  return (
    <div className="settings-page">
      <section className="settings-overview">
        <div className="panel stat-card" style={{ "--tone": "var(--accent)" } as CSSProperties}>
          <p className="eyebrow">Scheduler</p>
          <p className="metric">{schedulerStatus?.running ? "ON" : "OFF"}</p>
          <p className="muted">Fila e worker</p>
        </div>
        <div className="panel stat-card" style={{ "--tone": "var(--success)" } as CSSProperties}>
          <p className="eyebrow">Linux</p>
          <p className="metric">{settings?.execution.linux_agent_mode ?? "dry-run"}</p>
          <p className="muted">Modo padrao</p>
        </div>
        <div className="panel stat-card" style={{ "--tone": "var(--warning)" } as CSSProperties}>
          <p className="eyebrow">Apply real</p>
          <p className="metric">{settings?.execution.real_apply_enabled ? "ON" : "OFF"}</p>
          <p className="muted">Guardrail Linux</p>
        </div>
        <div className="panel stat-card" style={{ "--tone": "var(--danger)" } as CSSProperties}>
          <p className="eyebrow">Bootstrap</p>
          <p className="metric">{settings?.bootstrap.agent_bootstrap_token_is_expired ? "EXP" : "OK"}</p>
          <p className="muted">Token inicial</p>
        </div>
      </section>

      {error ? (
        <section className="panel section settings-card-wide">
          <p className="muted" style={{ margin: 0, color: "#ff9fb0" }}>
            {error}. Verifique se a API esta ativa.
          </p>
        </section>
      ) : null}
      {loading ? (
        <section className="panel section settings-card-wide">
          <p className="muted" style={{ margin: 0 }}>Carregando configuracoes...</p>
        </section>
      ) : null}

      <section className="panel section settings-card">
        <div className="section-header">
          <h2 className="section-title">Orquestracao do scheduler</h2>
          {schedulerStatus ? (
            <StatusBadge variant={schedulerStatus.running ? "ok" : "warn"}>
              {schedulerStatus.running ? "Ativo" : "Pausado"}
            </StatusBadge>
          ) : null}
        </div>
        {schedulerStatus ? (
          <div className="list">
            <div className="list-item">
              <div>
                <div style={{ fontWeight: 700 }}>Enfileiramento</div>
                <div className="muted" style={{ marginTop: 4 }}>
                  A cada {schedulerStatus.enqueue_interval_seconds} segundos.
                </div>
              </div>
              <div className="code">{schedulerStatus.enqueue_interval_seconds}s</div>
            </div>
            <div className="list-item">
              <div>
                <div style={{ fontWeight: 700 }}>Worker</div>
                <div className="muted" style={{ marginTop: 4 }}>
                  Processa um job por vez a cada {schedulerStatus.worker_interval_seconds} segundos.
                </div>
              </div>
              <div className="code">{schedulerStatus.worker_interval_seconds}s</div>
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

      <section className="panel section settings-card">
        <div className="section-header">
          <h2 className="section-title">Modo do agente Linux</h2>
          <span className="muted">{settings?.execution.linux_agent_mode ?? "dry-run"}</span>
        </div>
        <div className="list-item">
          <div>
            <div style={{ fontWeight: 700 }}>Politica de execucao</div>
            <div className="muted" style={{ marginTop: 4 }}>
              `dry-run` inspeciona. `apply` segue os guardrails configurados.
            </div>
          </div>
          <div style={{ display: "flex", gap: 10, flexWrap: "wrap", justifyContent: "flex-end" }}>
            {(["dry-run", "apply"] as const).map((mode) => (
              <button
                key={mode}
                className={settings?.execution.linux_agent_mode === mode ? "btn btn-primary" : "btn"}
                disabled={executionLoading}
                onClick={() => void handleExecutionModeChange(mode)}
                type="button"
              >
                {mode}
              </button>
            ))}
          </div>
        </div>
      </section>

      <section className="panel section settings-card-wide">
        <div className="section-header">
          <h2 className="section-title">Guardrails Linux</h2>
          <span className="muted">{settings?.execution.real_apply_enabled ? "apply real habilitado" : "apply real bloqueado"}</span>
        </div>
        <div className="content-grid">
          <div className="list">
            <div className="list-item">
              <div>
                <div style={{ fontWeight: 700 }}>Habilitacao de apply real</div>
                <div className="muted" style={{ marginTop: 4 }}>{realApplyAuditLabel}</div>
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
                <div style={{ fontWeight: 700 }}>Somente seguranca</div>
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
            <div className="list-item">
              <div>
                <div style={{ fontWeight: 700 }}>Politica de reboot</div>
                <div className="muted" style={{ marginTop: 4 }}>
                  Tratamento de reboot pendente apos patch aplicado.
                </div>
              </div>
              <div style={{ display: "flex", gap: 10, flexWrap: "wrap", justifyContent: "flex-end" }}>
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
                              execution: { ...current.execution, reboot_policy: policy },
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
          </div>
          <div className="form-grid">
            <label>
              <span className="field-label">Allowlist de pacotes</span>
              <input
                className="input"
                onChange={(event) => setAllowedPatternsDraft(event.target.value)}
                type="text"
                value={allowedPatternsDraft}
              />
            </label>
            <label>
              <span className="field-label">Timeout de apply (segundos)</span>
              <input
                className="input"
                min="30"
                onChange={(event) => setTimeoutDraft(event.target.value)}
                type="number"
                value={timeoutDraft}
              />
            </label>
            <label>
              <span className="field-label">Grace de reboot Linux (minutos)</span>
              <input
                className="input"
                min="5"
                onChange={(event) => setRebootGraceDraft(event.target.value)}
                type="number"
                value={rebootGraceDraft}
              />
            </label>
            <button
              className="btn btn-primary"
              disabled={executionLoading}
              onClick={() => void handleExecutionGuardrailsSave()}
              type="button"
            >
              {executionLoading ? "Salvando..." : "Salvar politicas"}
            </button>
          </div>
        </div>
      </section>

      <section className="panel section settings-card">
        <div className="section-header">
          <h2 className="section-title">Politicas Linux por grupo</h2>
          <span className="muted">{settings?.execution.linux_group_modes.length ?? 0} grupos</span>
        </div>
        <div className="list settings-scroll-list">
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
                  {item.uses_default ? "Segue a politica global." : "Override persistido."}
                </div>
              </div>
              <div style={{ display: "flex", gap: 10 }}>
                {(["dry-run", "apply"] as const).map((mode) => (
                  <button
                    key={mode}
                    className={item.linux_agent_mode === mode ? "btn btn-primary" : "btn"}
                    disabled={executionLoading}
                    onClick={() => void handleGroupExecutionModeChange(item.group_name, mode)}
                    type="button"
                  >
                    {mode}
                  </button>
                ))}
              </div>
            </div>
          ))}
        </div>
      </section>

      <section className="panel section settings-card">
        <div className="section-header">
          <h2 className="section-title">Execucao Windows</h2>
          <span className="muted">{settings?.execution.windows_scan_apply_enabled ? "scan habilitado" : "somente inventario"}</span>
        </div>
        <div className="form-grid">
          <div className="list-item">
            <div>
              <div style={{ fontWeight: 700 }}>StartScan</div>
              <div className="muted" style={{ marginTop: 4 }}>Permite scan via UsoClient.</div>
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
              <div style={{ fontWeight: 700 }}>Download e install</div>
              <div className="muted" style={{ marginTop: 4 }}>Permite StartDownload e StartInstall.</div>
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
          <label>
            <span className="field-label">Timeout Windows (segundos)</span>
            <input
              className="input"
              min="15"
              onChange={(event) => setWindowsTimeoutDraft(event.target.value)}
              type="number"
              value={windowsTimeoutDraft}
            />
          </label>
          <label>
            <span className="field-label">Grace de reboot Windows (minutos)</span>
            <input
              className="input"
              min="5"
              onChange={(event) => setWindowsRebootGraceDraft(event.target.value)}
              type="number"
              value={windowsRebootGraceDraft}
            />
          </label>
          <div>
            <span className="field-label">Politica de reboot Windows</span>
            <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
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
                            execution: { ...current.execution, windows_reboot_policy: policy },
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
          <button
            className="btn btn-primary"
            disabled={executionLoading}
            onClick={() => void handleExecutionGuardrailsSave()}
            type="button"
          >
            {executionLoading ? "Salvando..." : "Salvar politica Windows"}
          </button>
        </div>
      </section>

      <section className="panel section settings-card-wide">
        <div className="section-header">
          <h2 className="section-title">Bootstrap e instalacao dos agentes</h2>
          {settings ? (
            <StatusBadge variant={settings.bootstrap.agent_bootstrap_token_is_expired ? "error" : "ok"}>
              {settings.bootstrap.agent_bootstrap_token_is_expired ? "expirado" : "ativo"}
            </StatusBadge>
          ) : null}
        </div>
        <div className="content-grid">
          <div className="form-grid">
            <label>
              <span className="field-label">Bootstrap token</span>
              <input
                className="input"
                onChange={(event) => setBootstrapTokenDraft(event.target.value)}
                type="text"
                value={bootstrapTokenDraft}
              />
            </label>
            <label>
              <span className="field-label">URL publica do servidor</span>
              <input
                className="input"
                onChange={(event) => setInstallServerUrlDraft(event.target.value)}
                type="text"
                value={installServerUrlDraft}
              />
            </label>
            <label>
              <span className="field-label">Expiracao do token (dias)</span>
              <input
                className="input"
                min="1"
                onChange={(event) => setBootstrapExpiryDaysDraft(event.target.value)}
                type="number"
                value={bootstrapExpiryDaysDraft}
              />
            </label>
            <button
              className="btn btn-primary"
              disabled={bootstrapLoading}
              onClick={() => void handleBootstrapTokenSave()}
              type="button"
            >
              {bootstrapLoading ? "Salvando..." : "Salvar bootstrap"}
            </button>
            <div className="muted">
              Rotacionado em{" "}
              {settings?.bootstrap.agent_bootstrap_token_rotated_at
                ? formatDateTimeSaoPaulo(settings.bootstrap.agent_bootstrap_token_rotated_at)
                : "sem registro"}
            </div>
          </div>
          <div className="form-grid">
            {[
              ["Instalacao Linux", installCommand],
              ["Atualizacao Linux", upgradeCommand],
              ["Instalacao Windows", windowsInstallCommand],
              ["Atualizacao Windows", windowsUpgradeCommand],
            ].map(([label, command]) => (
              <label key={label}>
                <span className="field-label">{label}</span>
                <code
                  style={{
                    display: "block",
                    width: "100%",
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
                  {command}
                </code>
              </label>
            ))}
          </div>
        </div>
      </section>

      <ConfirmModal
        open={confirmRealApplyOpen}
        title="Habilitar apply real no Linux?"
        description="Isso libera execucao real de `apt-get --only-upgrade install -y` quando um job Linux estiver em modo apply. Revise allowlist, timeout e ambiente antes de seguir."
        confirmLabel="Habilitar apply real"
        cancelLabel="Manter bloqueado"
        onCancel={() => setConfirmRealApplyOpen(false)}
        onConfirm={confirmEnableRealApply}
      />
    </div>
  );
}
