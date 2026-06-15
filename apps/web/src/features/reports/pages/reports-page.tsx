import { useEffect, useState } from "react";
import { fetchPatchJobs, fetchReports } from "@/features/reports/api";
import { StatusBadge } from "@/components/common/status-badge";
import { formatDateTimeSaoPaulo, formatTimeSaoPaulo } from "@/lib/datetime";
import type { PatchJobItem, ReportItem } from "@/features/reports/types";

function getJobVariant(status: PatchJobItem["status"]) {
  if (status === "completed") return "ok";
  if (status === "failed") return "error";
  return "warn";
}

function getFailureReasonLabel(reason: PatchJobItem["failure_reason"]) {
  switch (reason) {
    case "guardrail_real_apply_disabled":
      return "apply real desabilitado";
    case "guardrail_invalid_package_name":
      return "pacote bloqueado por validacao";
    case "guardrail_package_not_allowed":
      return "fora da allowlist";
    case "guardrail_not_upgradable":
      return "pacote nao atualizavel";
    case "guardrail_security_only_blocked":
      return "bloqueado por security-only";
    case "execution_error":
      return "falha de execucao";
    default:
      return null;
  }
}

function escapeCsv(value: unknown) {
  const normalized = String(value ?? "");
  return `"${normalized.replace(/"/g, '""')}"`;
}

function escapeHtml(value: unknown) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

export function ReportsPage() {
  const [jobs, setJobs] = useState<PatchJobItem[]>([]);
  const [rows, setRows] = useState<ReportItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [exportingFormat, setExportingFormat] = useState<string | null>(null);

  const guardrailBlockedJobs = jobs.filter((job) => job.failure_reason?.startsWith("guardrail_"));
  const pendingJobs = jobs.filter((job) => job.status === "pending");
  const runningJobs = jobs.filter((job) => job.status === "running");
  const completedJobs = jobs.filter((job) => job.status === "completed");
  const failedJobs = jobs.filter((job) => job.status === "failed");
  const successfulExecutions = rows.filter((row) => row.result === "applied" || row.result === "completed");
  const failedExecutions = rows.filter((row) => row.result === "failed");
  const totalFailures = failedJobs.length + failedExecutions.length;

  useEffect(() => {
    let active = true;

    async function load() {
      try {
        const [jobsResponse, reportsResponse] = await Promise.all([
          fetchPatchJobs(),
          fetchReports(),
        ]);
        if (!active) return;
        setJobs(jobsResponse);
        setRows(reportsResponse);
      } catch (err) {
        if (!active) return;
        setError(err instanceof Error ? err.message : "Falha ao carregar relatorios.");
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

  function downloadTextFile(filename: string, content: string, type: string) {
    const blob = new Blob([content], { type });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  }

  function buildReportPayload() {
    return {
      exported_at: new Date().toISOString(),
      source: "Patch Manager Reports",
      summary: {
        jobs_total: jobs.length,
        jobs_pending: pendingJobs.length,
        jobs_running: runningJobs.length,
        jobs_completed: completedJobs.length,
        jobs_failed: failedJobs.length,
        executions_total: rows.length,
        executions_successful: successfulExecutions.length,
        executions_failed: failedExecutions.length,
        guardrail_blocks: guardrailBlockedJobs.length,
      },
      jobs,
      executions: rows,
    };
  }

  function buildCsv() {
    const header = [
      "tipo",
      "data",
      "janela",
      "maquina",
      "patch",
      "plataforma",
      "severidade",
      "status_resultado",
      "agente",
      "erro_ou_duracao",
    ];
    const jobRows = jobs.map((job) => [
      "job",
      formatDateTimeSaoPaulo(job.created_at),
      job.schedule_name,
      job.machine_name,
      job.patch_id,
      job.platform,
      job.severity,
      job.status,
      job.claimed_by_agent ?? "Worker interno",
      job.error_message ?? "",
    ]);
    const executionRows = rows.map((row) => [
      "execucao",
      row.date,
      row.schedule,
      row.machine,
      row.patch,
      row.platform,
      row.severity,
      row.result,
      "",
      row.duration,
    ]);
    return [header, ...jobRows, ...executionRows]
      .map((line) => line.map(escapeCsv).join(","))
      .join("\n");
  }

  function buildHtmlReport() {
    const payload = buildReportPayload();
    const jobRows = jobs
      .map(
        (job) => `<tr><td>${escapeHtml(formatDateTimeSaoPaulo(job.created_at))}</td><td>${escapeHtml(job.schedule_name)}</td><td>${escapeHtml(job.machine_name)}</td><td>${escapeHtml(job.patch_id)}</td><td>${escapeHtml(job.status)}</td><td>${escapeHtml(job.error_message ?? "-")}</td></tr>`,
      )
      .join("");
    const executionRows = rows
      .map(
        (row) => `<tr><td>${escapeHtml(row.date)}</td><td>${escapeHtml(row.schedule)}</td><td>${escapeHtml(row.machine)}</td><td>${escapeHtml(row.patch)}</td><td>${escapeHtml(row.platform)}</td><td>${escapeHtml(row.result)}</td><td>${escapeHtml(row.duration)}</td></tr>`,
      )
      .join("");

    return `<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8" />
  <title>Patch Manager - Relatorio operacional</title>
  <style>
    body { font-family: Arial, sans-serif; color: #172033; margin: 32px; }
    h1, h2 { margin-bottom: 8px; }
    .meta { color: #52627a; margin-bottom: 24px; }
    .cards { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin: 20px 0; }
    .card { border: 1px solid #d8dee9; border-radius: 12px; padding: 14px; }
    .value { font-size: 28px; font-weight: 800; }
    table { width: 100%; border-collapse: collapse; margin-top: 14px; }
    th, td { border-bottom: 1px solid #d8dee9; padding: 8px; text-align: left; font-size: 12px; }
    th { background: #f4f6fb; }
  </style>
</head>
<body>
  <h1>Patch Manager - Relatorio operacional</h1>
  <div class="meta">Exportado em ${escapeHtml(formatDateTimeSaoPaulo(payload.exported_at))}</div>
  <div class="cards">
    <div class="card"><div>Jobs recentes</div><div class="value">${payload.summary.jobs_total}</div></div>
    <div class="card"><div>Execucoes</div><div class="value">${payload.summary.executions_total}</div></div>
    <div class="card"><div>Falhas</div><div class="value">${payload.summary.jobs_failed + payload.summary.executions_failed}</div></div>
    <div class="card"><div>Guardrails</div><div class="value">${payload.summary.guardrail_blocks}</div></div>
  </div>
  <h2>Fila de jobs</h2>
  <table><thead><tr><th>Criado em</th><th>Janela</th><th>Maquina</th><th>Patch</th><th>Status</th><th>Erro</th></tr></thead><tbody>${jobRows || '<tr><td colspan="6">Nenhum job registrado.</td></tr>'}</tbody></table>
  <h2>Historico de execucao</h2>
  <table><thead><tr><th>Data</th><th>Janela</th><th>Maquina</th><th>Patch</th><th>Plataforma</th><th>Resultado</th><th>Duracao</th></tr></thead><tbody>${executionRows || '<tr><td colspan="7">Nenhum evento registrado.</td></tr>'}</tbody></table>
</body>
</html>`;
  }

  function handleExport(format: "json" | "csv" | "xlsx" | "html" | "pdf") {
    setError(null);
    setExportingFormat(format);
    const exportedAt = new Date().toISOString().slice(0, 10);
    const baseName = `patch-manager-relatorio-${exportedAt}`;

    try {
      if (format === "json") {
        downloadTextFile(
          `${baseName}.json`,
          JSON.stringify(buildReportPayload(), null, 2),
          "application/json;charset=utf-8",
        );
      }
      if (format === "csv") {
        downloadTextFile(`${baseName}.csv`, buildCsv(), "text/csv;charset=utf-8");
      }
      if (format === "xlsx") {
        downloadTextFile(
          `${baseName}.xls`,
          buildHtmlReport(),
          "application/vnd.ms-excel;charset=utf-8",
        );
      }
      if (format === "html") {
        downloadTextFile(`${baseName}.html`, buildHtmlReport(), "text/html;charset=utf-8");
      }
      if (format === "pdf") {
        const printWindow = window.open("", "_blank", "noopener,noreferrer");
        if (!printWindow) throw new Error("O navegador bloqueou a janela de exportacao.");
        printWindow.document.write(buildHtmlReport());
        printWindow.document.close();
        printWindow.focus();
        printWindow.print();
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Falha ao exportar relatorio.");
    } finally {
      setExportingFormat(null);
    }
  }

  return (
    <div className="single-panel-grid">
      <section className="panel section">
        <div className="section-header">
          <div>
            <h2 className="section-title">Relatorio operacional</h2>
            <span className="muted">
              {loading
                ? "Carregando da API..."
                : `${rows.length} execucoes e ${jobs.length} jobs recentes`}
            </span>
          </div>
          <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
            {(["xlsx", "pdf", "csv", "json", "html"] as const).map((format) => (
              <button
                className={format === "xlsx" ? "btn btn-primary" : "btn"}
                disabled={exportingFormat !== null}
                key={format}
                onClick={() => handleExport(format)}
                type="button"
              >
                {exportingFormat === format ? "Exportando..." : `Exportar ${format.toUpperCase()}`}
              </button>
            ))}
          </div>
        </div>
        {error ? (
          <p className="muted" style={{ marginTop: 0, marginBottom: 16 }}>
            {error}. Verifique se a API esta ativa em `http://localhost:8000`.
          </p>
        ) : null}
        <div
          style={{
            display: "grid",
            gap: 12,
            gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
            marginBottom: 18,
          }}
        >
          <div className="list-item">
            <div>
              <div className="eyebrow">Instalados</div>
              <div style={{ fontSize: 28, fontWeight: 800 }}>{successfulExecutions.length}</div>
              <div className="muted">patches aplicados com sucesso</div>
            </div>
          </div>
          <div className="list-item">
            <div>
              <div className="eyebrow">Jobs</div>
              <div style={{ fontSize: 28, fontWeight: 800 }}>{jobs.length}</div>
              <div className="muted">
                {pendingJobs.length} pendentes, {runningJobs.length} em andamento
              </div>
            </div>
          </div>
          <div className="list-item">
            <div>
              <div className="eyebrow">Falhas</div>
              <div style={{ fontSize: 28, fontWeight: 800 }}>{totalFailures}</div>
              <div className="muted">jobs e execucoes com erro</div>
            </div>
          </div>
          <div className="list-item">
            <div>
              <div className="eyebrow">Guardrails</div>
              <div style={{ fontSize: 28, fontWeight: 800 }}>{guardrailBlockedJobs.length}</div>
              <div className="muted">bloqueios por politica local</div>
            </div>
          </div>
        </div>
        {guardrailBlockedJobs.length > 0 ? (
          <div className="list-item" style={{ marginBottom: 16, borderColor: "var(--warning-border, var(--border))" }}>
            <div>
              <div style={{ fontWeight: 700 }}>Bloqueios por guardrail</div>
              <div className="muted" style={{ marginTop: 4 }}>
                {guardrailBlockedJobs.length} jobs recentes foram bloqueados por regras de seguranca do agente Linux.
              </div>
              <div className="muted" style={{ marginTop: 4 }}>
                Mais recentes:{" "}
                {guardrailBlockedJobs
                  .slice(0, 3)
                  .map((job) => `${job.machine_name} / ${job.patch_id}`)
                  .join(", ")}
              </div>
            </div>
            <StatusBadge variant="warn">
              {`${guardrailBlockedJobs.length} bloqueados`}
            </StatusBadge>
          </div>
        ) : null}
      </section>

      <section className="panel section">
        <div className="section-header" style={{ marginTop: 8 }}>
          <h3 className="section-title">Patches instalados</h3>
          <span className="muted">
            {loading ? "Carregando..." : `${successfulExecutions.length} instalacoes registradas`}
          </span>
        </div>
        <table className="table" style={{ marginBottom: 22 }}>
          <thead>
            <tr>
              <th>Data</th>
              <th>Patch</th>
              <th>Maquina</th>
              <th>Plataforma</th>
              <th>Criticidade</th>
              <th>Janela</th>
              <th>Duracao</th>
            </tr>
          </thead>
          <tbody>
            {!loading && successfulExecutions.length === 0 ? (
              <tr>
                <td colSpan={7} className="muted">
                  Nenhum patch instalado registrado ainda.
                </td>
              </tr>
            ) : null}
            {successfulExecutions.map((row, idx) => (
              <tr key={`${row.date}-${row.machine}-${row.patch}-${idx}`}>
                <td className="code">{row.date}</td>
                <td className="code">{row.patch}</td>
                <td>{row.machine}</td>
                <td>{row.platform}</td>
                <td>{row.severity}</td>
                <td>{row.schedule}</td>
                <td className="code">{row.duration}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section className="panel section">
        <div className="section-header" style={{ marginTop: 8 }}>
          <h3 className="section-title">Fila de jobs</h3>
          <span className="muted">{loading ? "Carregando..." : `${jobs.length} jobs recentes`}</span>
        </div>
        <table className="table" style={{ marginBottom: 22 }}>
          <thead>
            <tr>
              <th>Criado em</th>
              <th>Janela</th>
              <th>Maquina</th>
              <th>Patch</th>
              <th>Agente</th>
              <th>Status</th>
              <th>Erro</th>
            </tr>
          </thead>
          <tbody>
            {!loading && jobs.length === 0 ? (
              <tr>
                <td colSpan={7} className="muted">
                  Nenhum job registrado.
                </td>
              </tr>
            ) : null}
            {jobs.map((job) => (
              <tr key={job.id}>
                <td className="code">{formatDateTimeSaoPaulo(job.created_at)}</td>
                <td>{job.schedule_name}</td>
                <td>{job.machine_name}</td>
                <td className="code">{job.patch_id}</td>
                <td className="muted">
                  {job.claimed_by_agent
                    ? `${job.claimed_by_agent}${
                        job.claimed_at ? ` - ${formatTimeSaoPaulo(job.claimed_at)}` : ""
                      }`
                    : "Worker interno"}
                </td>
                <td>
                  <StatusBadge variant={getJobVariant(job.status)}>{job.status}</StatusBadge>
                </td>
                <td className="muted">
                  {job.failure_reason ? (
                    <div style={{ display: "grid", gap: 6 }}>
                      <StatusBadge variant="warn">
                        {getFailureReasonLabel(job.failure_reason) ?? "guardrail"}
                      </StatusBadge>
                      <span>{job.error_message ?? "-"}</span>
                    </div>
                  ) : (
                    job.error_message ?? "-"
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section className="panel section">
        <div className="section-header">
          <h3 className="section-title">Historico completo de execucao</h3>
          <span className="muted">{loading ? "Carregando..." : `${rows.length} eventos (instalados e falhas)`}</span>
        </div>
        <table className="table">
          <thead>
            <tr>
              <th>Data</th>
              <th>Janela</th>
              <th>Maquina</th>
              <th>Patch</th>
              <th>Plataforma</th>
              <th>Severidade</th>
              <th>Resultado</th>
              <th>Duracao</th>
            </tr>
          </thead>
          <tbody>
            {!loading && rows.length === 0 ? (
              <tr>
                <td colSpan={8} className="muted">
                  Nenhum evento registrado.
                </td>
              </tr>
            ) : null}
            {rows.map((row, idx) => (
              <tr key={`${row.date}-${row.machine}-${row.patch}-${idx}`}>
                <td className="code">{row.date}</td>
                <td>{row.schedule}</td>
                <td>{row.machine}</td>
                <td className="code">{row.patch}</td>
                <td>{row.platform}</td>
                <td>{row.severity}</td>
                <td>
                  <StatusBadge variant={row.result === "applied" || row.result === "completed" ? "ok" : "error"}>
                    {row.result}
                  </StatusBadge>
                </td>
                <td className="code">{row.duration}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </div>
  );
}
