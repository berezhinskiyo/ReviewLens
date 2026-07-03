import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { AppShell } from "../components/AppShell";
import { resources } from "../api/resources";
import { useAuth } from "../context/AuthContext";

export function NewAnalysisPage() {
  const { token, refreshMe } = useAuth();
  const navigate = useNavigate();
  const [url, setUrl] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const DOMAINS = ["wildberries.ru", "wb.ru"];
  const valid = DOMAINS.some((d) => url.includes(d));

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    if (!valid) {
      setError("Нужна ссылка на карточку Wildberries.");
      return;
    }
    setBusy(true);
    try {
      const analysis = await resources.createAnalysis(url.trim(), token);
      await refreshMe();
      navigate(`/analyses/${analysis.id}`);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <AppShell>
      <div className="page-head">
        <h1>Новый анализ</h1>
        <p className="muted">Вставьте ссылку на карточку конкурента на Wildberries.</p>
      </div>

      <div className="card" style={{ maxWidth: 620 }}>
        <div className="card-body">
          <form onSubmit={submit} className="stack">
            <div>
              <label className="field-label">Ссылка на карточку товара</label>
              <input
                className="input"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                placeholder="https://www.wildberries.ru/catalog/12345678/detail.aspx"
              />
            </div>
            <div
              className="card"
              style={{ background: "var(--surface-2)", boxShadow: "none" }}
            >
              <div className="card-body" style={{ padding: 14, fontSize: 14 }}>
                <span className="muted">
                  Поддерживается <strong>Wildberries</strong>. Другие площадки (Ozon,
                  Яндекс.Маркет, Мегамаркет, Avito) — в планах.
                </span>
              </div>
            </div>
            {error && <p className="error-text">{error}</p>}
            <button className="btn btn-primary btn-block" disabled={busy || !url}>
              {busy ? "Запускаем…" : "Запустить анализ"}
            </button>
          </form>
        </div>
      </div>
    </AppShell>
  );
}
