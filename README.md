# Instant Mechanic LiveOps Dashboard

> **A real-time operations cockpit for Instant Mechanic's dispatch and ops management team.**
> Built with Django, Django REST Framework, Django Channels (Daphne ASGI), PostgreSQL, React 18, Vite, TypeScript, and Tailwind CSS.

---

## 1. Executive Summary & Technology Decision

### The Product
Instant Mechanic LiveOps is not an ordinary reporting tool—it is an **active operations cockpit**. It gives ops executives immediate visibility into incoming bookings, mechanic workload, dispatch delays, and revenue streams, while proactively highlighting operations in jeopardy through a deterministic **"Requires Attention"** alert engine.

### Why Django & Django REST Framework?
The internship role explicitly requires **Python and Django** (CRUD with Django, REST API design, and full-stack integration). Rather than optimizing purely for the assignment brief in isolation, this project is built from the ground up using **Django + Django REST Framework + Django Channels** to demonstrate mastery in the exact stack the role requires:
- **Relational Integrity & Mature ORM:** Complex relationships between customers, multi-vehicle profiles, service categories, mechanics, and booking state history.
- **Explicit Lifecycle State Machine:** Strict transition rules governed in an atomic `BookingService` layer instead of loose models or unpredictable `post_save` signals.
- **ASGI Real-Time Streaming:** Leveraging Django Channels with Daphne ASGI for WebSocket push notifications (`/ws/operations/`) with seamless polling fallback.
- **Interactive OpenAPI Documentation:** Fully documented with `drf-spectacular` generating real-time Swagger UI and OpenAPI 3.0 schemas.

---

## 2. System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│              React + Vite + TypeScript + Tailwind           │
│  - Operations Cockpit Header & Connection Indicator         │
│  - "Requires Attention" Alert Panel (Tier 1 Core)           │
│  - 4 Server-Aggregated Analytics Charts (Recharts)          │
│  - Bookings Table (Search, Filters, Server Pagination)      │
│  - Booking Detail Drawer (Visual Status Timeline)           │
│  - Mechanics Workload & Customer Directory                  │
└──────────────────────────────┬──────────────────────────────┘
                               │ HTTP REST + WebSocket (/ws/operations/)
┌──────────────────────────────▼──────────────────────────────┐
│                  Nginx (Reverse Proxy)                      │
│                  - Proxy Pass to ASGI                       │
│                  - WebSocket Upgrade Headers                │
└──────────────────────────────┬──────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────┐
│                    Daphne ASGI Server                       │
│                             │                               │
│              Django 4.2+ / DRF + Django Channels            │
│  ┌───────────────────────────────────────────────────────┐  │
│  │                    Service Layer                      │  │
│  │  - BookingService: transition_booking(), assign()     │  │
│  │  - AttentionEngine: non-overlapping alert rules       │  │
│  │  - AnalyticsEngine: server-side aggregate/annotate    │  │
│  └───────────────────────────┬───────────────────────────┘  │
│                              │ transaction.atomic()         │
│                              │ + transaction.on_commit()    │
│                              ▼                              │
│          Channel Layer Broadcast (booking.updated)          │
└──────────────────────────────┬──────────────────────────────┘
                               │
                      PostgreSQL / Database
```

---

## 3. Tech Stack Matrix

| Layer | Choice | Rationale |
|---|---|---|
| **Backend** | **Django 4.2+ / DRF** | Matches the internship role's core required stack. |
| **Real-time** | **Django Channels + Daphne** | Official ASGI server and channel layers for async push events. |
| **Database** | **PostgreSQL / SQLite** | PostgreSQL in deployment; SQLite supported for lightweight local development/testing. |
| **Frontend** | **React + Vite + TypeScript** | High performance, strict type safety, fast build times. |
| **Styling** | **Tailwind CSS** | Operational dark-slate theme with high information density. |
| **Charts** | **Recharts** | Interactive timeline, revenue, and status visualizations. |
| **API Docs** | **drf-spectacular** | OpenAPI 3.0 schema and interactive Swagger UI. |

---

## 4. Key Architectural Highlights

### 4.1 State Transition Engine & Domain Invariants
Booking status mutations do **not** use generic field PATCHes or `post_save` signals (which cannot distinguish the source of a save). All status changes pass through the `BookingService` layer:

```python
ALLOWED_TRANSITIONS = {
    "PENDING": ["CANCELLED"],
    "ASSIGNED": ["ON_THE_WAY", "CANCELLED"],
    "ON_THE_WAY": ["ARRIVED", "CANCELLED"],
    "ARRIVED": ["IN_PROGRESS", "CANCELLED"],
    "IN_PROGRESS": ["COMPLETED", "CANCELLED"],
    "COMPLETED": [],
    "CANCELLED": [],
}
```

- **Dedicated Dispatch Operation:** Moving from `PENDING` to `ASSIGNED` requires mechanic selection via `BookingService.assign_mechanic()`. This guarantees that active bookings always have a valid assigned mechanic and prevents orphan assignments.
- **Capacity & Availability Guards:** Mechanics on `BREAK` or `OFFLINE` cannot be assigned, and an explicit capacity limit (`MAX_CONCURRENT_JOBS = 4`) prevents mechanic overloading.
- **Database-Level Constraints:** PostgreSQL `CheckConstraint` enforces `amount >= 0` and active states (`ASSIGNED`, `ON_THE_WAY`, `ARRIVED`, `IN_PROGRESS`) requiring `mechanic_id IS NOT NULL`.
- **Atomic Integrity & Row Locking:** Updating the booking and creating a `BookingStatusHistory` record happen inside `transaction.atomic()` using `select_for_update()` to prevent race conditions.
- **Post-Commit Push:** WebSocket broadcast triggers via `transaction.on_commit()` inside the atomic block, ensuring events only publish upon database success.
- **Semantic Error Codes:** Invalid transitions return `409 Conflict`.

### 4.2 "Requires Attention" Engine (Tier 1 Core)
Alert rules are non-overlapping and prioritized by severity:
1. **CRITICAL:** `PENDING` booking unassigned for $> 15$ minutes.
2. **HIGH:** `ASSIGNED` booking without travel progress for $> 10$ minutes.
3. **WARNING (Delayed):** `ON_THE_WAY` booking with passed ETA and `arrived_at IS NULL`.
4. **WARNING (Overloaded):** Mechanic with $\ge 4$ active bookings.

### 4.3 Disambiguated Mechanic Model
- `availability_status`: Manually set state (`AVAILABLE`, `OFFLINE`, `BREAK`).
- `operational_status`: Dynamically derived from workload (`AVAILABLE`, `ASSIGNED`, `ON_JOB`, `BREAK`, `OFFLINE`).
- `primary_booking`: Defined deterministically as the oldest active non-terminal booking.

---

## 5. API Reference

Interactive Swagger Documentation is available at `/api/docs/` when running the backend.

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v1/dashboard/overview/` | Returns 8 primary KPIs and secondary operational stats with deltas. |
| `GET` | `/api/v1/dashboard/attention/` | Returns active ops alerts with severity rankings. |
| `GET` | `/api/v1/analytics/bookings/?range=24h\|7d\|30d` | Server-aggregated booking volume timeline. |
| `GET` | `/api/v1/analytics/revenue/?range=7d\|30d` | Daily completed gross revenue. |
| `GET` | `/api/v1/analytics/status/` | Status distribution counts and percentages. |
| `GET` | `/api/v1/analytics/services/` | Category breakdown (jobs booked and revenue). |
| `GET` | `/api/v1/bookings/?page=&status=&service_category=&search=&ordering=` | Paginated bookings with search & filters. |
| `GET` | `/api/v1/bookings/{id}/` | Full booking details with status history audit trail. |
| `POST` | `/api/v1/bookings/{id}/transition/` | Validated status change $\rightarrow$ history row + WS broadcast. |
| `POST` | `/api/v1/bookings/{id}/assign/` | Assign mechanic $\rightarrow$ updates status + history + WS broadcast. |
| `GET` | `/api/v1/mechanics/` | Mechanics list with operational workload and active job counters. |
| `GET` | `/api/v1/customers/` | Customer directory with lifetime value. |
| `POST` | `/api/v1/demo/simulate/` | Advances one eligible booking in the demo pool. |
| `WS` | `/ws/operations/` | Real-time WebSocket event stream. |

---

## 6. Local Quickstart Guide

### Option A: Docker Compose (Recommended)
Spins up PostgreSQL, Django ASGI with Daphne, and the React frontend in one command:

```bash
docker compose up --build -d

# Seed demo data once (safe and idempotent):
docker compose exec backend python manage.py seed_data
```
- Frontend: `http://localhost:5173`
- Backend API & Swagger: `http://localhost:8000/api/docs/`
- Demo Reset (optional): `docker compose exec backend python manage.py seed_data --reset`

---

### Option B: Standalone Local Setup

#### 1. Backend Setup
```bash
cd backend
python -m venv .venv

# Windows PowerShell:
.\.venv\Scripts\Activate.ps1
# Linux/macOS:
source .venv/bin/activate

pip install -r requirements.txt

# Run migrations and seed data
python manage.py migrate
python manage.py seed_data

# Run tests
pytest

# Start ASGI server (Daphne)
daphne -b 127.0.0.1 -p 8000 core.asgi:application
```

#### 2. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```
Open `http://localhost:5173` in your browser.

---

## 7. Automated Test Suite

Run the backend test suite:
```bash
cd backend
pytest
```

**Test Coverage Highlights:**
- `tests/test_transitions.py`: Validates happy path (`PENDING -> ASSIGNED -> ON_THE_WAY -> ARRIVED -> IN_PROGRESS -> COMPLETED`), rejects invalid transitions with `409 Conflict`, verifies DB record immutability on failure, and checks mechanic assignment rules.
- `tests/test_attention.py`: Validates deterministic trigger conditions for CRITICAL, HIGH, and WARNING alerts.
- `tests/test_dashboard_kpis.py`: Verifies that total revenue strictly includes `COMPLETED` bookings and active mechanics exclude `OFFLINE` staff.

---

## 8. Interview Defense & Technical Decisions

1. **Why Django over FastAPI/Node for this assignment?**
   - Django and DRF are explicitly the core stack of the internship. Demonstrating relational modeling, custom management commands, atomic transactions, and Channels integration shows immediate readiness for production contributions.
2. **Walk through a status change end-to-end.**
   - Request hits `POST /api/v1/bookings/{id}/transition/` $\rightarrow$ payload validated $\rightarrow$ `BookingService.transition_booking()` checks `ALLOWED_TRANSITIONS` $\rightarrow$ inside `transaction.atomic()`, updates booking timestamp and inserts `BookingStatusHistory` $\rightarrow$ upon successful commit (`transaction.on_commit()`), broadcasts `booking.updated` over Channels $\rightarrow$ connected clients update state in real-time.
3. **Why not a `post_save` signal?**
   - A signal cannot discern *why* `save()` was invoked (seed scripts, admin updates, batch recalculations). An explicit service function ensures that status lifecycle transitions are unambiguous business events.
4. **Why derive mechanic counters instead of storing them?**
   - Storing derived counters introduces dual sources of truth that can drift. Calculating operational status dynamically from active non-terminal bookings ensures 100% accuracy.
5. **How is real-time resilience handled?**
   - The React frontend connects to Daphne via WebSockets with heartbeat pings and exponential reconnects. If WebSocket connectivity is blocked or unavailable, the UI automatically falls back to 12s polling without breaking the user experience.

---

## 9. Security Scope & Production Boundaries

> **Assignment Scope Note:** In accordance with the technical assignment brief, authentication and role-based access control (RBAC) are intentionally excluded to allow frictionless evaluation of the live dashboard and API endpoints. The core booking workflow is designed with production-oriented integrity controls, including atomic transactions, row-level locking, database constraints, and post-commit real-time events. In a commercial deployment, all operational mutation endpoints (`/transition/`, `/assign/`) would require authenticated operator sessions, and the `/demo/simulate/` endpoint would be gated behind staff permissions or disabled.

---

## 10. AI Usage Disclosure
In accordance with engineering integrity standards:
- **Tools Used:** Antigravity AI assistant for initial scaffolding, test case generation, and schema verification.
- **Human Oversight:** Architectural design, non-overlapping attention engine rules, state machine transitions, and derived operational status logic were verified and reviewed line by line.
