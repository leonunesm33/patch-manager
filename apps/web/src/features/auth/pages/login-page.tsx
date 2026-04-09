export function LoginPage() {
  return (
    <section className="panel section" style={{ maxWidth: 420, margin: "48px auto" }}>
      <div className="section-header">
        <h2 className="section-title">Login</h2>
        <span className="muted">placeholder para JWT</span>
      </div>
      <div className="form-grid">
        <label>
          <span className="field-label">Usuario</span>
          <input className="input" placeholder="admin@empresa.com" />
        </label>
        <label>
          <span className="field-label">Senha</span>
          <input className="input" type="password" placeholder="••••••••" />
        </label>
        <button className="btn btn-primary">Entrar</button>
      </div>
    </section>
  );
}
