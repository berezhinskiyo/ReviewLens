import { api } from "./client";
import type { Analysis, AnalysisListItem, Payment } from "../types";

// Доменные ресурсы ReviewLens (требуют access-токен).
export const resources = {
  createAnalysis: (url: string, token: string | null) =>
    api<Analysis>("/analyses", { method: "POST", body: JSON.stringify({ url }) }, token),

  listAnalyses: (token: string | null, limit = 10) =>
    api<AnalysisListItem[]>(`/analyses?limit=${limit}`, {}, token),

  getAnalysis: (id: string, token: string | null) =>
    api<Analysis>(`/analyses/${id}`, {}, token),

  deleteAnalysis: (id: string, token: string | null) =>
    api<void>(`/analyses/${id}`, { method: "DELETE" }, token),

  createPayment: (plan: string, token: string | null, periodMonths = 1) =>
    api<{ confirmation_url: string; payment_id: string }>(
      "/payments",
      { method: "POST", body: JSON.stringify({ plan, period_months: periodMonths }) },
      token
    ),

  paymentHistory: (token: string | null) => api<Payment[]>("/payments", {}, token),

  updateProfile: (displayName: string, token: string | null) =>
    api("/auth/me", { method: "PATCH", body: JSON.stringify({ display_name: displayName }) }, token),

  // 152-ФЗ: права субъекта ПДн
  dataExport: (token: string | null) => api<unknown>("/me/data-export", {}, token),

  deleteAccount: (token: string | null) =>
    api<void>("/me/account", { method: "DELETE" }, token),
};
