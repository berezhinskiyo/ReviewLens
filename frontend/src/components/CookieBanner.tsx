import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

const KEY = "reviewlens-cookie-consent";

export function CookieBanner() {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    try {
      if (!localStorage.getItem(KEY)) setVisible(true);
    } catch {
      /* ignore */
    }
  }, []);

  const accept = () => {
    try {
      localStorage.setItem(KEY, "1");
    } catch {
      /* ignore */
    }
    setVisible(false);
  };

  if (!visible) return null;

  return (
    <div className="cookie-banner" role="dialog" aria-label="Использование cookie">
      <p className="cookie-banner-text">
        Мы используем cookie для авторизации и сохранения настроек. Продолжая, вы соглашаетесь с{" "}
        <Link to="/privacy">Политикой обработки персональных данных</Link>.
      </p>
      <button type="button" className="btn btn-primary btn-sm" onClick={accept}>
        Принять
      </button>
    </div>
  );
}
