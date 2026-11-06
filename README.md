# URL Shortener Service

A FastAPI-based URL shortener microservice (Module 5: Foundation + Docker).

## Features
- Shorten long URLs into random 6-character codes
- Redirect from short codes to original URLs
- URL validation (rejects malformed/unsafe input)
- PostgreSQL storage with unique constraint on short codes
- Fully containerized with Docker Compose

## Tech Stack
- Python 3.x + FastAPI
- PostgreSQL 16
- Poetry (dependency management)
- Docker + Docker Compose

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
┌──────────┐      ┌─────────────────┐      ┌──────────────┐
│  Client  │ ───▶ │  FastAPI App     │ ───▶ │  PostgreSQL  │
│          │ ◀─── │  (Docker)        │ ◀─── │  (Docker)    │
└──────────┘      └─────────────────┘      └──────────────┘
```

Both services run in Docker Compose on a shared network. The app connects
to Postgres using the service name `postgres` as the host.

## Project Structure
```
src/url_shortener_service/
├── main.py       # FastAPI app and endpoints
├── db.py         # Database connection pool and queries
└── settings.py   # Environment-based configuration
```
