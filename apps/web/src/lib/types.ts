export interface User {
  id: string;
  name: string;
  email: string;
  preferred_language: string;
  created_at: string;
}

export interface BusinessMembershipSummary {
  business_id: string;
  business_name: string;
  role: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  user: User;
  businesses: BusinessMembershipSummary[];
  selected_business_id: string | null;
  needs_onboarding: boolean;
}

export interface BusinessResponse {
  id: string;
  name: string;
  type: string | null;
  location: string | null;
  currency: string;
  role: string;
  created_at: string;
}

export interface Product {
  id: string;
  name: string;
  category: string | null;
  unit: string;
  cost_price: string;
  selling_price: string;
  stock_quantity: string;
  reorder_level: string;
  is_active: boolean;
  is_low_stock: boolean;
  created_at: string;
  updated_at: string;
}

export interface TransactionItem {
  product_id: string;
  quantity: string;
  unit_price: string;
  total: string;
}

export interface Transaction {
  id: string;
  type: string;
  amount: string;
  payment_status: string;
  customer_id: string | null;
  occurred_at: string;
  items: TransactionItem[];
}

export interface Expense {
  id: string;
  category: string;
  amount: string;
  note: string | null;
  occurred_at: string;
}

export interface Customer {
  id: string;
  name: string;
  phone: string | null;
  balance_due: string;
  last_purchase_at: string | null;
  created_at: string;
}

export interface DashboardResponse {
  date_from: string;
  date_to: string;
  total_sales_amount: string;
  total_expenses_amount: string;
  profit: string;
  sale_count: number;
  low_stock_count: number;
  total_customer_dues: string;
  sales_by_payment_status: { payment_status: string; count: number; amount: string }[];
}

export interface VoiceCommandResponse {
  id: string;
  input_type: string;
  transcript: string | null;
  intent: string | null;
  entities: Record<string, unknown>;
  confidence: number | null;
  status: "PENDING" | "UNDERSTANDING" | "EXECUTING" | "NEEDS_CONFIRMATION" | "COMPLETED" | "FAILED";
  final_response: string | null;
  created_at: string;
  completed_at: string | null;
}

export interface Reminder {
  id: string;
  type: string;
  message: string;
  due_at: string;
  status: string;
  created_at: string;
}

export interface Insight {
  id: string;
  insight_type: string;
  message: string;
  confidence: number | null;
  created_at: string;
}

export interface DocumentResponse {
  id: string;
  title: string;
  document_type: string;
  language: string | null;
  status: string;
  chunk_count: number;
  created_at: string;
}

export interface RAGSourceChunk {
  chunk_id: string;
  document_id: string;
  document_title: string;
  chunk_text: string;
  similarity: number;
}

export interface RAGAnswerResponse {
  answer: string;
  sources: RAGSourceChunk[];
  provider_used: string;
  has_sufficient_context: boolean;
}

export interface AgentTask {
  id: string;
  agent_name: string;
  tool_name: string | null;
  status: string;
  input_json: Record<string, unknown>;
  output_json: Record<string, unknown>;
  created_at: string;
}

export interface AuditLog {
  id: string;
  actor_type: string;
  actor_id: string | null;
  action: string;
  entity_type: string;
  entity_id: string | null;
  metadata_json: Record<string, unknown>;
  created_at: string;
}

export class ApiError extends Error {
  status: number;
  body: unknown;
  constructor(status: number, body: unknown) {
    const detail =
      typeof body === "object" && body !== null && "detail" in body
        ? (body as { detail: unknown }).detail
        : body;
    super(typeof detail === "string" ? detail : JSON.stringify(detail));
    this.status = status;
    this.body = body;
  }
}
