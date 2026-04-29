import { supabase } from "@/lib/supabase";

const BASE = import.meta.env.VITE_API_URL || "/api";

class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const {
    data: { session },
  } = await supabase.auth.getSession();
  const isFormData =
    typeof FormData !== "undefined" && options?.body instanceof FormData;
  const headers: Record<string, string> = {
    ...(isFormData ? {} : { "Content-Type": "application/json" }),
    ...(options?.headers as Record<string, string>),
  };
  if (session?.access_token) {
    headers["Authorization"] = `Bearer ${session.access_token}`;
  }

  const res = await fetch(`${BASE}${path}`, { ...options, headers });

  if (res.status === 401) {
    await supabase.auth.signOut();
    window.location.href = "/login";
    throw new ApiError(401, "認証が必要です");
  }
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new ApiError(res.status, body.detail || `HTTP ${res.status}`);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

async function requestBlob(path: string): Promise<{ blob: Blob; filename: string | null }> {
  const {
    data: { session },
  } = await supabase.auth.getSession();
  const headers: Record<string, string> = {};
  if (session?.access_token) {
    headers["Authorization"] = `Bearer ${session.access_token}`;
  }

  const res = await fetch(`${BASE}${path}`, { headers });
  if (res.status === 401) {
    await supabase.auth.signOut();
    window.location.href = "/login";
    throw new ApiError(401, "認証が必要です");
  }
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new ApiError(res.status, body.detail || `HTTP ${res.status}`);
  }

  // Content-Disposition から filename を抽出 (RFC 5987: filename*=UTF-8''...)
  const disposition = res.headers.get("Content-Disposition");
  let filename: string | null = null;
  if (disposition) {
    const star = disposition.match(/filename\*=UTF-8''([^;]+)/i);
    if (star) {
      try {
        filename = decodeURIComponent(star[1]);
      } catch {
        filename = star[1];
      }
    } else {
      const plain = disposition.match(/filename="?([^";]+)"?/i);
      if (plain) filename = plain[1];
    }
  }

  const blob = await res.blob();
  return { blob, filename };
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body: unknown) =>
    request<T>(path, { method: "POST", body: JSON.stringify(body) }),
  patch: <T>(path: string, body: unknown) =>
    request<T>(path, { method: "PATCH", body: JSON.stringify(body) }),
  delete: (path: string) => request<void>(path, { method: "DELETE" }),
  upload: <T>(path: string, form: FormData, method: "POST" | "PUT" = "POST") =>
    request<T>(path, { method, body: form }),
  download: async (path: string, fallbackName: string) => {
    const { blob, filename } = await requestBlob(path);
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename || fallbackName;
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  },
};
