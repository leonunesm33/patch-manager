import { pendingApprovals } from "@/mocks/patches";

export function PatchApprovalsPage() {
  return (
    <section className="panel section">
      <div className="section-header">
        <h2 className="section-title">Fila de aprovacoes</h2>
        <button className="btn btn-primary">Aprovar selecionados</button>
      </div>
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
          {pendingApprovals.map((patch) => (
            <tr key={patch.id}>
              <td className="code">{patch.id}</td>
              <td>{patch.target}</td>
              <td>{patch.severity}</td>
              <td>{patch.machines}</td>
              <td className="code">{patch.releaseDate}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
