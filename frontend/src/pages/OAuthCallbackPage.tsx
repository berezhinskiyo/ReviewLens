import { useEffect, useRef, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export function OAuthCallbackPage() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const { completeOAuthLogin } = useAuth();
  const [error, setError] = useState("");
  const startedRef = useRef(false);

  useEffect(() => {
    if (startedRef.current) return;
    startedRef.current = true;

    const accessToken = params.get("access_token") || "";
    const refreshToken = params.get("refresh_token") || "";
    if (!accessToken || !refreshToken) {
      setError("Не удалось завершить вход через провайдера");
      return;
    }
    void completeOAuthLogin(accessToken, refreshToken)
      .then(() => navigate("/dashboard", { replace: true }))
      .catch((err) => setError((err as Error).message));
  }, [completeOAuthLogin, navigate, params]);

  return (
    <div className="container" style={{ padding: 64, maxWidth: 460 }}>
      <div className="card">
        <div className="card-body center stack">
          <h2>Вход через провайдера</h2>
          {error ? (
            <>
              <p className="error-text">{error}</p>
              <Link to="/" className="btn btn-secondary">
                На главную
              </Link>
            </>
          ) : (
            <>
              <div className="spinner" />
              <p className="muted">Завершаем вход…</p>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
