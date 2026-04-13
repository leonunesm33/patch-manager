import { useEffect, useState } from "react";
import {
  fetchPatchJobs,
  fetchReports,
  processPatchJobs,
  runPatchCycle,
} from "@/features/reports/api";
import { StatusBadge } from "@/components/common/status-badge";
import type {
  PatchCycleRunResponse,
  PatchJobProcessResponse,
  PatchJobItem,
  ReportItem,
} from "@/features/reports/types";

function getJobVariant(status: PatchJobItem["status"]) {
  if (status === "completed") return "ok";
  if (status === "failed") return "error";
  return "warn";
}

export function ReportsPage() {
  const [jobs, setJobs] = useState<PatchJobItem[]>([]);
  const [rows, setRows] = useState<ReportItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [enqueuingCycle, setEnqueuingCycle] = useState(false);
  const [processingJobs, setProcessingJobs] = useState(false);
  const [cycleResult, setCycleResult] = useState<PatchCycleRunResponse | null>(null);
  const [processResult, setProcessResult] = useState<PatchJobProcessResponse | null>(null);

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

  async function reloadReports() {
    const [jobsResponse, reportsResponse] = await Promise.all([
      fetchPatchJobs(),
      fetchReports(),
    ]);
    setJobs(jobsResponse);
    setRows(reportsResponse);
  }

  async function handleRunCycle() {
    setError(null);
    setEnqueuingCycle(true);

    try {
      const response = await runPatchCycle();
      setCycleResult(response);
      await reloadReports();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Falha ao enfileirar jobs de patch.");
    } finally {
      setEnqueuingCycle(false);
    }
  }

  async function handleProcessJobs() {
    setError(null);
    setProcessingJobs(true);

    try {
      const response = await processPatchJobs();
      setProcessResult(response);
      await reloadReports();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Falha ao processar fila de jobs.");
    } finally {
      setProcessingJobs(false);
    }
  }

  return (
    <section className="panel section">
      <div className="section-header">
        <div>
          <h2 className="section-title">Historico de execucao</h2>
          <span className="muted">
            {loading ? "Carregando da API..." : `${rows.length} execucoes listadas`}
          </span>
        </div>
        <div style={{ display: "flex", gap: 10 }}>
          <button
            className="btn"
            disabled={enqueuingCycle}
            onClick={() => void handleRunCycle()}
            type="button"
          >
            {enqueuingCycle ? "Enfileirando..." : "Enfileirar jobs"}
          </button>
          <button
            className="btn btn-primary"
            disabled={processingJobs}
            onClick={() => void handleProcessJobs()}
            type="button"
          >
            {processingJobs ? "Processando..." : "Processar fila"}
          </button>
        </div>
      </div>
      {error ? (
        <p className="muted" style={{ marginTop: 0, marginBottom: 16 }}>
          {error}. Verifique se a API esta ativa em `http://localhost:8000`.
        </p>
      ) : null}
      {cycleResult ? (
        <div className="list-item" style={{ marginBottom: 16 }}>
          <div>
            <div style={{ fontWeight: 700 }}>Resumo do ultimo enfileiramento</div>
            <div className="muted" style={{ marginTop: 4 }}>
              {cycleResult.approved_patches} patches aprovados, {cycleResult.schedules_matched} agendas
              combinadas e {cycleResult.jobs_enqueued} jobs enfileirados.
            </div>
          </div>
          <StatusBadge variant={cycleResult.jobs_enqueued > 0 ? "ok" : "warn"}>
            {cycleResult.jobs_enqueued > 0
              ? `${cycleResult.jobs_enqueued} novos jobs`
              : "Nada enfileirado"}
          </StatusBadge>
        </div>
      ) : null}
      {processResult ? (
        <div className="list-item" style={{ marginBottom: 16 }}>
          <div>
            <div style={{ fontWeight: 700 }}>Resumo do ultimo processamento</div>
            <div className="muted" style={{ marginTop: 4 }}>
              {processResult.pending_jobs_before} jobs aguardavam na fila, {processResult.jobs_started} entraram em
              execucao, {processResult.jobs_processed} foram concluidos e {processResult.executions_created} logs de
              execucao foram gerados.
            </div>
          </div>
          <StatusBadge
            variant={
              processResult.failed_executions > 0
                ? "warn"
                : processResult.jobs_started > 0
                  ? "warn"
                  : "ok"
            }
          >
            {processResult.failed_executions > 0
              ? `${processResult.failed_executions} falhas`
              : processResult.jobs_started > 0
                ? `${processResult.jobs_started} em andamento`
                : "Sem falhas"}
          </StatusBadge>
        </div>
      ) : null}
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
              <td className="code">{new Date(job.created_at).toLocaleString("pt-BR")}</td>
              <td>{job.schedule_name}</td>
              <td>{job.machine_name}</td>
              <td className="code">{job.patch_id}</td>
              <td className="muted">
                {job.claimed_by_agent
                  ? `${job.claimed_by_agent}${job.claimed_at ? ` · ${new Date(job.claimed_at).toLocaleTimeString("pt-BR")}` : ""}`
                  : "Worker interno"}
              </td>
              <td>
                <StatusBadge variant={getJobVariant(job.status)}>{job.status}</StatusBadge>
              </td>
              <td className="muted">{job.error_message ?? "-"}</td>
            </tr>
          ))}
        </tbody>
      </table>
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
          {rows.map((row) => (
            <tr key={`${row.date}-${row.machine}-${row.patch}`}>
              <td className="code">{row.date}</td>
              <td>{row.schedule}</td>
              <td>{row.machine}</td>
              <td className="code">{row.patch}</td>
              <td>{row.platform}</td>
              <td>{row.severity}</td>
              <td>{row.result}</td>
              <td className="code">{row.duration}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
