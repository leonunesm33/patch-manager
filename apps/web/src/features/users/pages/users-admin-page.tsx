import { useEffect, useState } from "react";
import type { CSSProperties } from "react";
import { ConfirmModal } from "@/components/common/confirm-modal";
import { StatusBadge } from "@/components/common/status-badge";
import { useAuth } from "@/features/auth/auth-context";
import {
  createUser,
  fetchUserRoles,
  fetchUsers,
  resetUserPassword,
  updateUser,
} from "@/features/users/api";
import type { ManagedUser, UserCreatePayload, UserRole, UserUpdatePayload } from "@/features/users/types";
import { getRoleLabel, getUserInitials } from "@/features/users/utils";
import { formatDateTimeSaoPaulo } from "@/lib/datetime";

const DEFAULT_COLOR = "#00d4ff";

const emptyForm: UserCreatePayload = {
  username: "",
  full_name: "",
  password: "",
  role: "user",
  avatar_initials: null,
  avatar_color: DEFAULT_COLOR,
  is_active: true,
  must_change_password: true,
};

export function UsersAdminPage() {
  const { user: currentUser } = useAuth();
  const [users, setUsers] = useState<ManagedUser[]>([]);
  const [roles, setRoles] = useState<UserRole[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<{ tone: "ok" | "error"; message: string } | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [editingUser, setEditingUser] = useState<ManagedUser | null>(null);
  const [resetPasswordUser, setResetPasswordUser] = useState<ManagedUser | null>(null);
  const [newPassword, setNewPassword] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [form, setForm] = useState<UserCreatePayload>(emptyForm);

  async function load() {
    const [usersResponse, rolesResponse] = await Promise.all([fetchUsers(), fetchUserRoles()]);
    setUsers(usersResponse);
    setRoles(rolesResponse);
  }

  useEffect(() => {
    let active = true;
    async function run() {
      try {
        await load();
      } catch (err) {
        if (!active) return;
        setError(err instanceof Error ? err.message : "Falha ao carregar usuarios.");
      } finally {
        if (active) setLoading(false);
      }
    }
    void run();
    return () => {
      active = false;
    };
  }, []);

  function openCreateForm() {
    setEditingUser(null);
    setForm(emptyForm);
    setFeedback(null);
    setShowForm(true);
  }

  function openEditForm(user: ManagedUser) {
    setEditingUser(user);
    setForm({
      username: user.username,
      full_name: user.full_name,
      password: "",
      role: user.role,
      avatar_initials: user.avatar_initials,
      avatar_color: user.avatar_color ?? DEFAULT_COLOR,
      is_active: user.is_active,
      must_change_password: user.must_change_password,
    });
    setFeedback(null);
    setShowForm(true);
  }

  function closeForm() {
    setShowForm(false);
    setEditingUser(null);
    setForm(emptyForm);
  }

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsSubmitting(true);
    setFeedback(null);
    try {
      if (editingUser) {
        const payload: UserUpdatePayload = {
          full_name: form.full_name,
          role: form.role,
          avatar_initials: form.avatar_initials,
          avatar_color: form.avatar_color,
          is_active: form.is_active,
          must_change_password: form.must_change_password,
        };
        await updateUser(editingUser.id, payload);
        setFeedback({ tone: "ok", message: "Usuario atualizado com sucesso." });
      } else {
        await createUser(form);
        setFeedback({ tone: "ok", message: "Usuario criado com sucesso." });
      }
      closeForm();
      await load();
    } catch (err) {
      setFeedback({ tone: "error", message: err instanceof Error ? err.message : "Falha ao salvar usuario." });
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handlePasswordReset() {
    if (!resetPasswordUser) return;
    setIsSubmitting(true);
    setFeedback(null);
    try {
      await resetUserPassword(resetPasswordUser.id, {
        new_password: newPassword,
        must_change_password: true,
      });
      setResetPasswordUser(null);
      setNewPassword("");
      setFeedback({ tone: "ok", message: "Senha temporaria definida. O usuario devera alterar no proximo login." });
      await load();
    } catch (err) {
      setFeedback({ tone: "error", message: err instanceof Error ? err.message : "Falha ao redefinir senha." });
    } finally {
      setIsSubmitting(false);
    }
  }

  if (currentUser?.role !== "admin") {
    return (
      <section className="panel section">
        <h2 className="section-title">Acesso restrito</h2>
        <p className="muted">Apenas administradores podem gerenciar usuarios.</p>
      </section>
    );
  }

  return (
    <div className="single-panel-grid">
      <ConfirmModal
        open={resetPasswordUser !== null}
        title="Redefinir senha"
        description={
          resetPasswordUser
            ? `Defina uma senha temporaria para ${resetPasswordUser.username}. A troca sera obrigatoria no proximo acesso.`
            : ""
        }
        confirmLabel={isSubmitting ? "Salvando..." : "Redefinir senha"}
        confirmDisabled={isSubmitting || newPassword.length < 10}
        onCancel={() => {
          setResetPasswordUser(null);
          setNewPassword("");
        }}
        onConfirm={() => void handlePasswordReset()}
      >
        <label>
          <span className="field-label">Senha temporaria</span>
          <input
            className="input"
            minLength={10}
            type="password"
            value={newPassword}
            onChange={(event) => setNewPassword(event.target.value)}
          />
        </label>
      </ConfirmModal>

      <section className="panel section">
        <div className="section-header">
          <div>
            <h2 className="section-title">Usuarios da plataforma</h2>
            <p className="section-caption">Perfis disponiveis neste momento: Administrador e Usuario.</p>
          </div>
          <div style={{ display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap" }}>
            <span className="muted">{loading ? "Carregando..." : `${users.length} usuarios`}</span>
            <button className="btn btn-primary" onClick={openCreateForm} type="button">
              Novo usuario
            </button>
          </div>
        </div>
        {error ? <div className="inline-feedback inline-feedback-error">{error}</div> : null}
        {feedback ? <div className={`inline-feedback inline-feedback-${feedback.tone}`}>{feedback.message}</div> : null}
        <div className="user-role-grid">
          {roles.map((role) => (
            <div className="list-item" key={role.value}>
              <div>
                <div style={{ fontWeight: 700 }}>{role.label}</div>
                <div className="muted" style={{ marginTop: 4 }}>{role.description}</div>
              </div>
            </div>
          ))}
        </div>
        <table className="table">
          <thead>
            <tr>
              <th>Usuario</th>
              <th>Perfil</th>
              <th>Status</th>
              <th>Senha</th>
              <th>Criado em</th>
              <th>Acoes</th>
            </tr>
          </thead>
          <tbody>
            {users.map((item) => (
              <tr key={item.id}>
                <td>
                  <div className="user-cell">
                    <span className="avatar avatar-small" style={{ "--avatar-color": item.avatar_color ?? DEFAULT_COLOR } as CSSProperties}>
                      {getUserInitials(item.full_name || item.username, item.avatar_initials)}
                    </span>
                    <div>
                      <div style={{ fontWeight: 700 }}>{item.full_name}</div>
                      <div className="muted" style={{ marginTop: 4 }}>{item.username}</div>
                    </div>
                  </div>
                </td>
                <td>{getRoleLabel(item.role)}</td>
                <td>
                  <StatusBadge variant={item.is_active ? "ok" : "error"}>
                    {item.is_active ? "ativo" : "inativo"}
                  </StatusBadge>
                </td>
                <td>{item.must_change_password ? "troca obrigatoria" : "regular"}</td>
                <td className="code">{formatDateTimeSaoPaulo(item.created_at)}</td>
                <td>
                  <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
                    <button className="btn" onClick={() => openEditForm(item)} type="button">
                      Editar
                    </button>
                    <button
                      className="btn"
                      onClick={() => {
                        setResetPasswordUser(item);
                        setNewPassword("");
                      }}
                      type="button"
                    >
                      Redefinir senha
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      {showForm ? (
        <div className="modal-backdrop" role="dialog" aria-modal="true" aria-label="Formulario de usuario">
          <div className="modal-card modal-card-form">
            <div className="modal-header">
              <div>
                <p className="eyebrow">{editingUser ? "Edicao" : "Cadastro"}</p>
                <h3 className="modal-title">{editingUser ? "Editar usuario" : "Novo usuario"}</h3>
                <p className="modal-copy">Defina identificacao, avatar visual, perfil e status de acesso.</p>
              </div>
              <button className="btn" onClick={closeForm} type="button">
                Fechar
              </button>
            </div>
            <form className="form-grid" onSubmit={handleSubmit}>
              <label>
                <span className="field-label">Username</span>
                <input
                  className="input"
                  disabled={Boolean(editingUser)}
                  value={form.username}
                  onChange={(event) => setForm((current) => ({ ...current, username: event.target.value }))}
                />
              </label>
              <label>
                <span className="field-label">Nome exibido</span>
                <input
                  className="input"
                  value={form.full_name}
                  onChange={(event) => setForm((current) => ({ ...current, full_name: event.target.value }))}
                />
              </label>
              {!editingUser ? (
                <label>
                  <span className="field-label">Senha temporaria</span>
                  <input
                    className="input"
                    minLength={10}
                    type="password"
                    value={form.password}
                    onChange={(event) => setForm((current) => ({ ...current, password: event.target.value }))}
                  />
                </label>
              ) : null}
              <label>
                <span className="field-label">Perfil</span>
                <select
                  className="select"
                  value={form.role}
                  onChange={(event) =>
                    setForm((current) => ({ ...current, role: event.target.value as "admin" | "user" }))
                  }
                >
                  <option value="admin">Administrador</option>
                  <option value="user">Usuario</option>
                </select>
              </label>
              <label>
                <span className="field-label">Iniciais do avatar</span>
                <input
                  className="input"
                  maxLength={4}
                  value={form.avatar_initials ?? ""}
                  onChange={(event) =>
                    setForm((current) => ({ ...current, avatar_initials: event.target.value.toUpperCase() || null }))
                  }
                />
              </label>
              <label>
                <span className="field-label">Cor do avatar</span>
                <input
                  className="input"
                  value={form.avatar_color ?? ""}
                  onChange={(event) => setForm((current) => ({ ...current, avatar_color: event.target.value }))}
                  placeholder="#00d4ff"
                />
              </label>
              <label className="setting-toggle-row">
                <span>
                  <strong>Usuario ativo</strong>
                  <span className="muted">Permite login na console.</span>
                </span>
                <input
                  checked={form.is_active}
                  onChange={(event) => setForm((current) => ({ ...current, is_active: event.target.checked }))}
                  type="checkbox"
                />
              </label>
              <label className="setting-toggle-row">
                <span>
                  <strong>Forcar troca de senha</strong>
                  <span className="muted">Exige alteracao no proximo acesso.</span>
                </span>
                <input
                  checked={form.must_change_password}
                  onChange={(event) =>
                    setForm((current) => ({ ...current, must_change_password: event.target.checked }))
                  }
                  type="checkbox"
                />
              </label>
              <button className="btn btn-primary" disabled={isSubmitting} type="submit">
                {isSubmitting ? "Salvando..." : editingUser ? "Salvar usuario" : "Criar usuario"}
              </button>
            </form>
          </div>
        </div>
      ) : null}
    </div>
  );
}
