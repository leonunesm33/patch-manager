import { reportRows } from "@/mocks/reports";

export function ReportsPage() {
  return (
    <section className="panel section">
      <div className="section-header">
        <h2 className="section-title">Historico de execucao</h2>
        <button className="btn">Exportar CSV</button>
      </div>
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
          {reportRows.map((row) => (
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
