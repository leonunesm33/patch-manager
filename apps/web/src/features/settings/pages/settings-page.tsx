import { useEffect, useState } from "react";
import { StatusBadge } from "@/components/common/status-badge";
import {
  fetchConnectedAgents,
  fetchSchedulerStatus,
  fetchSettings,
  startScheduler,
  stopScheduler,
  updateLinuxExecutionMode,
} from "@/features/settings/api";
import type {
  ConnectedAgent,
  ExecutionSettings,
  SchedulerStatusResponse,
  SettingsResponse,
} from "@/features/settings/types";

export function SettingsPage() {
  const [connectedAgents, setConnectedAgents] = useState<ConnectedAgent[]>([]);
  const [settings, setSettings] = useState<SettingsResponse | null>(null);
  const [schedulerStatus, setSchedulerStatus] = useState<SchedulerStatusResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [schedulerLoading, setSchedulerLoading] = useState(false);
  const [executionLoading, setExecutionLoading] = useState(false);

  useEffect(() => {
    let active = true;

    async function load() {
      try {
        const [settingsResponse, schedulerResponse, agentsResponse] = await Promise.all([
          fetchSettings(),
          fetchSchedulerStatus(),
          fetchConnectedAgents(),
        ]);
        if (!active) return;
        setSettings(settingsResponse);
        setSchedulerStatus(schedulerResponse);
        setConnectedAgents(agentsResponse);
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
      const response = await updateLinuxExecutionMode(mode);
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
                    ? new Date(schedulerStatus.next_enqueue_run_at).toLocaleString("pt-BR")
                    : "sem agenda"}
                </div>
                <div className="muted" style={{ marginTop: 4 }}>
                  Worker:{" "}
                  {schedulerStatus.next_worker_run_at
                    ? new Date(schedulerStatus.next_worker_run_at).toLocaleString("pt-BR")
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
                    ? new Date(schedulerStatus.last_enqueue_run_at).toLocaleString("pt-BR")
                    : "nunca executado"}
                </div>
                <div className="muted" style={{ marginTop: 4 }}>
                  Worker:{" "}
                  {schedulerStatus.last_worker_run_at
                    ? new Date(schedulerStatus.last_worker_run_at).toLocaleString("pt-BR")
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
              </div>
              <div style={{ textAlign: "right" }}>
                <StatusBadge variant="ok">online</StatusBadge>
                <div className="muted" style={{ marginTop: 8 }}>
                  {new Date(agent.last_seen_at).toLocaleString("pt-BR")}
                </div>
              </div>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
