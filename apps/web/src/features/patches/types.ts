export type PatchSeverity = "low" | "medium" | "moderate" | "high" | "critical" | "important" | "optional" | "unknown";
export type PatchCategory = "security" | "bugfix" | "enhancement" | "driver" | "firmware" | "feature" | "stability" | "other" | "unknown" | "normal";

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
  display_name: string | null;
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
  display_name: string | null;
  target: string;
  severity: PatchSeverity;
  category: PatchCategory | string;
  machines: number;
  release_date: string;
};
