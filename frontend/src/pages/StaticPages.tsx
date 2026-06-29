import { Link } from "react-router-dom";
import { Logo } from "../components/Logo";

function Shell({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="landing-bg">
      <div className="container">
        <header className="nav">
          <Link to="/">
            <Logo />
          </Link>
          <Link to="/" className="btn btn-secondary btn-sm">
            На главную
          </Link>
        </header>
        <div className="card" style={{ maxWidth: 720, margin: "24px auto 60px" }}>
          <div className="card-body stack">
            <h1>{title}</h1>
            {children}
          </div>
        </div>
      </div>
    </div>
  );
}

export function OfferPage() {
  return (
    <Shell title="Публичная оферта">
      <p className="muted">
        Черновик. Финальную версию подготовит юрист перед запуском приёма платежей. Сервис
        предоставляется «как есть»; приём платежей осуществляет ИП/самозанятый через ЮKassa с
        автоматическим выставлением чека по 54-ФЗ.
      </p>
    </Shell>
  );
}

export function PrivacyPage() {
  return (
    <Shell title="Политика обработки персональных данных">
      <p className="muted">
        Черновик. Мы обрабатываем минимум данных: email и пароль для авторизации (пароль
        хранится только в виде bcrypt-хеша) и, при входе через провайдера, идентификатор
        провайдера. Данные не передаются третьим лицам, кроме платёжного провайдера ЮKassa в
        объёме, необходимом для оплаты.
      </p>
    </Shell>
  );
}

export function ContactsPage() {
  return (
    <Shell title="Контакты">
      <p className="muted">
        По вопросам сотрудничества и поддержки: support@reviewlens.ru
      </p>
    </Shell>
  );
}
