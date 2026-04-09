import { schedules } from "@/mocks/schedules";

export function SchedulesPage() {
  return (
    <div className="split-grid">
      <section className="panel section">
        <div className="section-header">
          <h2 className="section-title">Agendamentos ativos</h2>
          <span className="muted">Politicas por grupo</span>
        </div>
        <div className="list">
          {schedules.map((schedule) => (
            <div key={schedule.id} className="list-item">
              <div>
                <div style={{ fontWeight: 700 }}>{schedule.name}</div>
                <div className="muted" style={{ marginTop: 4 }}>
                  {schedule.scope}
                </div>
              </div>
              <div style={{ textAlign: "right" }}>
                <div className="code">{schedule.cronLabel}</div>
                <div className="muted" style={{ marginTop: 4 }}>
                  {schedule.rebootPolicy}
                </div>
              </div>
            </div>
          ))}
        </div>
      </section>

      <section className="panel section">
        <div className="section-header">
          <h2 className="section-title">Nova janela de manutencao</h2>
          <span className="muted">Formulario inicial</span>
        </div>
        <div className="form-grid">
          <label>
            <span className="field-label">Nome</span>
            <input className="input" placeholder="Ex.: Linux Production Weekly" />
          </label>
          <label>
            <span className="field-label">Escopo</span>
            <select className="select" defaultValue="Ubuntu Production">
              <option>Ubuntu Production</option>
              <option>Windows Servers</option>
              <option>Finance Workstations</option>
            </select>
          </label>
          <label>
            <span className="field-label">Horario</span>
            <input className="input" type="time" defaultValue="02:00" />
          </label>
          <label>
            <span className="field-label">Politica de reboot</span>
            <select className="select" defaultValue="Somente se necessario">
              <option>Somente se necessario</option>
              <option>Sempre reiniciar</option>
              <option>Nunca reiniciar</option>
            </select>
          </label>
          <button className="btn btn-primary">Criar agendamento</button>
        </div>
      </section>
    </div>
  );
}
