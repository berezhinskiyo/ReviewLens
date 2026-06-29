import { useEffect, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { AuthModal } from "../components/AuthModal";
import { Footer } from "../components/Footer";
import { Logo } from "../components/Logo";
import { Report } from "../components/Report";
import { IconArrow } from "../components/icons";
import { useAuth } from "../context/AuthContext";
import { DEMO_RESULT } from "../lib/demo";

const STEPS = [
  { n: "1", title: "Вставьте URL", text: "Ссылку на карточку конкурента на Wildberries." },
  { n: "2", title: "Подождите", text: "2–5 минут — парсим и анализируем сотни отзывов." },
  { n: "3", title: "Получите отчёт", text: "Жалобы, похвалы и готовые идеи для внедрения." },
];

const PLANS = [
  { code: "free", title: "Бесплатно", price: "0 ₽", per: "", features: ["1 анализ при регистрации", "Полный отчёт", "История анализов"] },
  { code: "starter", title: "Старт", price: "990 ₽", per: "/мес", features: ["10 анализов в месяц", "Все секции отчёта", "Приоритетная очередь"], featured: true },
  { code: "pro", title: "Безлимит", price: "2 990 ₽", per: "/мес", features: ["Безлимит анализов", "Всё из тарифа Старт", "Поддержка"] },
];

const FAQ = [
  { q: "Откуда данные?", a: "Анализируем публичные отзывы карточки на Wildberries по ссылке." },
  { q: "Сколько ждать?", a: "2–5 минут. Если карточку недавно анализировали — быстрее." },
  { q: "Нужна ли настройка?", a: "Нет. Вставьте ссылку — получите готовый отчёт." },
  { q: "Поддерживается ли Ozon?", a: "Пока только Wildberries. Ozon в планах." },
];

export function LandingPage() {
  const { token } = useAuth();
  const navigate = useNavigate();
  const [params, setParams] = useSearchParams();
  const [authOpen, setAuthOpen] = useState(false);

  useEffect(() => {
    if (params.get("auth") === "1") setAuthOpen(true);
  }, [params]);

  const openAuth = () => {
    if (token) {
      navigate("/dashboard");
    } else {
      setAuthOpen(true);
    }
  };

  const closeAuth = () => {
    setAuthOpen(false);
    if (params.get("auth")) {
      params.delete("auth");
      setParams(params, { replace: true });
    }
  };

  return (
    <div className="landing-bg">
      <div className="container">
        <header className="nav">
          <Logo />
          <button className="btn btn-secondary btn-sm" onClick={openAuth}>
            {token ? "В кабинет" : "Войти"}
          </button>
        </header>

        <section className="hero">
          <span className="badge badge-accent">Для селлеров Wildberries</span>
          <h1>Узнайте, на что жалуются покупатели конкурентов — за 5 минут вместо 5 часов</h1>
          <p>
            Вставьте ссылку на карточку конкурента — получите структурированный отчёт: боли,
            сильные стороны и готовые идеи для товара, карточки и инфографики.
          </p>
          <div className="hero-cta">
            <button className="btn btn-primary btn-lg" onClick={openAuth}>
              Сделать бесплатный анализ <IconArrow />
            </button>
          </div>
        </section>

        <section className="section" id="how">
          <div className="grid grid-3">
            {STEPS.map((s) => (
              <div className="card card-hover" key={s.n}>
                <div className="card-body stack">
                  <div className="step-icon">
                    <strong>{s.n}</strong>
                  </div>
                  <h3>{s.title}</h3>
                  <p className="muted">{s.text}</p>
                </div>
              </div>
            ))}
          </div>
        </section>

        <section className="section" id="demo">
          <div className="section-h">
            <h2>Как выглядит отчёт</h2>
            <p className="muted">Пример на демо-данных</p>
          </div>
          <div className="demo-frame">
            <Report result={DEMO_RESULT} />
          </div>
        </section>

        <section className="section" id="pricing">
          <div className="section-h">
            <h2>Тарифы</h2>
            <p className="muted">Начните бесплатно</p>
          </div>
          <div className="grid grid-3">
            {PLANS.map((p) => (
              <div className={`card price-card${p.featured ? " featured" : ""}`} key={p.code}>
                <div className="card-body">
                  {p.featured && <span className="badge badge-primary">Популярный</span>}
                  <h3 style={{ marginTop: p.featured ? 10 : 0 }}>{p.title}</h3>
                  <p className="price-amount">
                    {p.price}
                    <span>{p.per}</span>
                  </p>
                  <ul className="price-list">
                    {p.features.map((f) => (
                      <li key={f}>{f}</li>
                    ))}
                  </ul>
                  <button
                    className={`btn btn-block ${p.featured ? "btn-primary" : "btn-secondary"}`}
                    onClick={openAuth}
                  >
                    Начать
                  </button>
                </div>
              </div>
            ))}
          </div>
        </section>

        <section className="section">
          <div className="section-h">
            <h2>Частые вопросы</h2>
          </div>
          <div className="grid grid-2">
            {FAQ.map((item) => (
              <div className="card faq-item" key={item.q}>
                <div className="card-body">
                  <h3>{item.q}</h3>
                  <p className="muted">{item.a}</p>
                </div>
              </div>
            ))}
          </div>
        </section>
      </div>

      <Footer />
      {authOpen && (
        <AuthModal onClose={closeAuth} onSuccess={() => navigate("/dashboard")} />
      )}
      <p className="center muted" style={{ padding: "12px 0", fontSize: 12 }}>
        <Link to="/offer">Оферта</Link> · <Link to="/privacy">Политика ПД</Link> ·{" "}
        <Link to="/contacts">Контакты</Link>
      </p>
    </div>
  );
}
