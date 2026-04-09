import { settingsGroups } from "@/mocks/settings";

export function SettingsPage() {
  return (
    <div className="split-grid">
      <section className="panel section">
        <div className="section-header">
          <h2 className="section-title">Politicas de patch</h2>
        </div>
        {settingsGroups.policy.map((item) => (
          <div key={item.label} className="setting-row">
            <div>
              <div style={{ fontWeight: 700 }}>{item.label}</div>
              <div className="muted" style={{ marginTop: 4 }}>
                {item.description}
              </div>
            </div>
            <div className={item.enabled ? "pill-switch on" : "pill-switch"} />
          </div>
        ))}
      </section>

      <section className="panel section">
        <div className="section-header">
          <h2 className="section-title">Notificacoes</h2>
        </div>
        {settingsGroups.notifications.map((item) => (
          <div key={item.label} className="setting-row">
            <div>
              <div style={{ fontWeight: 700 }}>{item.label}</div>
              <div className="muted" style={{ marginTop: 4 }}>
                {item.description}
              </div>
            </div>
            <div className={item.enabled ? "pill-switch on" : "pill-switch"} />
          </div>
        ))}
      </section>
    </div>
  );
}
