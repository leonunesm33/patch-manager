export type PatchApproval = {
  id: string;
  target: string;
  severity: "critical" | "important" | "optional";
  machines: number;
  release_date: string;
  approval_status: "pending" | "approved" | "rejected";
  reviewed_by: string | null;
  reviewed_at: string | null;
};

export type PatchCreate = {
  id: string;
  target: string;
  severity: "critical" | "important" | "optional";
  machines: number;
  release_date: string;
};
