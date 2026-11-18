# URL Shortener Service

A FastAPI-based URL shortener microservice with JWT authentication, tiered user accounts, tagging, and click analytics.

## Features

**Core**
- Shorten long URLs into random 6-character codes, or a user-chosen `custom_alias`
- Redirect from short codes to original URLs, with click tracking (increments `click_count`, logs a `Click` record with IP-based geolocation)
- URL validation (rejects malformed/unsafe input)
- PostgreSQL storage via SQLAlchemy ORM, with Alembic migrations
- Automatic retry on short-code collisions, plus a creation-time check preventing a `custom_alias` from colliding with any existing `short_code` or `custom_alias`
- Fully containerized with Docker Compose

**Data model**
- `User`, `URL`, `Click`, `Tag`, `RefreshToken` models with real relationships: one-to-many (`User → URL`, `URL → Click`) and many-to-many (`URL ↔ Tag`), cascading deletes, indexes on `short_code` and `created_at`
- Alembic migrations generated and applied for the full schema
- Custom query functions (managers): `active_urls()`, `expired_urls()`, `popular_urls()`, plus aggregation queries (`clicks_by_country()`, `clicks_over_time()`, `clicks_by_country_for_url()`, `count_active_urls_for_user()`)
- Eager loading (`selectinload`/`joinedload`) applied to avoid N+1 queries on relationships
- A small pytest suite covering the query functions

**Authentication & Authorization**
- JWT-based authentication (`pyjwt`), with passwords hashed using `pwdlib` (Argon2)
- Register, login (returns access + refresh tokens), and refresh endpoints
- `get_current_user` dependency protects every URL/tag endpoint — no request can act as another user
- **Refresh token rotation**: each call to `/api/refresh` issues a brand-new access + refresh token pair and immediately revokes the old refresh token (tracked in a `RefreshToken` table), so a reused/stolen refresh token is rejected on its next use
- Rate limiting on login (3 attempts/minute via `slowapi`) to slow brute-force attempts
- Ownership checks: list, get-details, update, and delete all verify the requesting user owns the URL, rejecting with 403 otherwise

**Tiered access**
- Free tier: capped at 10 active URLs, no custom aliases, no analytics access
- Premium tier: unlimited URLs, custom aliases allowed, full analytics access
- Tier is set server-side only (never client-controlled at registration) — upgrading a user to Premium is currently a manual/admin action

**Analytics (Premium only)**
- `GET /api/v1/analytics/{short_code}` returns click time-series (clicks per day) and clicks-by-country for a URL
- Country/city data comes from a real IP geolocation lookup (`ip-api.com` via `httpx`) performed on each click — this is fully implemented and functional, but only returns real data for genuine public IPs. Local/Docker testing will show `null` country/city values, since local request IPs aren't publicly geolocatable. This is expected behavior, not a bug.

**Application structure**
- Application factory pattern with modular routers (`urls`, `users`, `tags`)
- Dependency-injected service layer (`UrlShortenerService`, `UserService`)
- Request logging middleware
- Global exception handler, environment-aware (shows real error detail in development, a generic message in production)
- Standardized success response shape (`status_code`, `status`, `message`, `data`, `timestamp`) on most endpoints
- Multi-stage Docker build

## Tech Stack
- Python 3.x + FastAPI
- SQLAlchemy ORM + Alembic (migrations)
- PostgreSQL 16
- `pyjwt` (JWT), `pwdlib[argon2]` (password hashing), `slowapi` (rate limiting), `httpx` (async HTTP client, used for IP geolocation)
- Poetry (dependency management)
- Docker + Docker Compose (multi-stage build)
- pytest

## Setup

### Prerequisites
- Docker Desktop installed and running

### Run with Docker Compose
1. Clone this repository
2. Copy `.env.example` to `.env` and fill in values (including a real `SECRET_KEY` — generate one with `poetry run python -c "import secrets; print(secrets.token_hex(32))"`):
   ```
   cp .env.example .env
   ```
3. Start everything:
   ```
   docker compose up --build
   ```
4. App is available at `http://localhost:8000`
5. Interactive docs at `http://localhost:8000/docs`

### Run locally (without Docker)
1. Install dependencies: `poetry install`
2. Start Postgres only: `docker compose up postgres -d`
3. Run the app: `poetry run fastapi dev`

### Database migrations
```
poetry run alembic upgrade head
```
Alembic and local scripts connect via `LOCAL_DATABASE_URL` (host `localhost`), while the app running inside Docker Compose connects via `DATABASE_URL` (host `postgres`, the Compose service name). Both are built from the same `.env` credentials.

### Running tests
```
poetry run pytest tests/
```

### Environment / Config
Set `ENVIRONMENT=development` in `.env` for verbose error detail in responses (useful while building). Use `ENVIRONMENT=production` to return a generic error message instead, hiding internal details from clients.

## API Endpoints

### Authentication

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/register` | Register a user (email + password, server-assigns Free tier) |
| POST | `/api/login` | Login — returns access + refresh JWT (rate-limited, 3/minute) |
| POST | `/api/refresh` | Exchange a valid refresh token for a new access + refresh token pair (rotates and revokes the old refresh token) |

### URL Operations (require a valid access token)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/urls` | Create a short URL (`custom_alias` requires Premium; Free tier capped at 10 active URLs) |
| GET | `/api/urls` | List the authenticated user's URLs |
| GET | `/api/urls/{short_code}` | Get details for one of the user's URLs |
| PUT | `/api/urls/{short_code}` | Update a URL's destination (owner only) |
| DELETE | `/api/urls/{short_code}` | Delete a URL (owner only) |
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
┌──────────┐      ┌───────────────────────────────┐        ┌──────────────┐
│  Client  │ ───▶ │  FastAPI App (Docker)          │ ───▶ │  PostgreSQL  │
│          │ ◀─── │  ┌───────────────────────────┐ │ ◀─── │  (Docker)    │
└──────────┘       │  │ Middleware (logging,      │ │      └──────────────┘
                   │  │ rate limiting)            │ │
                   │  ├───────────────────────────┤ │
                   │  │ Routers (urls/users/tags) │ │
                   │  ├───────────────────────────┤ │
                   │  │ get_current_user (JWT)    │ │      ┌──────────────┐
                   │  ├───────────────────────────┤ │ ───▶│ ip-api.com   │
                   │  │ Services (Url/User)       │ │      │ (geolocation)│
                   │  ├───────────────────────────┤ │      └──────────────┘
                   │  │ SQLAlchemy models + Alembic│ │
                   │  ├───────────────────────────┤ │
                   │  │ Global exception handler  │ │
                   │  └───────────────────────────┘ │
                   └───────────────────────────────┘
```

Both services run in Docker Compose on a shared network. The app connects to Postgres using the service name `postgres` as the host.

The app is built with the **application factory pattern**: `create_app()` constructs the `FastAPI` instance, registers the routers, attaches the logging middleware and rate limiter, and installs the global exception handler.

**Authentication flow**: a client registers, logs in to receive a short-lived access token and a longer-lived refresh token, and attaches the access token to every subsequent request. `get_current_user` decodes and verifies the token on each request and injects the real `User` into the endpoint — no endpoint trusts a client-supplied identity. When the access token expires, the client exchanges the refresh token for a new pair via `/api/refresh`; the old refresh token is immediately revoked, so it cannot be reused even if intercepted.

Database access goes through SQLAlchemy models and is wrapped in service classes (`UrlShortenerService`, `UserService`), provided to endpoints via FastAPI's dependency injection (`Depends`), rather than importing database functions directly into each endpoint.

## Project Structure
```
src/url_shortener_service/
├── main.py            # create_app() factory: routers, middleware, rate limiter, exception handler
├── settings.py         # Environment-based configuration (incl. ENVIRONMENT, SECRET_KEY)
├── database.py          # SQLAlchemy engine/session, Base, DATABASE_URL / LOCAL_DATABASE_URL
├── models.py             # User, URL, Click, Tag, RefreshToken — relationships, cascades, indexes
├── queries.py              # Custom query functions (managers) and aggregation
├── auth.py                  # Password hashing, JWT creation/verification, get_current_user
├── rate_limit.py              # slowapi Limiter instance
├── requests.py                 # Request models (RegisterRequest, LoginRequest, RefreshRequest, etc.)
├── responses.py                  # Response models (SuccessResponse, etc.)
├── services/
│   ├── url_services.py              # UrlShortenerService (URL business logic)
│   ├── user_services.py              # UserService (register, login, refresh — with token rotation)
│   └── tag_services.py                # Tag-related business logic
└── routers/
    ├── urls.py                       # /api/urls, /{short_code}, /api/v1/analytics/{short_code}
    ├── users.py                        # /api/register, /api/login, /api/refresh
    └── tags.py                           # /api/tags

alembic/
└── versions/                             # Migration history

tests/
└── test_queries.py                         # pytest coverage for query functions
```

## Docker Build

The `Dockerfile` uses a **multi-stage build**:
- **Builder stage**: installs Poetry and project dependencies
- **Final stage**: copies only the installed packages and app code, leaving Poetry and build tooling out of the shipped image, for a smaller, leaner production image
