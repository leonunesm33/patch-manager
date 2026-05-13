import { useState } from "react";
import { NavLink } from "react-router-dom";
import { useAuth } from "@/features/auth/auth-context";

const navigation = [
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
    ],
  },
];

function getInitials(name: string) {
  const parts = name
    .trim()
    .split(/\s+/)
    .filter(Boolean);

  if (parts.length === 0) return "US";
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();

  return `${parts[0][0]}${parts[1][0]}`.toUpperCase();
}

export function AppSidebar() {
  const { user, logout } = useAuth();
  const [profileOpen, setProfileOpen] = useState(false);
  const displayName = user?.full_name || user?.username || "Usuario";
  const initials = getInitials(displayName);

  return (
    <aside className="sidebar">
      <div className="brand">
        <div className="brand-mark">PatchOps</div>
        <div className="brand-sub">Patch Manager v1.0</div>
      </div>

      {navigation.map((group) => (
        <div key={group.label} className="nav-group">
          <div className="nav-label">{group.label}</div>
          {group.items.map((item) => (
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
          <span className="avatar">{initials}</span>
          <span className="profile-name">{displayName}</span>
        </button>
        {profileOpen ? (
          <div className="profile-menu">
            <div className="profile-menu-meta">
              <strong>{user?.username ?? "usuario"}</strong>
              <span>{user?.role ?? "viewer"}</span>
            </div>
            <button className="btn btn-danger profile-logout" onClick={logout} type="button">
              Sair
            </button>
          </div>
        ) : null}
      </div>
    </aside>
  );
}
