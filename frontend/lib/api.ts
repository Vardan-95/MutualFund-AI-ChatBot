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

export type HealthResponse = {
  status: string;
  rag_ready?: boolean;
  warmup?: {
    status: "pending" | "loading" | "ready" | "failed";
    error?: string;
    load_seconds?: number;
  };
};

const apiBase = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8080";
let sessionKey: string | null = null;

const DEFAULT_TIMEOUT_MS = 45_000;
const CHAT_TIMEOUT_MS = 180_000;
const WARMUP_POLL_MS = 3_000;

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

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}

function withSessionKey(path: string): string {
  if (!sessionKey) return path;
  const join = path.includes("?") ? "&" : "?";
  return `${path}${join}session_key=${encodeURIComponent(sessionKey)}`;
}

function formatHttpError(status: number, body: string): string {
  const snippet = body.slice(0, 220).trim();
  if (status === 502 || status === 504) {
    return "The server took too long to respond (gateway timeout). Wait 30 seconds and try again.";
  }
  if (status === 503) {
    if (snippet.includes("still loading") || snippet.includes("warmup")) {
      return "AI models are still loading on the server (about 1–2 minutes after wake). Please wait and try again.";
    }
    return snippet ? `Service temporarily unavailable: ${snippet}` : "Service temporarily unavailable.";
  }
  return snippet ? `${status} ${snippet}` : `${status} request failed`;
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
      throw new Error(
        `Request timed out after ${Math.round(timeoutMs / 1000)}s. ${apiReachabilityHint()}`,
      );
    }
    throw new Error(`Cannot reach API at ${apiBase}. ${apiReachabilityHint()}`);
  } finally {
    window.clearTimeout(timer);
  }
  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new Error(formatHttpError(res.status, body));
  }
  return res.json() as Promise<T>;
}

export function fetchHealth() {
  return req<HealthResponse>("/health");
}

/** Poll /health until embedding model + indexes are warm (Render cold start). */
export async function waitForRagReady(maxWaitMs = 180_000): Promise<HealthResponse> {
  const deadline = Date.now() + maxWaitMs;
  let last: HealthResponse | null = null;
  while (Date.now() < deadline) {
    last = await fetchHealth();
    if (last.rag_ready) return last;
    if (last.warmup?.status === "failed") {
      throw new Error(last.warmup.error || "RAG warmup failed on the server.");
    }
    await sleep(WARMUP_POLL_MS);
  }
  throw new Error(
    "Timed out waiting for AI models to load. Open the Render service URL /health, wait 1–2 minutes, then refresh this page.",
  );
}

export function listThreads() {
  return req<{ threads: ThreadSummary[] }>(withSessionKey("/threads"));
}

export function createThread() {
  return req<{ thread: ThreadSummary }>(withSessionKey("/threads"), {
    method: "POST",
    body: JSON.stringify({ session_key: sessionKey }),
  });
}

export function getMessages(threadId: string) {
  return req<{ thread_id: string; messages: MessageItem[] }>(
    `/threads/${threadId}/messages`,
  );
}

export async function postMessage(threadId: string, content: string) {
  await waitForRagReady();
  let lastErr: Error | null = null;
  for (let attempt = 0; attempt < 3; attempt += 1) {
    try {
      return await req<{ assistant_message: { content: string } }>(
        `/threads/${threadId}/messages`,
        {
          method: "POST",
          body: JSON.stringify({ content }),
        },
        CHAT_TIMEOUT_MS,
      );
    } catch (err) {
      lastErr = err instanceof Error ? err : new Error(String(err));
      const retryable =
        lastErr.message.includes("503") ||
        lastErr.message.includes("502") ||
        lastErr.message.includes("504") ||
        lastErr.message.includes("still loading") ||
        lastErr.message.includes("gateway timeout");
      if (!retryable || attempt === 2) throw lastErr;
      await sleep(4_000 * (attempt + 1));
      await waitForRagReady(120_000);
    }
  }
  throw lastErr ?? new Error("Failed to send message.");
}

export function updateThread(threadId: string, payload: { title?: string; pinned?: boolean }) {
  return req<{ thread: ThreadSummary }>(`/threads/${threadId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export function deleteThread(threadId: string) {
  return req<{ ok: boolean }>(`/threads/${threadId}`, {
    method: "DELETE",
  });
}
