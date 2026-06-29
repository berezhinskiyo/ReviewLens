import { useEffect, useState } from "react";
import { AppShell } from "../components/AppShell";
import { resources } from "../api/resources";
import { useAuth } from "../context/AuthContext";
import { formatDate, formatRub } from "../lib/format";
import type { Payment } from "../types";

const PLANS = [
  { code: "starter", title: "Старт", price: "990 ₽/мес", features: ["10 анализов в месяц"] },
  { code: "pro", title: "Безлимит", price: "2 990 ₽/мес", features: ["Безлимит анализов"] },
];

export function BillingPage() {
  const { token, user } = useAuth();
  const [payments, setPayments] = useState<Payment[]>([]);
  const [loadingPlan, setLoadingPlan] = useState<string | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    resources
      .paymentHistory(token)
      .then(setPayments)
      .catch(() => setPayments([]));
  }, [token]);

  async function subscribe(plan: string) {
    setLoadingPlan(plan);
    setError("");
    try {
      const { confirmation_url } = await resources.createPayment(plan, token, 1);
      window.location.href = confirmation_url;
    } catch (err) {
      setError((err as Error).message);
      setLoadingPlan(null);
    }
  }

  return (
    <AppShell>
      <div className="page-head">
        <h1>Тарифы и оплата</h1>
        <p className="muted">
          Текущий тариф: <span className="badge badge-primary">{user?.plan}</span>
          {user?.subscription_until && ` · до ${formatDate(user.subscription_until)}`}
        </p>
      </div>

      <div className="grid grid-2" style={{ maxWidth: 720 }}>
        {PLANS.map((p) => (
          <div className="card" key={p.code}>
            <div className="card-body stack">
              <h3>{p.title}</h3>
              <p className="price-amount">{p.price}</p>
              <ul className="price-list">
                {p.features.map((f) => (
                  <li key={f}>{f}</li>
                ))}
              </ul>
              <button
                className="btn btn-primary btn-block"
                onClick={() => subscribe(p.code)}
                disabled={loadingPlan === p.code}
              >
                {loadingPlan === p.code ? "Переходим к оплате…" : "Оформить"}
              </button>
            </div>
          </div>
        ))}
      </div>

      {error && <p className="error-text" style={{ marginTop: 12 }}>{error}</p>}

      <h2 style={{ margin: "28px 0 12px" }}>История платежей</h2>
      {payments.length === 0 ? (
        <p className="muted">Платежей пока нет.</p>
      ) : (
        <div className="stack">
          {payments.map((p) => (
            <div className="card" key={p.id}>
              <div className="card-body analysis-row">
                <span>
                  {p.plan} · {p.period_months} мес.
                </span>
                <span>{formatRub(p.amount_kopecks)}</span>
                <span className={p.status === "succeeded" ? "badge badge-success" : "badge badge-neutral"}>
                  {p.status}
                </span>
                <span className="muted">{formatDate(p.created_at)}</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </AppShell>
  );
}
