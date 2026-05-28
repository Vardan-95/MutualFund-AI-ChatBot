# Test UI (HTML/CSS/JS)

Basic static UI for quickly testing the API and chat flow.

## Run

1) Start API:

```bash
set PYTHONPATH=.
python -m runtime.phase_9_api
```

2) Serve this folder:

```bash
python -m http.server 3000 --directory web
```

3) Open:

`http://127.0.0.1:3000`

Set API URL in the top bar (default `http://127.0.0.1:8080`).

## What it tests

- `POST /threads`
- `GET /threads`
- `GET /threads/{id}/messages`
- `POST /threads/{id}/messages`

This is for manual testing only. Production UI (Next.js) remains planned.
