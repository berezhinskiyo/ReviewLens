import { Navigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { token, loading } = useAuth();

  if (loading) {
    return (
      <div className="container" style={{ padding: "64px 0" }}>
        <div className="spinner" />
        <p className="muted center">Загрузка…</p>
      </div>
    );
  }

  if (!token) return <Navigate to="/?auth=1" replace />;

  return <>{children}</>;
}
