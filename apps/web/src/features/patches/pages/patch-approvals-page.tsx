import { useEffect, useState } from "react";
import { fetchPatchApprovals } from "@/features/patches/api";
import type { PatchApproval } from "@/features/patches/types";

export function PatchApprovalsPage() {
  const [patches, setPatches] = useState<PatchApproval[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;

    async function load() {
      try {
        const response = await fetchPatchApprovals();
        if (!active) return;
        setPatches(response);
      } catch (err) {
        if (!active) return;
        setError(err instanceof Error ? err.message : "Falha ao carregar aprovacoes.");
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
        <h2 className="section-title">Fila de aprovacoes</h2>
        <span className="muted">
          {loading ? "Carregando da API..." : `${patches.length} itens pendentes`}
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
            <th>Patch</th>
            <th>Escopo</th>
            <th>Severidade</th>
            <th>Maquinas</th>
            <th>Lancamento</th>
          </tr>
        </thead>
        <tbody>
          {!loading && patches.length === 0 ? (
            <tr>
              <td colSpan={5} className="muted">
                Nenhum patch aguardando aprovacao.
              </td>
            </tr>
          ) : null}
          {patches.map((patch) => (
            <tr key={patch.id}>
              <td className="code">{patch.id}</td>
              <td>{patch.target}</td>
              <td>{patch.severity}</td>
              <td>{patch.machines}</td>
              <td className="code">{patch.release_date}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
