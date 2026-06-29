import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { AppShell } from "../components/AppShell";
import { IconArrow, IconPlus } from "../components/icons";
import { resources } from "../api/resources";
import { useAuth } from "../context/AuthContext";
import { formatDate, statusBadge, statusLabel } from "../lib/format";
import type { AnalysisListItem } from "../types";

const ACTIVE = ["pending", "scraping", "analyzing"];

export function DashboardPage() {
  const { token } = useAuth();
  const [items, setItems] = useState<AnalysisListItem[] | null>(null);
  const timer = useRef<number>();

  useEffect(() => {
    let stop = false;
    const load = async () => {
      try {
        const data = await resources.listAnalyses(token, 10);
        if (stop) return;
        setItems(data);
        // авто-обновление, пока есть незавершённые
        if (data.some((a) => ACTIVE.includes(a.status))) {
          timer.current = window.setTimeout(load, 4000);
        }
      } catch {
        if (!stop) setItems([]);
      }
    };
    void load();
    return () => {
      stop = true;
      if (timer.current) window.clearTimeout(timer.current);
    };
  }, [token]);

  return (
    <AppShell>
      <div className="page-head row between">
        <div>
          <h1>Ваши анализы</h1>
          <p className="muted">История разборов карточек конкурентов</p>
        </div>
        <Link to="/analyses/new" className="btn btn-primary">
          <IconPlus /> Новый анализ
        </Link>
      </div>

      {items === null && <p className="muted">Загрузка…</p>}

      {items && items.length === 0 && (
        <div className="card">
          <div className="card-body center" style={{ padding: 48 }}>
            <p className="muted">Пока нет анализов. Создайте первый — это бесплатно.</p>
            <Link to="/analyses/new" className="btn btn-primary" style={{ marginTop: 16 }}>
              <IconPlus /> Начать
            </Link>
          </div>
        </div>
      )}

      <div className="stack">
        {items?.map((a) => (
          <div className="card card-hover" key={a.id}>
            <div className="card-body analysis-row">
              <div style={{ minWidth: 0 }}>
                <div className="url">{a.input_url}</div>
                <div className="meta">
                  {formatDate(a.created_at)}
                  {a.reviews_analyzed_count ? ` · ${a.reviews_analyzed_count} отзывов` : ""}
                </div>
              </div>
              <div className="row">
                <span className={statusBadge(a.status)}>{statusLabel(a.status)}</span>
                <Link to={`/analyses/${a.id}`} className="btn btn-secondary btn-sm">
                  Открыть <IconArrow />
                </Link>
              </div>
            </div>
          </div>
        ))}
      </div>
    </AppShell>
  );
}
