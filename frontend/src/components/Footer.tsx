import { Link } from "react-router-dom";
import { Logo } from "./Logo";

export function Footer() {
  const year = new Date().getFullYear();
  return (
    <footer className="site-footer">
      <div className="container site-footer-inner">
        <div className="site-footer-col">
          <Logo light />
          <p className="muted" style={{ maxWidth: 320 }}>
            AI-анализ отзывов конкурентов на маркетплейсах: боли покупателей, сильные
            стороны и готовые идеи для товара, карточки и инфографики.
          </p>
        </div>
        <nav className="site-footer-col">
          <h4>Навигация</h4>
          <a href="/#how">Как работает</a>
          <a href="/#demo">Демо-отчёт</a>
          <a href="/#pricing">Тарифы</a>
          <Link to="/offer">Оферта</Link>
          <Link to="/privacy">Конфиденциальность</Link>
        </nav>
        <nav className="site-footer-col">
          <h4>Сервис делает</h4>
          <span className="muted">📉 Карту жалоб</span>
          <span className="muted">📈 Сильные стороны</span>
          <span className="muted">💡 Идеи для карточки</span>
          <span className="muted">⚡ Отчёт за 5 минут</span>
        </nav>
      </div>
      <div className="container site-footer-bottom">
        <span>© {year} ReviewLens</span>
        <Link to="/offer">Оферта и политика</Link>
      </div>
    </footer>
  );
}
