# URL Shortener Service

A FastAPI-based URL shortener microservice with JWT authentication, tiered user accounts, tagging, click analytics, a fully async data layer, and a Prometheus + Grafana observability stack.

## Features

**Core**
- Shorten long URLs into random 6-character codes, or a user-chosen `custom_alias`
- Redirect from short codes to original URLs, with click tracking (increments `click_count`, logs a `Click` record with IP-based geolocation)
- URL validation (rejects malformed/unsafe input)
- PostgreSQL storage via async SQLAlchemy (`asyncpg`), with Alembic migrations
- Automatic retry on short-code collisions, plus a creation-time check preventing a `custom_alias` from colliding with any existing `short_code` or `custom_alias`
- Fully containerized with Docker Compose (app, PostgreSQL, Prometheus, Grafana)

**Data model**
- `User`, `URL`, `Click`, `Tag`, `RefreshToken` models with real relationships: one-to-many (`User → URL`, `URL → Click`) and many-to-many (`URL ↔ Tag`), cascading deletes, indexes on `short_code` and `created_at`
- `URL.clicks` uses `cascade="all, delete-orphan"` with `passive_deletes=True`, so deleting a URL lets PostgreSQL's `ON DELETE CASCADE` remove its clicks in one statement instead of the ORM loading every click first
- Alembic migrations generated and applied for the full schema
- Custom query functions (managers): `active_urls()`, `expired_urls()`, `popular_urls()`, plus aggregation queries (`clicks_by_country()`, `clicks_over_time()`, `clicks_by_country_for_url()`, `count_active_urls_for_user()`)
- Eager loading (`selectinload`/`joinedload`) on every relationship that is read, which avoids N+1 queries (and is required in async SQLAlchemy, where lazy loading raises `MissingGreenlet`)
- An async pytest suite covering the query functions

**Authentication & Authorization**
- JWT-based authentication (`pyjwt`), with passwords hashed using `pwdlib` (Argon2)
- Password verification runs in a threadpool (`run_in_threadpool`), because Argon2 is deliberately slow CPU work and would otherwise block the event loop for every other request
- Register, login (returns access + refresh tokens), and refresh endpoints
- `get_current_user` dependency protects every URL/tag endpoint, so no request can act as another user
- **Refresh token rotation**: each call to `/api/refresh` issues a brand-new access + refresh token pair and immediately revokes the old refresh token (tracked in a `RefreshToken` table), so a reused/stolen refresh token is rejected on its next use
- Rate limiting on login (3 attempts/minute via `slowapi`) to slow brute-force attempts
- Ownership checks: list, get-details, update, and delete all verify the requesting user owns the URL, rejecting with 403 otherwise

**Tiered access**
- Free tier: capped at 10 active URLs, no custom aliases, no analytics access
- Premium tier: unlimited URLs, custom aliases allowed, full analytics access
- Tier is set server-side only (never client-controlled at registration); upgrading a user to Premium is currently a manual/admin action

**Analytics (Premium only)**
- `GET /api/v1/analytics/{short_code}` returns click time-series (clicks per day) and clicks-by-country for a URL
- Country/city data comes from a real IP geolocation lookup (`ip-api.com` via an async `httpx.AsyncClient`) performed on each click. It is fully implemented, but only returns real data for genuine public IPs. Local/Docker testing shows `null` country/city values, since local request IPs aren't publicly geolocatable. This is expected behavior, not a bug.

**Operations**
- Fully async data layer (`AsyncSession`, `asyncpg`)
- Prometheus metrics at `/metrics` and a Grafana dashboard (see [Monitoring](#monitoring))
- Liveness (`/health`) and readiness (`/ready`) endpoints, plus a Kubernetes manifest (see [Deployment Notes](#deployment-notes))

**Application structure**
- Application factory pattern with modular routers (`urls`, `users`, `tags`, `health`)
- Dependency-injected service layer (`UrlShortenerService`, `UserService`)
- Request logging middleware
- Global exception handler, environment-aware (shows real error detail in development, a generic message in production)
- Standardized success response shape (`status_code`, `status`, `message`, `data`, `timestamp`) on most endpoints
- Multi-stage Docker build; secrets are passed at runtime via `env_file` and never copied into the image (`.dockerignore` excludes `.env`)

## Tech Stack
- Python 3.14 + FastAPI (served by Uvicorn via `fastapi run`)
- SQLAlchemy 2.x (async) + `asyncpg` + Alembic (async env)
- PostgreSQL 16
- `pyjwt` (JWT), `pwdlib[argon2]` (password hashing), `slowapi` (rate limiting), `httpx` (async HTTP client for IP geolocation)
- `prometheus-fastapi-instrumentator`, Prometheus, Grafana
- Poetry (dependency management)
- Docker + Docker Compose (multi-stage build)
- pytest + `pytest-asyncio`; `cProfile` + `snakeviz` for profiling
- Ruff, mypy, Black via pre-commit

## Setup

### Prerequisites
- Docker Desktop installed and running

### Run with Docker Compose
1. Clone this repository
2. Copy `.env.example` to `.env` and fill in values (including a real `SECRET_KEY`; generate one with `poetry run python -c "import secrets; print(secrets.token_hex(32))"`):
   ```
   cp .env.example .env
   ```
3. Start everything:
   ```
   docker compose up -d --build
   ```
4. Apply migrations (see [Database migrations](#database-migrations))
5. Services:
   - App: `http://localhost:8000` (interactive docs at `/docs`)
   - Prometheus: `http://localhost:9090`
   - Grafana: `http://localhost:3000` (default login `admin` / `admin`, you're asked to change it on first login)
6. Follow the app logs:
   ```
   docker compose logs -f app
   ```

### Run locally (without Docker)
1. Install dependencies: `poetry install`
2. Start Postgres only: `docker compose up -d postgres`
3. Point the app at the local port (environment variables override `.env`). In PowerShell:
   ```
   $env:POSTGRES_HOST="localhost"; $env:POSTGRES_PORT="5433"
   ```
4. Run the app: `poetry run fastapi dev`

### Database migrations
```
poetry run alembic upgrade head
```
Alembic and local scripts connect via `LOCAL_DATABASE_URL` (host `localhost`), while the app running inside Docker Compose connects via `DATABASE_URL` (host `postgres`, the Compose service name). Both are built from the same `.env` credentials. Both use the async `postgresql+asyncpg://` driver.

### Running tests
```
poetry run pytest
```
Tests are `async def` and run via `pytest-asyncio` (`asyncio_mode = "auto"`). They need the Postgres container running.

### Environment / Config
Set `ENVIRONMENT=development` in `.env` for verbose error detail in responses (useful while building). Use `ENVIRONMENT=production` to return a generic error message instead, hiding internal details from clients.

## API Endpoints

### Authentication

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/register` | Register a user (email + password, server-assigns Free tier) |
| POST | `/api/login` | Login, returns access + refresh JWT (rate-limited, 3/minute) |
| POST | `/api/refresh` | Exchange a valid refresh token for a new access + refresh token pair (rotates and revokes the old refresh token) |

### URL Operations (require a valid access token)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/urls` | Create a short URL (`custom_alias` requires Premium; Free tier capped at 10 active URLs) |
| GET | `/api/urls` | List the authenticated user's URLs |
| GET | `/api/urls/{short_code}` | Get details for one of the user's URLs |
| PUT | `/api/urls/{short_code}` | Update a URL's destination (owner only) |
| DELETE | `/api/urls/{short_code}` | Delete a URL and its clicks (owner only) |
| POST | `/api/tags` | Create a tag |
| POST | `/api/urls/{short_code}/tags` | Attach an existing tag to one of the user's URLs (owner only) |

### Public Interface

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/{short_code}` | Redirects to the original URL (matches `short_code` or `custom_alias`), records a click with geolocation |

### Analytics (Premium only, requires a valid access token)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/analytics/{short_code}` | Time-series clicks + clicks-by-country for a URL |

### Operations

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Liveness: returns `200 {"status": "alive"}` if the process is running. Deliberately does **not** touch the database |
| GET | `/ready` | Readiness: runs `SELECT 1`; returns `200 {"status": "ready"}`, or `503` if the database is unreachable |
| GET | `/metrics` | Prometheus metrics (request counts, latency histograms, process stats) |

`/health`, `/ready` and `/metrics` are registered **before** the URLs router, because the catch-all redirect route `/{short_code}` would otherwise match them first.

### Example

**Login request:**
```
POST /api/login
{ "email": "someone@email.com", "password": "StrongPass1" }
```

**Response (200):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer"
}
```

Subsequent requests attach the access token:
```
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
```

## Architecture

```
┌──────────┐      ┌────────────────────────────────┐       ┌──────────────┐
│  Client  │ ───▶ │  FastAPI App (Docker, async)   │ ───▶ │  PostgreSQL  │
│          │ ◀─── │  ┌──────────────────────────┐  │ ◀─── │  (asyncpg)   │
└──────────┘      │  │ Middleware (logging,     │  │       └──────────────┘
                  │  │ metrics, rate limiting)  │  │
                  │  ├──────────────────────────┤  │      ┌──────────────┐
                  │  │ Routers (health/urls/    │  │ ───▶ │ ip-api.com   │
                  │  │ users/tags)              │  │      │ (geolocation)│
                  │  ├──────────────────────────┤  │      └──────────────┘
                  │  │ get_current_user (JWT)   │  │
                  │  ├──────────────────────────┤  │
                  │  │ Services (Url/User/Tag)  │  │
                  │  ├──────────────────────────┤  │
                  │  │ SQLAlchemy models (async)│  │
                  │  ├──────────────────────────┤  │
                  │  │ Global exception handler │  │
                  │  └──────────────────────────┘  │
                  └───────────────┬────────────────┘
                                  │ /metrics (scraped every 15s)
                          ┌───────▼────────┐      ┌──────────────┐
                          │   Prometheus   │ ───▶ │   Grafana    │
                          └────────────────┘      └──────────────┘
```

All services run in Docker Compose on a shared network and reach each other by service name (`postgres`, `app`, `prometheus`), not `localhost`: inside a container, `localhost` means that container itself.

The app is built with the **application factory pattern**: `create_app()` constructs the `FastAPI` instance, sets up Prometheus instrumentation, registers the routers, attaches the logging middleware and rate limiter, and installs the global exception handler.

**Authentication flow**: a client registers, logs in to receive a short-lived access token and a longer-lived refresh token, and attaches the access token to every subsequent request. `get_current_user` decodes and verifies the token on each request and injects the real `User` into the endpoint, so no endpoint trusts a client-supplied identity. When the access token expires, the client exchanges the refresh token for a new pair via `/api/refresh`; the old refresh token is immediately revoked, so it cannot be reused even if intercepted.

Database access goes through SQLAlchemy models and is wrapped in service classes (`UrlShortenerService`, `UserService`), provided to endpoints via FastAPI's dependency injection (`Depends`), rather than importing database functions directly into each endpoint.

## Monitoring

`docker compose up` also starts Prometheus and Grafana:

- **Metrics:** the app exposes Prometheus metrics at `/metrics` (request counts, latency, process stats)
- **Prometheus:** `http://localhost:9090`, scrapes the app every 15 seconds (config in `prometheus.yml`)
- **Grafana:** `http://localhost:3000` (default login `admin` / `admin`)

To set up a dashboard in Grafana, add a Prometheus data source with the URL `http://prometheus:9090`, then create panels with these queries:

| Panel | PromQL |
|-------|--------|
| Requests per second | `sum by (handler) (rate(http_requests_total{handler!="/metrics"}[1m]))` |
| Latency (p95) | `histogram_quantile(0.95, sum by (le) (rate(http_request_duration_seconds_bucket{handler!="/metrics"}[5m])))` |

## Deployment Notes

**Server:** the container runs a single worker (`fastapi run --workers 1`). Rate limiting and metrics are kept in memory per process, so the app scales by adding containers rather than workers.

**Health checks:**
- `/health` (liveness): returns `200` while the process is running; it doesn't check the database
- `/ready` (readiness): returns `200` if the database is reachable, `503` otherwise

**Kubernetes:** `kubernetes/deployment.yaml` defines a Deployment that uses these endpoints for its startup, liveness and readiness probes, with configuration supplied through a Kubernetes Secret. It hasn't been tested on a cluster yet.

## Known Limitations
- **Access tokens can't be revoked before they expire.** Verification is stateless (signature + expiry only); only refresh tokens are revocable. Short access-token lifetimes are the mitigation
- **Geolocation only works for public IPs.** Local and Docker traffic shows `null` country/city
- **Rate limiting is in-memory and per process.** Fine for a single worker; multiple workers or replicas need a shared store (e.g. Redis)
- **Timestamps are naive UTC.** Columns are `DateTime` without time zone, and code uses `datetime.now(UTC).replace(tzinfo=None)`. Planned: migrate to `DateTime(timezone=True)`
- **The first migration assumes a pre-existing `url_table`** (created outside Alembic in an early version), so a brand-new database needs `CREATE TABLE url_table (id int);` before `alembic upgrade head`. Planned fix: `DROP TABLE IF EXISTS`
- **`User.urls` has no ORM cascade yet**, so deleting a user would hit the same `NULL` foreign-key problem fixed for `URL.clicks`. There's no delete-user endpoint today
- **Login timing can reveal registered emails** (password verification is skipped when the email doesn't exist). Planned fix: verify against a dummy hash
- **The Grafana dashboard isn't provisioned from the repo.** It lives in the `grafana_data` volume; exporting it as JSON into the repo would make it reproducible

## Project Structure
```
src/url_shortener_service/
├── main.py            # create_app(): instrumentation, routers, middleware, rate limiter, exception handler
├── settings.py        # Environment-based configuration (incl. ENVIRONMENT, SECRET_KEY)
├── database.py        # Async engine/session, Base, DATABASE_URL / LOCAL_DATABASE_URL, get_db
├── models.py          # User, URL, Click, Tag, RefreshToken: relationships, cascades, indexes
├── queries.py         # Custom async query functions (managers) and aggregation
├── auth.py            # Password hashing, JWT creation/verification, get_current_user
├── rate_limit.py      # slowapi Limiter instance
├── requests.py        # Request models (RegisterRequest, LoginRequest, RefreshRequest, etc.)
├── responses.py       # Response models (SuccessResponse, etc.)
├── services/
│   ├── url_services.py    # UrlShortenerService (URL business logic, async geolocation)
│   ├── user_services.py   # UserService (register, login, refresh with token rotation)
│   └── tag_services.py    # Tag-related business logic
└── routers/
    ├── health.py          # /health (liveness), /ready (readiness)
    ├── urls.py            # /api/urls, /{short_code}, /api/v1/analytics/{short_code}
    ├── users.py           # /api/register, /api/login, /api/refresh
    └── tags.py            # /api/tags

alembic/
├── env.py                 # Async migration environment
└── versions/              # Migration history

kubernetes/
└── deployment.yaml        # Deployment with startup, liveness and readiness probes

scripts/
└── profile_list_urls.py   # cProfile target: 50 in-process calls to GET /api/urls

docs/
└── module-8-notes.md        # Background on the async conversion, profiling, monitoring and probes

tests/
└── test_queries.py        # Async pytest coverage for query functions

prometheus.yml             # Prometheus scrape config (target app:8000)
docker-compose.yml         # app, postgres, prometheus, grafana
```

## Docker Build

The `Dockerfile` uses a **multi-stage build**:
- **Builder stage**: installs Poetry and project dependencies
- **Final stage**: copies only the installed packages and app code, leaving Poetry and build tooling out of the shipped image, for a smaller, leaner production image

`.dockerignore` keeps `.env`, virtual environments, caches and `.git` out of the build context, so secrets are never baked into an image layer. The app receives its configuration at runtime through `env_file: .env` in `docker-compose.yml`.