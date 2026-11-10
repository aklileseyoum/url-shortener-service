# URL Shortener Service

A FastAPI-based URL shortener microservice (Module 5: Foundation + Docker).

## Features
- Shorten long URLs into random 6-character codes
- Redirect from short codes to original URLs
- URL validation (rejects malformed/unsafe input)
- PostgreSQL storage with unique constraint on short codes
- Automatic retry on short-code collisions
- Application factory pattern with modular routers
- Dependency-injected service layer (`UrlShortenerService`)
- Request logging middleware
- Global exception handler with environment-aware error detail
  (shows real error messages in development, generic message in production)
- Multi-stage Docker build for a smaller, leaner production image
- Fully containerized with Docker Compose

## Tech Stack
- Python 3.x + FastAPI
- PostgreSQL 16
- Poetry (dependency management)
- Docker + Docker Compose (multi-stage build)

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

### Environment / Config
Set `ENVIRONMENT=development` in `.env` for verbose error detail in responses
(useful while building). Use `ENVIRONMENT=production` to return a generic
error message instead, hiding internal details from clients.

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/urls` | Accepts a URL, returns a short code |
| GET | `/{short_code}` | Redirects to the original URL |

### Example

**Request:**
```
POST /api/urls?url=https://example.com
```

**Response (201):**
```json
{
  "short_code": "aB3xY9",
  "message": "It was successful"
}
```

**Redirect:**
```
GET /aB3xY9  →  302 redirect to https://example.com
```

## Architecture

```
┌──────────┐       ┌───────────────────────────────┐       ┌──────────────┐
│  Client  │ ───▶ │  FastAPI App (Docker)          │ ───▶ │  PostgreSQL  │
│          │ ◀─── │  ┌───────────────────────────┐ │ ◀─── │  (Docker)    │
└──────────┘       │  │ Middleware (logging)      │ │      └──────────────┘
                   │  ├───────────────────────────┤ │
                   │  │ Router (/api/urls)        │ │
                   │  ├───────────────────────────┤ │
                   │  │ UrlShortenerService (DI)  │ │
                   │  ├───────────────────────────┤ │
                   │  │ Global exception handler  │ │
                   │  └───────────────────────────┘ │
                   └─────────────────────────────── ┘
```

Both services run in Docker Compose on a shared network. The app connects
to Postgres using the service name `postgres` as the host.

The app is built with the **application factory pattern**: `create_app()`
constructs the `FastAPI` instance, registers the URL router, attaches the
logging middleware, and installs the global exception handler, rather than
configuring everything at module import time.

Database access is wrapped in a `UrlShortenerService` class and provided to
endpoints via FastAPI's dependency injection (`Depends`), rather than
importing database functions directly into each endpoint.

## Project Structure
```
src/url_shortener_service/
├── main.py          # create_app() factory: router, middleware, exception handler
├── settings.py       # Environment-based configuration (incl. ENVIRONMENT flag)
├── db.py             # Database connection pool (get_connection/release_connection)
├── services.py        # UrlShortenerService (DI-wrapped DB logic) + generate_code()
└── routers/
    └── urls.py        # /api/urls and /{short_code} endpoints
```

## Docker Build

The `Dockerfile` uses a **multi-stage build**:
- **Builder stage**: installs Poetry and project dependencies
- **Final stage**: copies only the installed packages and app code, leaving
  Poetry and build tooling out of the shipped image, for a smaller,
  leaner production image
