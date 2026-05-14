import { useEffect, useState, type ReactNode } from "react";
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

function InfoHint({ text }: { text: string }) {
  return (
    <span className="info-hint">
      <button aria-label={text} className="info-hint-button" type="button">
        ?
      </button>
      <span className="info-hint-popover">{text}</span>
    </span>
  );
}

function SettingTitle({ children, help }: { children: ReactNode; help: string }) {
  return (
    <span className="setting-title-row">
      <strong>{children}</strong>
      <InfoHint text={help} />
    </span>
  );
}

export function SettingsPage() {
  const [settings, setSettings] = useState<SettingsResponse | null>(null);
  const [schedulerStatus, setSchedulerStatus] = useState<SchedulerStatusResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<{ tone: "ok" | "warn" | "error"; message: string } | null>(null);
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
    setFeedback(null);
    setSchedulerLoading(true);

    try {
      const response = schedulerStatus?.running ? await stopScheduler() : await startScheduler();
      setSchedulerStatus(response);
      setFeedback({
        tone: "ok",
        message: response.running ? "Scheduler iniciado com sucesso." : "Scheduler pausado com sucesso.",
      });
    } catch (err) {
      setFeedback({
        tone: "error",
        message: err instanceof Error ? err.message : "Falha ao atualizar o scheduler.",
      });
    } finally {
      setSchedulerLoading(false);
    }
  }

  async function handleExecutionModeChange(mode: ExecutionSettings["linux_agent_mode"]) {
    setError(null);
    setFeedback(null);
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
      setFeedback({ tone: "ok", message: `Modo Linux atualizado para ${mode}.` });
    } catch (err) {
      setFeedback({
        tone: "error",
        message: err instanceof Error ? err.message : "Falha ao atualizar o modo do agente Linux.",
      });
    } finally {
      setExecutionLoading(false);
    }
  }

  async function handleExecutionGuardrailsSave(message = "Politicas salvas com sucesso.") {
    if (!settings) return;

    setError(null);
    setFeedback(null);
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
      setFeedback({ tone: "ok", message });
    } catch (err) {
      setFeedback({
        tone: "error",
        message: err instanceof Error ? err.message : "Falha ao atualizar as politicas de execucao.",
      });
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
    setFeedback({ tone: "warn", message: "Apply real foi desligado no rascunho. Clique em salvar para persistir." });
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
    setFeedback({ tone: "warn", message: "Apply real foi habilitado no rascunho. Clique em salvar para persistir." });
  }

  async function handleGroupExecutionModeChange(
    machineGroup: string,
    mode: ExecutionSettings["linux_agent_mode"],
  ) {
    setError(null);
    setFeedback(null);
    setExecutionLoading(true);

    try {
      const response = await updateLinuxExecutionMode(mode, machineGroup);
      setSettings((current) => (current ? { ...current, execution: response } : current));
      setFeedback({ tone: "ok", message: `Politica do grupo ${machineGroup} atualizada para ${mode}.` });
    } catch (err) {
      setFeedback({
        tone: "error",
        message: err instanceof Error ? err.message : "Falha ao atualizar a politica do grupo Linux.",
      });
    } finally {
      setExecutionLoading(false);
    }
  }

  async function handleBootstrapTokenSave() {
    setError(null);
    setFeedback(null);
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
      setFeedback({ tone: "ok", message: "Bootstrap salvo com sucesso." });
    } catch (err) {
      setFeedback({
        tone: "error",
        message: err instanceof Error ? err.message : "Falha ao atualizar o bootstrap token.",
      });
    } finally {
      setBootstrapLoading(false);
    }
  }

  return (
    <div className="settings-page settings-page-grouped">
      {error ? (
        <section className="panel section settings-card-wide">
          <p className="muted" style={{ margin: 0, color: "#ff9fb0" }}>
            {error}. Verifique se a API esta ativa.
          </p>
        </section>
      ) : null}
      {feedback ? (
        <div className={`inline-feedback inline-feedback-${feedback.tone} settings-card-wide`}>
          {feedback.message}
        </div>
      ) : null}
      {loading ? (
        <section className="panel section settings-card-wide">
          <p className="muted" style={{ margin: 0 }}>Carregando configuracoes...</p>
        </section>
      ) : null}

      <section className="settings-group settings-card-wide">
        <div className="settings-group-header">
          <div>
            <p className="eyebrow">Globais</p>
            <h2 className="section-title">Configuracoes globais</h2>
          </div>
          <StatusBadge variant={schedulerStatus?.running ? "ok" : "warn"}>
            {schedulerStatus?.running ? "Scheduler ativo" : "Scheduler pausado"}
          </StatusBadge>
        </div>
        <div className="settings-section-grid">
          <section className="panel section settings-tile">
            <div className="section-header">
              <h3 className="section-title">Orquestracao do scheduler</h3>
              <InfoHint text="Controla a fila de jobs e o worker interno que processa agendamentos." />
            </div>
            {schedulerStatus ? (
              <div className="compact-setting-list">
                <div className="setting-row">
                  <SettingTitle help="Intervalo usado para procurar agendamentos e enfileirar jobs.">
                    Enfileiramento
                  </SettingTitle>
                  <span className="code">{schedulerStatus.enqueue_interval_seconds}s</span>
                </div>
                <div className="setting-row">
                  <SettingTitle help="Intervalo do worker que processa um job por vez.">
                    Worker
                  </SettingTitle>
                  <span className="code">{schedulerStatus.worker_interval_seconds}s</span>
                </div>
              </div>
            ) : null}
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
          </section>

          <section className="panel section settings-tile">
            <div className="section-header">
              <h3 className="section-title">Bootstrap e instalacao</h3>
              {settings ? (
                <StatusBadge variant={settings.bootstrap.agent_bootstrap_token_is_expired ? "error" : "ok"}>
                  {settings.bootstrap.agent_bootstrap_token_is_expired ? "expirado" : "ativo"}
                </StatusBadge>
              ) : null}
            </div>
            <div className="form-grid">
              <label>
                <span className="field-label">
                  Bootstrap token <InfoHint text="Token inicial usado pelos agentes durante o primeiro cadastro." />
                </span>
                <input
                  className="input"
                  onChange={(event) => setBootstrapTokenDraft(event.target.value)}
                  type="text"
                  value={bootstrapTokenDraft}
                />
              </label>
              <label>
                <span className="field-label">
                  URL publica do servidor <InfoHint text="Endereco usado pelos instaladores dos agentes para chegar na central." />
                </span>
                <input
                  className="input"
                  onChange={(event) => setInstallServerUrlDraft(event.target.value)}
                  type="text"
                  value={installServerUrlDraft}
                />
              </label>
              <label>
                <span className="field-label">
                  Expiracao do token <InfoHint text="Quantidade de dias ate o token bootstrap expirar." />
                </span>
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
              <span className="muted">
                Rotacionado em{" "}
                {settings?.bootstrap.agent_bootstrap_token_rotated_at
                  ? formatDateTimeSaoPaulo(settings.bootstrap.agent_bootstrap_token_rotated_at)
                  : "sem registro"}
              </span>
            </div>
          </section>
        </div>
      </section>

      <section className="settings-group settings-card-wide">
        <div className="settings-group-header">
          <div>
            <p className="eyebrow">Linux</p>
            <h2 className="section-title">Politicas Linux</h2>
          </div>
          <span className="muted">{settings?.execution.linux_agent_mode ?? "dry-run"}</span>
        </div>
        <div className="settings-section-grid">
          <section className="panel section settings-tile">
            <div className="section-header">
              <h3 className="section-title">Modo do agente</h3>
              <InfoHint text="dry-run apenas inspeciona. apply executa conforme guardrails configurados." />
            </div>
            <div className="segmented-actions">
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
          </section>

          <section className="panel section settings-tile">
            <div className="section-header">
              <h3 className="section-title">Politicas por grupo</h3>
              <span className="muted">{settings?.execution.linux_group_modes.length ?? 0} grupos</span>
            </div>
            <div className="settings-scroll-list compact-setting-list">
              {(settings?.execution.linux_group_modes ?? []).length === 0 ? (
                <div className="setting-row">
                  <span className="muted">Nenhum grupo cadastrado ainda.</span>
                </div>
              ) : null}
              {(settings?.execution.linux_group_modes ?? []).map((item) => (
                <div key={item.group_name} className="setting-row">
                  <SettingTitle help={item.uses_default ? "Segue a politica Linux global." : "Override persistido para este grupo."}>
                    {item.group_name}
                  </SettingTitle>
                  <div className="segmented-actions">
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

          <section className="panel section settings-tile settings-tile-wide">
            <div className="section-header">
              <h3 className="section-title">Guardrails Linux</h3>
              <span className="muted">{settings?.execution.real_apply_enabled ? "apply real habilitado" : "apply real bloqueado"}</span>
            </div>
            <div className="content-grid">
              <div className="compact-setting-list">
                <div className="setting-row">
                  <SettingTitle help={realApplyAuditLabel}>Apply real</SettingTitle>
                  <button
                    className={settings?.execution.real_apply_enabled ? "btn btn-primary" : "btn"}
                    disabled={executionLoading}
                    onClick={handleRealApplyToggle}
                    type="button"
                  >
                    {settings?.execution.real_apply_enabled ? "Ligado" : "Desligado"}
                  </button>
                </div>
                <div className="setting-row">
                  <SettingTitle help="Restringe apply real a candidatos com indicio de origem security.">
                    Somente seguranca
                  </SettingTitle>
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
                <div className="setting-row">
                  <SettingTitle help="Tratamento de reboot pendente apos patch aplicado.">
                    Politica de reboot
                  </SettingTitle>
                  <div className="segmented-actions">
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
                  <span className="field-label">
                    Allowlist de pacotes <InfoHint text="Lista separada por virgula com padroes permitidos no apply real." />
                  </span>
                  <input
                    className="input"
                    onChange={(event) => setAllowedPatternsDraft(event.target.value)}
                    type="text"
                    value={allowedPatternsDraft}
                  />
                </label>
                <label>
                  <span className="field-label">
                    Timeout de apply <InfoHint text="Tempo maximo, em segundos, para execucao do apply Linux." />
                  </span>
                  <input
                    className="input"
                    min="30"
                    onChange={(event) => setTimeoutDraft(event.target.value)}
                    type="number"
                    value={timeoutDraft}
                  />
                </label>
                <label>
                  <span className="field-label">
                    Grace de reboot Linux <InfoHint text="Tempo de tolerancia, em minutos, para reboot planejado." />
                  </span>
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
                  onClick={() => void handleExecutionGuardrailsSave("Politicas Linux salvas com sucesso.")}
                  type="button"
                >
                  {executionLoading ? "Salvando..." : "Salvar Linux"}
                </button>
              </div>
            </div>
          </section>
        </div>
      </section>

      <section className="settings-group settings-card-wide">
        <div className="settings-group-header">
          <div>
            <p className="eyebrow">Windows</p>
            <h2 className="section-title">Politicas Windows</h2>
          </div>
          <span className="muted">{settings?.execution.windows_scan_apply_enabled ? "scan habilitado" : "somente inventario"}</span>
        </div>
        <div className="settings-section-grid">
          <section className="panel section settings-tile settings-tile-wide">
            <div className="section-header">
              <h3 className="section-title">Execucao Windows</h3>
              <InfoHint text="Controla scan, download, install e reboot em hosts Windows." />
            </div>
            <div className="content-grid">
              <div className="compact-setting-list">
                <div className="setting-row">
                  <SettingTitle help="Permite scan controlado via UsoClient StartScan.">StartScan</SettingTitle>
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
                <div className="setting-row">
                  <SettingTitle help="Permite StartDownload e StartInstall nos hosts Windows.">
                    Download e install
                  </SettingTitle>
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
                <div className="setting-row">
                  <SettingTitle help="Tratamento do reboot pendente apos execucao Windows.">
                    Politica de reboot
                  </SettingTitle>
                  <div className="segmented-actions">
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
              </div>
              <div className="form-grid">
                <label>
                  <span className="field-label">
                    Timeout Windows <InfoHint text="Tempo maximo, em segundos, para comandos Windows." />
                  </span>
                  <input
                    className="input"
                    min="15"
                    onChange={(event) => setWindowsTimeoutDraft(event.target.value)}
                    type="number"
                    value={windowsTimeoutDraft}
                  />
                </label>
                <label>
                  <span className="field-label">
                    Grace de reboot Windows <InfoHint text="Tempo de tolerancia, em minutos, para reboot planejado." />
                  </span>
                  <input
                    className="input"
                    min="5"
                    onChange={(event) => setWindowsRebootGraceDraft(event.target.value)}
                    type="number"
                    value={windowsRebootGraceDraft}
                  />
                </label>
                <button
                  className="btn btn-primary"
                  disabled={executionLoading}
                  onClick={() => void handleExecutionGuardrailsSave("Politicas Windows salvas com sucesso.")}
                  type="button"
                >
                  {executionLoading ? "Salvando..." : "Salvar Windows"}
                </button>
              </div>
            </div>
          </section>

          <section className="panel section settings-tile settings-tile-wide">
            <div className="section-header">
              <h3 className="section-title">Comandos de instalacao</h3>
              <InfoHint text="Comandos gerados com base na URL publica e token bootstrap configurados." />
            </div>
            <div className="settings-command-grid">
              {[
                ["Instalacao Linux", installCommand],
                ["Atualizacao Linux", upgradeCommand],
                ["Instalacao Windows", windowsInstallCommand],
                ["Atualizacao Windows", windowsUpgradeCommand],
              ].map(([label, command]) => (
                <label key={label}>
                  <span className="field-label">{label}</span>
                  <code className="command-snippet">{command}</code>
                </label>
              ))}
            </div>
          </section>
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
