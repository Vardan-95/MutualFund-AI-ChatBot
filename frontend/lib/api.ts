export type ThreadSummary = {
  thread_id: string;
  created_at: string;
  updated_at: string;
  title?: string | null;
  pinned?: boolean;
};

export type MessageItem = {
  role: "user" | "assistant";
  content: string;
  timestamp: string;
};

const apiBase = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8080";
let sessionKey: string | null = null;

const DEFAULT_TIMEOUT_MS = 30_000;
const CHAT_TIMEOUT_MS = 120_000;

export function getApiBase(): string {
  return apiBase;
}

export function isLikelyMisconfiguredApiBase(): boolean {
  if (typeof window === "undefined") return false;
  const host = window.location.hostname;
  const localApi =
    apiBase.includes("127.0.0.1") || apiBase.includes("localhost");
  const onDeployedSite = host !== "localhost" && host !== "127.0.0.1";
  return localApi && onDeployedSite;
}

export function apiReachabilityHint(): string {
  if (isLikelyMisconfiguredApiBase()) {
    return "Set NEXT_PUBLIC_API_URL to your Render URL on Vercel (Settings → Environment Variables), then redeploy.";
  }
  return `Ensure ${apiBase} is Live and API_CORS_ORIGINS on Render includes ${typeof window !== "undefined" ? window.location.origin : "your Vercel URL"}.`;
}

export function setApiSessionKey(next: string | null) {
  sessionKey = next && next.trim() ? next.trim() : null;
}

function withSessionKey(path: string): string {
  if (!sessionKey) return path;
  const join = path.includes("?") ? "&" : "?";
  return `${path}${join}session_key=${encodeURIComponent(sessionKey)}`;
}

async function req<T>(
  path: string,
  init?: RequestInit,
  timeoutMs = DEFAULT_TIMEOUT_MS,
): Promise<T> {
  const controller = new AbortController();
  const timer = window.setTimeout(() => controller.abort(), timeoutMs);
  let res: Response;
  try {
    res = await fetch(`${apiBase}${path}`, {
      ...init,
      signal: controller.signal,
      headers: {
        "Content-Type": "application/json",
        ...(init?.headers || {}),
      },
      cache: "no-store",
    });
  } catch (err) {
    if (err instanceof Error && err.name === "AbortError") {
      throw new Error(`API request timed out after ${Math.round(timeoutMs / 1000)}s. ${apiReachabilityHint()}`);
    }
    throw new Error(`Cannot reach API at ${apiBase}. ${apiReachabilityHint()}`);
  } finally {
    window.clearTimeout(timer);
  }
  if (!res.ok) {
    const body = await res.text().catch(() => "");
    const detail = body ? ` — ${body.slice(0, 200)}` : "";
    throw new Error(`${res.status} ${res.statusText}${detail}`);
  }
  return res.json() as Promise<T>;
}

export function listThreads() {
  return req<{ threads: ThreadSummary[] }>(withSessionKey("/threads"));
}

export function createThread() {
  return req<{ thread: ThreadSummary }>(withSessionKey("/threads"), {
    method: "POST",
    body: JSON.stringify({ session_key: sessionKey })
  });
}

export function getMessages(threadId: string) {
  return req<{ thread_id: string; messages: MessageItem[] }>(`/threads/${threadId}/messages`);
}

export function postMessage(threadId: string, content: string) {
  return req<{ assistant_message: { content: string } }>(
    `/threads/${threadId}/messages`,
    {
      method: "POST",
      body: JSON.stringify({ content }),
    },
    CHAT_TIMEOUT_MS,
  );
}

export function updateThread(threadId: string, payload: { title?: string; pinned?: boolean }) {
  return req<{ thread: ThreadSummary }>(`/threads/${threadId}`, {
    method: "PATCH",
    body: JSON.stringify(payload)
  });
}

export function deleteThread(threadId: string) {
  return req<{ ok: boolean }>(`/threads/${threadId}`, {
    method: "DELETE"
  });
}

