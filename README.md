<div align="center">

# **Campaign** `Pulse`

### Launch winning campaigns at scale

*Automate cold email outreach with inbox rotation, warmup, reply ingestion, and campaign analytics — built for high-volume teams.*

<br/>

[![Next.js](https://img.shields.io/badge/Next.js-15-000000?style=for-the-badge&logo=next.js&logoColor=white)](https://nextjs.org/)
[![React](https://img.shields.io/badge/React-19-61DAFB?style=for-the-badge&logo=react&logoColor=black)](https://react.dev/)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind-06B6D4?style=for-the-badge&logo=tailwindcss&logoColor=white)](https://tailwindcss.com/)

<br/>

[**Features**](#features) · [**Quick Start**](#getting-started) · [**API Docs**](#api-documentation) · [**Architecture**](#architecture)

</div>

<br/>

**Campaign Pulse** is a full-stack email outreach platform that pairs a modern Next.js dashboard with a FastAPI backend, PostgreSQL database, and an automated sending engine.

---

## Table of Contents

- [Features](#features)
- [Tech Stack](#tech-stack)
- [Architecture](#architecture)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Getting Started](#getting-started)
- [Environment Variables](#environment-variables)
- [Database Migrations](#database-migrations)
- [Running the Application](#running-the-application)
- [Background Workers](#background-workers)
- [Testing](#testing)
- [Seed Data](#seed-data)
- [Key Routes](#key-routes)
- [API Documentation](#api-documentation)
- [Development History](#development-history)
- [Contributing](#contributing)

---

## Features

### Authentication & Identity
- Email/password signup with verification links
- Google OAuth 2.0 sign-in and account linking
- Password reset flow with token-based confirmation
- Session cookies with middleware-protected dashboard routes
- Remember-me and dual-auth identity support

### Workspace & Collaboration
- Multi-user workspaces with role-based permissions
- Email invitations and collaborator management
- Shared access to campaigns, accounts, and analytics

### Email Accounts
- Connect and manage sender (Gmail) accounts per workspace
- Configurable sending limits, min delay, and daily caps
- Account warmup mode with automatic scheduling
- Manual and background IMAP inbox scanning for reply detection

### Campaigns & Sequences
- Create and manage outreach campaigns
- Multi-step sequences with A/B email variants
- CSV/XLSX lead import with custom variables
- Pool-driven scheduling with send windows and wait days
- Start/stop campaign controls with live queue status

### Unibox
- Unified inbox for campaign replies across all sender accounts
- Threaded conversation view with search and filtering
- Automatic reply ingestion via IMAP background workers

### Analytics
- Campaign performance dashboard with date-range filtering
- Open, click, reply, and opportunity tracking
- Recharts-powered visualizations

### Marketing Site
- Animated landing page with features, pricing, and social proof
- Privacy policy and terms of service pages
- Responsive design with dark mode support

---

## Tech Stack

| Layer | Technologies |
|-------|-------------|
| **Frontend** | [Next.js 15](https://nextjs.org/) (App Router, Turbopack), [React 19](https://react.dev/), [Tailwind CSS 3](https://tailwindcss.com/) |
| **UI Libraries** | [Framer Motion](https://www.framer.com/motion/), [Lucide React](https://lucide.dev/), [Recharts](https://recharts.org/), [Sonner](https://sonner.emilkowal.ski/) |
| **Backend** | [FastAPI](https://fastapi.tiangolo.com/), [Uvicorn](https://www.uvicorn.org/), [Pydantic v2](https://docs.pydantic.dev/) |
| **Database** | [PostgreSQL](https://www.postgresql.org/), [SQLAlchemy 2](https://www.sqlalchemy.org/), [Alembic](https://alembic.sqlalchemy.org/) |
| **Auth** | JWT (python-jose), bcrypt/passlib, [Authlib](https://docs.authlib.org/) (Google OAuth) |
| **Email** | SMTP (Gmail), IMAP reply scanning, signed open/click tracking pixels |
| **Testing** | [pytest](https://docs.pytest.org/) with real PostgreSQL test database |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Next.js Frontend (:3000)                    │
│  Landing · Auth · Dashboard (Campaigns · Unibox · Analytics)   │
└──────────────────────────┬──────────────────────────────────────┘
                           │ HTTP + session cookies
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                    FastAPI Backend (:8000)                      │
│  /auth  /workspaces  /campaigns  /unibox  /analytics  /track   │
└──────────┬──────────────────────────────┬───────────────────────┘
           │                              │
           ▼                              ▼
┌─────────────────────┐      ┌──────────────────────────────────┐
│    PostgreSQL       │      │   Background Engine Loops        │
│  Users · Campaigns  │      │  · Sending loop (every 5s)       │
│  Leads · Unibox     │      │  · Warmup loop (every 15 min)    │
│  Email Events       │      │  · IMAP reply scan (every 2 min) │
└─────────────────────┘      └──────────────────────────────────┘
```

The frontend communicates with the backend via REST API calls using cookie-based authentication. Protected routes are guarded by Next.js middleware that validates sessions against `/auth/me`. The sending engine runs as async background tasks inside the FastAPI process, respecting per-account rate limits and warmup states.

---

## Project Structure

```
Campaign-Pulse/
├── app/                          # Next.js App Router pages
│   ├── auth/                     # Login, signup, OAuth callback, verification
│   ├── dashboard/                # Protected dashboard routes
│   │   ├── campaigns/            # Campaign list & detail views
│   │   ├── email-accounts/       # Sender account management
│   │   ├── collaborators/        # Team member management
│   │   ├── unibox/               # Unified reply inbox
│   │   └── analytics/            # Performance dashboard
│   ├── features/                 # Marketing feature pages
│   ├── pricing/                  # Pricing page
│   └── page.jsx                  # Landing page
├── components/
│   ├── auth/                     # Login/signup forms
│   ├── dashboard/                # Dashboard views & shell
│   ├── landing/                  # Marketing site components
│   ├── providers/                # Theme, toast, layout providers
│   └── ui/                       # Shared UI primitives
├── contexts/                     # React context (workspace state)
├── middleware.ts                 # Route protection & session validation
├── backend/
│   ├── app/
│   │   ├── main.py               # FastAPI entry point
│   │   ├── models.py             # SQLAlchemy ORM models
│   │   ├── routers/              # API route handlers
│   │   ├── services/             # Business logic layer
│   │   └── workers/              # Background sending/IMAP loops
│   ├── alembic/                  # Database migrations
│   ├── scripts/                  # Local seed & utility scripts
│   └── tests/                    # pytest test suite
├── public/                       # Static assets
└── Campaign_Pulse_ER_Diagram.drawio  # Entity-relationship diagram
```

---

## Prerequisites

- **Node.js** 18+ and npm
- **Python** 3.11+
- **PostgreSQL** 13+ (uses `gen_random_uuid()` natively)
- A Gmail account with App Password (for SMTP/IMAP in development)

---

## Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/ArsalanTahirr/Campaign-Pulse.git
cd Campaign-Pulse
```

### 2. Set up environment variables

Create a `.env` file at the repository root:

```env
# Database
DATABASE_URL=postgresql+psycopg2://postgres:password@localhost:5432/campaign_pulse

# Auth
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# URLs
FRONTEND_URL=http://localhost:3000
BACKEND_BASE_URL=http://localhost:8000
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000

# SMTP (Gmail App Password)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=465
SMTP_EMAIL=your-email@gmail.com
SMTP_APP_PASSWORD=your-app-password
EMAIL_FROM=your-email@gmail.com

# Google OAuth (optional)
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GOOGLE_REDIRECT_URI=http://localhost:8000/auth/google/callback

# Sending Engine
ENABLE_SENDING_ENGINE=true
TRACKING_BASE_URL=http://localhost:8000
TRACKING_SIGNING_SECRET=dev-tracking-secret
```

### 3. Install dependencies

```bash
# Frontend
npm install

# Backend
cd backend
python -m venv venv
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate
pip install -r requirements.txt
```

### 4. Run database migrations

```bash
cd backend
alembic upgrade head
```

### 5. (Optional) Seed local demo data

```bash
python backend/scripts/seed_local_full.py
```

---

## Environment Variables

### Frontend

| Variable | Default | Description |
|----------|---------|-------------|
| `NEXT_PUBLIC_API_BASE_URL` | `http://localhost:8000` | Backend API base URL |
| `NEXT_PUBLIC_LOGIN_ENDPOINT` | `/auth/login` | Login API path |
| `NEXT_PUBLIC_SIGNUP_ENDPOINT` | `/auth/signup` | Signup API path |
| `NEXT_PUBLIC_GOOGLE_LOGIN_ENDPOINT` | `/auth/google/login` | Google OAuth initiation path |

### Backend — Core

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | Yes | PostgreSQL connection string |
| `SECRET_KEY` | Yes | JWT signing secret |
| `FRONTEND_URL` | No | Frontend origin for CORS and redirects |
| `BACKEND_BASE_URL` | No | Backend public URL |

### Backend — Email

| Variable | Description |
|----------|-------------|
| `SMTP_HOST` | SMTP server (default: `smtp.gmail.com`) |
| `SMTP_PORT` | SMTP port (default: `465`) |
| `SMTP_EMAIL` | Sender email address |
| `SMTP_APP_PASSWORD` | Gmail App Password |
| `EMAIL_FROM` | From address in outgoing emails |

### Backend — Sending Engine

| Variable | Default | Description |
|----------|---------|-------------|
| `ENABLE_SENDING_ENGINE` | `false` | Enable background sending/IMAP loops |
| `SEND_LOOP_SECONDS` | `5` | Interval between send batch runs |
| `SEND_BATCH_SIZE` | `20` | Max emails per send batch |
| `WARMUP_LOOP_SECONDS` | `900` | Warmup check interval (15 min) |
| `IMAP_LOOP_SECONDS` | `120` | IMAP scan interval (2 min) |
| `TRACKING_BASE_URL` | `http://localhost:8000` | Base URL for open/click tracking links |

---

## Database Migrations

Migrations are managed with Alembic from the `backend/` directory:

```bash
cd backend

# Apply all pending migrations
alembic upgrade head

# Create a new migration after model changes
alembic revision --autogenerate -m "describe your change"

# Roll back one migration
alembic downgrade -1
```

The schema follows a normalized PostgreSQL design with UUID primary keys, JSONB columns for semi-structured data, and cascade rules for related entities. See `Campaign_Pulse_ER_Diagram.drawio` for the full entity-relationship diagram.

---

## Running the Application

Start both services in separate terminals:

```bash
# Terminal 1 — Frontend (with Turbopack)
npm run dev

# Terminal 2 — Backend
cd backend
uvicorn app.main:app --reload --port 8000
```

| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:8000 |
| Swagger Docs | http://localhost:8000/docs |
| ReDoc | http://localhost:8000/redoc |

---

## Background Workers

When `ENABLE_SENDING_ENGINE=true`, FastAPI starts three async background loops on startup:

| Loop | Interval | Purpose |
|------|----------|---------|
| **Sending loop** | 5 seconds | Processes the email queue, rotates step variants, respects min delay and daily caps |
| **Warmup loop** | 15 minutes | Advances sender account warmup schedules |
| **IMAP reply loop** | 2 minutes | Scans connected inboxes and ingests replies into Unibox |

Accounts in warmup mode are excluded from sending and IMAP scanning until warmup completes.

---

## Testing

The backend test suite uses pytest with a dedicated PostgreSQL test database (`campaign_pulse_test_db`), created automatically on first run.

```bash
cd backend
pytest
```

Test coverage includes:

| Module | Areas Covered |
|--------|---------------|
| `test_users.py` | Signup, login, verification, Google OAuth |
| `test_auth_robust.py` | Edge cases, account linking, reset lifecycle |
| `test_campaigns.py` | Campaign CRUD and lifecycle |
| `test_sequences.py` | Sequence steps and email variants |
| `test_leads.py` | Lead import, scheduling, deletion guards |
| `test_email_accounts.py` | Sender account management |
| `test_unibox.py` | Thread ingestion and reply handling |
| `test_analytics.py` | Dashboard metrics and date filtering |
| `test_collaborators.py` | Workspace permissions |
| `test_invitations.py` | Invite flow and acceptance |
| `test_tracking.py` | Open/click event tracking |
| `test_workspaces.py` | Workspace creation and ownership |

---

## Seed Data

Local development seed scripts populate a full demo workspace:

```bash
# Full demo: users, campaigns, leads, analytics events, unibox threads
python backend/scripts/seed_local_full.py

# Unibox-only demo data
python backend/scripts/seed_unibox_demo.py

# Analytics-only demo data
python backend/scripts/seed_analytics.py

# Re-run after cleanup
python backend/scripts/seed_local_full.py --cleanup
```

> **Safety:** Seed scripts refuse to run against production databases unless `ALLOW_SEED_IN_PROD=true` is explicitly set.

---

## Key Routes

### Public

| Route | Description |
|-------|-------------|
| `/` | Landing page |
| `/login` | Login |
| `/auth/signup` | Registration |
| `/reset-password` | Password reset |
| `/features` | Product features |
| `/pricing` | Pricing plans |
| `/privacy` | Privacy policy |
| `/terms` | Terms of service |
| `/invitations/accept/[token]` | Workspace invitation acceptance |

### Dashboard (authenticated)

| Route | Description |
|-------|-------------|
| `/dashboard/email-accounts` | Manage sender accounts and IMAP scanning |
| `/dashboard/campaigns` | Campaign list |
| `/dashboard/campaigns/[id]` | Campaign detail, leads, sequence builder |
| `/dashboard/collaborators` | Team members and invitations |
| `/dashboard/unibox` | Unified reply inbox |
| `/dashboard/analytics` | Campaign performance metrics |

---

## API Documentation

Interactive API documentation is available when the backend is running:

- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

Major API namespaces:

| Prefix | Description |
|--------|-------------|
| `/auth` | Authentication and user management |
| `/workspaces` | Workspace CRUD |
| `/workspaces/{id}/campaigns` | Campaign management |
| `/workspaces/{id}/campaigns/{id}/sequences` | Sequence steps and variants |
| `/workspaces/{id}/campaigns/{id}/leads` | Lead import and management |
| `/workspaces/{id}/email-accounts` | Sender account configuration |
| `/workspaces/{id}/engine` | Sending engine operations |
| `/workspaces/{id}/unibox` | Unified inbox threads and messages |
| `/workspaces/{id}/analytics` | Dashboard metrics |
| `/track` | Public open/click tracking endpoints |

---

## Development History

Campaign Pulse was built incrementally across several major phases:

1. **Foundation** — Landing page, login/signup UI, ER diagram, and PostgreSQL schema with Alembic migrations
2. **Authentication** — FastAPI auth backend with local signup/login, email verification, Google OAuth, password reset, and session middleware
3. **Dashboard UI** — Sidebar navigation, email accounts, campaigns, collaborators, unibox, and analytics views
4. **Campaign Engine** — Backend services for campaigns, sequences, lead import, and collaborative workspace access
5. **Sending Engine** — Automated email dispatch with pool-driven scheduling, variant rotation, warmup, and IMAP reply ingestion
6. **Unibox & Analytics** — Reply threading, search, and performance dashboards with open/click/reply tracking
7. **Polish & Hardening** — UI consistency fixes, queue logic refinements, auth regression tests, and production-readiness improvements

---

## License

This project is currently private. All rights reserved.
