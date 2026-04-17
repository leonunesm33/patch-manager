import { FormEvent, useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { useAuth } from "@/features/auth/auth-context";

export function ChangePasswordPage() {
  const navigate = useNavigate();
  const { token, user, changePassword, logout } = useAuth();
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  if (!token) {
    return <Navigate to="/login" replace />;
  }

  if (!user?.must_change_password) {
    return <Navigate to="/" replace />;
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    if (newPassword !== confirmPassword) {
      setError("A confirmacao da nova senha precisa ser igual.");
      return;
    }

    setIsSubmitting(true);
    try {
      await changePassword(currentPassword, newPassword);
      navigate("/", { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Falha ao atualizar a senha.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <section
      className="panel section"
      style={{
        maxWidth: 520,
        margin: "64px auto",
        borderRadius: 24,
      }}
    >
      <div className="section-header" style={{ marginBottom: 10 }}>
        <h2 className="section-title">Atualizar senha inicial</h2>
        <span className="muted">{user.role}</span>
      </div>
      <p className="muted" style={{ marginTop: 0, marginBottom: 20 }}>
        Por seguranca, a senha inicial precisa ser trocada antes de acessar o restante do painel.
      </p>
      <form className="form-grid" onSubmit={handleSubmit}>
        <label>
          <span className="field-label">Senha atual</span>
          <input
            className="input"
            type="password"
            value={currentPassword}
            onChange={(event) => setCurrentPassword(event.target.value)}
            autoComplete="current-password"
          />
        </label>
        <label>
          <span className="field-label">Nova senha</span>
          <input
            className="input"
            type="password"
            value={newPassword}
            onChange={(event) => setNewPassword(event.target.value)}
            autoComplete="new-password"
          />
        </label>
        <label>
          <span className="field-label">Confirmar nova senha</span>
          <input
            className="input"
            type="password"
            value={confirmPassword}
            onChange={(event) => setConfirmPassword(event.target.value)}
            autoComplete="new-password"
          />
        </label>
        {error ? (
          <p className="muted" style={{ margin: 0, color: "#ff9fb0" }}>
            {error}
          </p>
        ) : null}
        <div style={{ display: "flex", gap: 10 }}>
          <button className="btn btn-primary" type="submit" disabled={isSubmitting}>
            {isSubmitting ? "Atualizando..." : "Atualizar senha"}
          </button>
          <button className="btn" onClick={logout} type="button">
            Sair
          </button>
        </div>
      </form>
    </section>
  );
}
