import { useEffect, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { AppShell } from "../components/AppShell";
import { ProgressView } from "../components/ProgressView";
import { Report } from "../components/Report";
import { IconBack } from "../components/icons";
import { resources } from "../api/resources";
import { useAuth } from "../context/AuthContext";
import type { Analysis } from "../types";

const DONE = ["completed", "failed"];

export function AnalysisPage() {
  const { id } = useParams<{ id: string }>();
  const { token } = useAuth();
  const [analysis, setAnalysis] = useState<Analysis | null>(null);
  const [notFound, setNotFound] = useState(false);
  const timer = useRef<number>();

  useEffect(() => {
    if (!id) return;
    let stop = false;
    const poll = async () => {
      try {
        const data = await resources.getAnalysis(id, token);
        if (stop) return;
        setAnalysis(data);
        // polling каждые 3 секунды, пока не completed/failed
        if (!DONE.includes(data.status)) {
          timer.current = window.setTimeout(poll, 3000);
        }
      } catch {
        if (!stop) setNotFound(true);
      }
    };
    void poll();
    return () => {
      stop = true;
      if (timer.current) window.clearTimeout(timer.current);
    };
  }, [id, token]);

  return (
    <AppShell>
      <Link to="/dashboard" className="btn btn-ghost btn-sm" style={{ marginBottom: 16 }}>
        <IconBack /> К списку
      </Link>

      {notFound && <p className="muted">Анализ не найден.</p>}
      {!notFound && !analysis && <p className="muted">Загрузка…</p>}

      {analysis && analysis.status === "failed" && (
        <div className="card">
          <div className="card-body stack">
            <h2>Не удалось выполнить анализ</h2>
            <p className="muted">
              {analysis.error_message || "Попробуйте другую карточку."}
            </p>
            <p className="badge badge-success" style={{ alignSelf: "flex-start" }}>
              Этот анализ не списан с вашего лимита
            </p>
          </div>
        </div>
      )}

      {analysis && !DONE.includes(analysis.status) && (
        <ProgressView status={analysis.status} />
      )}

      {analysis && analysis.status === "completed" && analysis.result && (
        <Report result={analysis.result} />
      )}
    </AppShell>
  );
}
