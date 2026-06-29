import type { AnalysisStatus } from "../types";

export function formatRub(kopecks: number): string {
  return (kopecks / 100).toLocaleString("ru-RU") + " ₽";
}

export function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("ru-RU", {
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function statusLabel(status: string): string {
  const map: Record<string, string> = {
    pending: "В очереди",
    scraping: "Парсим отзывы",
    analyzing: "Анализируем",
    completed: "Готово",
    failed: "Ошибка",
  };
  return map[status] || status;
}

export function statusBadge(status: AnalysisStatus): string {
  if (status === "completed") return "badge badge-success";
  if (status === "failed") return "badge badge-danger";
  if (status === "pending") return "badge badge-neutral";
  return "badge badge-warning";
}
