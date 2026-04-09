import { FormEvent, useState } from "react";
import { Navigate, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "@/features/auth/auth-context";

export function LoginPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const { token, login } = useAuth();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  if (token) {
    return <Navigate to="/" replace />;
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);

    try {
      await login(username, password);
      const nextPath = (location.state as { from?: { pathname?: string } } | null)?.from
        ?.pathname;
      navigate(nextPath || "/", { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Falha ao autenticar.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <section
      className="panel section"
      style={{
        maxWidth: 460,
        margin: "64px auto",
        borderRadius: 24,
      }}
    >
      <div className="section-header" style={{ marginBottom: 10 }}>
        <h2 className="section-title">Entrar no Patch Manager</h2>
        <span className="muted">JWT ativo</span>
      </div>
      <p className="muted" style={{ marginTop: 0, marginBottom: 20 }}>
        Use o usuario inicial criado pelo seed para acessar o painel.
      </p>
      <form className="form-grid" onSubmit={handleSubmit}>
        <label>
          <span className="field-label">Usuario</span>
          <input
            className="input"
            value={username}
            onChange={(event) => setUsername(event.target.value)}
            placeholder="Digite seu usuario"
            autoComplete="username"
          />
        </label>
        <label>
          <span className="field-label">Senha</span>
          <input
            className="input"
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            placeholder="Digite sua senha"
            autoComplete="current-password"
          />
        </label>
        {error ? (
          <p className="muted" style={{ margin: 0, color: "#ff9fb0" }}>
            {error}
          </p>
        ) : null}
        <button className="btn btn-primary" type="submit" disabled={isSubmitting}>
          {isSubmitting ? "Entrando..." : "Entrar"}
        </button>
      </form>
    </section>
  );
}
