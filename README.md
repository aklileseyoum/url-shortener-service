# URL Shortener Service

A FastAPI-based URL shortener microservice with user accounts, tagging, and click analytics.

## Features

**Core**
- Shorten long URLs into random 6-character codes, or a user-chosen `custom_alias`
- Redirect from short codes to original URLs, with click tracking (increments `click_count`, logs a `Click` record)
- URL validation (rejects malformed/unsafe input)
- PostgreSQL storage via SQLAlchemy ORM, with Alembic migrations
- Automatic retry on short-code collisions
- Fully containerized with Docker Compose

**Data model**
- `User`, `URL`, `Click`, `Tag` models with real relationships: one-to-many (`User → URL`, `URL → Click`) and many-to-many (`URL ↔ Tag`), cascading deletes, indexes on `short_code` and `created_at`
- Alembic migration generated and applied for the full schema
- Custom query functions (managers): `active_urls()`, `expired_urls()`, `popular_urls()`, plus an aggregation query (`clicks_by_country()`)
- Eager loading (`selectinload`/`joinedload`) applied to avoid N+1 queries on relationships
- A small pytest suite covering the query functions

**Ownership**
- Simple email-based user registration — no password/JWT yet
- URLs belong to a user (`owner_id`); list, get-details, update, and delete all check ownership and reject (403) if the requesting email doesn't match
- Tags: create a tag, attach an existing tag to one of your own URLs (many-to-many, shared across users, ownership enforced only on the URL side)

**Application structure**
- Application factory pattern with modular routers (`urls`, `users`, `tags`)
- Dependency-injected service layer (`UrlShortenerService`)
- Request logging middleware
- Global exception handler, environment-aware (shows real error detail in development, a generic message in production)
- Standardized success response shape (`status_code`, `status`, `message`, `data`, `timestamp`) on most endpoints
- Multi-stage Docker build

## Tech Stack
- Python 3.x + FastAPI
- SQLAlchemy ORM + Alembic (migrations)
- PostgreSQL 16
- Poetry (dependency management)
- Docker + Docker Compose (multi-stage build)
- pytest

## Setup

### Prerequisites
- Docker Desktop installed and running

### Run with Docker Compose
1. Clone this repository
2. Copy `.env.example` to `.env` and fill in values:
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

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/register` | Register a user by email |
| POST | `/api/urls` | Create a short URL (accepts optional `custom_alias`) |
| GET | `/{short_code}` | Redirects to the original URL, records a click |
| GET | `/api/urls` | List the requesting user's URLs (`email` required) |
| GET | `/api/urls/{short_code}` | Get details for one of the user's URLs |
| PUT | `/api/urls/{short_code}` | Update a URL's destination (owner only) |
| DELETE | `/api/urls/{short_code}` | Delete a URL (owner only) |
| POST | `/api/tags` | Create a tag |
| POST | `/api/urls/{short_code}/tags` | Attach an existing tag to one of the user's URLs |

### Example

**Request:**
```
POST /api/urls?email=someone@email.com&url=https://example.com
```

**Response (201):**
```json
{
  "status_code": 201,
  "status": "success",
  "message": "It was successful",
  "data": { "short_code": "aB3xY9" },
  "timestamp": "2026-11-13T19:00:00Z"
}
```

## Architecture

```
┌──────────┐       ┌───────────────────────────────┐       ┌──────────────┐
│  Client  │ ───▶ │  FastAPI App (Docker)          │ ───▶ │  PostgreSQL  │
│          │ ◀─── │  ┌───────────────────────────┐ │ ◀─── │  (Docker)    │
└──────────┘      │  │ Middleware (logging)       │ │      └──────────────┘
                   │  ├───────────────────────────┤ │
                   │  │ Routers (urls/users/tags) │ │
                   │  ├───────────────────────────┤ │
                   │  │ UrlShortenerService (DI)  │ │
                   │  ├───────────────────────────┤ │
                   │  │ SQLAlchemy models + Alembic│ │
                   │  ├───────────────────────────┤ │
                   │  │ Global exception handler  │ │
                   │  └───────────────────────────┘ │
                   └───────────────────────────────┘
```

Both services run in Docker Compose on a shared network. The app connects
to Postgres using the service name `postgres` as the host.

The app is built with the **application factory pattern**: `create_app()`
constructs the `FastAPI` instance, registers the routers, attaches the
logging middleware, and installs the global exception handler.

Database access goes through SQLAlchemy models and is wrapped in a
`UrlShortenerService` class, provided to endpoints via FastAPI's dependency
injection (`Depends`), rather than importing database functions directly
into each endpoint.

## Project Structure
```
src/url_shortener_service/
├── main.py           # create_app() factory: routers, middleware, exception handler
├── settings.py        # Environment-based configuration (incl. ENVIRONMENT flag)
├── database.py         # SQLAlchemy engine/session, Base, DATABASE_URL / LOCAL_DATABASE_URL
├── models.py            # User, URL, Click, Tag — relationships, cascades, indexes
├── queries.py             # Custom query functions (managers) and aggregation
├── services.py             # UrlShortenerService (DI-wrapped business logic)
├── schemas.py               # SuccessResponse (standardized API response shape)
└── routers/
    ├── urls.py               # /api/urls, /{short_code}
    ├── users.py                # /api/register
    └── tags.py                  # /api/tags

alembic/
└── versions/                      # Migration history

tests/
└── test_queries.py                  # pytest coverage for query functions
```

## Docker Build

The `Dockerfile` uses a **multi-stage build**:
- **Builder stage**: installs Poetry and project dependencies
- **Final stage**: copies only the installed packages and app code, leaving
  Poetry and build tooling out of the shipped image, for a smaller,
  leaner production image

