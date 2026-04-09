import type { MachineStatus, Platform, Severity } from "@/types/shared";

export type Machine = {
  id: string;
  name: string;
  ip: string;
  platform: Platform;
  group: string;
  status: MachineStatus;
  pendingPatches: number;
  lastCheckIn: string;
  risk: Severity;
};

export const machines: Machine[] = [
  {
    id: "srv-web-01",
    name: "SRV-WEB-01",
    ip: "10.0.1.21",
    platform: "Windows",
    group: "Web Servers",
    status: "online",
    pendingPatches: 4,
    lastCheckIn: "09/04 14:12",
    risk: "critical",
  },
  {
    id: "srv-db-02",
    name: "SRV-DB-02",
    ip: "10.0.2.11",
    platform: "Windows",
    group: "Database",
    status: "warning",
    pendingPatches: 7,
    lastCheckIn: "09/04 13:58",
    risk: "critical",
  },
  {
    id: "ubuntu-prod-03",
    name: "ubuntu-prod-03",
    ip: "10.1.4.33",
    platform: "Ubuntu",
    group: "Linux Production",
    status: "online",
    pendingPatches: 3,
    lastCheckIn: "09/04 14:10",
    risk: "important",
  },
  {
    id: "win10-fin-07",
    name: "WIN10-FIN-07",
    ip: "10.9.8.77",
    platform: "Windows",
    group: "Finance",
    status: "offline",
    pendingPatches: 6,
    lastCheckIn: "08/04 22:30",
    risk: "important",
  },
];
