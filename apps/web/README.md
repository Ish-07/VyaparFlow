# VyaparFlow — Web (Next.js)

A simple frontend for testing the VyaparFlow backend end-to-end: auth,
business onboarding, the voice/text command bar, products, transactions,
and RAG documents. Built to be extended later (voice input, richer
dashboard, etc.) — this is intentionally minimal for now.

## Stack
Next.js 14 (App Router) + TypeScript + Tailwind CSS + Zustand, per the
project's Frontend/Backend design transcript.

## Setup

```bash
cd apps/web
npm install
cp .env.local.example .env.local
```

Edit `.env.local` if your backend isn't at the default `http://127.0.0.1:8000`.

## Run

Make sure the backend is running first (`apps/api`, `uvicorn app.main:app --reload`),
then:

```bash
npm run dev
```

Open http://localhost:3000.

## Pages

- `/register`, `/login` — auth
- `/onboarding` — create your first business, or pick one if you have several
- `/` — dashboard: the command bar (type a command like "sold 5 pickle
  bottles for 100 rupees each") plus sales/expense/profit metrics,
  low-stock and reminders
- `/products` — list + add products
- `/transactions` — sales/purchases history
- `/documents` — RAG: paste business documents (supplier terms, notes)
  and ask questions against them

## Known limitations (documented, matching the backend's own scope choices)

- Text input only — voice/microphone input is a later step (Whisper
  pipeline hasn't been built yet).
- Document ingestion is paste-text only, no file upload yet (matches the
  backend — no object storage wired up).
- No automated browser (E2E) tests in this repo yet — Playwright couldn't
  be set up in the development sandbox (no network access to its browser
  download CDN). The API contract (every request/response shape used
  here) was verified against a live backend instance instead; browser-level
  E2E testing is a good next addition once you have local browser access.

## A note on `npm audit`

Next.js 14.2.x currently has several known advisories (see `npm audit`)
that fall due mostly for internet-exposed production deployments
(Server Actions, Image Optimizer, Middleware edge cases). For local
development against `127.0.0.1` this is low-risk, but before any real
deployment, plan to upgrade to a current Next.js major version.
