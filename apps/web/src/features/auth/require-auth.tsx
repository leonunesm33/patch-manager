import { Navigate, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "@/features/auth/auth-context";

export function RequireAuth() {
  const location = useLocation();
  const { token, isLoading } = useAuth();

  if (isLoading) {
    return (
      <section className="panel section" style={{ maxWidth: 540, margin: "48px auto" }}>
        <div className="section-title">Validando sessao...</div>
      </section>
    );
  }

  if (!token) {
    return <Navigate to="/login" replace state={{ from: location }} />;
  }

  return <Outlet />;
}
