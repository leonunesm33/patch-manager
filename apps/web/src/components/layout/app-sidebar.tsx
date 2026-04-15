import { NavLink } from "react-router-dom";

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

export function AppSidebar() {
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
        <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
          <div className="avatar">LM</div>
          <div>
            <div style={{ fontWeight: 700 }}>Infra Admin</div>
            <div className="muted" style={{ fontSize: "0.85rem" }}>
              Ambiente de homologacao
            </div>
          </div>
        </div>
      </div>
    </aside>
  );
}
