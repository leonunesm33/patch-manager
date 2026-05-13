export type PatchSeverity = "low" | "medium" | "high" | "critical" | "important" | "optional";
export type PatchCategory = "security" | "bugfix" | "feature" | "stability" | "other";

export type PatchAffectedMachine = {
  id: string;
  name: string;
  ip: string;
  platform: string;
  environment: string;
  group: string;
  status: string;
};

export type PatchApproval = {
  id: string;
  target: string;
  severity: PatchSeverity;
  category: PatchCategory | string;
  machines: number;
  affected_machines: PatchAffectedMachine[];
  release_date: string;
  approval_status: "pending" | "approved" | "rejected";
  reviewed_by: string | null;
  reviewed_at: string | null;
};

export type PatchCreate = {
  id: string;
  target: string;
  severity: PatchSeverity;
  category: PatchCategory | string;
  machines: number;
  release_date: string;
};
