import { createBrowserRouter } from "react-router-dom";
import { AppShell } from "@/components/layout/app-shell";
import { LoginPage } from "@/features/auth/pages/login-page";
import { RequireAuth } from "@/features/auth/require-auth";
import { DashboardPage } from "@/features/dashboard/pages/dashboard-page";
import { MachinesPage } from "@/features/machines/pages/machines-page";
import { PatchApprovalsPage } from "@/features/patches/pages/patch-approvals-page";
import { ReportsPage } from "@/features/reports/pages/reports-page";
import { SchedulesPage } from "@/features/schedules/pages/schedules-page";
import { SettingsPage } from "@/features/settings/pages/settings-page";

export const router = createBrowserRouter([
  {
    path: "/login",
    element: <LoginPage />,
  },
  {
    element: <RequireAuth />,
    children: [
      {
        path: "/",
        element: <AppShell />,
        children: [
          { index: true, element: <DashboardPage /> },
          { path: "machines", element: <MachinesPage /> },
          { path: "patches", element: <PatchApprovalsPage /> },
          { path: "schedules", element: <SchedulesPage /> },
          { path: "reports", element: <ReportsPage /> },
          { path: "settings", element: <SettingsPage /> },
        ],
      },
    ],
  },
]);
