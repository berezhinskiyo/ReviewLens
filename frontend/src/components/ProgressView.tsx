import type { AnalysisStatus } from "../types";

const STEPS = [
  { label: "Парсим отзывы…", at: 20 },
  { label: "Анализируем отзывы…", at: 60 },
  { label: "Готовим отчёт…", at: 90 },
];

function pctFor(status: AnalysisStatus): number {
  if (status === "pending") return 8;
  if (status === "scraping") return 25;
  if (status === "analyzing") return 65;
  return 90;
}

export function ProgressView({ status }: { status: AnalysisStatus }) {
  const pct = pctFor(status);
  return (
    <div className="card">
      <div className="card-body progress-wrap">
        <div className="spinner" />
        <h2>Готовим ваш отчёт</h2>
        <p className="muted" style={{ marginTop: 4 }}>
          Обычно занимает 2–5 минут. Можно не закрывать страницу.
        </p>
        <div className="progress-bar" style={{ marginTop: 22 }}>
          <div className="progress-fill" style={{ width: `${pct}%` }} />
        </div>
        <ul className="progress-steps">
          {STEPS.map((s) => (
            <li key={s.label} className={pct >= s.at - 5 ? "done" : ""}>
              {pct >= s.at - 5 ? "● " : "○ "}
              {s.label}
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
