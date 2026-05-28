"use strict";

const apiUrlInput = document.getElementById("apiUrl");
const saveApiBtn = document.getElementById("saveApiBtn");
const newThreadBtn = document.getElementById("newThreadBtn");
const threadList = document.getElementById("threadList");
const statusEl = document.getElementById("status");
const messagesEl = document.getElementById("messages");
const chatForm = document.getElementById("chatForm");
const messageInput = document.getElementById("messageInput");
const sendBtn = document.getElementById("sendBtn");

const storageKeyApi = "mf_test_ui_api_url";
const storageKeyThread = "mf_test_ui_thread_id";
const defaultApi = "http://127.0.0.1:8080";

let activeThreadId = null;
const threadTitleCache = new Map();
const threadPinnedCache = new Map();
let openThreadMenuForId = null;

const SCHEME_SLUGS = [
  { match: /hdfc-equity-fund-direct-growth|equity fund direct growth/i, label: "HDFC Equity" },
  { match: /hdfc-mid-cap|mid cap/i, label: "HDFC Mid Cap" },
  { match: /hdfc-large-cap|large cap/i, label: "HDFC Large Cap" },
  { match: /hdfc-focused|focused fund/i, label: "HDFC Focused" },
  { match: /hdfc-elss|elss|tax saver/i, label: "HDFC ELSS" },
  { match: /\bhdfc\b/i, label: "HDFC" },
];

const TOPIC_RULES = [
  { match: /\b(5 schemes|five schemes|list schemes|what schemes)\b/i, label: "Scheme list" },
  { match: /\bnav\b/i, label: "NAV" },
  { match: /\b(expense ratio|ter)\b/i, label: "Expense ratio" },
  { match: /\b(minimum sip|min sip|\bsip\b)/i, label: "SIP" },
  { match: /\bexit load\b/i, label: "Exit load" },
  { match: /\b(lock-?in|lock in)\b/i, label: "Lock-in" },
  { match: /\b(aum|fund size)\b/i, label: "Fund size" },
  { match: /\b(rating|riskometer)\b/i, label: "Risk" },
  { match: /\b(benchmark)\b/i, label: "Benchmark" },
  { match: /\b(return|cagr)\b/i, label: "Returns" },
];

function getApiBase() {
  return (apiUrlInput.value || "").trim().replace(/\/+$/, "");
}

function setStatus(text, isError = false) {
  statusEl.textContent = text;
  statusEl.style.color = isError ? "#ff7b72" : "";
}

function escapeHtml(value) {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

function closeThreadMenu() {
  openThreadMenuForId = null;
  const existing = document.querySelector(".thread-menu");
  if (existing) existing.remove();
}

document.addEventListener("click", (e) => {
  const target = e.target;
  if (!(target instanceof Element)) return;
  if (target.closest(".thread-menu") || target.closest(".thread-kebab")) return;
  closeThreadMenu();
});

function threadDisplayName(threadId) {
  if (!threadId) return "No thread selected";
  return threadTitleCache.get(threadId) || "New chat";
}

function isThreadPinned(threadId) {
  return !!threadPinnedCache.get(threadId);
}

function setThreadStatus(threadId, suffix = "") {
  const name = threadDisplayName(threadId);
  setStatus(suffix ? `${name} · ${suffix}` : name);
}

function shortThreadTitle(text) {
  const q = (text || "").replace(/\s+/g, " ").trim();
  if (!q) return "New chat";

  let scheme = "";
  for (const rule of SCHEME_SLUGS) {
    if (rule.match.test(q)) {
      scheme = rule.label;
      break;
    }
  }

  const topics = [];
  for (const rule of TOPIC_RULES) {
    if (rule.match.test(q) && !topics.includes(rule.label)) {
      topics.push(rule.label);
    }
  }

  if (scheme && topics.length) {
    return `${scheme} · ${topics.slice(0, 2).join(" · ")}`.slice(0, 42);
  }
  if (scheme) return scheme.slice(0, 42);
  if (topics.length) return topics.slice(0, 2).join(" · ").slice(0, 42);

  const stop = new Set([
    "what", "is", "the", "of", "for", "a", "an", "in", "on", "at", "to",
    "i", "am", "asking", "please", "tell", "me", "about", "value", "as",
  ]);
  const words = q
    .toLowerCase()
    .replace(/[^a-z0-9\s-]/g, " ")
    .split(/\s+/)
    .filter((w) => w.length > 2 && !stop.has(w))
    .slice(0, 4);

  if (words.length) {
    const title = words
      .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
      .join(" ");
    return title.length > 36 ? `${title.slice(0, 36)}…` : title;
  }

  return q.length > 36 ? `${q.slice(0, 36)}…` : q;
}

function titleFromQuestion(text) {
  return shortThreadTitle(text);
}

function formatThreadMeta(t) {
  const ts = t.updated_at || t.created_at;
  return ts ? new Date(ts).toLocaleString() : "";
}

function renderMessages(messages) {
  messagesEl.innerHTML = "";
  for (const msg of messages) {
    const div = document.createElement("div");
    div.className = `msg ${msg.role === "user" ? "user" : "assistant"}`;
    div.innerHTML = escapeHtml(msg.content || "");
    messagesEl.appendChild(div);
  }
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

async function hydrateThreadTitles(threads) {
  const pending = threads
    .filter((t) => !threadTitleCache.has(t.thread_id) && !t.title)
    .map(async (t) => {
      try {
        const data = await apiGet(`/threads/${t.thread_id}/messages`);
        const firstUser = (data.messages || []).find((m) => m.role === "user");
        threadTitleCache.set(
          t.thread_id,
          firstUser ? shortThreadTitle(firstUser.content) : "New chat",
        );
      } catch (_err) {
        threadTitleCache.set(t.thread_id, "New chat");
      }
    });
  for (const t of threads) {
    if (typeof t.pinned === "boolean") {
      threadPinnedCache.set(t.thread_id, t.pinned);
    }
    if (t.title && t.title.trim()) {
      threadTitleCache.set(t.thread_id, t.title.trim());
    } else if (!threadTitleCache.has(t.thread_id)) {
      threadTitleCache.set(t.thread_id, "New chat");
    }
  }
  await Promise.all(pending);
}

function renderThreads(threads) {
  threadList.innerHTML = "";
  const pinnedThreads = threads.filter((t) => isThreadPinned(t.thread_id));
  const normalThreads = threads.filter((t) => !isThreadPinned(t.thread_id));

  if (pinnedThreads.length) {
    const title = document.createElement("div");
    title.className = "thread-section-title";
    title.textContent = "Pinned chats";
    threadList.appendChild(title);
    for (const t of pinnedThreads) threadList.appendChild(renderThreadItem(t));
  }

  if (normalThreads.length) {
    if (pinnedThreads.length) {
      const title = document.createElement("div");
      title.className = "thread-section-title";
      title.textContent = "Chats";
      threadList.appendChild(title);
    }
    for (const t of normalThreads) threadList.appendChild(renderThreadItem(t));
  }
}

function renderThreadItem(t) {
  const item = document.createElement("div");
  item.className = `thread-item${t.thread_id === activeThreadId ? " active" : ""}`;
  const title = threadTitleCache.get(t.thread_id) || "New chat";
  item.innerHTML = `
    <div class="thread-row">
      <div class="thread-title">${escapeHtml(title)}</div>
      <button type="button" class="thread-kebab" aria-label="Thread options">⋯</button>
    </div>
    <div class="thread-meta">${escapeHtml(formatThreadMeta(t))}</div>
  `;

  item.addEventListener("click", async () => {
    activeThreadId = t.thread_id;
    localStorage.setItem(storageKeyThread, activeThreadId);
    closeThreadMenu();
    await refreshThreads();
    await loadMessages();
  });

  const kebab = item.querySelector(".thread-kebab");
  if (kebab) {
    kebab.addEventListener("click", (e) => {
      e.stopPropagation();
      toggleThreadMenu(t.thread_id, item);
    });
  }

  return item;
}

function toggleThreadMenu(threadId, anchorEl) {
  const isOpen = openThreadMenuForId === threadId && document.querySelector(".thread-menu");
  closeThreadMenu();
  if (isOpen) return;

  openThreadMenuForId = threadId;
  const menu = document.createElement("div");
  menu.className = "thread-menu";
  const pinned = isThreadPinned(threadId);
  menu.innerHTML = `
    <button type="button" class="menu-pin">${pinned ? "Unpin" : "Pin"}</button>
    <button type="button" class="menu-rename">Rename</button>
    <button type="button" class="menu-delete">Delete</button>
  `;
  anchorEl.appendChild(menu);

  const pin = menu.querySelector(".menu-pin");
  if (pin) pin.addEventListener("click", async (e) => { e.stopPropagation(); closeThreadMenu(); await togglePinThread(threadId); });
  const rename = menu.querySelector(".menu-rename");
  if (rename) rename.addEventListener("click", async (e) => { e.stopPropagation(); closeThreadMenu(); await renameThread(threadId); });
  const del = menu.querySelector(".menu-delete");
  if (del) del.addEventListener("click", async (e) => { e.stopPropagation(); closeThreadMenu(); await deleteThread(threadId); });
}

async function apiGet(path) {
  const res = await fetch(`${getApiBase()}${path}`);
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return await res.json();
}

async function apiPost(path, body) {
  const res = await fetch(`${getApiBase()}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body || {}),
  });
  if (!res.ok) {
    let detail = `${res.status} ${res.statusText}`;
    try {
      const j = await res.json();
      if (j && j.detail) {
        detail = typeof j.detail === "string" ? j.detail : JSON.stringify(j.detail);
      }
    } catch (_err) {
      // ignore JSON parse errors
    }
    throw new Error(detail);
  }
  return await res.json();
}

async function apiPatch(path, body) {
  const res = await fetch(`${getApiBase()}${path}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body || {}),
  });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return await res.json();
}

async function apiDelete(path) {
  const res = await fetch(`${getApiBase()}${path}`, { method: "DELETE" });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
}

async function togglePinThread(threadId) {
  try {
    const current = isThreadPinned(threadId);
    await apiPatch(`/threads/${threadId}`, { pinned: !current });
    threadPinnedCache.set(threadId, !current);
    await refreshThreads();
    if (activeThreadId) setThreadStatus(activeThreadId);
  } catch (err) {
    setStatus(`Pin failed: ${String(err.message || err)}`, true);
  }
}

async function renameThread(threadId) {
  const current = threadDisplayName(threadId);
  const next = window.prompt("Rename thread", current === "New chat" ? "" : current);
  if (next === null) return;
  const trimmed = next.trim();
  if (!trimmed) {
    setStatus("Rename cancelled: title cannot be empty", true);
    return;
  }
  try {
    await apiPatch(`/threads/${threadId}`, { title: trimmed });
    threadTitleCache.set(threadId, trimmed);
    await refreshThreads();
    if (threadId === activeThreadId) setThreadStatus(activeThreadId);
  } catch (err) {
    setStatus(`Rename failed: ${String(err.message || err)}`, true);
  }
}

async function deleteThread(threadId) {
  const ok = window.confirm("Delete this thread and its chat history?");
  if (!ok) return;
  try {
    await apiDelete(`/threads/${threadId}`);
    threadTitleCache.delete(threadId);
    threadPinnedCache.delete(threadId);
    if (activeThreadId === threadId) {
      activeThreadId = null;
      localStorage.removeItem(storageKeyThread);
      renderMessages([]);
    }
    await refreshThreads();
    const latest = await apiGet("/threads");
    const threads = latest.threads || [];
    if (!activeThreadId && threads.length) {
      activeThreadId = threads[0].thread_id;
      localStorage.setItem(storageKeyThread, activeThreadId);
      await loadMessages();
    } else if (!threads.length) {
      setStatus("No thread selected");
    }
  } catch (err) {
    setStatus(`Delete failed: ${String(err.message || err)}`, true);
  }
}

async function createThread() {
  const data = await apiPost("/threads", {});
  activeThreadId = data.thread.thread_id;
  threadTitleCache.set(activeThreadId, "New chat");
  localStorage.setItem(storageKeyThread, activeThreadId);
  await refreshThreads();
  renderMessages([]);
  setThreadStatus(activeThreadId);
}

async function refreshThreads() {
  const data = await apiGet("/threads");
  const threads = data.threads || [];
  await hydrateThreadTitles(threads);
  renderThreads(threads);
}

async function loadMessages() {
  if (!activeThreadId) {
    renderMessages([]);
    setStatus("No thread selected");
    return;
  }
  const data = await apiGet(`/threads/${activeThreadId}/messages`);
  renderMessages(data.messages || []);
  setThreadStatus(activeThreadId);
}

async function sendMessage(content) {
  if (!activeThreadId) {
    await createThread();
  }

  const wasNewChat = threadDisplayName(activeThreadId) === "New chat";
  if (wasNewChat) {
    threadTitleCache.set(activeThreadId, shortThreadTitle(content));
    renderThreads(
      (await apiGet("/threads")).threads || [],
    );
  }

  sendBtn.disabled = true;
  setThreadStatus(activeThreadId, "Thinking…");

  const current = Array.from(messagesEl.querySelectorAll(".msg")).map((el) => ({
    role: el.classList.contains("user") ? "user" : "assistant",
    content: el.textContent || "",
  }));
  renderMessages([
    ...current,
    { role: "user", content },
    { role: "assistant", content: "Thinking…" },
  ]);
  const typingEl = messagesEl.lastElementChild;
  if (typingEl) typingEl.classList.add("typing");

  try {
    const data = await apiPost(`/threads/${activeThreadId}/messages`, { content });
    if (typingEl) {
      typingEl.classList.remove("typing");
      typingEl.textContent = data.assistant_message.content || "";
    }
    await refreshThreads();
    setThreadStatus(activeThreadId);
  } catch (err) {
    await loadMessages();
    throw err;
  } finally {
    sendBtn.disabled = false;
  }
}

async function initialize() {
  const savedApi = localStorage.getItem(storageKeyApi);
  apiUrlInput.value = savedApi || defaultApi;

  try {
    const health = await apiGet("/health");
    setStatus(`Connected · corpus v${health.corpus_version ?? "?"}`);
  } catch (err) {
    setStatus(`API not reachable: ${String(err.message || err)}`, true);
    return;
  }

  try {
    await refreshThreads();
    const savedThread = localStorage.getItem(storageKeyThread);
    const data = await apiGet("/threads");
    const threads = data.threads || [];
    const pick =
      (savedThread && threads.find((t) => t.thread_id === savedThread)) ||
      threads[0] ||
      null;

    if (pick) {
      activeThreadId = pick.thread_id;
      localStorage.setItem(storageKeyThread, activeThreadId);
      await loadMessages();
      await refreshThreads();
    } else {
      setStatus("No thread selected");
    }
  } catch (err) {
    setStatus(`Failed to load threads: ${String(err.message || err)}`, true);
  }
}

saveApiBtn.addEventListener("click", async () => {
  localStorage.setItem(storageKeyApi, getApiBase());
  await initialize();
});

newThreadBtn.addEventListener("click", async () => {
  try {
    await createThread();
  } catch (err) {
    setStatus(`Create thread failed: ${String(err.message || err)}`, true);
  }
});

chatForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const content = (messageInput.value || "").trim();
  if (!content) return;
  messageInput.value = "";
  try {
    await sendMessage(content);
  } catch (err) {
    setStatus(`Send failed: ${String(err.message || err)}`, true);
  }
});

initialize();
