import { useEffect, useState } from "react";
import { StatCard } from "@/components/common/stat-card";
import { StatusBadge } from "@/components/common/status-badge";
import { fetchDashboard } from "@/features/dashboard/api";
import type { DashboardResponse } from "@/features/dashboard/types";

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
      ]
    : [];

  const distributionLabel = data
    ? `${data.platform_distribution.windows_servers} / ${data.platform_distribution.windows_workstations} / ${data.platform_distribution.linux_servers}`
    : "0 / 0 / 0";

  return (
    <div>
      <section className="hero">
        <h1 className="hero-title">Centro de operacao de atualizacoes</h1>
        <p className="hero-copy">
          Esta base inicial traduz o prototipo HTML em uma aplicacao React pronta para
          receber integracao com API, autenticacao e os agentes de patch para Windows
          e Linux.
        </p>
        <div className="status-strip">
          <span>
            <strong>API:</strong> {loading ? "carregando" : error ? "indisponivel" : "conectada"}
          </span>
          <span>
            <strong>Banco:</strong> PostgreSQL previsto
          </span>
          <span>
            <strong>Agentes:</strong> estrutura preparada
          </span>
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
            <h2 className="section-title">Volume semanal de patches</h2>
            <span className="muted">Windows x Linux</span>
          </div>
          <div className="chart-bars">
            {(data?.patch_volume ?? []).map((entry) => (
              <div key={entry.label}>
                <div className="bar-stack">
                  <div className="bar linux" style={{ height: `${entry.linux * 14}px` }} />
                  <div
                    className="bar windows"
                    style={{ height: `${entry.windows * 12}px` }}
                  />
                </div>
                <div className="bar-label">{entry.label}</div>
              </div>
            ))}
          </div>
        </section>

        <section className="panel section">
          <div className="section-header">
            <h2 className="section-title">Distribuicao do parque</h2>
            <span className="muted">{data?.summary.monitored_machines ?? 0} dispositivos</span>
          </div>
          <div className="ring-chart">
            <div className="ring">
              <span>{distributionLabel}</span>
            </div>
          </div>
        </section>
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
