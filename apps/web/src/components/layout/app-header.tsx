type AppHeaderProps = {
  title: string;
  subtitle: string;
};

export function AppHeader({ title, subtitle }: AppHeaderProps) {
  return (
    <header className="topbar">
      <div>
        <div className="topbar-title">{title}</div>
        <div className="topbar-subtitle">{subtitle}</div>
      </div>

      <div className="topbar-actions">
        <button className="btn">Exportar</button>
        <button className="btn btn-primary">Nova janela</button>
      </div>
    </header>
  );
}
