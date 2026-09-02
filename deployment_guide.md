# Production Deployment Guide — Instant Mechanic LiveOps Dashboard

**Recommended Deployment Stack:**  
- **Database:** Supabase PostgreSQL  
- **Backend (ASGI + Channels):** Render (Web Service)  
- **Frontend:** Vercel (React + Vite)  

---

## 1. Supabase PostgreSQL Setup

1. Create a project at [supabase.com](https://supabase.com).
2. Navigate to **Project Settings** → **Database** → **Connection string** → **URI**.
3. Copy your URI connection string. It will follow this format:
   ```env
   DATABASE_URL=postgresql://postgres:<YOUR_PASSWORD>@db.<YOUR_PROJECT_REF>.supabase.co:5432/postgres?sslmode=require
   ```

> **Note on Special Characters in Passwords:** If your database password contains special characters (like `@`, `#`, `$`, `%`), make sure to URL-encode them in `DATABASE_URL` (e.g., `@` becomes `%40`). Django's database parser will automatically decode it upon connection.

---

## 2. Render Backend Deployment (Django + Daphne ASGI)

Render provides free/standard Linux environments with native HTTPS and WebSocket support.

### Step-by-Step Render Setup:

1. Log into [Render Dashboard](https://dashboard.render.com/) and click **New +** → **Web Service**.
2. Connect your GitHub repository: `https://github.com/Chandradeep05/instant-mechanic-assignment`
3. Configure the service settings:
   - **Name:** `instant-mechanic-api`
   - **Region:** Singapore or Frankfurt (close to Delhi NCR / India)
   - **Branch:** `main`
   - **Root Directory:** `backend`
   - **Runtime:** `Python 3`
   - **Build Command:**
     ```bash
     pip install -r requirements.txt && python manage.py migrate && python manage.py seed_data
     ```
   - **Start Command:**
     ```bash
     daphne -b 0.0.0.0 -p $PORT core.asgi:application
     ```

4. **Environment Variables (under "Environment" tab):**

| Key | Value | Notes |
|---|---|---|
| `DEBUG` | `False` | Production fail-closed mode |
| `DJANGO_SECRET_KEY` | *(Generate a 50+ char random string)* | E.g. `python -c "import secrets; print(secrets.token_hex(50))"` |
| `ALLOWED_HOSTS` | `<YOUR_RENDER_URL_WITHOUT_HTTPS>,<YOUR_VERCEL_URL_WITHOUT_HTTPS>` | E.g. `instant-mechanic-api.onrender.com,instant-mechanic.vercel.app` |
| `DATABASE_URL` | `postgresql://postgres:<PASSWORD>@db.<PROJECT_REF>.supabase.co:5432/postgres?sslmode=require` | Your Supabase connection string |
| `CORS_ALLOWED_ORIGINS` | `https://<YOUR_VERCEL_APP_URL>` | E.g. `https://instant-mechanic.vercel.app` |

5. Click **Create Web Service**.
6. When the build finishes, your backend will be live at `https://<YOUR_RENDER_APP>.onrender.com`.
   - Test Swagger UI: `https://<YOUR_RENDER_APP>.onrender.com/api/docs/`
   - Test Overview API: `https://<YOUR_RENDER_APP>.onrender.com/api/v1/dashboard/overview/`

---

## 3. Vercel Frontend Deployment (React + Vite)

1. Go to [Vercel Dashboard](https://vercel.com/dashboard) → **Add New...** → **Project**.
2. Import `Chandradeep05/instant-mechanic-assignment`.
3. Configure project:
   - **Framework Preset:** `Vite`
   - **Root Directory:** `frontend`
   - **Build Command:** `npm run build`
   - **Output Directory:** `dist`

4. **Environment Variables:**

| Variable | Value | Description |
|---|---|---|
| `VITE_API_URL` | `https://<YOUR_RENDER_APP>.onrender.com/api/v1` | Render backend REST API endpoint |
| `VITE_WS_URL` | `wss://<YOUR_RENDER_APP>.onrender.com/ws/operations/` | Render backend WebSocket endpoint (`wss://` for secure WS) |

5. Click **Deploy**.
6. Once deployed, copy your Vercel URL (e.g., `https://instant-mechanic.vercel.app`) and ensure it matches the `CORS_ALLOWED_ORIGINS` and `ALLOWED_HOSTS` in your Render backend settings.

---

## 4. First-Time Verification & Smoke Test Checklist

Once both services are deployed:

- [x] **Database Migration & Seed:** Automatically executed during Render build (`python manage.py migrate && python manage.py seed_data`).
- [x] **Dashboard Overview:** KPI cards load with revenue in ₹ and active operational metrics.
- [x] **Requires Attention Panel:** Headline CRITICAL/HIGH alerts show correct ₹ prices consistent with the service catalog.
- [x] **WebSocket Live Stream:** Top-right connection indicator shows `LIVE` (green) over `wss://`.
- [x] **Mechanic Dispatch:** Opening any `PENDING` booking allows dispatching from all 25 mechanics via the dropdown.
- [x] **Simulation Trigger:** Clicking "Simulate Live Activity" advances state and broadcasts updates in real-time.
