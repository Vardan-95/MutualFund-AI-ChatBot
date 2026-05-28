# Next.js Frontend

Production-oriented frontend built with Next.js (App Router) with two routes:

- `/` landing page (hero + Start Free Analysis)
- `/analysis` chat workspace connected to phase 9 API

## Run locally

1. Start API:

```bash
set PYTHONPATH=.
python -m runtime.phase_9_api
```

2. In a new terminal:

```bash
cd frontend
npm install
npm run dev
```

3. Open:

`http://127.0.0.1:3000`

## Environment

- `NEXT_PUBLIC_API_URL` (default: `http://127.0.0.1:8080`)

