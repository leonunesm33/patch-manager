import { createPortal } from "react-dom";
import { useEffect, useState, type ReactNode } from "react";
import { ConfirmModal } from "@/components/common/confirm-modal";
import { CopyButton } from "@/components/common/copy-button";
import { InfoHint } from "@/components/common/info-hint";
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
        allow_security_and_critical: settings?.execution.allow_security_and_critical,
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
        allow_security_and_critical: settings.execution.allow_security_and_critical,
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
              <InfoHint text="Dispara jobs nos horarios agendados e entrega aos agentes. Pausar aqui congela toda execucao de patches — use apenas para manutencao da central." />
            </div>
            {schedulerStatus ? (
              <div className="compact-setting-list">
                <div className="setting-row">
                  <SettingTitle help="Com que frequencia a central verifica os agendamentos ativos e cria novos jobs para execucao.">
                    Enfileiramento
                  </SettingTitle>
                  <span className="code">{schedulerStatus.enqueue_interval_seconds}s</span>
                </div>
                <div className="setting-row">
                  <SettingTitle help="Com que frequencia a central entrega o proximo job pendente para um agente executar.">
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
                  Bootstrap token <InfoHint text="Senha temporaria usada por novos agentes na primeira conexao com a central. Compartilhe apenas durante a instalacao — rotacione apos uso em lote para impedir novos cadastros nao autorizados." />
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
                  URL publica do servidor <InfoHint text="Endereco HTTPS desta central acessivel pelos hosts gerenciados. E usado nos comandos de instalacao dos agentes e nas chamadas de heartbeat e inventario." />
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
                  Expiracao do token <InfoHint text="Apos esse prazo, o token expira e novos agentes nao conseguem se cadastrar. Rotacione ou renove antes do vencimento se ainda houver maquinas a instalar." />
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
              <InfoHint text="dry-run: apenas coleta inventario e simula, sem instalar nada — ideal para validar antes de habilitar patches reais. apply: executa a instalacao das atualizacoes aprovadas segundo as politicas abaixo." />
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
                  <SettingTitle help={item.uses_default ? "Herda o modo global definido acima (apply ou dry-run). Para sobrescrever, selecione um modo especifico." : "Modo especifico para este grupo — substitui o modo global. Util para promover grupos gradualmente sem afetar todos os hosts."}>
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
                  <SettingTitle help={`Chave mestra: quando desligado, nenhum job Linux instala nada de verdade, mesmo com modo 'apply' ativo — age como dry-run. Ligue somente apos validar allowlist, timeout e ambiente. ${realApplyAuditLabel}`}>Apply real</SettingTitle>
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
                  <SettingTitle help="Quando ligado, instala apenas pacotes classificados como 'security' (ex: vindos do repositorio jammy-security). Patches de bugfix e enhancement sao ignorados — util para ambientes que so aceitam correcoes criticas. Mutuamente exclusivo com 'Seguranca e criticos'.">
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
                                allow_security_and_critical: current.execution.allow_security_only
                                  ? current.execution.allow_security_and_critical
                                  : false,
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
                  <SettingTitle help="Quando ligado, instala pacotes classificados como 'security' OU com severidade critica, independente da categoria. Mais permissivo que 'Somente seguranca'. Mutuamente exclusivo com ela.">
                    Seguranca e criticos
                  </SettingTitle>
                  <button
                    className={settings?.execution.allow_security_and_critical ? "btn btn-primary" : "btn"}
                    disabled={executionLoading}
                    onClick={() =>
                      setSettings((current) =>
                        current
                          ? {
                              ...current,
                              execution: {
                                ...current.execution,
                                allow_security_and_critical: !current.execution.allow_security_and_critical,
                                allow_security_only: current.execution.allow_security_and_critical
                                  ? current.execution.allow_security_only
                                  : false,
                              },
                            }
                          : current,
                      )
                    }
                    type="button"
                  >
                    {settings?.execution.allow_security_and_critical ? "Ligado" : "Desligado"}
                  </button>
                </div>
                <div className="setting-row">
                  <SettingTitle help="O que fazer quando um patch Linux exige reinicializacao: 'manual' = aguarda acao do operador; 'notify' = registra a pendencia sem reiniciar (para uso futuro com alertas); 'maintenance-window' = reinicia automaticamente apos o grace period configurado abaixo.">
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
                    Allowlist de pacotes <InfoHint text="Padroes de nomes de pacotes que podem ser instalados em apply real (ex: 'openssl*, nginx*'). Deixe vazio para sem restricao. Use para limitar o apply a pacotes especificos e evitar surpresas." />
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
                    Timeout de apply <InfoHint text="Tempo maximo, em segundos, que o agente aguarda o apt-get concluir a instalacao antes de marcar o job como falho. Atualizacoes grandes ou conexoes lentas podem precisar de valores maiores (ex: 900s = 15min)." />
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
                    Grace de reboot Linux <InfoHint text="Quando a politica e 'maintenance-window', o agente aguarda esse tempo (em minutos) antes de reiniciar o host Linux — dando margem para processos em andamento finalizarem." />
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
              <InfoHint text="Controla se o agente Windows pode acionar o Windows Update e como lidar com reinicializacoes. Ambos os toggles precisam estar ligados para uma instalacao completa." />
            </div>
            <div className="content-grid">
              <div className="compact-setting-list">
                <div className="setting-row">
                  <SettingTitle help="Autoriza o agente a acionar uma varredura do Windows Update no host (UsoClient StartScan). Sem isso, todos os jobs Windows falham imediatamente sem instalar nada.">StartScan</SettingTitle>
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
                  <SettingTitle help="Autoriza o agente a baixar e instalar as atualizacoes encontradas pelo scan (StartDownload + StartInstall). Exige StartScan ligado. Quando desligado, o job apenas escaneia — util para verificar o que seria instalado sem aplicar.">
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
                  <SettingTitle help="O que fazer quando um patch Windows exige reinicializacao: 'manual' = aguarda acao do operador; 'notify' = registra a pendencia sem reiniciar (para uso futuro com alertas); 'maintenance-window' = agenda o reboot automaticamente apos o grace period abaixo.">
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
                    Timeout Windows <InfoHint text="Tempo maximo, em segundos, que o agente aguarda cada etapa do Windows Update (scan, download, install). Redes lentas ou pacotes grandes podem precisar de valores maiores (ex: 300s = 5min por etapa)." />
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
                    Grace de reboot Windows <InfoHint text="Quando a politica e 'maintenance-window', o agente aguarda esse tempo (em minutos) antes de reiniciar o host Windows — dando margem para usuarios salvarem trabalho em andamento." />
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
              <InfoHint text="Comandos prontos para instalar ou atualizar o agente em cada plataforma. Copie e execute no host de destino com privilegios de administrador. Apos instalar, aprove o agente em Maquinas > Pendentes." />
            </div>
            <div className="settings-command-grid">
              {[
                ["Instalacao Linux", installCommand],
                ["Atualizacao Linux", upgradeCommand],
                ["Instalacao Windows", windowsInstallCommand],
                ["Atualizacao Windows", windowsUpgradeCommand],
              ].map(([label, command]) => (
                <label key={label}>
                  <span className="field-label" style={{ display: "flex", alignItems: "center", gap: 8 }}>
                    {label}
                    {command ? <CopyButton text={command} /> : null}
                  </span>
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
