import { useState } from "react";
import type { CSSProperties } from "react";
import { NavLink } from "react-router-dom";
import { useAuth } from "@/features/auth/auth-context";
import { getUserInitials } from "@/features/users/utils";

type NavItem = {
  to: string;
  name: string;
  badge?: string;
  adminOnly?: boolean;
};

const navigation: Array<{ label: string; items: NavItem[] }> = [
  {
    label: "Principal",
    items: [{ to: "/", name: "Dashboard" }, { to: "/machines", name: "Maquinas" }],
  },
  {
    label: "Patches",
    items: [
      { to: "/patches", name: "Aprovacoes", badge: "7" },
      { to: "/schedules", name: "Agendamentos" },
    ],
  },
  {
    label: "Analise",
    items: [
      { to: "/operations", name: "Operacoes" },
      { to: "/reports", name: "Relatorios" },
      { to: "/settings", name: "Configuracoes" },
      { to: "/users", name: "Usuarios", adminOnly: true },
    ],
  },
];

export function AppSidebar() {
  const { user, logout } = useAuth();
  const [profileOpen, setProfileOpen] = useState(false);
  const displayName = user?.username || user?.full_name || "Usuario";
  const secondaryName = user?.full_name && user.full_name !== displayName ? user.full_name : null;
  const initials = getUserInitials(displayName, user?.avatar_initials);
  const avatarColor = user?.avatar_color ?? "#00d4ff";

  return (
    <aside className="sidebar">
      <div className="brand">
        <div className="brand-mark">PatchOps</div>
        <div className="brand-sub">Patch Manager v1.0</div>
      </div>

      {navigation.map((group) => (
        <div key={group.label} className="nav-group">
          <div className="nav-label">{group.label}</div>
          {group.items.filter((item) => !item.adminOnly || user?.role === "admin").map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === "/"}
              className={({ isActive }) =>
                isActive ? "nav-link active" : "nav-link"
              }
            >
              <span>{item.name}</span>
              {item.badge ? <span className="nav-badge">{item.badge}</span> : null}
            </NavLink>
          ))}
        </div>
      ))}

      <div className="sidebar-footer">
        <button
          aria-expanded={profileOpen}
          className="profile-button"
          onClick={() => setProfileOpen((current) => !current)}
          type="button"
        >
          <span className="avatar" style={{ "--avatar-color": avatarColor } as CSSProperties}>{initials}</span>
          <span className="profile-name">{displayName}</span>
        </button>
        {profileOpen ? (
          <div className="profile-menu">
            <div className="profile-menu-meta">
              <strong>{displayName}</strong>
              {secondaryName ? <span>{secondaryName}</span> : null}
            </div>
            <NavLink className="btn profile-account-link" to="/account" onClick={() => setProfileOpen(false)}>
              Minha conta
            </NavLink>
            <button className="btn btn-danger profile-logout" onClick={logout} type="button">
              Sair
            </button>
          </div>
        ) : null}
      </div>
    </aside>
  );
}
