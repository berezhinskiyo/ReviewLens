// Типы зеркалят Pydantic-схемы backend.

export type TokenResponse = {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
};

export type UserMe = {
  id: string;
  email: string;
  display_name: string | null;
  is_admin: boolean;
  email_verified: boolean;
  plan: string;
  subscription_until: string | null;
  analyses_used_this_period: number;
  analyses_limit: number | null;
  analyses_remaining: number | null;
};

export type ProductInfo = {
  title: string | null;
  brand: string | null;
  rating: number | null;
  reviews_analyzed: number;
};

export type Complaint = {
  topic: string;
  frequency: number;
  severity: "low" | "medium" | "high";
  description: string;
  sample_quotes: string[];
};

export type Praise = {
  topic: string;
  frequency: number;
  description: string;
  sample_quotes: string[];
};

export type Opportunity = {
  category: "product" | "card" | "infographic" | "description";
  title: string;
  rationale: string;
};

export type AnalysisResult = {
  summary: string;
  product_info: ProductInfo;
  complaints: Complaint[];
  praises: Praise[];
  opportunities: Opportunity[];
  demographic_hints: string;
  generated_at: string;
};

export type AnalysisStatus =
  | "pending"
  | "scraping"
  | "analyzing"
  | "completed"
  | "failed";

export type Analysis = {
  id: string;
  input_url: string;
  status: AnalysisStatus;
  error_message: string | null;
  reviews_analyzed_count: number | null;
  result: AnalysisResult | null;
  created_at: string;
  completed_at: string | null;
};

export type AnalysisListItem = {
  id: string;
  input_url: string;
  status: AnalysisStatus;
  reviews_analyzed_count: number | null;
  created_at: string;
  completed_at: string | null;
};

export type Payment = {
  id: string;
  amount_kopecks: number;
  plan: string;
  period_months: number;
  status: string;
  created_at: string;
  completed_at: string | null;
};
