"use client";

import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import {
  createThread,
  deleteThread,
  fetchHealth,
  getMessages,
  listThreads,
  postMessage,
  updateThread,
  waitForRagReady,
  type MessageItem,
  type ThreadSummary,
} from "@/lib/api";
import { QuestionGuideModal } from "@/components/QuestionGuideModal";
import { clearUserProfile, loadUserProfile, type UserProfile } from "@/lib/userProfile";
import { QUESTION_GUIDE_HINT } from "@/lib/questionGuide";
import { apiReachabilityHint, isLikelyMisconfiguredApiBase, setApiSessionKey } from "@/lib/api";

const SUGGESTED_QUESTIONS = [
  "What is the latest NAV of HDFC Mid Cap Fund Direct Growth?",
  "What is the expense ratio of HDFC Focused Fund Direct Growth?",
  "What are the top 5 holdings in HDFC Equity Fund Direct Growth?",
  "What is the minimum SIP for HDFC Large Cap Fund Direct Growth?",
] as const;

type SuggestPopupPhase = "hidden" | "enter" | "shown" | "exit";
const SUGGEST_ANIM_MS = 520;

function shortTitleFromQuestion(text: string): string {
  const q = text.toLowerCase();
  const bits: string[] = [];
  if (q.includes("nav")) bits.push("NAV");
  if (q.includes("expense")) bits.push("Expense Ratio");
  if (q.includes("holding")) bits.push("Holdings");
  if (q.includes("sip")) bits.push("SIP");
  const scheme = q.includes("equity")
    ? "HDFC Equity"
    : q.includes("mid cap")
      ? "HDFC Mid Cap"
      : q.includes("large cap")
        ? "HDFC Large Cap"
        : q.includes("focused")
          ? "HDFC Focused"
          : q.includes("elss")
            ? "HDFC ELSS"
            : "";
  const out = [scheme, ...bits].filter(Boolean).join(" · ");
  return out || text.slice(0, 28);
}

export default function AnalysisPage() {
  const [threads, setThreads] = useState<ThreadSummary[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [messages, setMessages] = useState<MessageItem[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [titles, setTitles] = useState<Record<string, string>>({});
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [openMenuThreadId, setOpenMenuThreadId] = useState<string | null>(null);
  const [openSettings, setOpenSettings] = useState(false);
  const [showArchived, setShowArchived] = useState(false);
  const [archivedIds, setArchivedIds] = useState<string[]>([]);
  const [showQuestionGuide, setShowQuestionGuide] = useState(false);
  const [popupPhase, setPopupPhase] = useState<SuggestPopupPhase>("hidden");
  const suggestAnimTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [suggestionsInteractable, setSuggestionsInteractable] = useState(false);
  const [apiError, setApiError] = useState<string | null>(null);
  const [warmStatus, setWarmStatus] = useState<"idle" | "warming" | "ready" | "failed">("idle");
  const bootstrappedRef = useRef(false);

  function clearSuggestAnimTimer() {
    if (suggestAnimTimer.current) {
      clearTimeout(suggestAnimTimer.current);
      suggestAnimTimer.current = null;
    }
  }

  function armSuggestionsAfterDelay(ms = 650) {
    setSuggestionsInteractable(false);
    window.setTimeout(() => setSuggestionsInteractable(true), ms);
  }

  function presentSuggestions() {
    clearSuggestAnimTimer();
    if (popupPhase === "enter" || popupPhase === "shown") return;
    setPopupPhase("enter");
    suggestAnimTimer.current = setTimeout(() => setPopupPhase("shown"), SUGGEST_ANIM_MS);
  }

  function dismissSuggestions() {
    if (popupPhase === "hidden" || popupPhase === "exit") return;
    clearSuggestAnimTimer();
    setPopupPhase("exit");
    suggestAnimTimer.current = setTimeout(() => setPopupPhase("hidden"), SUGGEST_ANIM_MS);
  }

  useEffect(() => () => clearSuggestAnimTimer(), []);

  useEffect(() => {
    const p = loadUserProfile();
    setProfile(p);
    setApiSessionKey(p?.email || null);
    const userKey = p?.email || "guest";
    try {
      const raw = window.localStorage.getItem(`wealthai_archived_threads_${userKey}`);
      if (raw) setArchivedIds(JSON.parse(raw) as string[]);
    } catch {
      setArchivedIds([]);
    }
    if (isLikelyMisconfiguredApiBase()) {
      setApiError(apiReachabilityHint());
    } else {
      setWarmStatus("warming");
      void fetchHealth()
        .then((h) => {
          if (h.rag_ready) {
            setWarmStatus("ready");
            return;
          }
          return waitForRagReady();
        })
        .then(() => {
          setWarmStatus("ready");
          setApiError(null);
        })
        .catch((err) => {
          setWarmStatus("failed");
          const msg = err instanceof Error ? err.message : "Could not warm up the API.";
          setApiError(msg);
        });
    }
    void bootstrapWorkspace();
  }, []);

  useEffect(() => {
    const userKey = profile?.email || "guest";
    window.localStorage.setItem(`wealthai_archived_threads_${userKey}`, JSON.stringify(archivedIds));
  }, [archivedIds, profile?.email]);

  async function refreshThreads() {
    const data = await listThreads();
    const list = data.threads || [];
    setThreads(list);
    setActiveId((current) => {
      if (current) return current;
      return list.length ? list[0].thread_id : null;
    });
    return list;
  }

  async function bootstrapWorkspace() {
    if (bootstrappedRef.current) return;
    bootstrappedRef.current = true;
    armSuggestionsAfterDelay();
    try {
      const list = await refreshThreads();
      if (list.length > 0) return;
      const created = await createThread();
      setThreads([created.thread]);
      setActiveId(created.thread.thread_id);
      setMessages([]);
      setApiError(null);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Could not connect to the API.";
      setApiError(msg);
    }
  }

  useEffect(() => {
    if (!activeId) {
      setMessages([]);
      return;
    }
    getMessages(activeId)
      .then((data) => {
        const loaded = data.messages || [];
        setMessages(loaded);
        if (loaded.some((m) => m.role === "user")) {
          dismissSuggestions();
          return;
        }
        const show = () => presentSuggestions();
        if (suggestionsInteractable) show();
        else window.setTimeout(show, 650);
      })
      .catch((err) => {
        const msg = err instanceof Error ? err.message : "Could not load messages.";
        setApiError(msg);
      });
  }, [activeId, suggestionsInteractable]);

  const sortedThreads = useMemo(() => [...threads], [threads]);
  const pinnedThreads = sortedThreads.filter((t) => !!t.pinned && !archivedIds.includes(t.thread_id));
  const recentThreads = sortedThreads.filter((t) => !t.pinned && !archivedIds.includes(t.thread_id));
  const archivedThreads = sortedThreads.filter((t) => archivedIds.includes(t.thread_id));

  async function onNewThread() {
    try {
      const created = await createThread();
      setThreads((p) => [created.thread, ...p]);
      setActiveId(created.thread.thread_id);
      setMessages([]);
      setApiError(null);
      armSuggestionsAfterDelay();
      presentSuggestions();
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Could not create a new chat.";
      setApiError(msg);
    }
  }

  async function sendQuestion(content: string) {
    if (!content || busy) return;
    dismissSuggestions();
    setBusy(true);

    try {
      let threadId = activeId;
      if (!threadId) {
        const created = await createThread();
        threadId = created.thread.thread_id;
        setActiveId(threadId);
        setThreads((p) => [created.thread, ...p]);
      }

      setTitles((prev) =>
        prev[threadId!] ? prev : { ...prev, [threadId!]: shortTitleFromQuestion(content) },
      );
      setMessages((prev) => [
        ...prev,
        { role: "user", content, timestamp: new Date().toISOString() },
      ]);

      const res = await postMessage(threadId!, content);
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: res.assistant_message.content || "",
          timestamp: new Date().toISOString(),
        },
      ]);
      setApiError(null);
      await refreshThreads();
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Something went wrong while fetching response.";
      setApiError(msg);
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: `I could not complete that request: ${msg}`,
          timestamp: new Date().toISOString(),
        },
      ]);
    } finally {
      setBusy(false);
    }
  }

  function openQuestionGuide() {
    setOpenSettings(false);
    setShowQuestionGuide(true);
  }

  async function onGuideQuestion(question: string) {
    if (busy) return;
    setShowQuestionGuide(false);
    await sendQuestion(question);
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    const content = input.trim();
    if (!content || busy) return;
    setInput("");
    await sendQuestion(content);
  }

  function onSuggestedQuestion(question: string) {
    if (busy || !suggestionsInteractable) return;
    void sendQuestion(question);
  }

  function toggleSuggestions() {
    if (popupPhase === "hidden") presentSuggestions();
    else dismissSuggestions();
  }

  const suggestionsVisible = popupPhase !== "hidden";

  const userAvatar = profile?.gender === "female" ? "👩" : profile?.gender === "male" ? "👨" : "🧑";
  const botAvatar = "🤖";

  function renderMessage(role: "user" | "assistant", content: string, key?: string) {
    const isUser = role === "user";
    return (
      <div key={key} className={`msg-row ${isUser ? "user" : "assistant"}`}>
        <span className="msg-avatar" aria-hidden="true">
          {isUser ? userAvatar : botAvatar}
        </span>
        <div className={`bubble ${isUser ? "user" : "assistant"}`}>{content}</div>
      </div>
    );
  }

  function onSignOut() {
    clearUserProfile();
    window.location.href = "/";
  }

  async function onPinToggle(thread: ThreadSummary) {
    await updateThread(thread.thread_id, { pinned: !thread.pinned });
    setOpenMenuThreadId(null);
    await refreshThreads();
  }

  async function onRenameThread(thread: ThreadSummary) {
    const next = window.prompt("Rename chat", titles[thread.thread_id] || thread.title || "New chat");
    if (!next) return;
    const trimmed = next.trim();
    if (!trimmed) return;
    await updateThread(thread.thread_id, { title: trimmed });
    setTitles((prev) => {
      const copy = { ...prev };
      delete copy[thread.thread_id];
      return copy;
    });
    setOpenMenuThreadId(null);
    await refreshThreads();
  }

  async function onDeleteThread(thread: ThreadSummary) {
    const ok = window.confirm("Delete this chat permanently?");
    if (!ok) return;
    await deleteThread(thread.thread_id);
    if (activeId === thread.thread_id) {
      setActiveId(null);
      setMessages([]);
    }
    setTitles((prev) => {
      const copy = { ...prev };
      delete copy[thread.thread_id];
      return copy;
    });
    setOpenMenuThreadId(null);
    await refreshThreads();
  }

  function onArchiveThread(thread: ThreadSummary) {
    setArchivedIds((prev) => (prev.includes(thread.thread_id) ? prev : [...prev, thread.thread_id]));
    if (activeId === thread.thread_id) {
      setActiveId(null);
      setMessages([]);
    }
    setOpenMenuThreadId(null);
  }

  function onUnarchiveThread(thread: ThreadSummary) {
    setArchivedIds((prev) => prev.filter((id) => id !== thread.thread_id));
    setOpenMenuThreadId(null);
  }

  function renderThreadRow(thread: ThreadSummary, archived = false) {
    const label = thread.title || titles[thread.thread_id] || "New chat";
    return (
      <div key={thread.thread_id} className={`thread-chip ${activeId === thread.thread_id ? "active" : ""}`}>
        <button className="thread-main-btn" onClick={() => setActiveId(thread.thread_id)}>
          {label}
        </button>
        <button
          className="thread-kebab"
          onClick={() => setOpenMenuThreadId((p) => (p === thread.thread_id ? null : thread.thread_id))}
          aria-label="Thread actions"
        >
          ⋯
        </button>
        {openMenuThreadId === thread.thread_id ? (
          <div className="thread-menu">
            <button onClick={() => onPinToggle(thread)}>{thread.pinned ? "Unpin" : "Pin"}</button>
            <button onClick={() => onRenameThread(thread)}>Rename</button>
            <button onClick={() => onDeleteThread(thread)}>Delete</button>
            {archived ? (
              <button onClick={() => onUnarchiveThread(thread)}>Unarchive</button>
            ) : (
              <button onClick={() => onArchiveThread(thread)}>Archive</button>
            )}
          </div>
        ) : null}
      </div>
    );
  }

  return (
    <main className="analysis-page">
      <aside className="analysis-sidebar">
        <div className="side-brand">
          <div className="side-brand-row">
            <span className="side-brand-icon" aria-hidden="true">🏛️</span>
            <div className="brand">WealthAI</div>
          </div>
        </div>
        <button className="primary-btn full" onClick={onNewThread}>
          + New Analysis
        </button>
        <p className="side-label">Pinned conversations</p>
        <div className="side-threads pinned-list">
          {pinnedThreads.length ? pinnedThreads.map((t) => renderThreadRow(t)) : <p className="empty-row">No pinned chats</p>}
        </div>
        <div className="recent-section">
          <p className="side-label">Recent conversations</p>
          <div className="side-threads recent-list">
            {recentThreads.map((t) => renderThreadRow(t))}
          </div>
        </div>

        {showArchived ? (
          <div className="archived-section">
            <p className="side-label">Archived conversations</p>
            <div className="side-threads archived-list">
              {archivedThreads.length
                ? archivedThreads.map((t) => renderThreadRow(t, true))
                : <p className="empty-row">No archived chats</p>}
            </div>
          </div>
        ) : null}

        <div className="sidebar-footer">
          <button className="settings-btn" onClick={() => setOpenSettings((v) => !v)}>⚙ Settings</button>
          {openSettings ? (
            <div className="settings-menu">
              <button onClick={() => { setShowArchived((v) => !v); setOpenSettings(false); }}>
                {showArchived ? "Hide archived chats" : "Archived chats"}
              </button>
              <button onClick={openQuestionGuide}>Question guide</button>
              <button onClick={onSignOut}>Sign out</button>
            </div>
          ) : null}
        </div>
      </aside>

      <section className="analysis-main">
        <header className="analysis-header">
          <h2 className="analysis-title"><span className="analysis-title-icon" aria-hidden="true">📈</span>FundAdvisor AI</h2>
          <span className="market-pill">Markets Open</span>
          <div className="header-user">
            <span className="header-avatar" aria-hidden="true">{userAvatar}</span>
            <span className="header-welcome">
              Welcome{profile?.name ? `, ${profile.name}` : ""}
            </span>
          </div>
        </header>
        {apiError ? (
          <div className="api-error-banner" role="alert">
            {apiError}
          </div>
        ) : warmStatus === "warming" ? (
          <div className="api-info-banner" role="status">
            Waking up AI on the server — first load can take 1–2 minutes on the free tier. You can
            browse suggested questions while this finishes.
          </div>
        ) : null}
        <div className="analysis-chat-panel">
          <div className="analysis-chat-bg" aria-hidden="true" />
          <div className="analysis-chat">
            {renderMessage(
              "assistant",
              "Hello! I can help with facts about the five HDFC schemes on Groww. Ask NAV, expense ratio, holdings, SIP, AUM, or exit load.",
              "welcome",
            )}
            {messages.map((m, i) =>
              renderMessage(m.role === "user" ? "user" : "assistant", m.content, `${i}-${m.timestamp}`),
            )}
          </div>
        </div>
        <div className="analysis-composer">
          <div className="suggest-cloud-wrap">
            {suggestionsVisible ? (
              <div
                className={`suggest-cloud-popups suggest-cloud-popups--${popupPhase}`}
                role="list"
                aria-label="Suggested questions"
              >
                {SUGGESTED_QUESTIONS.map((q) => (
                  <button
                    key={q}
                    type="button"
                    className="suggest-cloud-chip"
                    role="listitem"
                    disabled={busy || !suggestionsInteractable}
                    onClick={() => onSuggestedQuestion(q)}
                  >
                    {q}
                  </button>
                ))}
                <p className="suggest-cloud-hint" role="note">
                  {QUESTION_GUIDE_HINT}
                </p>
              </div>
            ) : null}
            <button
              type="button"
              className={`suggest-cloud-btn ${suggestionsVisible ? "open" : ""}`}
              onClick={toggleSuggestions}
              aria-label={suggestionsVisible ? "Hide suggested questions" : "Show suggested questions"}
              aria-expanded={suggestionsVisible}
            >
              <span className="suggest-cloud-icon" aria-hidden="true">
                <svg viewBox="0 0 24 24" width="26" height="26" focusable="false">
                  <path
                    fill="#F5C518"
                    d="M19.35 10.04C18.67 6.59 15.64 4 12 4 9.11 4 6.6 5.64 5.35 8.04 2.34 8.36 0 10.91 0 14c0 3.31 2.69 6 6 6h13c2.76 0 5-2.24 5-5 0-2.64-2.05-4.78-4.65-4.96z"
                  />
                </svg>
              </span>
            </button>
          </div>
          <form className="analysis-composer-form" onSubmit={onSubmit}>
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask about funds, holdings, NAV, SIP..."
            />
            <button className="primary-btn small" disabled={busy} type="submit">
              {busy ? (warmStatus === "warming" ? "Warming up…" : "Analyzing…") : "Send"}
            </button>
          </form>
        </div>
      </section>

      <QuestionGuideModal
        open={showQuestionGuide}
        busy={busy}
        onClose={() => setShowQuestionGuide(false)}
        onPickQuestion={(q) => void onGuideQuestion(q)}
      />
    </main>
  );
}
