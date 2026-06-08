# Drax Dashboard

A minimal React + Recharts dashboard for Phase 5.

## Run locally

1. Install dependencies:

```bash
cd frontend
npm install
```

2. Start the dashboard:

```bash
npm run dev
```

3. Open the local URL printed by Vite (default `http://localhost:5173`).

4. Make sure your backend is running on `http://localhost:8000`.

## Notes

- The dashboard calls the existing FastAPI endpoint `POST /query`.
- It also loads session history from `GET /history`.
- The page renders charts returned by the API using Recharts.
