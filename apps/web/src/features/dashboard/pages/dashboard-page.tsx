import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { StatCard } from "@/components/common/stat-card";
import { StatusBadge } from "@/components/common/status-badge";
import { fetchDashboard } from "@/features/dashboard/api";
import type { DashboardResponse } from "@/features/dashboard/types";
import { formatDateTimeSaoPaulo } from "@/lib/datetime";

function formatPercent(value: number, total: number) {
  if (total <= 0) return "0%";
  const percent = (value / total) * 100;
  return `${Number(percent.toFixed(percent < 10 && percent > 0 ? 1 : 0))}%`;
}

export function DashboardPage() {
  const [data, setData] = useState<DashboardResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;

    async function load() {
      try {
        const response = await fetchDashboard();
        if (!active) return;
        setData(response);
      } catch (err) {
        if (!active) return;
        setError(err instanceof Error ? err.message : "Falha ao carregar dashboard.");
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

  const metrics = data
    ? [
        {
          label: "Maquinas monitoradas",
          value: String(data.summary.monitored_machines),
          detail: "visao consolidada do ambiente",
          tone: "#00d4ff",
        },
        {
          label: "Patches pendentes",
          value: String(data.summary.pending_patches),
          detail: "fila pronta para rollout e aprovacao",
          tone: "#ffc542",
        },
        {
          label: "Conformidade",
          value: `${data.summary.compliance_rate}%`,
          detail: "janela dos ultimos 30 dias",
          tone: "#00e5a0",
        },
        {
          label: "Falhas recentes",
          value: String(data.summary.failed_jobs),
          detail: "execucoes com necessidade de revisao",
          tone: "#ff4d6a",
        },
        {
          label: "Reboot pendente",
          value: String(data.summary.reboot_pending_hosts),
          detail: "hosts aguardando acao pos-patch",
          tone: "#ff8a3d",
        },
        {
          label: "Reboot agendado",
          value: String(data.summary.reboot_scheduled_hosts),
          detail: "hosts com reboot ja programado",
          tone: "#ffb347",
        },
        {
          label: "Comandos pendentes",
          value: String(data.summary.pending_agent_commands),
          detail: "comandos administrativos aguardando retorno",
          tone: "#8f7cff",
        },
        {
          label: "Updates Windows",
          value: String(data.summary.windows_pending_updates),
          detail: "updates reportados pelo pool Windows",
          tone: "#3dd9b8",
        },
        {
          label: "Seguranca pendente",
          value: String(data.summary.security_pending_patches),
          detail: "patches de seguranca aguardando aprovacao",
          tone: "#ff4d6a",
        },
        {
          label: "Seguranca instalada",
          value: String(data.summary.security_installed_patches),
          detail: "patches de seguranca aplicados (registros recentes)",
          tone: "#00e5a0",
        },
      ]
    : [];

  const distributionLabel = data
    ? `${data.platform_distribution.windows_servers} / ${data.platform_distribution.windows_workstations} / ${data.platform_distribution.linux_servers}`
    : "0 / 0 / 0";
  const windowsServerCount = data?.platform_distribution.windows_servers ?? 0;
  const windowsWorkstationCount = data?.platform_distribution.windows_workstations ?? 0;
  const linuxServerCount = data?.platform_distribution.linux_servers ?? 0;
  const weeklyWindowsTotal = (data?.patch_volume ?? []).reduce(
    (total, entry) => total + entry.windows,
    0,
  );
  const weeklyLinuxTotal = (data?.patch_volume ?? []).reduce(
    (total, entry) => total + entry.linux,
    0,
  );
  const CHART_MAX_PX = 100;
  const patchVolumeMaxValue = Math.max(
    1,
    ...(data?.patch_volume ?? []).flatMap((e) => [e.linux, e.windows]),
  );
  function barPx(value: number): number {
    if (value === 0) return 0;
    return Math.max(3, Math.round((value / patchVolumeMaxValue) * CHART_MAX_PX));
  }
  const totalDistributionDevices =
    windowsServerCount + windowsWorkstationCount + linuxServerCount;
  const distributionSegments = [
    {
      label: "Servidores Windows",
      value: windowsServerCount,
      className: "windows-server",
    },
    {
      label: "Estacoes Windows",
      value: windowsWorkstationCount,
      className: "windows-workstation",
    },
    {
      label: "Servidores Linux",
      value: linuxServerCount,
      className: "linux",
    },
  ];
  let distributionOffset = 0;
  const distributionArcs = distributionSegments.map((segment) => {
    const percent = totalDistributionDevices
      ? (segment.value / totalDistributionDevices) * 100
      : 0;
    const arc = {
      ...segment,
      offset: distributionOffset,
      percent,
      tooltip: `${segment.label}: ${segment.value} dispositivos (${formatPercent(
        segment.value,
        totalDistributionDevices,
      )})`,
    };
    distributionOffset += percent;
    return arc;
  });
  const systemStatusItems = [
    {
      label: "API",
      value: loading ? "carregando" : error ? "indisponivel" : "conectada",
      variant: loading ? "warn" : error ? "error" : "ok",
    },
    {
      label: "Banco de dados",
      value: loading ? "validando" : error ? "sem resposta" : "operacional",
      variant: loading ? "warn" : error ? "error" : "ok",
    },
  ] as const;

  return (
    <div>
      <section className="hero">
        <div className="hero-title">Status do sistema</div>
        <div className="status-strip">
          {systemStatusItems.map((item) => (
            <div key={item.label} className="status-pill">
              <span className="status-pill-label">{item.label}</span>
              <StatusBadge variant={item.variant}>{item.value}</StatusBadge>
            </div>
          ))}
        </div>
      </section>

      {error ? (
        <section className="panel section">
          <div className="section-title">Falha ao carregar dashboard</div>
          <p className="muted" style={{ marginTop: 8 }}>
            {error}. Verifique se a API esta rodando em `http://localhost:8000`.
          </p>
        </section>
      ) : null}

      {loading ? (
        <section className="panel section">
          <div className="section-title">Carregando indicadores...</div>
        </section>
      ) : (
        <section className="cards-grid">
          {metrics.map((metric) => (
            <StatCard key={metric.label} {...metric} />
          ))}
        </section>
      )}

      <section className="content-grid">
        <section className="panel section">
          <div className="section-header">
            <div>
              <h2 className="section-title">Volume semanal de patches</h2>
              <p className="section-caption">
                Quantidade de patches pendentes reportados por plataforma em cada dia.
              </p>
            </div>
            <Link className="reference-link" to="/patches">
              Ver aprovacoes
            </Link>
          </div>
          <div className="chart-bars">
            {(data?.patch_volume ?? []).map((entry) => {
              const dailyTotal = entry.windows + entry.linux;
              const linuxTooltip = `Linux - ${entry.label}: ${entry.linux} patches (${formatPercent(
                entry.linux,
                dailyTotal,
              )})`;
              const windowsTooltip = `Windows - ${entry.label}: ${entry.windows} patches (${formatPercent(
                entry.windows,
                dailyTotal,
              )})`;

              return (
                <div key={entry.label} className="bar-column">
                  <div className="bar-stack">
                    <div className="bar-value">{dailyTotal}</div>
                    <div
                      className="bar linux chart-hover-target"
                      data-tooltip={linuxTooltip}
                      role="img"
                      style={{ height: `${barPx(entry.linux)}px` }}
                      title={linuxTooltip}
                    />
                    <div
                      className="bar windows chart-hover-target"
                      data-tooltip={windowsTooltip}
                      role="img"
                      style={{ height: `${barPx(entry.windows)}px` }}
                      title={windowsTooltip}
                    />
                  </div>
                  <div className="bar-label">{entry.label}</div>
                </div>
              );
            })}
          </div>
          <div className="chart-reference">
            <div className="legend-list">
              <span className="legend-item">
                <span className="legend-dot linux" />
                Linux: {weeklyLinuxTotal} patches na semana
              </span>
              <span className="legend-item">
                <span className="legend-dot windows" />
                Windows: {weeklyWindowsTotal} patches na semana
              </span>
            </div>
          </div>
        </section>

        <section className="panel section">
          <div className="section-header">
            <div>
              <h2 className="section-title">Distribuicao do parque</h2>
              <p className="section-caption">
                Classificacao dos dispositivos monitorados por tipo de sistema.
              </p>
            </div>
            <Link className="reference-link" to="/machines">
              Ver maquinas
            </Link>
          </div>
          <div className="ring-chart">
            <div className="ring">
              <svg
                aria-label="Distribuicao do parque por plataforma"
                className="ring-svg"
                role="img"
                viewBox="0 0 180 180"
              >
                {totalDistributionDevices === 0 ? (
                  <circle className="ring-segment empty" cx="90" cy="90" r="70">
                    <title>Nenhum dispositivo monitorado no inventario</title>
                  </circle>
                ) : (
                  distributionArcs.map((segment) => (
                    <circle
                      key={segment.label}
                      aria-label={segment.tooltip}
                      className={`ring-segment ${segment.className}`}
                      cx="90"
                      cy="90"
                      pathLength="100"
                      r="70"
                      strokeDasharray={`${segment.percent} ${100 - segment.percent}`}
                      strokeDashoffset={-segment.offset}
                    >
                      <title>{segment.tooltip}</title>
                    </circle>
                  ))
                )}
              </svg>
              <span>{distributionLabel}</span>
            </div>
          </div>
          <div className="chart-reference">
            <div className="legend-list vertical">
              <span className="legend-item">
                <span className="legend-dot windows-server" />
                Servidores Windows: {windowsServerCount}
              </span>
              <span className="legend-item">
                <span className="legend-dot windows-workstation" />
                Estacoes Windows: {windowsWorkstationCount}
              </span>
              <span className="legend-item">
                <span className="legend-dot linux" />
                Servidores Linux: {linuxServerCount}
              </span>
            </div>
          </div>
        </section>
      </section>

      <section className="panel section">
        <div className="section-header">
          <h2 className="section-title">Acoes pendentes</h2>
          <span className="muted">{data?.pending_actions.length ?? 0} itens prioritarios</span>
        </div>
        <div className="list">
          {(data?.pending_actions ?? []).length === 0 ? (
            <div className="list-item">
              <div className="muted">Nenhuma acao pendente critica no momento.</div>
            </div>
          ) : null}
          {(data?.pending_actions ?? []).map((item) => (
            <div key={`${item.action_type}-${item.title}`} className="list-item">
              <div>
                <div style={{ fontWeight: 700 }}>{item.title}</div>
                <div className="muted" style={{ marginTop: 4 }}>
                  {item.detail}
                </div>
              </div>
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
            </div>
          ))}
        </div>
      </section>

      <section className="panel section">
        <div className="section-header">
          <h2 className="section-title">Hosts em estado pos-patch</h2>
          <span className="muted">{data?.reboot_pending.length ?? 0} hosts com reboot sinalizado</span>
        </div>
        <div className="list">
          {(data?.reboot_pending ?? []).length === 0 ? (
            <div className="list-item">
              <div className="muted">Nenhum host com reboot pendente ou agendado no momento.</div>
            </div>
          ) : null}
          {(data?.reboot_pending ?? []).map((item) => (
            <div key={`${item.agent_id}-${item.last_seen_at}`} className="list-item">
              <div>
                <div style={{ fontWeight: 700 }}>
                  {item.hostname} - {item.platform}
                </div>
                <div className="muted" style={{ marginTop: 4 }}>
                  {item.primary_ip ?? "n/d"}
                </div>
                {item.post_patch_message ? (
                  <div className="muted" style={{ marginTop: 4 }}>
                    {item.post_patch_message}
                  </div>
                ) : null}
                <div className="muted" style={{ marginTop: 4 }}>
                  Ultimo heartbeat: {formatDateTimeSaoPaulo(item.last_seen_at)}
                </div>
              </div>
              <div style={{ textAlign: "right", display: "grid", gap: 8, justifyItems: "end" }}>
                <StatusBadge variant={item.post_patch_state === "reboot-scheduled" ? "ok" : "warn"}>
                  {item.post_patch_state === "reboot-scheduled" ? "reboot agendado" : "reboot pendente"}
                </StatusBadge>
                {item.reboot_scheduled_at ? (
                  <div className="muted">agendado em {formatDateTimeSaoPaulo(item.reboot_scheduled_at)}</div>
                ) : null}
              </div>
            </div>
          ))}
        </div>
      </section>

      <section className="panel section">
        <div className="section-header">
          <h2 className="section-title">Atividade recente</h2>
          <span className="muted">ultimos eventos de patching</span>
        </div>
        <div className="list">
          {(data?.activity ?? []).map((item) => (
            <div key={item.title} className="list-item">
              <div>
                <div style={{ fontWeight: 700 }}>{item.title}</div>
                <div className="muted" style={{ marginTop: 4 }}>
                  {item.detail}
                </div>
              </div>
              <StatusBadge variant={item.status as "ok" | "warn" | "error"}>
                {item.status === "ok"
                  ? "Saudavel"
                  : item.status === "warn"
                    ? "Atencao"
                    : "Falha"}
              </StatusBadge>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
