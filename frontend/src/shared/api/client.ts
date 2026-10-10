export type VideoStatus = {
  video_id: number;
  filename: string;
  status: string;
  duration: number | null;
  error_message: string | null;
  created_at: string;
  indexed_at: string | null;
  progress?: number;
  object_count?: number;
};

export type SearchResult = {
  video_id: number;
  track_id: number;
  class_name: string;
  score: number;
  confidence: number;
  match_time: number;
  start: number;
  end: number;
  start_label: string;
  end_label: string;
  object_id: number;
  bounding_box: number[];
  clip_url: string;
};

export type TokenResponse = {
  access_token: string;
  refresh_token: string;
  token_type: string;
  user_id: number;
  email: string;
};

const API_URL = (import.meta.env.VITE_API_URL || "http://127.0.0.1:8001").replace(/\/$/, "");

let refreshInFlight: Promise<boolean> | null = null;

function authHeaders(json = true): HeadersInit {
  const token = localStorage.getItem("ivs_token");
  const headers: Record<string, string> = {};
  if (json) headers["Content-Type"] = "application/json";
  if (token) headers.Authorization = `Bearer ${token}`;
  return headers;
}

async function readError(res: Response): Promise<string> {
  try {
    const data = await res.json();
    if (typeof data.detail === "string") return data.detail;
    return JSON.stringify(data.detail ?? data);
  } catch {
    return res.statusText;
  }
}

export function getApiUrl(): string {
  return API_URL;
}

async function tryRefresh(): Promise<boolean> {
  const refresh = localStorage.getItem("ivs_refresh");
  if (!refresh) return false;
  if (!refreshInFlight) {
    refreshInFlight = (async () => {
      try {
        const res = await fetch(`${getApiUrl()}/auth/refresh`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ refresh_token: refresh }),
        });
        if (!res.ok) return false;
        const data: TokenResponse = await res.json();
        localStorage.setItem("ivs_token", data.access_token);
        localStorage.setItem("ivs_refresh", data.refresh_token);
        localStorage.setItem("ivs_email", data.email);
        localStorage.setItem("ivs_user_id", String(data.user_id));
        window.dispatchEvent(new Event("ivs-auth-refresh"));
        return true;
      } catch {
        return false;
      } finally {
        refreshInFlight = null;
      }
    })();
  }
  return refreshInFlight;
}

async function apiFetch(path: string, init: RequestInit, json = true): Promise<Response> {
  const headers = { ...authHeaders(json), ...(init.headers || {}) };
  let res = await fetch(`${getApiUrl()}${path}`, { ...init, headers });
  if (res.status === 401 && !path.startsWith("/auth/")) {
    const ok = await tryRefresh();
    if (ok) {
      const retryHeaders = { ...authHeaders(json), ...(init.headers || {}) };
      res = await fetch(`${getApiUrl()}${path}`, { ...init, headers: retryHeaders });
    }
    if (res.status === 401) {
      for (const key of ["ivs_token", "ivs_refresh", "ivs_email", "ivs_user_id"]) localStorage.removeItem(key);
      window.dispatchEvent(new Event("ivs-auth-refresh"));
    }
  }
  return res;
}

export async function register(email: string, password: string): Promise<TokenResponse> {
  const res = await fetch(`${getApiUrl()}/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export async function login(email: string, password: string): Promise<TokenResponse> {
  const res = await fetch(`${getApiUrl()}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export async function logoutRequest(): Promise<void> {
  const refresh = localStorage.getItem("ivs_refresh");
  if (!refresh) return;
  try {
    await apiFetch("/auth/logout", {
      method: "POST",
      body: JSON.stringify({ refresh_token: refresh }),
    });
  } catch {
    // local logout still proceeds
  }
}

export async function forgotPassword(email: string): Promise<{ ok: boolean; reset_url?: string }> {
  const res = await fetch(`${getApiUrl()}/auth/forgot-password`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email }),
  });
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export async function resetPassword(token: string, password: string): Promise<void> {
  const res = await fetch(`${getApiUrl()}/auth/reset-password`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ token, password }),
  });
  if (!res.ok) throw new Error(await readError(res));
}

export async function uploadVideo(file: File): Promise<{ video_id: number; filename: string; status: string }> {
  const form = new FormData();
  form.append("file", file);
  const res = await apiFetch("/videos/upload", { method: "POST", body: form }, false);
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export async function getVideo(videoId: number): Promise<VideoStatus> {
  const res = await apiFetch(`/videos/${videoId}`, {}, false);
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export async function listVideos(): Promise<VideoStatus[]> {
  const res = await apiFetch("/videos/", {}, false);
  if (!res.ok) throw new Error(await readError(res));
  const data = await res.json();
  return data.videos;
}

export async function deleteVideo(videoId: number): Promise<void> {
  const res = await apiFetch(`/videos/${videoId}`, { method: "DELETE" }, false);
  if (!res.ok) throw new Error(await readError(res));
}

export async function searchVideos(body: {
  query: string;
  video_id?: number | null;
  top_k?: number;
  class_names?: string[] | null;
  min_score?: number;
}): Promise<{ query: string; results: SearchResult[] }> {
  const res = await apiFetch("/search", {
    method: "POST",
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export async function fetchClipBlob(clipUrl: string): Promise<string> {
  const res = await apiFetch(clipUrl, {}, false);
  if (!res.ok) throw new Error(await readError(res));
  const blob = await res.blob();
  return URL.createObjectURL(blob);
}
