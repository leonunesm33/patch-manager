import { useEffect, useState } from "react";
import { fetchMachines } from "@/features/machines/api";
import type { Machine } from "@/features/machines/types";
import { StatusBadge } from "@/components/common/status-badge";

function getVariant(status: string) {
  if (status === "online") return "ok";
  if (status === "warning") return "warn";
  return "error";
}

export function MachinesPage() {
  const [machines, setMachines] = useState<Machine[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;

    async function load() {
      try {
        const response = await fetchMachines();
        if (!active) return;
        setMachines(response);
      } catch (err) {
        if (!active) return;
        setError(err instanceof Error ? err.message : "Falha ao carregar maquinas.");
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
        <h2 className="section-title">Inventario de maquinas</h2>
        <span className="muted">
          {loading ? "Carregando da API..." : `${machines.length} maquinas carregadas`}
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
            <th>Host</th>
            <th>IP</th>
            <th>Plataforma</th>
            <th>Grupo</th>
            <th>Patches pendentes</th>
            <th>Ultimo check-in</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          {!loading && machines.length === 0 ? (
            <tr>
              <td colSpan={7} className="muted">
                Nenhuma maquina encontrada.
              </td>
            </tr>
          ) : null}
          {machines.map((machine) => (
            <tr key={machine.id}>
              <td style={{ fontWeight: 700 }}>{machine.name}</td>
              <td className="code">{machine.ip}</td>
              <td>{machine.platform}</td>
              <td>{machine.group}</td>
              <td>{machine.pending_patches}</td>
              <td className="code">{machine.last_check_in}</td>
              <td>
                <StatusBadge variant={getVariant(machine.status)}>
                  {machine.status}
                </StatusBadge>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
