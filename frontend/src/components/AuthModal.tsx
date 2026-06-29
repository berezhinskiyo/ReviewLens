import { useState } from "react";
import { API_URL } from "../api/client";
import { useAuth } from "../context/AuthContext";
import { SmartCaptcha, captchaEnabled } from "./SmartCaptcha";

type Mode = "login" | "register";

export function AuthModal({
  onClose,
  onSuccess,
}: {
  onClose: () => void;
  onSuccess: () => void;
}) {
  const { login, requestRegisterCode, verifyRegisterCode } = useAuth();
  const [mode, setMode] = useState<Mode>("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [code, setCode] = useState("");
  const [codeSent, setCodeSent] = useState(false);
  const [captchaToken, setCaptchaToken] = useState<string | undefined>();
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const oauthUrl = (provider: string) =>
    `${API_URL}/auth/oauth/${provider}/start`;

  async function submitLogin(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      await login(email, password);
      onSuccess();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function submitRequestCode(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      await requestRegisterCode(email, password, captchaToken);
      setCodeSent(true);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function submitVerify(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      await verifyRegisterCode(email, code);
      onSuccess();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="auth-overlay" onClick={onClose}>
      <div className="auth-card" onClick={(e) => e.stopPropagation()}>
        <h2 className="center">Добро пожаловать в ReviewLens</h2>
        <p className="muted center" style={{ marginTop: 4 }}>
          1 бесплатный анализ при регистрации
        </p>

        <div className="auth-tabs">
          <button
            className={`auth-tab${mode === "login" ? " active" : ""}`}
            onClick={() => {
              setMode("login");
              setError("");
            }}
          >
            Вход
          </button>
          <button
            className={`auth-tab${mode === "register" ? " active" : ""}`}
            onClick={() => {
              setMode("register");
              setError("");
              setCodeSent(false);
            }}
          >
            Регистрация
          </button>
        </div>

        {mode === "login" && (
          <form onSubmit={submitLogin} className="stack">
            <div>
              <label className="field-label">Email</label>
              <input
                className="input"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                autoComplete="email"
              />
            </div>
            <div>
              <label className="field-label">Пароль</label>
              <input
                className="input"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                autoComplete="current-password"
              />
            </div>
            {error && <p className="error-text">{error}</p>}
            <button className="btn btn-primary btn-block" disabled={busy}>
              {busy ? "Входим…" : "Войти"}
            </button>
          </form>
        )}

        {mode === "register" && !codeSent && (
          <form onSubmit={submitRequestCode} className="stack">
            <div>
              <label className="field-label">Email</label>
              <input
                className="input"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                autoComplete="email"
              />
            </div>
            <div>
              <label className="field-label">Пароль (минимум 8 символов)</label>
              <input
                className="input"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                minLength={8}
                autoComplete="new-password"
              />
            </div>
            {captchaEnabled && <SmartCaptcha onToken={setCaptchaToken} />}
            {error && <p className="error-text">{error}</p>}
            <button className="btn btn-primary btn-block" disabled={busy}>
              {busy ? "Отправляем код…" : "Получить код на почту"}
            </button>
            <p className="muted" style={{ fontSize: 12 }}>
              Регистрируясь, вы принимаете оферту и политику обработки персональных данных.
            </p>
          </form>
        )}

        {mode === "register" && codeSent && (
          <form onSubmit={submitVerify} className="stack">
            <p className="muted">
              Мы отправили 6-значный код на <strong>{email}</strong>.
            </p>
            <div>
              <label className="field-label">Код из письма</label>
              <input
                className="input"
                inputMode="numeric"
                value={code}
                onChange={(e) => setCode(e.target.value)}
                required
                placeholder="000000"
              />
            </div>
            {error && <p className="error-text">{error}</p>}
            <button className="btn btn-primary btn-block" disabled={busy}>
              {busy ? "Проверяем…" : "Подтвердить и войти"}
            </button>
            <button
              type="button"
              className="btn btn-ghost btn-sm"
              onClick={() => setCodeSent(false)}
            >
              Изменить email
            </button>
          </form>
        )}

        <div className="divider">или через провайдера</div>
        <div className="oauth-row">
          <a className="btn btn-secondary" href={oauthUrl("yandex")}>
            Яндекс
          </a>
          <a className="btn btn-secondary" href={oauthUrl("vk")}>
            VK
          </a>
        </div>
      </div>
    </div>
  );
}
