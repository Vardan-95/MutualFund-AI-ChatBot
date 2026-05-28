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

export function setApiSessionKey(next: string | null) {
  sessionKey = next && next.trim() ? next.trim() : null;
}

function withSessionKey(path: string): string {
  if (!sessionKey) return path;
  const join = path.includes("?") ? "&" : "?";
  return `${path}${join}session_key=${encodeURIComponent(sessionKey)}`;
}

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${apiBase}${path}`, {
      ...init,
      headers: {
        "Content-Type": "application/json",
        ...(init?.headers || {})
      },
      cache: "no-store"
    });
  } catch {
    throw new Error(
      `Cannot reach API at ${apiBase}. Start the backend: python -m runtime.phase_9_api`
    );
  }
  if (!res.ok) {
    throw new Error(`${res.status} ${res.statusText}`);
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
  return req<{ assistant_message: { content: string } }>(`/threads/${threadId}/messages`, {
    method: "POST",
    body: JSON.stringify({ content })
  });
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

