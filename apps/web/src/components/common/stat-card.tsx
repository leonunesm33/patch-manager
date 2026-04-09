type StatCardProps = {
  label: string;
  value: string;
  detail: string;
  tone: string;
};

export function StatCard({ label, value, detail, tone }: StatCardProps) {
  return (
    <section className="panel stat-card" style={{ ["--tone" as string]: tone }}>
      <p className="eyebrow">{label}</p>
      <p className="metric">{value}</p>
      <p className="muted">{detail}</p>
    </section>
  );
}
