import { Outlet, useLocation } from "react-router-dom";
import { AppHeader } from "@/components/layout/app-header";
import { AppSidebar } from "@/components/layout/app-sidebar";

const pageMeta: Record<string, { title: string; subtitle: string }> = {
  "/": {
    title: "Dashboard",
    subtitle: "Visao operacional de conformidade, risco e atividade recente.",
  },
  "/machines": {
    title: "Maquinas",
    subtitle: "Inventario de endpoints Windows e Linux acompanhados pelo agente.",
  },
  "/patches": {
    title: "Aprovacoes",
    subtitle: "Fila de patches pendentes para aprovacao e rollout controlado.",
  },
  "/schedules": {
    title: "Agendamentos",
    subtitle: "Janelas de manutencao e politicas de execucao por grupo.",
  },
  "/operations": {
    title: "Operacoes",
    subtitle: "Acoes operacionais, pendencias e acompanhamento de agentes.",
  },
  "/reports": {
    title: "Relatorios",
    subtitle: "Historico operacional com foco em sucesso, falhas e auditoria.",
  },
  "/settings": {
    title: "Configuracoes",
    subtitle: "Politicas globais, notificacoes e defaults da plataforma.",
  },
  "/account": {
    title: "Minha conta",
    subtitle: "Perfil, avatar e seguranca do usuario conectado.",
  },
  "/users": {
    title: "Usuarios",
    subtitle: "Perfis de acesso e usuarios autorizados na plataforma.",
  },
};

function getPageMeta(pathname: string) {
  if (pathname.startsWith("/machines/")) {
    return {
      title: "Inventario detalhado do host",
      subtitle: "Inventario, jobs, execucoes e comandos operacionais de um unico host.",
    };
  }
  return pageMeta[pathname] ?? pageMeta["/"];
}

export function AppShell() {
  const location = useLocation();
  const meta = getPageMeta(location.pathname);

  return (
    <div className="app-shell">
      <AppSidebar />
      <main className="main-panel">
        <AppHeader title={meta.title} subtitle={meta.subtitle} />
        <div className="page-body">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
