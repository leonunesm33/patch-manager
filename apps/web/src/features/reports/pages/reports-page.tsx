import { useEffect, useState } from "react";
import { fetchReports } from "@/features/reports/api";
import type { ReportItem } from "@/features/reports/types";

export function ReportsPage() {
  const [rows, setRows] = useState<ReportItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;

    async function load() {
      try {
        const response = await fetchReports();
        if (!active) return;
        setRows(response);
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

  return (
    <section className="panel section">
      <div className="section-header">
        <h2 className="section-title">Historico de execucao</h2>
        <span className="muted">
          {loading ? "Carregando da API..." : `${rows.length} execucoes listadas`}
        </span>
      </div>
      {error ? (
        <p className="muted" style={{ marginTop: 0, marginBottom: 16 }}>
          {error}. Verifique se a API esta ativa em `http://localhost:8000`.
        </p>
      ) : null}
      <table className="table">
        <thead>
          <tr>
            <th>Data</th>
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
              <td colSpan={7} className="muted">
                Nenhum evento registrado.
              </td>
            </tr>
          ) : null}
          {rows.map((row) => (
            <tr key={`${row.date}-${row.machine}-${row.patch}`}>
              <td className="code">{row.date}</td>
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
