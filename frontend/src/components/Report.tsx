import type { AnalysisResult } from "../types";
import { IconBulb, IconStar, IconThumbDown, IconThumbUp } from "./icons";

const severityBadge: Record<string, string> = {
  high: "badge badge-danger",
  medium: "badge badge-warning",
  low: "badge badge-neutral",
};

const categoryLabel: Record<string, string> = {
  product: "Товар",
  card: "Карточка",
  infographic: "Инфографика",
  description: "Описание",
};
const categoryBadge: Record<string, string> = {
  product: "badge badge-primary",
  card: "badge badge-accent",
  infographic: "badge badge-success",
  description: "badge badge-neutral",
};

function Quotes({ quotes }: { quotes: string[] }) {
  if (!quotes?.length) return null;
  return (
    <ul className="quote-list">
      {quotes.map((q, i) => (
        <li key={i}>«{q}»</li>
      ))}
    </ul>
  );
}

export function Report({ result }: { result: AnalysisResult }) {
  const p = result.product_info;
  return (
    <div className="report">
      <div className="card">
        <div className="card-body report-head">
          <div>
            <h2>{p.title || "Товар"}</h2>
            <p className="muted">{p.brand}</p>
          </div>
          <div className="row">
            {p.rating != null && (
              <span className="report-rating">
                <IconStar /> {p.rating}
              </span>
            )}
            <span className="badge badge-primary">{p.reviews_analyzed} отзывов</span>
          </div>
        </div>
      </div>

      {result.summary && (
        <div className="card">
          <div className="card-body">
            <h3 style={{ marginBottom: 8 }}>Краткое резюме</h3>
            <p style={{ color: "var(--text-secondary)" }}>{result.summary}</p>
          </div>
        </div>
      )}

      <div className="grid grid-2">
        <div>
          <div className="section-title">
            <IconThumbDown className="" /> На что жалуются
          </div>
          <div className="stack">
            {result.complaints.map((c, i) => (
              <div className="card" key={i}>
                <div className="card-body">
                  <div className="row between" style={{ alignItems: "flex-start" }}>
                    <strong>{c.topic}</strong>
                    <span className="row" style={{ gap: 6 }}>
                      <span className="badge badge-neutral">{c.frequency}</span>
                      <span className={severityBadge[c.severity]}>{c.severity}</span>
                    </span>
                  </div>
                  <p className="muted" style={{ marginTop: 6, fontSize: 14 }}>
                    {c.description}
                  </p>
                  <Quotes quotes={c.sample_quotes} />
                </div>
              </div>
            ))}
            {result.complaints.length === 0 && <p className="muted">Серьёзных жалоб не найдено.</p>}
          </div>
        </div>

        <div>
          <div className="section-title">
            <IconThumbUp className="" /> За что хвалят
          </div>
          <div className="stack">
            {result.praises.map((c, i) => (
              <div className="card" key={i}>
                <div className="card-body">
                  <div className="row between" style={{ alignItems: "flex-start" }}>
                    <strong>{c.topic}</strong>
                    <span className="badge badge-success">{c.frequency}</span>
                  </div>
                  <p className="muted" style={{ marginTop: 6, fontSize: 14 }}>
                    {c.description}
                  </p>
                  <Quotes quotes={c.sample_quotes} />
                </div>
              </div>
            ))}
            {result.praises.length === 0 && <p className="muted">Похвал не найдено.</p>}
          </div>
        </div>
      </div>

      {result.opportunities.length > 0 && (
        <div>
          <div className="section-title">
            <IconBulb className="" /> Идеи для вас
          </div>
          <div className="grid grid-2">
            {result.opportunities.map((o, i) => (
              <div className="card card-hover" key={i}>
                <div className="card-body stack">
                  <span className={categoryBadge[o.category]}>
                    {categoryLabel[o.category] || o.category}
                  </span>
                  <strong>{o.title}</strong>
                  <p className="muted" style={{ fontSize: 14 }}>
                    {o.rationale}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {result.demographic_hints && (
        <div className="card">
          <div className="card-body">
            <h3 style={{ marginBottom: 6 }}>Аудитория</h3>
            <p className="muted">{result.demographic_hints}</p>
          </div>
        </div>
      )}

      <div className="row" style={{ justifyContent: "flex-end" }}>
        <button className="btn btn-secondary" disabled title="Появится позже">
          Скачать PDF
        </button>
      </div>
    </div>
  );
}
