import { useState } from "react";
import type { CSSProperties } from "react";
import { useAuth } from "@/features/auth/auth-context";
import { getUserInitials, getRoleLabel } from "@/features/users/utils";

const AVATAR_COLORS = ["#00d4ff", "#00e5a0", "#ffc542", "#ff6b6b", "#a855f7", "#4ee7ff"];

export function AccountPage() {
  const { user, updateProfile, changePassword } = useAuth();
  const [fullName, setFullName] = useState(user?.full_name ?? "");
  const [avatarInitials, setAvatarInitials] = useState(user?.avatar_initials ?? "");
  const [avatarColor, setAvatarColor] = useState(user?.avatar_color ?? AVATAR_COLORS[0]);
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [profileFeedback, setProfileFeedback] = useState<{ tone: "ok" | "error"; message: string } | null>(null);
  const [passwordFeedback, setPasswordFeedback] = useState<{ tone: "ok" | "error"; message: string } | null>(null);
  const [savingProfile, setSavingProfile] = useState(false);
  const [savingPassword, setSavingPassword] = useState(false);

  if (!user) {
    return (
      <section className="panel section">
        <p className="muted" style={{ margin: 0 }}>Carregando usuario...</p>
      </section>
    );
  }

  async function handleProfileSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setProfileFeedback(null);
    setSavingProfile(true);
    try {
      await updateProfile({
        full_name: fullName,
        avatar_initials: avatarInitials.trim() || null,
        avatar_color: avatarColor,
      });
      setProfileFeedback({ tone: "ok", message: "Perfil atualizado com sucesso." });
    } catch (err) {
      setProfileFeedback({
        tone: "error",
        message: err instanceof Error ? err.message : "Falha ao atualizar perfil.",
      });
    } finally {
      setSavingProfile(false);
    }
  }

  async function handlePasswordSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPasswordFeedback(null);
    if (newPassword !== confirmPassword) {
      setPasswordFeedback({ tone: "error", message: "A confirmacao da senha nao confere." });
      return;
    }
    setSavingPassword(true);
    try {
      await changePassword(currentPassword, newPassword);
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
      setPasswordFeedback({ tone: "ok", message: "Senha atualizada com sucesso." });
    } catch (err) {
      setPasswordFeedback({
        tone: "error",
        message: err instanceof Error ? err.message : "Falha ao alterar senha.",
      });
    } finally {
      setSavingPassword(false);
    }
  }

  const initials = getUserInitials(fullName || user.username, avatarInitials);

  return (
    <div className="content-grid">
      <section className="panel section">
        <div className="section-header">
          <div>
            <h2 className="section-title">Perfil do usuario</h2>
            <p className="section-caption">Nome, avatar visual e informacoes da conta.</p>
          </div>
          <span className="muted">{getRoleLabel(user.role)}</span>
        </div>
        <form className="form-grid" onSubmit={handleProfileSubmit}>
          <div className="user-avatar-preview" style={{ "--avatar-color": avatarColor } as CSSProperties}>
            <span>{initials}</span>
            <div>
              <strong>{fullName || user.username}</strong>
              <p className="muted" style={{ margin: "4px 0 0" }}>{user.username}</p>
            </div>
          </div>
          <label>
            <span className="field-label">Nome exibido</span>
            <input className="input" value={fullName} onChange={(event) => setFullName(event.target.value)} />
          </label>
          <label>
            <span className="field-label">Iniciais do avatar</span>
            <input
              className="input"
              maxLength={4}
              value={avatarInitials}
              onChange={(event) => setAvatarInitials(event.target.value.toUpperCase())}
              placeholder="Ex.: LM"
            />
          </label>
          <div>
            <span className="field-label">Cor do avatar</span>
            <div className="avatar-color-grid">
              {AVATAR_COLORS.map((color) => (
                <button
                  aria-label={`Selecionar cor ${color}`}
                  className={avatarColor === color ? "avatar-color-option selected" : "avatar-color-option"}
                  key={color}
                  onClick={() => setAvatarColor(color)}
                  style={{ "--avatar-color": color } as React.CSSProperties}
                  type="button"
                />
              ))}
            </div>
          </div>
          {profileFeedback ? (
            <div className={`inline-feedback inline-feedback-${profileFeedback.tone}`}>
              {profileFeedback.message}
            </div>
          ) : null}
          <button className="btn btn-primary" disabled={savingProfile} type="submit">
            {savingProfile ? "Salvando..." : "Salvar perfil"}
          </button>
        </form>
      </section>

      <section className="panel section">
        <div className="section-header">
          <div>
            <h2 className="section-title">Seguranca</h2>
            <p className="section-caption">Altere sua senha periodicamente para proteger a console.</p>
          </div>
        </div>
        <form className="form-grid" onSubmit={handlePasswordSubmit}>
          <label>
            <span className="field-label">Senha atual</span>
            <input
              className="input"
              type="password"
              value={currentPassword}
              onChange={(event) => setCurrentPassword(event.target.value)}
            />
          </label>
          <label>
            <span className="field-label">Nova senha</span>
            <input
              className="input"
              type="password"
              value={newPassword}
              onChange={(event) => setNewPassword(event.target.value)}
            />
          </label>
          <label>
            <span className="field-label">Confirmar nova senha</span>
            <input
              className="input"
              type="password"
              value={confirmPassword}
              onChange={(event) => setConfirmPassword(event.target.value)}
            />
          </label>
          {passwordFeedback ? (
            <div className={`inline-feedback inline-feedback-${passwordFeedback.tone}`}>
              {passwordFeedback.message}
            </div>
          ) : null}
          <button className="btn btn-primary" disabled={savingPassword} type="submit">
            {savingPassword ? "Salvando..." : "Modificar senha"}
          </button>
        </form>
      </section>
    </div>
  );
}
