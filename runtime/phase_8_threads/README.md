# Phase 8 — Multi-thread chat

- **Storage:** SQLite (`THREAD_DB_PATH`, default `data/threads/threads.db`)
- **Context:** last `THREAD_MAX_TURNS` user lines (default 4)
- **Expansion:** follow-up hints merge prior user line (§8.2)
- **API:** `POST /chat` with `thread_id` uses `post_user_message()`

```bash
set PYTHONPATH=.
python -m runtime.phase_8_threads new-thread
python -m runtime.phase_8_threads say <uuid> What is the minimum SIP for HDFC Large Cap?
python -m runtime.phase_8_threads history <uuid>
```
