import { useAuthStore } from "./store";
import {
  AgentTask,
  ApiError,
  AuditLog,
  BusinessResponse,
  Customer,
  DashboardResponse,
  DocumentResponse,
  Expense,
  Insight,
  LoginResponse,
  Product,
  RAGAnswerResponse,
  Reminder,
  Transaction,
  User,
  VoiceCommandResponse,
} from "./types";

const BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000/api/v1";

async function request<T>(
  path: string,
  options: { method?: string; body?: unknown; auth?: boolean } = {}
): Promise<T> {
  const { method = "GET", body, auth = true } = options;
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (auth) {
    const token = useAuthStore.getState().token;
    if (token) headers["Authorization"] = `Bearer ${token}`;
  }

  const res = await fetch(`${BASE_URL}${path}`, {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });

  let data: unknown = null;
  const text = await res.text();
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = text;
    }
  }

  if (!res.ok) {
    throw new ApiError(res.status, data);
  }
  return data as T;
}

export const api = {
  register: (params: { name: string; email: string; password: string }) =>
    request<User>("/auth/register", { method: "POST", body: params, auth: false }),

  login: (params: { email: string; password: string }) =>
    request<LoginResponse>("/auth/login", { method: "POST", body: params, auth: false }),

  selectBusiness: (businessId: string) =>
    request<LoginResponse>("/auth/select-business", {
      method: "POST",
      body: { business_id: businessId },
    }),

  createBusiness: (params: { name: string; type?: string; location?: string; currency: string }) =>
    request<BusinessResponse>("/businesses", { method: "POST", body: params }),

  listBusinesses: () => request<BusinessResponse[]>("/businesses"),

  listProducts: (params?: { low_stock_only?: boolean }) =>
    request<Product[]>(`/products${params?.low_stock_only ? "?low_stock_only=true" : ""}`),

  createProduct: (params: {
    name: string;
    category?: string;
    unit?: string;
    cost_price?: number;
    selling_price?: number;
    stock_quantity?: number;
    reorder_level?: number;
  }) => request<Product>("/products", { method: "POST", body: params }),

  adjustStock: (
    productId: string,
    params: { quantity_change: number; reference_type?: string; confirm_negative_stock?: boolean }
  ) => request(`/products/${productId}/stock`, { method: "PATCH", body: params }),

  listTransactions: (params?: { type?: string; payment_status?: string }) => {
    const qs = new URLSearchParams();
    if (params?.type) qs.set("type", params.type);
    if (params?.payment_status) qs.set("payment_status", params.payment_status);
    const suffix = qs.toString() ? `?${qs.toString()}` : "";
    return request<Transaction[]>(`/transactions${suffix}`);
  },

  listExpenses: () => request<Expense[]>("/expenses"),

  createExpense: (params: { category: string; amount: number; note?: string }) =>
    request<Expense>("/expenses", { method: "POST", body: params }),

  listCustomers: () => request<Customer[]>("/customers"),

  createCustomer: (params: { name: string; phone?: string }) =>
    request<Customer>("/customers", { method: "POST", body: params }),

  getDashboard: () => request<DashboardResponse>("/analytics/dashboard"),

  listReminders: (status?: string) =>
    request<Reminder[]>(`/reminders${status ? `?status=${status}` : ""}`),

  updateReminderStatus: (id: string, status: "PENDING" | "SENT" | "DISMISSED") =>
    request<Reminder>(`/reminders/${id}`, { method: "PATCH", body: { status } }),

  checkLowStock: () => request<Reminder[]>("/reminders/check-low-stock", { method: "POST" }),

  listInsights: () => request<Insight[]>("/insights"),

  listAuditLogs: (params?: { entity_type?: string }) =>
    request<AuditLog[]>(`/audit-logs${params?.entity_type ? `?entity_type=${params.entity_type}` : ""}`),

  submitVoiceCommand: (params: { text: string; idempotency_key: string }) =>
    request<VoiceCommandResponse>("/voice-commands", { method: "POST", body: params }),

  confirmVoiceCommand: (
    commandId: string,
    params: {
      product_id?: string;
      quantity?: number;
      unit_price?: number;
      amount?: number;
      category?: string;
      payment_status?: string;
      confirm_negative_stock?: boolean;
    }
  ) => request<VoiceCommandResponse>(`/voice-commands/${commandId}/confirm`, { method: "POST", body: params }),

  listVoiceCommands: (status?: string) =>
    request<VoiceCommandResponse[]>(`/voice-commands${status ? `?status=${status}` : ""}`),

  getVoiceCommand: (id: string) => request<VoiceCommandResponse>(`/voice-commands/${id}`),

  getVoiceCommandTasks: (id: string) => request<AgentTask[]>(`/voice-commands/${id}/tasks`),

  listDocuments: () => request<DocumentResponse[]>("/documents"),

  ingestDocument: (params: { title: string; document_type?: string; text: string }) =>
    request<DocumentResponse>("/documents", { method: "POST", body: params }),

  queryDocuments: (params: { query: string; top_k?: number }) =>
    request<RAGAnswerResponse>("/documents/query", { method: "POST", body: params }),

  uploadDocument: async (params: {
  title: string;
  document_type?: string;
  language?: string;
  file: File;
}) => {
  const token = useAuthStore.getState().token;

  const formData = new FormData();
  formData.append("title", params.title);
  formData.append("document_type", params.document_type || "invoice");
  if (params.language) {
    formData.append("language", params.language);
  }
  formData.append("file", params.file);

  const res = await fetch(`${BASE_URL}/documents/upload`, {
    method: "POST",
    headers: token ? { Authorization: `Bearer ${token}` } : undefined,
    body: formData,
  });

  let data: unknown = null;
  const text = await res.text();
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = text;
    }
  }

  if (!res.ok) {
    throw new ApiError(res.status, data);
  }

  return data as DocumentResponse;
},
};

export { ApiError };
