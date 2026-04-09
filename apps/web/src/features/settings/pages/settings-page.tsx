import { useEffect, useState } from "react";
import { fetchSettings } from "@/features/settings/api";
import type { SettingsResponse } from "@/features/settings/types";

export function SettingsPage() {
  const [settings, setSettings] = useState<SettingsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;

    async function load() {
      try {
        const response = await fetchSettings();
        if (!active) return;
        setSettings(response);
      } catch (err) {
        if (!active) return;
        setError(err instanceof Error ? err.message : "Falha ao carregar configuracoes.");
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    }

    void load();

    return () => {
      active = false;
    };
  }, []);

  return (
    <div className="split-grid">
      <section className="panel section">
        <div className="section-header">
          <h2 className="section-title">Politicas de patch</h2>
        </div>
        {error ? (
          <p className="muted" style={{ marginTop: 0, marginBottom: 16 }}>
            {error}. Verifique se a API esta ativa em `http://localhost:8000`.
          </p>
        ) : null}
        {loading ? <p className="muted">Carregando configuracoes...</p> : null}
        {(settings?.policy ?? []).map((item) => (
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
        {(settings?.notifications ?? []).map((item) => (
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
