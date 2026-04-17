import type { AgentInventoryDetail } from "@/features/agents/types";
import { StatusBadge } from "@/components/common/status-badge";
import { formatDateTimeSaoPaulo } from "@/lib/datetime";

type AgentInventoryDetailPanelProps = {
  detail: AgentInventoryDetail | null;
  loading: boolean;
  error: string | null;
  title?: string;
};

function renderVersion(label: string, value: string | null) {
  if (!value) return null;
  return (
    <span className="code" style={{ marginRight: 10 }}>
      {label}: {value}
    </span>
  );
}

export function AgentInventoryDetailPanel({
  detail,
  loading,
  error,
  title = "Inventario detalhado",
}: AgentInventoryDetailPanelProps) {
  return (
    <section className="panel section">
      <div className="section-header">
        <h2 className="section-title">{title}</h2>
        <span className="muted">
          {detail
            ? `${detail.hostname} - ${detail.package_manager}`
            : loading
              ? "Carregando..."
              : "Selecione um host gerenciado por agente"}
        </span>
      </div>

      {error ? (
        <p className="muted" style={{ marginTop: 0, marginBottom: 16 }}>
          {error}
        </p>
      ) : null}

      {loading ? <p className="muted">Carregando inventario detalhado...</p> : null}

      {!loading && !detail ? (
        <p className="muted">
          Quando voce abrir o inventario de um agente, vamos mostrar aqui a lista detalhada de
          updates pendentes e o historico recente instalado nesse host.
        </p>
      ) : null}

      {detail ? (
        <div style={{ display: "grid", gap: 18 }}>
          <div className="list">
            <div className="list-item">
              <div>
                <div style={{ fontWeight: 700 }}>Pendentes</div>
                <div className="muted" style={{ marginTop: 4 }}>
                  {detail.pending_count} updates reportados neste host
                </div>
              </div>
              <div className="muted">
                {detail.updated_at ? formatDateTimeSaoPaulo(detail.updated_at) : "sem data"}
              </div>
            </div>
          </div>
          <div className="list">
            {detail.pending_updates.length === 0 ? (
              <div className="list-item">
                <div className="muted">Nenhum update pendente detalhado no momento.</div>
              </div>
            ) : null}
            {detail.pending_updates.map((item) => (
              <div key={`pending-${item.identifier}-${item.target_version ?? "na"}`} className="list-item">
                <div>
                  <div style={{ fontWeight: 700 }}>
                    {item.title}
                    {item.kb_id ? ` - ${item.kb_id}` : ""}
                  </div>
                  <div className="muted" style={{ marginTop: 4 }}>
                    {renderVersion("Atual", item.current_version)}
                    {renderVersion("Destino", item.target_version)}
                    {item.source ? <span className="code">Fonte: {item.source}</span> : null}
                  </div>
                  {item.summary ? (
                    <div className="muted" style={{ marginTop: 4 }}>
                      {item.summary}
                    </div>
                  ) : null}
                </div>
                <div style={{ textAlign: "right" }}>
                  <StatusBadge variant={item.security_only ? "warn" : "ok"}>
                    {item.security_only ? "security" : "pending"}
                  </StatusBadge>
                </div>
              </div>
            ))}
          </div>

          <div className="list">
            <div className="list-item">
              <div>
                <div style={{ fontWeight: 700 }}>Instalados recentemente</div>
                <div className="muted" style={{ marginTop: 4 }}>
                  {detail.installed_updates.length} itens detalhados no snapshot atual
                </div>
              </div>
            </div>
            {detail.installed_updates.length === 0 ? (
              <div className="list-item">
                <div className="muted">Nenhum update instalado recente foi capturado ainda.</div>
              </div>
            ) : null}
            {detail.installed_updates.map((item) => (
              <div key={`installed-${item.identifier}-${item.installed_at ?? item.target_version ?? "na"}`} className="list-item">
                <div>
                  <div style={{ fontWeight: 700 }}>
                    {item.title}
                    {item.kb_id ? ` - ${item.kb_id}` : ""}
                  </div>
                  <div className="muted" style={{ marginTop: 4 }}>
                    {renderVersion("Anterior", item.current_version)}
                    {renderVersion("Instalado", item.target_version)}
                    {item.source ? <span className="code">Origem: {item.source}</span> : null}
                  </div>
                  {item.summary ? (
                    <div className="muted" style={{ marginTop: 4 }}>
                      {item.summary}
                    </div>
                  ) : null}
                </div>
                <div className="muted" style={{ textAlign: "right" }}>
                  {item.installed_at ? formatDateTimeSaoPaulo(item.installed_at) : "sem data"}
                </div>
              </div>
            ))}
          </div>
        </div>
      ) : null}
    </section>
  );
}
