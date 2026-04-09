type StatusBadgeProps = {
  variant: "ok" | "warn" | "error";
  children: string;
};

export function StatusBadge({ variant, children }: StatusBadgeProps) {
  return <span className={`tag ${variant}`}>{children}</span>;
}
